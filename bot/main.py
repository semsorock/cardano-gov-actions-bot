"""Cardano Governance Actions Bot — webhook entry point.

A Blockfrost block webhook (``POST /``) drives every scan. On each webhook the
bot:

1. Scans the governance *proposals* and *committee-votes* feeds (Blockfrost),
   processing any items newer than the persisted watermarks — this is the
   primary discovery step; a failure here returns ``500`` so Blockfrost retries.
2. Reads the block's transaction CBOR to accumulate treasury donations, and
   posts a per-epoch summary when an epoch boundary is crossed — secondary work
   that never fails the webhook.

Duplicate / out-of-order deliveries are safe: feed watermarks bound the scan
and per-item idempotency keys (in Firestore) prevent double-posting.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from bot.blockfrost import client as bf_client
from bot.blockfrost.cbor import extract_block_donations
from bot.blockfrost.client import MAX_PAGE_SIZE, BlockfrostError, BlockfrostNotFound
from bot.blockfrost.committee import CommitteeSnapshot, parse_committee_snapshot
from bot.blockfrost.feeds import collect_new_items
from bot.blockfrost.mapping import (
    build_cc_vote,
    build_gov_action,
    committee_vote_key,
    proposal_key,
)
from bot.cc_profiles import get_x_handle_for_voter_hash
from bot.config import config
from bot.logging import get_logger, setup_logging
from bot.metadata.fetcher import fetch_metadata, sanitise_url
from bot.models import GovAction, TreasuryDonation
from bot.rationale_validator import validate_cc_vote_rationale, validate_gov_action_rationale
from bot.state_store import (
    ensure_donation_start_epoch,
    get_action_tweet_id,
    get_checkpoint,
    get_committee_snapshot,
    get_donation_start_epoch,
    get_feed_watermark,
    get_treasury_epoch,
    is_action_archived,
    is_cc_vote_archived,
    mark_cc_vote_archived,
    mark_treasury_epoch_summarized,
    record_treasury_donations,
    save_action_tweet_id,
    save_committee_snapshot,
    set_checkpoint,
    set_feed_watermark,
)
from bot.thresholds import (
    GovThresholds,
    build_threshold_context,
    classify_parameters,
    compute_thresholds,
)
from bot.twitter.client import post_quote_tweet, post_tweet
from bot.twitter.formatter import (
    format_cc_vote_tweet,
    format_gov_action_tweet,
    format_treasury_donations_tweet,
)
from bot.webhook_auth import verify_webhook_signature

setup_logging()
logger = get_logger("main")

# Validate config at startup — fail fast on missing required vars.
config.validate()

CHECKPOINT_NAME = "blockfrost_main"
PROPOSALS_FEED = "governance_proposals"
CC_VOTES_FEED = "committee_votes"

# Per-process caches (safe across webhooks: epoch params are effectively
# immutable, committee snapshots change rarely and are keyed by epoch).
_epoch_params_cache: dict[int, dict] = {}
_committee_cache: dict[int, dict] = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Own the shared async Blockfrost client for the app's lifetime."""
    try:
        yield
    finally:
        await bf_client.close_client()


app = FastAPI(lifespan=lifespan)


# ---------------------------------------------------------------------------
# Threshold context assembly
# ---------------------------------------------------------------------------


async def _current_committee(epoch: int) -> dict | None:
    """Fetch, cache and prospectively persist the current committee snapshot."""
    if epoch in _committee_cache:
        return _committee_cache[epoch]
    try:
        data = await bf_client.get_client().get_committee()
    except BlockfrostNotFound:
        return None
    _committee_cache[epoch] = data
    save_committee_snapshot(epoch, data)
    return data


async def _epoch_parameters(epoch: int) -> dict | None:
    if epoch in _epoch_params_cache:
        return _epoch_params_cache[epoch]
    try:
        params = await bf_client.get_client().get_epoch_parameters(epoch)
    except BlockfrostNotFound:
        return None
    _epoch_params_cache[epoch] = params
    return params


