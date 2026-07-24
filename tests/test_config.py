import pytest

from bot.config import DEFAULT_BLOCKFROST_API_BASE_URL, Config, ConfigError, TwitterConfig


class TestConfigValidate:
    def test_valid_minimal(self):
        """BLOCKFROST_PROJECT_ID set, tweeting disabled — should pass."""
        cfg = Config(blockfrost_project_id="mainnetXXXX")
        cfg.validate()  # no exception

    def test_missing_blockfrost_project_id(self):
        cfg = Config(blockfrost_project_id="")
        with pytest.raises(ConfigError, match="BLOCKFROST_PROJECT_ID"):
            cfg.validate()

    def test_tweeting_enabled_without_creds(self):
        cfg = Config(
            blockfrost_project_id="mainnetXXXX",
            tweet_posting_enabled=True,
            twitter=TwitterConfig(),
        )
        with pytest.raises(ConfigError, match="API_KEY"):
            cfg.validate()

    def test_tweeting_enabled_with_creds(self):
        cfg = Config(
            blockfrost_project_id="mainnetXXXX",
            tweet_posting_enabled=True,
            twitter=TwitterConfig(
                api_key="k",
                api_secret_key="s",
                access_token="t",
                access_token_secret="ts",
            ),
        )
        cfg.validate()  # no exception

    def test_default_api_base_url(self):
        cfg = Config(blockfrost_project_id="mainnetXXXX")
        assert cfg.blockfrost_api_base_url == DEFAULT_BLOCKFROST_API_BASE_URL
