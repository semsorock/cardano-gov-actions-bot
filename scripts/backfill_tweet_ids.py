#!/usr/bin/env python3
"""Backfill tweet IDs for existing governance action rationales.

Fetches the bot's last 100 posts from X, matches governance action tweets
to rationale directories by AdaStat link, and writes tweet_id.txt files.
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

# Ensure project root is on the path.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv

load_dotenv(override=True)

from bot.logging import get_logger, setup_logging  # noqa: E402

setup_logging()
logger = get_logger("backfill_tweet_ids")

# AdaStat governance link pattern:  .../governances/<tx_hash><hex_index>
ADASTAT_RE = re.compile(r"adastat\.net/governances/([0-9a-f]{64})([0-9a-f]{2,})")


def _parse_action_id(text: str) -> str | None:
    """Extract '<tx_hash>_<index>' from an AdaStat governance link in tweet text."""
    match = ADASTAT_RE.search(text)
    if not match:
        return None
    tx_hash = match.group(1)
    index_hex = match.group(2)
    index = int(index_hex, 16)
    return f"{tx_hash}_{index}"


def _get_client():
    """Build an authenticated XDK client using env vars."""
    from xdk import Client
    from xdk.oauth1_auth import OAuth1

    oauth1 = OAuth1(
        api_key=os.environ["API_KEY"],
        api_secret=os.environ["API_SECRET_KEY"],
        callback="oob",
        access_token=os.environ["ACCESS_TOKEN"],
        access_token_secret=os.environ["ACCESS_TOKEN_SECRET"],
    )
    return Client(auth=oauth1)


def main() -> None:
    rationales_dir = Path(__file__).resolve().parent.parent / "rationales"
    if not rationales_dir.is_dir():
        logger.error("No rationales/ directory found at %s", rationales_dir)
        sys.exit(1)

    client = _get_client()

    # Get the bot's own user ID.
    me_response = client.users.get_me()
    me_data = me_response.get("data") if isinstance(me_response, dict) else me_response.data
    if isinstance(me_data, dict):
        user_id = me_data.get("id")
    else:
        user_id = getattr(me_data, "id", None)

    if not user_id:
        logger.error("Could not determine bot user ID: %s", me_response)
        sys.exit(1)

    logger.info("Bot user ID: %s", user_id)

    # Fetch last 100 posts.
    matched = 0
    skipped = 0
    written = 0
    total = 0

    for page in client.users.get_posts(id=user_id, max_results=100, tweet_fields=["entities"]):
        tweets = page.get("data") if isinstance(page, dict) else getattr(page, "data", None)
        if not tweets:
            break

        for tweet in tweets:
            total += 1
            if isinstance(tweet, dict):
                tweet_id = tweet.get("id", "")
                text = tweet.get("text", "")
                entities = tweet.get("entities", {})
            else:
                tweet_id = getattr(tweet, "id", "")
                text = getattr(tweet, "text", "")
                entities = getattr(tweet, "entities", {})

            if "NEW GOVERNANCE ACTION ALERT" not in text:
                continue

            # X shortens URLs to t.co links in tweet text.
            # The original URLs are in entities.urls[].expanded_url.
            urls = entities.get("urls", []) if isinstance(entities, dict) else getattr(entities, "urls", [])
            action_id = None
            for url_obj in urls or []:
                if isinstance(url_obj, dict):
                    expanded = url_obj.get("expanded_url", "")
                else:
                    expanded = getattr(url_obj, "expanded_url", "")
                action_id = _parse_action_id(expanded)
                if action_id:
                    break

            if not action_id:
                continue

            matched += 1
            action_dir = rationales_dir / action_id
            tweet_id_file = action_dir / "tweet_id.txt"

            if tweet_id_file.exists():
                skipped += 1
                logger.debug("Already has tweet_id: %s", action_id)
                continue

            if not action_dir.is_dir():
                logger.debug("No rationale dir for %s — skipping", action_id)
                continue

            tweet_id_file.write_text(str(tweet_id) + "\n")
            written += 1
            logger.info("Wrote tweet_id for %s: %s", action_id, tweet_id)

        # Only fetch first page (up to 100 posts).
        break

    logger.info(
        "Done — %d posts scanned, %d matched gov actions, %d written, %d skipped",
        total,
        matched,
        written,
        skipped,
    )


if __name__ == "__main__":
    main()
