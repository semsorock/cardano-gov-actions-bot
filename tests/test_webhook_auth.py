import hashlib
import hmac
import time
from unittest.mock import patch

from bot.webhook_auth import verify_webhook_signature


def _make_signature(body: bytes, secret: str, timestamp: int | None = None) -> str:
    """Build a valid Blockfrost-Signature header value."""
    ts = timestamp or int(time.time())
    signed_payload = f"{ts}.{body.decode('utf-8')}"
    sig = hmac.new(secret.encode(), signed_payload.encode(), hashlib.sha256).hexdigest()
    return f"t={ts},v1={sig}"


class TestVerifyWebhookSignature:
    @patch("bot.webhook_auth.config")
    def test_valid_signature(self, mock_config):
        mock_config.blockfrost_webhook_secret = "test-secret"
        body = b'{"payload": {}}'
        header = _make_signature(body, "test-secret")
        assert verify_webhook_signature(header, body) is True

    @patch("bot.webhook_auth.config")
    def test_invalid_signature(self, mock_config):
        mock_config.blockfrost_webhook_secret = "test-secret"
        body = b'{"payload": {}}'
        header = "t=12345,v1=invalidsignature"
        assert verify_webhook_signature(header, body) is False

    @patch("bot.webhook_auth.config")
    def test_missing_header(self, mock_config):
        mock_config.blockfrost_webhook_secret = "test-secret"
        assert verify_webhook_signature(None, b"{}") is False

    @patch("bot.webhook_auth.config")
    def test_no_secret_configured(self, mock_config):
        mock_config.blockfrost_webhook_secret = ""
        assert verify_webhook_signature(None, b"{}") is True

    @patch("bot.webhook_auth.config")
    def test_expired_timestamp(self, mock_config):
        mock_config.blockfrost_webhook_secret = "test-secret"
        body = b'{"payload": {}}'
        old_ts = int(time.time()) - 600  # 10 minutes ago
        header = _make_signature(body, "test-secret", timestamp=old_ts)
        assert verify_webhook_signature(header, body) is False

    @patch("bot.webhook_auth.config")
    def test_malformed_header(self, mock_config):
        mock_config.blockfrost_webhook_secret = "test-secret"
        assert verify_webhook_signature("garbage", b"{}") is False
