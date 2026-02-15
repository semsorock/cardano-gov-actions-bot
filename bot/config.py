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


def _parse_float(value: str | None, default: float) -> float:
    """Parse a float from an environment variable string."""
    if value is None:
        return default
    try:
        return float(value.strip())
    except ValueError:
        logger.warning("Invalid float value '%s' — using default %.2f", value, default)
        return default


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

    # Blockfrost webhook auth token (for signature verification)
    blockfrost_webhook_auth_token: str = ""

    # Feature flags
    tweet_posting_enabled: bool = False
    x_webhook_enabled: bool = False

    # LLM triage settings (used by X webhook flow)
    llm_model: str = ""
    llm_issue_confidence_threshold: float = 0.8

    # GitHub integration (for rationale archiving)
    github_token: str = ""
    github_repo: str = ""

    # Firestore integration (for persistent runtime state)
    firestore_project_id: str = ""
    firestore_database: str = "(default)"

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
            blockfrost_webhook_auth_token=os.environ.get("BLOCKFROST_WEBHOOK_AUTH_TOKEN", ""),
            tweet_posting_enabled=_parse_bool(os.environ.get("TWEET_POSTING_ENABLED"), default=False),
            x_webhook_enabled=_parse_bool(os.environ.get("X_WEBHOOK_ENABLED"), default=False),
            llm_model=os.environ.get("LLM_MODEL", ""),
            llm_issue_confidence_threshold=_parse_float(os.environ.get("LLM_ISSUE_CONFIDENCE_THRESHOLD"), default=0.8),
            github_token=os.environ.get("GITHUB_TOKEN", ""),
            github_repo=os.environ.get("GITHUB_REPO", ""),
            firestore_project_id=os.environ.get("FIRESTORE_PROJECT_ID", ""),
            firestore_database=os.environ.get("FIRESTORE_DATABASE", "(default)"),
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

        if not self.blockfrost_webhook_auth_token:
            logger.warning("BLOCKFROST_WEBHOOK_AUTH_TOKEN not set — webhook signature verification disabled")

        if self.x_webhook_enabled:
            if not self.twitter.api_secret_key:
                missing.append("API_SECRET_KEY")
            if not self.llm_model:
                missing.append("LLM_MODEL")
            if not self.github_token:
                missing.append("GITHUB_TOKEN")
            if not self.github_repo:
                missing.append("GITHUB_REPO")

        if not 0 <= self.llm_issue_confidence_threshold <= 1:
            missing.append("LLM_ISSUE_CONFIDENCE_THRESHOLD (must be between 0 and 1)")

        if missing:
            raise ConfigError(f"Missing required environment variables: {', '.join(missing)}")


# Singleton – import `config` wherever you need it.
config = Config.from_env()
