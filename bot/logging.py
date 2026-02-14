import logging
import sys


def setup_logging(level: int = logging.INFO) -> None:
    """Configure logging for the application.

    Uses a simple format for local development / Cloud Run structured logging.
    Call once at application startup.
    """
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        stream=sys.stdout,
    )


def get_logger(name: str) -> logging.Logger:
    """Return a logger namespaced under 'bot'."""
    return logging.getLogger(f"bot.{name}")