async def _resolve_inclusion_epoch(item: dict) -> int | None:
    """Resolve a proposal's inclusion epoch via its transaction's block."""
    client = bf_client.get_client()
    try:
        tx = await client.get_tx(item["tx_hash"])
        block_ref = tx.get("block_height") or tx.get("block")
        if block_ref is None:
            return None
        block = await client.get_block(block_ref)
        return block.get("epoch")
    except (BlockfrostError, KeyError):
        logger.warning("Could not resolve inclusion epoch for proposal %s", item.get("tx_hash", "")[:8])
        return None


async def _committee_for_epoch(epoch: int, *, epoch_hint: int | None) -> dict | None:
    """Return the committee snapshot to use for ``epoch``.

    Live (``epoch == epoch_hint``): the current snapshot, which is also
    persisted prospectively. Historical: the snapshot we persisted for that
    epoch, or ``None`` (Blockfrost has no committee-by-epoch query, so the
    threshold line is omitted when no snapshot was captured).
    """
    if epoch_hint is not None and epoch == epoch_hint:
        return await _current_committee(epoch)
    return get_committee_snapshot(epoch)


async def _threshold_context_for(item: dict, epoch_hint: int | None):
    epoch = epoch_hint if epoch_hint is not None else await _resolve_inclusion_epoch(item)
    if epoch is None:
        return None
    params = await _epoch_parameters(epoch)
    if not params:
        return None
    committee_data = await _committee_for_epoch(epoch, epoch_hint=epoch_hint)
    snapshot = parse_committee_snapshot(committee_data)
    if snapshot is None:
        return None
    return build_threshold_context(
        params,
        committee_quorum=snapshot.quorum,
        committee_dissolved=snapshot.is_dissolved,
        committee_active_size=snapshot.active_member_count(epoch),
    )


async def _resolve_thresholds(action: GovAction, item: dict, epoch_hint: int | None) -> GovThresholds | None:
    """Best-effort thresholds; returns ``None`` so the line is dropped on failure."""
    try:
        context = await _threshold_context_for(item, epoch_hint)
        if context is None:
            return None
        param_groups = None
        if action.action_type == "ParameterChange":
            try:
                params = await bf_client.get_client().get_proposal_parameters(action.tx_hash, action.index)
                param_groups = classify_parameters(params.get("parameters"))
            except BlockfrostNotFound:
                param_groups = None
        return compute_thresholds(action.action_type, context, param_groups=param_groups)
    except BlockfrostError:
        logger.warning("Threshold context unavailable for %s — omitting threshold line", action.tx_hash[:8])
        return None


# ---------------------------------------------------------------------------
# Governance action processing
# ---------------------------------------------------------------------------


async def _resolve_proposal_metadata(tx_hash: str, cert_index: int) -> tuple[str, dict | None]:
    """Return the proposal's anchor URL and metadata JSON.

    Prefers Blockfrost's already-validated ``json_metadata``; falls back to
    fetching the anchor over IPFS/HTTP ourselves when Blockfrost has none.
    """
    try:
        meta = await bf_client.get_client().get_proposal_metadata(tx_hash, cert_index)
    except BlockfrostNotFound:
        return "", None

    url = meta.get("url") or ""
    json_metadata = meta.get("json_metadata")
    if isinstance(json_metadata, dict):
        return url, json_metadata
    if url:
        return url, fetch_metadata(sanitise_url(url))
    return url, None


async def _process_one_proposal(item: dict, *, epoch_hint: int | None, block_no: int | None) -> None:
    tx_hash = item["tx_hash"]
    cert_index = item["cert_index"]

    raw_url, metadata = await _resolve_proposal_metadata(tx_hash, cert_index)
    action = build_gov_action(
        tx_hash=tx_hash,
        cert_index=cert_index,
        governance_type=item.get("governance_type", ""),
        raw_url=raw_url,
    )

    warnings = validate_gov_action_rationale(metadata)
    for w in warnings:
        logger.warning("CIP-0108 validation [%s#%s]: %s", tx_hash[:8], cert_index, w)

    thresholds = await _resolve_thresholds(action, item, epoch_hint)

    tweet = format_gov_action_tweet(action, metadata, thresholds)
    tweet_id = post_tweet(tweet)
    save_action_tweet_id(tx_hash, cert_index, tweet_id or "", source_block=block_no)


