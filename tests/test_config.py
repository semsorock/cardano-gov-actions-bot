import pytest

from bot.config import Config, ConfigError, TwitterConfig


class TestConfigValidate:
    def test_valid_minimal(self):
        """DB_SYNC_URL set, tweeting disabled — should pass."""
        cfg = Config(db_sync_url="postgresql://localhost/test")
        cfg.validate()  # no exception

    def test_missing_db_url(self):
        cfg = Config(db_sync_url="")
        with pytest.raises(ConfigError, match="DB_SYNC_URL"):
            cfg.validate()

    def test_tweeting_enabled_without_creds(self):
        cfg = Config(
            db_sync_url="postgresql://localhost/test",
            tweet_posting_enabled=True,
            twitter=TwitterConfig(),
        )
        with pytest.raises(ConfigError, match="API_KEY"):
            cfg.validate()

    def test_tweeting_enabled_with_creds(self):
        cfg = Config(
            db_sync_url="postgresql://localhost/test",
            tweet_posting_enabled=True,
            twitter=TwitterConfig(
                api_key="k",
                api_secret_key="s",
                access_token="t",
                access_token_secret="ts",
            ),
        )
        cfg.validate()  # no exception
