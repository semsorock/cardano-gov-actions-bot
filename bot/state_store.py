"""Persistent state helpers backed by Firestore with safe fallbacks.

Holds four kinds of runtime state:

* **Domain idempotency** — which governance actions / CC votes have already been
  processed (so duplicate or replayed webhooks never post twice).
* **Feed watermarks** — the last-seen item of each Blockfrost feed, so a scan
  only pages back as far as needed.
* **Committee snapshots** — persisted prospectively per epoch, since Blockfrost
  has no historical committee-by-epoch query.
* **Treasury donations** — per-epoch accumulation of donations seen in block
  CBOR, summarised on epoch transition.

Every helper degrades to a no-op / ``None`` when Firestore is unavailable.
"""

from __future__ import annotations

from typing import Any

from bot.config import config
from bot.logging import get_logger
from bot.models import TreasuryDonation

try:
    from google.cloud import firestore
except Exception:  # pragma: no cover - exercised via runtime fallback.
    firestore = None

logger = get_logger("state_store")

_FIRESTORE_CLIENT = None
_FIRESTORE_UNAVAILABLE_LOGGED = False

GOV_ACTION_STATE_COLLECTION = "gov_action_state"
CC_VOTE_STATE_COLLECTION = "cc_vote_state"
CHECKPOINTS_COLLECTION = "checkpoints"
FEED_WATERMARKS_COLLECTION = "feed_watermarks"
COMMITTEE_SNAPSHOTS_COLLECTION = "committee_snapshots"
TREASURY_DONATIONS_COLLECTION = "treasury_epoch_donations"


def _get_firestore_client():
    global _FIRESTORE_CLIENT  # noqa: PLW0603

    if _FIRESTORE_CLIENT is not None:
        return _FIRESTORE_CLIENT

    if firestore is None:
        _log_firestore_unavailable_once("google-cloud-firestore is not installed")
        return None

    kwargs: dict[str, Any] = {}
    if config.firestore_project_id:
        kwargs["project"] = config.firestore_project_id
    if config.firestore_database:
        kwargs["database"] = config.firestore_database

    try:
        _FIRESTORE_CLIENT = firestore.Client(**kwargs)
        return _FIRESTORE_CLIENT
    except Exception:
        _log_firestore_unavailable_once("failed to initialize Firestore client")
        logger.warning("Firestore init error", exc_info=True)
        return None


def _log_firestore_unavailable_once(reason: str) -> None:
    global _FIRESTORE_UNAVAILABLE_LOGGED  # noqa: PLW0603

    if _FIRESTORE_UNAVAILABLE_LOGGED:
        return

    logger.warning("Firestore unavailable: %s. Runtime state reads/writes will be skipped.", reason)
    _FIRESTORE_UNAVAILABLE_LOGGED = True


def _server_timestamp() -> Any | None:
    if firestore is None:
        return None
    return firestore.SERVER_TIMESTAMP


def _action_id(tx_hash: str, index: int) -> str:
    return f"{tx_hash}_{index}"


# ---------------------------------------------------------------------------
# Governance action idempotency + tweet IDs
# ---------------------------------------------------------------------------


def get_action_tweet_id(tx_hash: str, index: int) -> str | None:
    """Return the persisted action tweet ID from Firestore."""
    client = _get_firestore_client()
    if client is None:
        return None

    try:
        doc = client.collection(GOV_ACTION_STATE_COLLECTION).document(_action_id(tx_hash, index)).get()
        if not doc.exists:
            return None

        tweet_id = (doc.to_dict() or {}).get("tweet_id")
        if not tweet_id:
            return None
        return str(tweet_id).strip() or None
    except Exception:
        logger.warning("Failed to read action tweet ID from Firestore [%s_%s]", tx_hash[:8], index, exc_info=True)
        return None


def is_action_archived(tx_hash: str, index: int) -> bool:
    """Return whether a governance action has already been processed."""
    client = _get_firestore_client()
    if client is None:
        return False

    try:
        doc = client.collection(GOV_ACTION_STATE_COLLECTION).document(_action_id(tx_hash, index)).get()
        if not doc.exists:
            return False
        return bool((doc.to_dict() or {}).get("archived_action"))
    except Exception:
        logger.warning("Failed to read action state from Firestore [%s_%s]", tx_hash[:8], index, exc_info=True)
        return False


