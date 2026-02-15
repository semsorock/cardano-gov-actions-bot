"""X webhook signature and CRC validation helpers."""

from __future__ import annotations

import base64
import hashlib
import hmac

from bot.logging import get_logger

logger = get_logger("x_webhook_auth")


def build_crc_response_token(crc_token: str, secret: str) -> str:
    """Build the response token for X webhook CRC checks."""
    digest = hmac.new(secret.encode("utf-8"), crc_token.encode("utf-8"), hashlib.sha256).digest()
    return "sha256=" + base64.b64encode(digest).decode("utf-8")


def verify_x_webhook_signature(signature_header: str | None, body: bytes, secret: str) -> bool:
    """Verify X webhook POST signature.

    Header format: `sha256=<base64_digest>`.
    """
    if not secret:
        logger.warning("Cannot verify X webhook signature: missing API secret")
        return False

    if not signature_header:
        logger.warning("Missing X-Twitter-Webhooks-Signature header")
        return False

    if not signature_header.startswith("sha256="):
        logger.warning("Malformed X webhook signature header")
        return False

    digest = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).digest()
    expected = "sha256=" + base64.b64encode(digest).decode("utf-8")
    return hmac.compare_digest(expected, signature_header)
