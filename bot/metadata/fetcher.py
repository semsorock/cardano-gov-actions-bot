import requests
from tenacity import retry, stop_after_attempt, wait_exponential

from bot.logging import get_logger

logger = get_logger("metadata.fetcher")


def sanitise_url(url: str) -> str:
    """Convert ipfs:// URIs to an HTTPS gateway URL."""
    return url.replace("ipfs://", "https://ipfs.io/ipfs/")


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
def fetch_metadata(url: str) -> dict | None:
    """Fetch and parse JSON metadata from a URL. Returns None on failure."""
    try:
        response = requests.get(url, timeout=30)
        if response.status_code == 200:
            return response.json()
        logger.warning("Error retrieving metadata (HTTP %s): %s", response.status_code, url)
        return None
    except Exception:
        logger.exception("Error retrieving metadata from %s", url)
        return None