def save_action_tweet_id(tx_hash: str, index: int, tweet_id: str, source_block: int | None = None) -> None:
    """Persist action tweet ID and archived progress in Firestore."""
    client = _get_firestore_client()
    if client is None:
        return

    payload: dict[str, Any] = {"archived_action": True}
    if tweet_id.strip():
        payload["tweet_id"] = tweet_id.strip()
    if source_block is not None:
        payload["source_block"] = source_block

    timestamp = _server_timestamp()
    if timestamp is not None:
        payload["last_updated_at"] = timestamp

    try:
        client.collection(GOV_ACTION_STATE_COLLECTION).document(_action_id(tx_hash, index)).set(payload, merge=True)
    except Exception:
        logger.warning("Failed to save action state in Firestore [%s_%s]", tx_hash[:8], index, exc_info=True)


# ---------------------------------------------------------------------------
# CC vote idempotency
# ---------------------------------------------------------------------------


def is_cc_vote_archived(vote_key: str) -> bool:
    """Return whether a specific committee vote has already been processed."""
    client = _get_firestore_client()
    if client is None:
        return False

    try:
        doc = client.collection(CC_VOTE_STATE_COLLECTION).document(vote_key).get()
        if not doc.exists:
            return False
        return bool((doc.to_dict() or {}).get("archived_vote"))
    except Exception:
        logger.warning("Failed to read CC vote state from Firestore [%s]", vote_key[:16], exc_info=True)
        return False


def mark_cc_vote_archived(
    vote_key: str,
    *,
    ga_tx_hash: str,
    ga_index: int,
    voter_hash: str,
    source_block: int | None = None,
) -> None:
    """Persist CC vote archived status in Firestore, keyed by the vote identity."""
    client = _get_firestore_client()
    if client is None:
        return

    payload: dict[str, Any] = {
        "archived_vote": True,
        "ga_tx_hash": ga_tx_hash,
        "ga_index": ga_index,
        "voter_hash": voter_hash,
    }
    if source_block is not None:
        payload["source_block"] = source_block

    timestamp = _server_timestamp()
    if timestamp is not None:
        payload["last_updated_at"] = timestamp

    try:
        client.collection(CC_VOTE_STATE_COLLECTION).document(vote_key).set(payload, merge=True)
    except Exception:
        logger.warning("Failed to save CC vote state in Firestore [%s]", vote_key[:16], exc_info=True)


# ---------------------------------------------------------------------------
# Feed watermarks
# ---------------------------------------------------------------------------


def get_feed_watermark(name: str) -> str | None:
    """Return the persisted watermark for a feed, or ``None`` if unset."""
    client = _get_firestore_client()
    if client is None:
        return None

    try:
        doc = client.collection(FEED_WATERMARKS_COLLECTION).document(name).get()
        if not doc.exists:
            return None
        watermark = (doc.to_dict() or {}).get("watermark")
        return str(watermark) if watermark else None
    except Exception:
        logger.warning("Failed to read feed watermark from Firestore [%s]", name, exc_info=True)
        return None


def set_feed_watermark(name: str, watermark: str) -> None:
    """Persist the watermark for a feed."""
    client = _get_firestore_client()
    if client is None:
        return

    payload: dict[str, Any] = {"watermark": watermark}
    timestamp = _server_timestamp()
    if timestamp is not None:
        payload["updated_at"] = timestamp

    try:
        client.collection(FEED_WATERMARKS_COLLECTION).document(name).set(payload, merge=True)
    except Exception:
        logger.warning("Failed to write feed watermark to Firestore [%s]", name, exc_info=True)


# ---------------------------------------------------------------------------
# Committee snapshots (persisted prospectively, per epoch)
# ---------------------------------------------------------------------------


def save_committee_snapshot(epoch: int, data: dict) -> None:
    """Persist the committee snapshot seen during ``epoch`` for later lookup."""
    client = _get_firestore_client()
    if client is None:
        return

    payload: dict[str, Any] = {"epoch": epoch, "data": data}
    timestamp = _server_timestamp()
    if timestamp is not None:
        payload["updated_at"] = timestamp

    try:
        client.collection(COMMITTEE_SNAPSHOTS_COLLECTION).document(str(epoch)).set(payload, merge=True)
    except Exception:
        logger.warning("Failed to write committee snapshot to Firestore [epoch=%s]", epoch, exc_info=True)


def get_committee_snapshot(epoch: int) -> dict | None:
    """Return the persisted committee snapshot for ``epoch``, or ``None``."""
    client = _get_firestore_client()
    if client is None:
        return None

    try:
        doc = client.collection(COMMITTEE_SNAPSHOTS_COLLECTION).document(str(epoch)).get()
        if not doc.exists:
            return None
        return (doc.to_dict() or {}).get("data")
    except Exception:
        logger.warning("Failed to read committee snapshot from Firestore [epoch=%s]", epoch, exc_info=True)
        return None


