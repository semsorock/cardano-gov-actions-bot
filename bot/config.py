import os
from dataclasses import dataclass, field


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
            tweet_posting_enabled=_parse_bool(os.environ.get("TWEET_POSTING_ENABLED"), default=False),
        )


# Singleton – import `config` wherever you need it.
config = Config.from_env()
