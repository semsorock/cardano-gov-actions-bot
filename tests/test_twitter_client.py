from dataclasses import replace

from xdk.posts.models import CreateRequest

from bot.config import TwitterConfig
from bot.twitter import client as twitter_client


class _FakePosts:
    def __init__(self):
        self.calls = []

    def create(self, body):
        self.calls.append(body)
        return {"data": {"id": "12345"}}


class _FakeClient:
    def __init__(self):
        self.posts = _FakePosts()


class TestTwitterClient:
    def test_exports_quote_tweet_function(self):
        assert callable(twitter_client.post_quote_tweet)

    def test_post_tweet_disabled_returns_none(self, monkeypatch):
        cfg = replace(
            twitter_client.config,
            tweet_posting_enabled=False,
            twitter=TwitterConfig(api_key="", api_secret_key="", access_token="", access_token_secret=""),
        )
        monkeypatch.setattr(twitter_client, "config", cfg)

        assert twitter_client.post_tweet("hello") is None

    def test_post_tweet_enabled_sends_create_request(self, monkeypatch):
        fake_client = _FakeClient()
        cfg = replace(
            twitter_client.config,
            tweet_posting_enabled=True,
            twitter=TwitterConfig(
                api_key="k",
                api_secret_key="s",
                access_token="t",
                access_token_secret="ts",
            ),
        )
        monkeypatch.setattr(twitter_client, "config", cfg)
        monkeypatch.setattr(twitter_client, "_get_client", lambda: fake_client)

        post_id = twitter_client.post_tweet("hello")

        assert post_id == "12345"
        assert len(fake_client.posts.calls) == 1
        body = fake_client.posts.calls[0]
        assert isinstance(body, CreateRequest)
        assert body.text == "hello"
        assert body.quote_tweet_id is None

    def test_post_quote_tweet_enabled_sends_quote_tweet_id(self, monkeypatch):
        fake_client = _FakeClient()
        cfg = replace(
            twitter_client.config,
            tweet_posting_enabled=True,
            twitter=TwitterConfig(
                api_key="k",
                api_secret_key="s",
                access_token="t",
                access_token_secret="ts",
            ),
        )
        monkeypatch.setattr(twitter_client, "config", cfg)
        monkeypatch.setattr(twitter_client, "_get_client", lambda: fake_client)

        post_id = twitter_client.post_quote_tweet("cc vote update", "987654321")

        assert post_id == "12345"
        assert len(fake_client.posts.calls) == 1
        body = fake_client.posts.calls[0]
        assert isinstance(body, CreateRequest)
        assert body.text == "cc vote update"
        assert body.quote_tweet_id == "987654321"
