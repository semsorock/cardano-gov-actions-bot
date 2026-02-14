import tweepy

from bot.config import config
from bot.logging import get_logger

logger = get_logger("twitter.client")


def _get_client() -> tweepy.Client:
    return tweepy.Client(
        consumer_key=config.twitter.api_key,
        consumer_secret=config.twitter.api_secret_key,
        access_token=config.twitter.access_token,
        access_token_secret=config.twitter.access_token_secret,
    )


def post_tweet(text: str) -> None:
    """Post a tweet. Controlled by the TWEET_POSTING_ENABLED flag in config."""
    logger.info("Tweet content:\n%s", text)

    if not config.tweet_posting_enabled:
        logger.info("Tweet posting disabled — set TWEET_POSTING_ENABLED=true to enable")
        return

    client = _get_client()
    response = client.create_tweet(text=text)
    logger.info("Tweet posted: %s", response)
