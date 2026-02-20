"""Persistent state helpers backed by Firestore with safe fallbacks."""

from __future__ import annotations

from typing import Any

from bot.config import config
from bot.logging import get_logger

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


def _cc_vote_id(ga_tx_hash: str, ga_index: int, voter_hash: str) -> str:
    return f"{ga_tx_hash}_{ga_index}_{voter_hash}"


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


def mark_cc_vote_archived(
    ga_tx_hash: str,
    ga_index: int,
    voter_hash: str,
    source_block: int | None = None,
) -> None:
    """Persist CC vote archived status in Firestore."""
    client = _get_firestore_client()
    if client is None:
        return

    payload: dict[str, Any] = {"archived_vote": True}
    if source_block is not None:
        payload["source_block"] = source_block

    timestamp = _server_timestamp()
    if timestamp is not None:
        payload["last_updated_at"] = timestamp

    try:
        client.collection(CC_VOTE_STATE_COLLECTION).document(_cc_vote_id(ga_tx_hash, ga_index, voter_hash)).set(
            payload, merge=True
        )
    except Exception:
        logger.warning(
            "Failed to save CC vote state in Firestore [%s_%s_%s]",
            ga_tx_hash[:8],
            ga_index,
            voter_hash[:8],
            exc_info=True,
        )


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


def get_last_processed_proposal() -> dict[str, Any] | None:
    """Get the last processed proposal from Firestore.

    Returns:
        Dict with tx_hash and cert_index, or None if not found
    """
    client = _get_firestore_client()
    if client is None:
        return None

    try:
        doc = client.collection(CHECKPOINTS_COLLECTION).document("last_proposal").get()
        if doc.exists:
            return doc.to_dict()
        return None
    except Exception:
        logger.warning("Failed to read last proposal checkpoint from Firestore", exc_info=True)
        return None


def set_last_processed_proposal(tx_hash: str, cert_index: int) -> None:
    """Store the last processed proposal in Firestore.

    Args:
        tx_hash: Transaction hash of the proposal
        cert_index: Certificate index within the transaction
    """
    client = _get_firestore_client()
    if client is None:
        return

    payload: dict[str, Any] = {"tx_hash": tx_hash, "cert_index": cert_index}
    timestamp = _server_timestamp()
    if timestamp is not None:
        payload["updated_at"] = timestamp

    try:
        client.collection(CHECKPOINTS_COLLECTION).document("last_proposal").set(payload, merge=True)
    except Exception:
        logger.warning("Failed to write last proposal checkpoint to Firestore", exc_info=True)


def get_last_processed_vote() -> dict[str, Any] | None:
    """Get the last processed vote from Firestore.

    Returns:
        Dict with tx_hash, or None if not found
    """
    client = _get_firestore_client()
    if client is None:
        return None

    try:
        doc = client.collection(CHECKPOINTS_COLLECTION).document("last_vote").get()
        if doc.exists:
            return doc.to_dict()
        return None
    except Exception:
        logger.warning("Failed to read last vote checkpoint from Firestore", exc_info=True)
        return None


def set_last_processed_vote(tx_hash: str) -> None:
    """Store the last processed vote transaction in Firestore.

    Args:
        tx_hash: Transaction hash of the vote
    """
    client = _get_firestore_client()
    if client is None:
        return

    payload: dict[str, Any] = {"tx_hash": tx_hash}
    timestamp = _server_timestamp()
    if timestamp is not None:
        payload["updated_at"] = timestamp

    try:
        client.collection(CHECKPOINTS_COLLECTION).document("last_vote").set(payload, merge=True)
    except Exception:
        logger.warning("Failed to write last vote checkpoint to Firestore", exc_info=True)
