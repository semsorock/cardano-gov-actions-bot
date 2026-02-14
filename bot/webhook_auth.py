"""Blockfrost webhook signature verification."""

import hashlib
import hmac
import time

from bot.config import config
from bot.logging import get_logger

logger = get_logger("webhook.auth")

# Allow up to 5 minutes of clock skew
_MAX_AGE_SECONDS = 300


def verify_webhook_signature(signature_header: str | None, body: bytes) -> bool:
    """Verify a Blockfrost webhook signature.

    The signature header format is: t=<timestamp>,v1=<signature>
    See: https://blockfrost.dev/docs/start-building/webhooks/#signature-verification
    """
    secret = config.blockfrost_webhook_secret

    if not secret:
        logger.debug("No webhook secret configured — skipping verification")
        return True

    if not signature_header:
        logger.warning("Missing Blockfrost-Signature header")
        return False

    try:
        parts = dict(part.split("=", 1) for part in signature_header.split(","))
        timestamp = parts.get("t", "")
        received_sig = parts.get("v1", "")
    except (ValueError, AttributeError):
        logger.warning("Malformed Blockfrost-Signature header")
        return False

    if not timestamp or not received_sig:
        logger.warning("Incomplete Blockfrost-Signature header")
        return False

    # Check timestamp freshness
    try:
        ts = int(timestamp)
        if abs(time.time() - ts) > _MAX_AGE_SECONDS:
            logger.warning("Webhook signature timestamp too old: %s", timestamp)
            return False
    except ValueError:
        logger.warning("Invalid timestamp in signature: %s", timestamp)
        return False

    # Compute expected signature
    signed_payload = f"{timestamp}.{body.decode('utf-8')}"
    expected_sig = hmac.new(
        secret.encode("utf-8"),
        signed_payload.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(expected_sig, received_sig):
        logger.warning("Webhook signature mismatch")
        return False

    return True