async def _process_new_proposals(*, epoch_hint: int | None, block_no: int | None) -> None:
    client = bf_client.get_client()
    watermark = get_feed_watermark(PROPOSALS_FEED)
    scan = await collect_new_items(
        lambda page: client.get_proposals(page=page),
        watermark,
        proposal_key,
    )

    if scan.bootstrapped:
        set_feed_watermark(PROPOSALS_FEED, scan.watermark)
        return
    if not scan.items:
        return

    for item in scan.items:
        if is_action_archived(item["tx_hash"], item["cert_index"]):
            continue
        await _process_one_proposal(item, epoch_hint=epoch_hint, block_no=block_no)

    if scan.watermark is not None:
        set_feed_watermark(PROPOSALS_FEED, scan.watermark)


# ---------------------------------------------------------------------------
# CC vote processing
# ---------------------------------------------------------------------------


async def _process_one_cc_vote(
    item: dict,
    vote_key: str,
    snapshot: CommitteeSnapshot | None,
    block_no: int | None,
) -> None:
    hot_id = item.get("voter_hot_id", "")
    cold_hex = snapshot.cold_hex_for_hot(hot_id) if snapshot else None
    voter_hash = cold_hex or hot_id

    vote = build_cc_vote(item, voter_cold_hex=voter_hash)

    metadata = None
    if vote.raw_url:
        metadata = fetch_metadata(sanitise_url(vote.raw_url))

    warnings = validate_cc_vote_rationale(metadata)
    for w in warnings:
        logger.warning("CIP-0136 validation [%s]: %s", voter_hash[:8], w)

    quote_id = get_action_tweet_id(vote.ga_tx_hash, vote.ga_index)
    voter_x_handle = get_x_handle_for_voter_hash(cold_hex) if cold_hex else None
    if not voter_x_handle:
        logger.info("No X handle mapping for CC voter: %s", voter_hash[:12])

    tweet = format_cc_vote_tweet(
        vote,
        metadata,
        quote_tweet_id=quote_id,
        voter_x_handle=voter_x_handle,
    )

    if quote_id:
        post_quote_tweet(tweet, quote_id)
    else:
        logger.info(
            "No tweet ID for action %s_%s — posting without quote",
            vote.ga_tx_hash[:8],
            vote.ga_index,
        )
        post_tweet(tweet)

    mark_cc_vote_archived(
        vote_key,
        ga_tx_hash=vote.ga_tx_hash,
        ga_index=vote.ga_index,
        voter_hash=voter_hash,
        source_block=block_no,
    )


async def _process_new_committee_votes(*, epoch_hint: int | None, block_no: int | None) -> None:
    client = bf_client.get_client()
    watermark = get_feed_watermark(CC_VOTES_FEED)
    scan = await collect_new_items(
        lambda page: client.get_committee_votes(page=page),
        watermark,
        committee_vote_key,
    )

    if scan.bootstrapped:
        set_feed_watermark(CC_VOTES_FEED, scan.watermark)
        return
    if not scan.items:
        return

    # The committee snapshot resolves hot→cold voter identities. A transient
    # failure degrades voter resolution rather than failing the whole webhook.
    committee_data = None
    if epoch_hint is not None:
        try:
            committee_data = await _current_committee(epoch_hint)
        except BlockfrostError:
            logger.warning("Committee snapshot unavailable — voter identities may be unresolved")
    snapshot = parse_committee_snapshot(committee_data)

    for item in scan.items:
        vote_key = committee_vote_key(item)
        if is_cc_vote_archived(vote_key):
            continue
        await _process_one_cc_vote(item, vote_key, snapshot, block_no)

    if scan.watermark is not None:
        set_feed_watermark(CC_VOTES_FEED, scan.watermark)


async def _process_governance(payload: dict) -> None:
    """Primary discovery: scan both governance feeds and process new items.

    Proposals are processed before votes so a new action's tweet exists for a
    same-scan CC vote to quote.
    """
    epoch_hint = payload.get("epoch")
    block_no = payload.get("height")
    await _process_new_proposals(epoch_hint=epoch_hint, block_no=block_no)
    await _process_new_committee_votes(epoch_hint=epoch_hint, block_no=block_no)


# ---------------------------------------------------------------------------
# Treasury donations
# ---------------------------------------------------------------------------


