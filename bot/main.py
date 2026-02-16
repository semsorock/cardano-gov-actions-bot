"""Cardano Governance Actions Bot — webhook entry point."""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from bot.cc_profiles import get_x_handle_for_voter_hash
from bot.config import config
from bot.db.repository import (
    get_active_gov_actions,
    get_block_epoch,
    get_cc_votes,
    get_gov_actions,
    get_treasury_donations,
    get_voting_stats,
)
from bot.logging import get_logger, setup_logging
from bot.metadata.fetcher import fetch_metadata, sanitise_url
from bot.rationale_archiver import archive_cc_vote, archive_gov_action
from bot.rationale_archiver import get_action_tweet_id as get_action_tweet_id_from_github
from bot.rationale_validator import validate_cc_vote_rationale, validate_gov_action_rationale
from bot.state_store import (
    get_action_tweet_id,
    mark_cc_vote_archived,
    save_action_tweet_id,
    set_checkpoint,
)
from bot.twitter.client import post_quote_tweet, post_reply_tweet, post_tweet
from bot.twitter.formatter import (
    format_cc_vote_tweet,
    format_gov_action_tweet,
    format_treasury_donations_tweet,
    format_voting_progress_tweet,
)
from bot.webhook_auth import verify_webhook_signature

setup_logging()
logger = get_logger("main")

# Validate config at startup — fail fast on missing required vars.
config.validate()

app = FastAPI()


# ---------------------------------------------------------------------------
# Block processing
# ---------------------------------------------------------------------------


async def _process_gov_actions(block_no: int) -> None:
    actions = await get_gov_actions(block_no)

    if not actions:
        logger.info("No gov actions for block: %s", block_no)
        return

    for action in actions:
        url = sanitise_url(action.raw_url)
        metadata = fetch_metadata(url)

        # Validate rationale (non-blocking).
        warnings = validate_gov_action_rationale(metadata)
        for w in warnings:
            logger.warning("CIP-0108 validation [%s#%s]: %s", action.tx_hash[:8], action.index, w)

        tweet = format_gov_action_tweet(action, metadata)
        tweet_id = post_tweet(tweet)
        archive_gov_action(action, metadata, tweet_id=tweet_id)
        save_action_tweet_id(action.tx_hash, action.index, tweet_id or "", source_block=block_no)


async def _process_cc_votes(block_no: int) -> None:
    votes = await get_cc_votes(block_no)

    if not votes:
        logger.info("No CC vote records for block: %s", block_no)
        return

    for vote in votes:
        url = sanitise_url(vote.raw_url)
        metadata = fetch_metadata(url)

        # Validate rationale (non-blocking).
        warnings = validate_cc_vote_rationale(metadata)
        for w in warnings:
            logger.warning("CIP-0136 validation [%s]: %s", vote.voter_hash[:8], w)

        # Look up the original gov action tweet for quote-tweeting.
        quote_id = get_action_tweet_id(vote.ga_tx_hash, vote.ga_index)
        if not quote_id:
            quote_id = get_action_tweet_id_from_github(vote.ga_tx_hash, vote.ga_index)
        voter_x_handle = get_x_handle_for_voter_hash(vote.voter_hash)
        if not voter_x_handle:
            logger.warning("No X handle mapping for CC voter hash: %s", vote.voter_hash)

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

        archive_cc_vote(vote, metadata)
        mark_cc_vote_archived(
            vote.ga_tx_hash,
            vote.ga_index,
            vote.voter_hash,
            source_block=block_no,
        )


# ---------------------------------------------------------------------------
# Epoch processing
# ---------------------------------------------------------------------------


async def _process_treasury_donations(epoch_no: int) -> None:
    donations = await get_treasury_donations(epoch_no)
    logger.debug("Donations: %s", donations)

    if not donations:
        logger.info("No treasury donations for epoch: %s", epoch_no)
        return

    tweet = format_treasury_donations_tweet(donations)
    post_tweet(tweet)


async def _process_voting_progress(epoch_no: int) -> None:
    """Post voting progress updates for all active governance actions."""
    active_actions = await get_active_gov_actions(epoch_no)
    logger.info("Found %s active gov actions for epoch %s", len(active_actions), epoch_no)

    for action in active_actions:
        try:
            # Get voting statistics for this action
            stats = await get_voting_stats(
                action.tx_hash, action.index, epoch_no, action.created_epoch, action.expiration
            )

            if not stats:
                logger.warning(
                    "No voting stats for action %s_%s",
                    action.tx_hash[:8],
                    action.index,
                )
                continue

            # Format the tweet
            tweet = format_voting_progress_tweet(stats)

            # Try to get the original tweet ID to reply to it
            original_tweet_id = get_action_tweet_id(action.tx_hash, action.index)

            if original_tweet_id:
                logger.info(
                    "Posting voting progress as reply to tweet %s for action %s_%s",
                    original_tweet_id,
                    action.tx_hash[:8],
                    action.index,
                )
                post_reply_tweet(tweet, original_tweet_id)
            else:
                logger.info(
                    "No tweet ID found for action %s_%s — posting standalone",
                    action.tx_hash[:8],
                    action.index,
                )
                post_tweet(tweet)

        except Exception:
            logger.exception(
                "Error processing voting progress for action %s_%s",
                action.tx_hash[:8],
                action.index,
            )


async def _check_epoch_transition(payload: dict) -> None:
    """Detect epoch boundary and run epoch processing if one occurred."""
    current_epoch = payload.get("epoch")
    previous_block_hash = payload.get("previous_block")

    if current_epoch is None or not previous_block_hash:
        logger.debug("No epoch or previous_block in payload — skipping epoch check")
        return

    previous_epoch = await get_block_epoch(previous_block_hash)

    if previous_epoch is None:
        logger.warning("Could not find previous block %s in DB", previous_block_hash)
        return

    if current_epoch != previous_epoch:
        logger.info(
            "Epoch transition detected: %s → %s",
            previous_epoch,
            current_epoch,
        )
        # Process the completed epoch (previous_epoch).
        await _process_treasury_donations(previous_epoch)
        # Post voting progress for active actions in the new epoch.
        await _process_voting_progress(current_epoch)


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

    try:
        # Always process block events.
        await _process_gov_actions(block_no)
        await _process_cc_votes(block_no)

        # Detect epoch transitions and process if needed.
        await _check_epoch_transition(payload)
        set_checkpoint(
            name="blockfrost_main",
            block_no=block_no,
            epoch_no=payload.get("epoch"),
        )
    except Exception:
        logger.exception("Error processing webhook for block: %s", block_no)
        return JSONResponse({"error": "Internal server error"}, status_code=500)

    return JSONResponse({"status": "ok"})
