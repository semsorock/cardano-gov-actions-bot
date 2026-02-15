import base64
import hashlib
import hmac

from bot.x_webhook_auth import build_crc_response_token, verify_x_webhook_signature


def _make_x_signature(body: bytes, secret: str) -> str:
    digest = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).digest()
    return "sha256=" + base64.b64encode(digest).decode("utf-8")


class TestXWebhookAuth:
    def test_build_crc_response_token(self):
        token = build_crc_response_token("abc123", "secret")
        assert token.startswith("sha256=")
        assert len(token) > 7

    def test_verify_signature_valid(self):
        body = b'{"tweet_create_events":[]}'
        signature = _make_x_signature(body, "secret")
        assert verify_x_webhook_signature(signature, body, "secret") is True

    def test_verify_signature_invalid(self):
        body = b'{"tweet_create_events":[]}'
        assert verify_x_webhook_signature("sha256=invalid", body, "secret") is False

    def test_verify_signature_missing_header(self):
        assert verify_x_webhook_signature(None, b"{}", "secret") is False

    def test_verify_signature_malformed_header(self):
        assert verify_x_webhook_signature("bad-header", b"{}", "secret") is False
