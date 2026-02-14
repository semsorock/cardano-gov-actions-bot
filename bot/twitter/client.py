from xdk import Client
from xdk.oauth1_auth import OAuth1
from xdk.posts.models import CreateRequest

from bot.config import config
from bot.logging import get_logger

logger = get_logger("twitter.client")


def _get_client() -> Client:
    oauth1 = OAuth1(
        api_key=config.twitter.api_key,
        api_secret=config.twitter.api_secret_key,
        callback="oob",
        access_token=config.twitter.access_token,
        access_token_secret=config.twitter.access_token_secret,
    )
    return Client(auth=oauth1)


def _extract_post_id(response: object) -> str | None:
    """Best-effort extraction of post ID from XDK response model/dict."""
    data = getattr(response, "data", None)
    if data is not None:
        post_id = getattr(data, "id", None)
        if post_id:
            return str(post_id)

    if isinstance(response, dict):
        response_data = response.get("data")
        if isinstance(response_data, dict):
            post_id = response_data.get("id")
            if post_id:
                return str(post_id)

    return None


def post_tweet(text: str) -> str | None:
    """Post a tweet. Controlled by the TWEET_POSTING_ENABLED flag in config."""
    logger.info("Tweet content:\n%s", text)

    if not config.tweet_posting_enabled:
        logger.info("Tweet posting disabled — set TWEET_POSTING_ENABLED=true to enable")
        return None

    client = _get_client()
    response = client.posts.create(CreateRequest(text=text))
    post_id = _extract_post_id(response)
    logger.info("Tweet posted: %s", response)
    return post_id


def post_quote_tweet(text: str, quote_tweet_id: str) -> str | None:
    """Post a quote tweet. Controlled by the TWEET_POSTING_ENABLED flag in config."""
    logger.info("Quote tweet content:\n%s", text)
    logger.info("Quote target tweet id: %s", quote_tweet_id)

    if not config.tweet_posting_enabled:
        logger.info("Tweet posting disabled — set TWEET_POSTING_ENABLED=true to enable")
        return None

    client = _get_client()
    response = client.posts.create(CreateRequest(text=text, quote_tweet_id=quote_tweet_id))
    post_id = _extract_post_id(response)
    logger.info("Quote tweet posted: %s", response)
    return post_id