async def _fetch_block_donations(block_ref: str, block_no: int) -> list[TreasuryDonation]:
    client = bf_client.get_client()
    donations: list[TreasuryDonation] = []
    page = 1
    while True:
        txs = await client.get_block_txs_cbor(block_ref, page=page)
        if not txs:
            break
        donations.extend(extract_block_donations(block_no, txs))
        if len(txs) < MAX_PAGE_SIZE:
            break
        page += 1
    return donations


async def _process_block_donations(payload: dict) -> None:
    """Accumulate the current block's treasury donations for its epoch."""
    epoch = payload.get("epoch")
    block_no = payload.get("height")
    block_ref = payload.get("hash") or block_no
    tx_count = payload.get("tx_count")

    if epoch is None or block_ref is None:
        return
    if tx_count == 0:
        return

    try:
        donations = await _fetch_block_donations(block_ref, block_no or 0)
    except BlockfrostError:
        logger.warning("Failed to fetch block CBOR for donations [block=%s]", block_no)
        return

    if donations:
        logger.info("Recorded %d treasury donation(s) in block %s (epoch %s)", len(donations), block_no, epoch)
        record_treasury_donations(epoch, donations)


def _summarize_treasury_epoch(epoch: int) -> None:
    doc = get_treasury_epoch(epoch)
    if not doc or doc.get("summarized"):
        return

    donations_map = doc.get("donations") or {}
    if not donations_map:
        mark_treasury_epoch_summarized(epoch)
        return

    donations = [
        TreasuryDonation(block_no=0, tx_hash=tx_hash, amount_lovelace=int(amount))
        for tx_hash, amount in donations_map.items()
    ]
    tweet = format_treasury_donations_tweet(donations)
    post_tweet(tweet)
    mark_treasury_epoch_summarized(epoch)


def _maybe_summarize_epochs(current_epoch: int) -> None:
    """Post a donation summary for each epoch that just completed."""
    checkpoint = get_checkpoint(CHECKPOINT_NAME)
    last_epoch = checkpoint.get("last_epoch") if checkpoint else None
    if last_epoch is None or current_epoch <= last_epoch:
        return

    start_epoch = get_donation_start_epoch()
    for completed in range(last_epoch, current_epoch):
        # The epoch we cold-started in is only partially observed — skip it.
        if start_epoch is not None and completed <= start_epoch:
            continue
        logger.info("Epoch %s complete — summarising treasury donations", completed)
        _summarize_treasury_epoch(completed)


async def _process_treasury(payload: dict) -> None:
    epoch = payload.get("epoch")
    if epoch is not None:
        ensure_donation_start_epoch(epoch)
        _maybe_summarize_epochs(epoch)
    await _process_block_donations(payload)


# ---------------------------------------------------------------------------
# Webhook handler
# ---------------------------------------------------------------------------


@app.post("/")
async def handle_webhook(request: Request) -> JSONResponse:
    """Main entry point for Blockfrost webhooks."""
    # --- Signature verification ---
    raw_body = await request.body()
    signature = request.headers.get("Blockfrost-Signature")

    if not verify_webhook_signature(signature, raw_body):
        logger.warning("Webhook signature verification failed")
        return JSONResponse({"error": "Unauthorized"}, status_code=401)

    # --- Parse payload ---
    request_json = await request.json()

    logger.info("Incoming webhook")
    logger.debug("Webhook payload: %s", request_json)

    if not request_json:
        return JSONResponse({"error": "Invalid or missing JSON body"}, status_code=400)

    payload = request_json.get("payload", {})
    block_no = payload.get("height")

    if block_no is None:
        logger.warning("Missing block height in payload")
        return JSONResponse({"error": "Missing block height"}, status_code=400)

    # --- Primary discovery: governance feeds. A failure here returns 500 so
    # Blockfrost retries; watermarks are only advanced on success. ---
    try:
        await _process_governance(payload)
    except Exception:
        logger.exception("Error scanning governance feeds for block: %s", block_no)
        return JSONResponse({"error": "Internal server error"}, status_code=500)

    # --- Secondary: treasury donations + epoch summaries never fail the webhook. ---
    try:
        await _process_treasury(payload)
    except Exception:
        logger.exception("Error processing treasury donations for block: %s", block_no)

    set_checkpoint(name=CHECKPOINT_NAME, block_no=block_no, epoch_no=payload.get("epoch"))

    return JSONResponse({"status": "ok"})
