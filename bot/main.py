"""Cardano Governance Actions Bot — webhook entry point."""

import json

import flask
import functions_framework

from bot.config import config
from bot.db.repository import get_cc_votes, get_gov_actions, get_treasury_donations
from bot.logging import get_logger, setup_logging
from bot.metadata.fetcher import fetch_metadata, sanitise_url
from bot.twitter.client import post_tweet
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

# Hard-coded skip for known test transactions from the original code.
_SKIP_TX_HASH = "8ad3d454f3496a35cb0d07b0fd32f687f66338b7d60e787fc0a22939e5d8833e"
_SKIP_INDEX_BELOW = 17


# ---------------------------------------------------------------------------
# Block processing
# ---------------------------------------------------------------------------


def _process_gov_actions(block_no: int) -> None:
    actions = get_gov_actions(block_no)

    if not actions:
        logger.info("No gov actions for block: %s", block_no)
        return

    for action in actions:
        if action.tx_hash == _SKIP_TX_HASH and action.index < _SKIP_INDEX_BELOW:
            logger.debug("Skipping gov action: %s#%s", action.tx_hash, action.index)
            continue

        url = sanitise_url(action.raw_url)
        metadata = fetch_metadata(url)
        tweet = format_gov_action_tweet(action, metadata)
        post_tweet(tweet)


def _process_cc_votes(block_no: int) -> None:
    votes = get_cc_votes(block_no)

    if not votes:
        logger.info("No CC vote records for block: %s", block_no)
        return

    for vote in votes:
        url = sanitise_url(vote.raw_url)
        metadata = fetch_metadata(url)
        tweet = format_cc_vote_tweet(vote, metadata)
        post_tweet(tweet)


def process_block(request_json: dict) -> None:
    block_no = request_json.get("payload", {}).get("height")
    if block_no is None:
        logger.warning("Missing block height in payload")
        return
    _process_gov_actions(block_no)
    _process_cc_votes(block_no)


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


def process_epoch(request_json: dict) -> None:
    epoch_no = request_json.get("payload", {}).get("current_epoch", {}).get("epoch")
    if epoch_no is None:
        logger.warning("Missing epoch number in payload")
        return

    logger.info("Processing epoch: %s", epoch_no)

    # GA expirations disabled for now — uncomment when ready:
    # _process_ga_expirations(epoch_no)

    _process_treasury_donations(epoch_no - 1)


# ---------------------------------------------------------------------------
# Webhook router
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

    # --- Route to handler ---
    request_json = request.get_json(silent=True)
    request_path = request.path

    logger.info("Incoming webhook — path: %s", request_path)
    logger.debug("Webhook payload: %s", request_json)

    if not request_json:
        return _json_response({"error": "Invalid or missing JSON body"}, 400)

    try:
        if request_path == "/block":
            process_block(request_json)
        elif request_path == "/epoch":
            process_epoch(request_json)
        else:
            logger.warning("Unknown request path: %s", request_path)
            return _json_response({"error": f"Unknown path: {request_path}"}, 404)
    except Exception:
        logger.exception("Error processing webhook for path: %s", request_path)
        return _json_response({"error": "Internal server error"}, 500)

    return _json_response({"status": "ok"})