# ---------------------------------------------------------------------------
# Treasury donation accumulation (per epoch)
# ---------------------------------------------------------------------------


def record_treasury_donations(epoch: int, donations: list[TreasuryDonation]) -> None:
    """Accumulate donations for ``epoch``, keyed by tx hash (idempotent)."""
    if not donations:
        return
    client = _get_firestore_client()
    if client is None:
        return

    try:
        doc_ref = client.collection(TREASURY_DONATIONS_COLLECTION).document(str(epoch))
        snap = doc_ref.get()
        existing = (snap.to_dict() or {}).get("donations", {}) if snap.exists else {}
        merged = dict(existing)
        for d in donations:
            merged[d.tx_hash] = d.amount_lovelace

        payload: dict[str, Any] = {"epoch": epoch, "donations": merged}
        timestamp = _server_timestamp()
        if timestamp is not None:
            payload["updated_at"] = timestamp
        doc_ref.set(payload, merge=True)
    except Exception:
        logger.warning("Failed to record treasury donations in Firestore [epoch=%s]", epoch, exc_info=True)


def get_treasury_epoch(epoch: int) -> dict | None:
    """Return the accumulated treasury-donation document for ``epoch``."""
    client = _get_firestore_client()
    if client is None:
        return None

    try:
        doc = client.collection(TREASURY_DONATIONS_COLLECTION).document(str(epoch)).get()
        if not doc.exists:
            return None
        return doc.to_dict() or None
    except Exception:
        logger.warning("Failed to read treasury donations from Firestore [epoch=%s]", epoch, exc_info=True)
        return None


def mark_treasury_epoch_summarized(epoch: int) -> None:
    """Flag ``epoch``'s treasury donations as already summarised (idempotency)."""
    client = _get_firestore_client()
    if client is None:
        return

    try:
        client.collection(TREASURY_DONATIONS_COLLECTION).document(str(epoch)).set({"summarized": True}, merge=True)
    except Exception:
        logger.warning("Failed to mark treasury epoch summarized [epoch=%s]", epoch, exc_info=True)


_DONATION_TRACKING_DOC = "donation_tracking"


def get_donation_start_epoch() -> int | None:
    """Return the epoch the bot cold-started donation tracking in, if recorded.

    Donation totals for that epoch are only partially observed (we joined
    mid-epoch), so callers skip summarising it.
    """
    client = _get_firestore_client()
    if client is None:
        return None

    try:
        doc = client.collection(CHECKPOINTS_COLLECTION).document(_DONATION_TRACKING_DOC).get()
        if not doc.exists:
            return None
        value = (doc.to_dict() or {}).get("start_epoch")
        return int(value) if value is not None else None
    except Exception:
        logger.warning("Failed to read donation start epoch from Firestore", exc_info=True)
        return None


def ensure_donation_start_epoch(epoch: int) -> None:
    """Record the donation-tracking start epoch once (first observation wins)."""
    client = _get_firestore_client()
    if client is None:
        return

    try:
        doc_ref = client.collection(CHECKPOINTS_COLLECTION).document(_DONATION_TRACKING_DOC)
        if doc_ref.get().exists:
            return
        payload: dict[str, Any] = {"start_epoch": epoch}
        timestamp = _server_timestamp()
        if timestamp is not None:
            payload["created_at"] = timestamp
        doc_ref.set(payload, merge=True)
    except Exception:
        logger.warning("Failed to record donation start epoch [epoch=%s]", epoch, exc_info=True)


# ---------------------------------------------------------------------------
# Checkpoints
# ---------------------------------------------------------------------------


def get_checkpoint(name: str) -> dict[str, Any] | None:
    """Return a checkpoint document by name."""
    client = _get_firestore_client()
    if client is None:
        return None

    try:
        doc = client.collection(CHECKPOINTS_COLLECTION).document(name).get()
        if not doc.exists:
            return None
        return doc.to_dict() or None
    except Exception:
        logger.warning("Failed to read checkpoint from Firestore [%s]", name, exc_info=True)
        return None


def set_checkpoint(name: str, block_no: int, epoch_no: int | None = None) -> None:
    """Write/update a named checkpoint document."""
    client = _get_firestore_client()
    if client is None:
        return

    payload: dict[str, Any] = {"last_block_no": block_no, "last_epoch": epoch_no}
    timestamp = _server_timestamp()
    if timestamp is not None:
        payload["updated_at"] = timestamp

    try:
        client.collection(CHECKPOINTS_COLLECTION).document(name).set(payload, merge=True)
    except Exception:
        logger.warning("Failed to write checkpoint to Firestore [%s]", name, exc_info=True)
