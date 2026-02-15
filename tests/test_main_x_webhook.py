import json
from dataclasses import replace

from flask import Flask

from bot import main
from bot.config import TwitterConfig
from bot.x_webhook_auth import build_crc_response_token


class TestMainXWebhook:
    def test_get_crc_handshake(self, monkeypatch):
        cfg = replace(
            main.config,
            x_webhook_enabled=True,
            twitter=replace(main.config.twitter, api_secret_key="secret"),
        )
        monkeypatch.setattr(main, "config", cfg)

        app = Flask(__name__)
        with app.test_request_context("/x/webhook?crc_token=abc", method="GET"):
            response = main.handle_webhook(main.flask.request)

        assert response.status_code == 200
        payload = json.loads(response.get_data(as_text=True))
        assert payload["response_token"] == build_crc_response_token("abc", "secret")

    def test_x_post_uses_x_signature_verification(self, monkeypatch):
        cfg = replace(
            main.config,
            x_webhook_enabled=True,
            twitter=replace(main.config.twitter, api_secret_key="secret"),
        )
        monkeypatch.setattr(main, "config", cfg)

        called = {"processed": False}

        monkeypatch.setattr(main, "verify_x_webhook_signature", lambda *_: True)
        monkeypatch.setattr(main, "_process_x_mentions", lambda *_: called.__setitem__("processed", True))

        def _unexpected_blockfrost_call(*_args, **_kwargs):
            raise AssertionError("Blockfrost signature verification should not run for /x/webhook")

        monkeypatch.setattr(main, "verify_webhook_signature", _unexpected_blockfrost_call)

        app = Flask(__name__)
        with app.test_request_context(
            "/x/webhook",
            method="POST",
            data='{"tweet_create_events":[]}',
            headers={"X-Twitter-Webhooks-Signature": "sha256=test"},
            content_type="application/json",
        ):
            response = main.handle_webhook(main.flask.request)

        assert response.status_code == 200
        assert called["processed"] is True

    def test_root_path_keeps_blockfrost_flow(self, monkeypatch):
        cfg = replace(
            main.config,
            x_webhook_enabled=True,
            twitter=TwitterConfig(api_secret_key="secret"),
        )
        monkeypatch.setattr(main, "config", cfg)

        calls = {"gov": 0, "cc": 0, "epoch": 0}
        monkeypatch.setattr(main, "verify_webhook_signature", lambda *_: True)
        monkeypatch.setattr(main, "_process_gov_actions", lambda *_: calls.__setitem__("gov", calls["gov"] + 1))
        monkeypatch.setattr(main, "_process_cc_votes", lambda *_: calls.__setitem__("cc", calls["cc"] + 1))
        monkeypatch.setattr(main, "_check_epoch_transition", lambda *_: calls.__setitem__("epoch", calls["epoch"] + 1))

        app = Flask(__name__)
        with app.test_request_context(
            "/",
            method="POST",
            data='{"payload":{"height":123}}',
            content_type="application/json",
        ):
            response = main.handle_webhook(main.flask.request)

        assert response.status_code == 200
        assert calls == {"gov": 1, "cc": 1, "epoch": 1}
