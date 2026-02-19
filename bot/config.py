import os
from dataclasses import dataclass, field

from dotenv import load_dotenv

from bot.logging import get_logger

# Load .env if present — values override system env vars.
load_dotenv(override=True)

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

    # Blockfrost API
    blockfrost_project_id: str = ""
    blockfrost_network: str = "mainnet"

    # Twitter credentials
    twitter: TwitterConfig = field(default_factory=TwitterConfig)

    # Blockfrost webhook auth token (for signature verification)
    blockfrost_webhook_auth_token: str = ""

    # Feature flags
    tweet_posting_enabled: bool = False

    # GitHub integration (for rationale archiving)
    github_token: str = ""
    github_repo: str = ""

    # Firestore integration (for persistent runtime state)
    firestore_project_id: str = ""
    firestore_database: str = "(default)"

    @classmethod
    def from_env(cls) -> "Config":
        return cls(
            blockfrost_project_id=os.environ.get("BLOCKFROST_PROJECT_ID", ""),
            blockfrost_network=os.environ.get("BLOCKFROST_NETWORK", "mainnet"),
            twitter=TwitterConfig(
                api_key=os.environ.get("API_KEY", ""),
                api_secret_key=os.environ.get("API_SECRET_KEY", ""),
                access_token=os.environ.get("ACCESS_TOKEN", ""),
                access_token_secret=os.environ.get("ACCESS_TOKEN_SECRET", ""),
            ),
            blockfrost_webhook_auth_token=os.environ.get("BLOCKFROST_WEBHOOK_AUTH_TOKEN", ""),
            tweet_posting_enabled=_parse_bool(os.environ.get("TWEET_POSTING_ENABLED"), default=False),
            github_token=os.environ.get("GITHUB_TOKEN", ""),
            github_repo=os.environ.get("GITHUB_REPO", ""),
            firestore_project_id=os.environ.get("FIRESTORE_PROJECT_ID", ""),
            firestore_database=os.environ.get("FIRESTORE_DATABASE", "(default)"),
        )

    def validate(self) -> None:
        """Check that all required config is present. Call at startup."""
        missing = []

        if not self.blockfrost_project_id:
            missing.append("BLOCKFROST_PROJECT_ID")

        if self.tweet_posting_enabled:
            for field_name, env_name in [
                ("api_key", "API_KEY"),
                ("api_secret_key", "API_SECRET_KEY"),
                ("access_token", "ACCESS_TOKEN"),
                ("access_token_secret", "ACCESS_TOKEN_SECRET"),
            ]:
                if not getattr(self.twitter, field_name):
                    missing.append(env_name)

        if not self.blockfrost_webhook_auth_token:
            logger.warning("BLOCKFROST_WEBHOOK_AUTH_TOKEN not set — webhook signature verification disabled")

        if missing:
            raise ConfigError(f"Missing required environment variables: {', '.join(missing)}")


# Singleton – import `config` wherever you need it.
config = Config.from_env()
