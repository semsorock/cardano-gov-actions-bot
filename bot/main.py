"""Cardano Governance Actions Bot — webhook entry point."""

import json

import flask
import functions_framework

from bot.cc_profiles import get_x_handle_for_voter_hash
from bot.config import config
from bot.db.repository import (
    get_block_epoch,
    get_cc_votes,
    get_gov_actions,
    get_treasury_donations,
)
from bot.github_issues import create_or_get_issue_for_mention
from bot.llm_triage import classify_mention
from bot.logging import get_logger, setup_logging
from bot.metadata.fetcher import fetch_metadata, sanitise_url
from bot.rationale_archiver import archive_cc_vote, archive_gov_action
from bot.rationale_archiver import get_action_tweet_id as get_action_tweet_id_from_github
from bot.rationale_validator import validate_cc_vote_rationale, validate_gov_action_rationale
from bot.state_store import (
    get_action_tweet_id,
    mark_cc_vote_archived,
    mark_mention_processed,
    save_action_tweet_id,
    set_checkpoint,
    was_mention_processed,
)
from bot.twitter.client import post_quote_tweet, post_reply_tweet, post_tweet
from bot.twitter.formatter import (
    format_cc_vote_tweet,
    format_gov_action_tweet,
    format_treasury_donations_tweet,
)
from bot.webhook_auth import verify_webhook_signature
from bot.x_mentions import extract_actionable_mentions
from bot.x_webhook_auth import build_crc_response_token, verify_x_webhook_signature

setup_logging()
logger = get_logger("main")

# Validate config at startup — fail fast on missing required vars.
config.validate()

X_WEBHOOK_PATH = "/x/webhook"


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
        save_action_tweet_id(action.tx_hash, action.index, tweet_id or "", source_block=block_no)


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
# X mentions processing
# ---------------------------------------------------------------------------


def _process_x_mentions(payload: dict) -> None:
    mentions, ignored_mentions = extract_actionable_mentions(payload, is_duplicate=was_mention_processed)

    for ignored in ignored_mentions:
        logger.info("Ignored X mention post_id=%s reason=%s", ignored.post_id, ignored.reason)

    for mention in mentions:
        triage = classify_mention(mention, model=config.llm_model)

        should_create_issue = (
            triage.decision in {"bug_report", "feature_request"}
            and triage.confidence >= config.llm_issue_confidence_threshold
        )

        if should_create_issue:
            issue = create_or_get_issue_for_mention(mention, triage)
            mark_mention_processed(
                mention.post_id,
                decision=triage.decision,
                issue_number=issue.issue_number,
            )
            if issue.created:
                reply_text = f"@{mention.author_handle} Thanks - tracked here: {issue.issue_url}"
                post_reply_tweet(reply_text, mention.post_id)
            else:
                logger.info("Issue already existed for mention %s; skipping reply", mention.post_id)
            continue

        if triage.decision == "ignore":
            logger.info("Ignored X mention %s after triage: %s", mention.post_id, triage.reason)
            mark_mention_processed(mention.post_id, decision=triage.decision)
            continue

        if triage.decision in {"bug_report", "feature_request"}:
            reason = triage.short_reply or "Thanks. I could not confidently classify this as a trackable issue yet."
        else:
            reason = triage.short_reply or "Thanks. I did not open an issue for this one."

        post_reply_tweet(f"@{mention.author_handle} {reason}".strip(), mention.post_id)
        mark_mention_processed(mention.post_id, decision=triage.decision)


# ---------------------------------------------------------------------------
# Webhook handlers
# ---------------------------------------------------------------------------


def _json_response(data: dict, status: int = 200) -> flask.Response:
    return flask.Response(
        response=json.dumps(data),
        status=status,
        content_type="application/json",
    )


def _handle_blockfrost_webhook(request: flask.Request) -> flask.Response:
    """Handle Blockfrost webhook events."""
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
        set_checkpoint(
            name="blockfrost_main",
            block_no=block_no,
            epoch_no=payload.get("epoch"),
        )
    except Exception:
        logger.exception("Error processing webhook for block: %s", block_no)
        return _json_response({"error": "Internal server error"}, 500)

    return _json_response({"status": "ok"})


def _handle_x_webhook(request: flask.Request) -> flask.Response:
    """Handle X webhook CRC and mention events."""
    if not config.x_webhook_enabled:
        return _json_response({"error": "Not found"}, 404)

    if request.method == "GET":
        crc_token = (request.args.get("crc_token") or "").strip()
        if not crc_token:
            return _json_response({"error": "Missing crc_token"}, 400)

        response_token = build_crc_response_token(crc_token, config.twitter.api_secret_key)
        return _json_response({"response_token": response_token})

    if request.method != "POST":
        return _json_response({"error": "Method not allowed"}, 405)

    raw_body = request.get_data()
    signature = request.headers.get("X-Twitter-Webhooks-Signature")

    if not verify_x_webhook_signature(signature, raw_body, config.twitter.api_secret_key):
        logger.warning("X webhook signature verification failed")
        return _json_response({"error": "Unauthorized"}, 401)

    request_json = request.get_json(silent=True)
    logger.info("Incoming X webhook")
    logger.debug("X webhook payload: %s", request_json)

    if not isinstance(request_json, dict):
        return _json_response({"error": "Invalid or missing JSON body"}, 400)

    try:
        _process_x_mentions(request_json)
    except Exception:
        logger.exception("Error processing X webhook")
        return _json_response({"error": "Internal server error"}, 500)

    return _json_response({"status": "ok"})


@functions_framework.http
def handle_webhook(request: flask.Request) -> flask.Response:
    """Main entry point for Blockfrost and X webhooks."""
    if request.path.rstrip("/") == X_WEBHOOK_PATH:
        return _handle_x_webhook(request)

    return _handle_blockfrost_webhook(request)
