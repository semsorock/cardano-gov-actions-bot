"""Cardano Governance Actions Bot — webhook entry point."""

import json

import flask
import functions_framework

from bot.config import config
from bot.db.repository import (
    get_block_epoch,
    get_cc_votes,
    get_gov_actions,
    get_treasury_donations,
)
from bot.logging import get_logger, setup_logging
from bot.metadata.fetcher import fetch_metadata, sanitise_url
from bot.rationale_archiver import archive_cc_vote, archive_gov_action, get_action_tweet_id
from bot.rationale_validator import validate_cc_vote_rationale, validate_gov_action_rationale
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


# ---------------------------------------------------------------------------
# Block processing
# ---------------------------------------------------------------------------


def _process_gov_actions(block_no: int) -> None:
    actions = get_gov_actions(block_no)

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


def _process_cc_votes(block_no: int) -> None:
    votes = get_cc_votes(block_no)

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
        tweet = format_cc_vote_tweet(vote, metadata, quote_tweet_id=quote_id)

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


# ---------------------------------------------------------------------------
# Epoch processing
# ---------------------------------------------------------------------------


def _process_treasury_donations(epoch_no: int) -> None:
    donations = get_treasury_donations(epoch_no)
    logger.debug("Donations: %s", donations)

    if not donations:
        logger.info("No treasury donations for epoch: %s", epoch_no)
        return

    tweet = format_treasury_donations_tweet(donations)
    post_tweet(tweet)


def _check_epoch_transition(payload: dict) -> None:
    """Detect epoch boundary and run epoch processing if one occurred."""
    current_epoch = payload.get("epoch")
    previous_block_hash = payload.get("previous_block")

    if current_epoch is None or not previous_block_hash:
        logger.debug("No epoch or previous_block in payload — skipping epoch check")
        return

    previous_epoch = get_block_epoch(previous_block_hash)

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
        _process_treasury_donations(previous_epoch)


# ---------------------------------------------------------------------------
# Webhook handler
# ---------------------------------------------------------------------------


def _json_response(data: dict, status: int = 200) -> flask.Response:
    return flask.Response(
        response=json.dumps(data),
        status=status,
        content_type="application/json",
    )


@functions_framework.http
def handle_webhook(request: flask.Request) -> flask.Response:
    """Main entry point for Blockfrost webhook events."""
    # --- Signature verification ---
    raw_body = request.get_data()
    signature = request.headers.get("Blockfrost-Signature")

    if not verify_webhook_signature(signature, raw_body):
        logger.warning("Webhook signature verification failed")
        return _json_response({"error": "Unauthorized"}, 401)

    # --- Parse payload ---
    request_json = request.get_json(silent=True)

    logger.info("Incoming webhook")
    logger.debug("Webhook payload: %s", request_json)

    if not request_json:
        return _json_response({"error": "Invalid or missing JSON body"}, 400)

    payload = request_json.get("payload", {})
    block_no = payload.get("height")

    if block_no is None:
        logger.warning("Missing block height in payload")
        return _json_response({"error": "Missing block height"}, 400)

    try:
        # Always process block events.
        _process_gov_actions(block_no)
        _process_cc_votes(block_no)

        # Detect epoch transitions and process if needed.
        _check_epoch_transition(payload)
    except Exception:
        logger.exception("Error processing webhook for block: %s", block_no)
        return _json_response({"error": "Internal server error"}, 500)

    return _json_response({"status": "ok"})
