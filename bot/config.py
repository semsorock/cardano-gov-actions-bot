import os
from dataclasses import dataclass, field

from bot.logging import get_logger

logger = get_logger("config")


class ConfigError(Exception):
    """Raised when required configuration is missing."""


def _parse_bool(value: str | None, default: bool = False) -> bool:
    """Parse a boolean from an environment variable string."""
    if value is None:
        return default
    return value.strip().lower() in ("1", "true", "yes")


@dataclass(frozen=True)
class TwitterConfig:
    api_key: str = ""
    api_secret_key: str = ""
    access_token: str = ""
    access_token_secret: str = ""


@dataclass(frozen=True)
class Config:
    """Centralised application configuration loaded from environment variables."""

    # Database
    db_sync_url: str = ""

    # Twitter credentials
    twitter: TwitterConfig = field(default_factory=TwitterConfig)

    # Blockfrost webhook secret (for signature verification)
    blockfrost_webhook_secret: str = ""

    # Feature flags
    tweet_posting_enabled: bool = False

    @classmethod
    def from_env(cls) -> "Config":
        return cls(
            db_sync_url=os.environ.get("DB_SYNC_URL", ""),
            twitter=TwitterConfig(
                api_key=os.environ.get("API_KEY", ""),
                api_secret_key=os.environ.get("API_SECRET_KEY", ""),
                access_token=os.environ.get("ACCESS_TOKEN", ""),
                access_token_secret=os.environ.get("ACCESS_TOKEN_SECRET", ""),
            ),
            blockfrost_webhook_secret=os.environ.get("BLOCKFROST_WEBHOOK_SECRET", ""),
            tweet_posting_enabled=_parse_bool(os.environ.get("TWEET_POSTING_ENABLED"), default=False),
        )

    def validate(self) -> None:
        """Check that all required config is present. Call at startup."""
        missing = []

        if not self.db_sync_url:
            missing.append("DB_SYNC_URL")

        if self.tweet_posting_enabled:
            for field_name, env_name in [
                ("api_key", "API_KEY"),
                ("api_secret_key", "API_SECRET_KEY"),
                ("access_token", "ACCESS_TOKEN"),
                ("access_token_secret", "ACCESS_TOKEN_SECRET"),
            ]:
                if not getattr(self.twitter, field_name):
                    missing.append(env_name)

        if not self.blockfrost_webhook_secret:
            logger.warning("BLOCKFROST_WEBHOOK_SECRET not set — webhook signature verification disabled")

        if missing:
            raise ConfigError(f"Missing required environment variables: {', '.join(missing)}")


# Singleton – import `config` wherever you need it.
config = Config.from_env()
