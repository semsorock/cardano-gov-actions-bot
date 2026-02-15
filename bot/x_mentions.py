"""Helpers for extracting actionable mention events from X webhooks."""

from __future__ import annotations

from collections import deque
from collections.abc import Callable
from dataclasses import dataclass

MAX_TRACKED_POST_IDS = 10_000
_PROCESSED_POST_IDS: set[str] = set()
_POST_ID_QUEUE: deque[str] = deque()


@dataclass(frozen=True)
class MentionEvent:
    post_id: str
    text: str
    author_id: str
    author_handle: str
    permalink: str


@dataclass(frozen=True)
class IgnoredMention:
    post_id: str | None
    reason: str


def was_already_processed(post_id: str) -> bool:
    """Return whether this post ID has been handled by this process."""
    return post_id in _PROCESSED_POST_IDS


def mark_processed(post_id: str) -> None:
    """Track post IDs to avoid duplicate processing within one process lifetime."""
    if post_id in _PROCESSED_POST_IDS:
        return

    _PROCESSED_POST_IDS.add(post_id)
    _POST_ID_QUEUE.append(post_id)

    while len(_POST_ID_QUEUE) > MAX_TRACKED_POST_IDS:
        evicted = _POST_ID_QUEUE.popleft()
        _PROCESSED_POST_IDS.discard(evicted)


def extract_actionable_mentions(
    payload: dict,
    *,
    is_duplicate: Callable[[str], bool] | None = None,
) -> tuple[list[MentionEvent], list[IgnoredMention]]:
    """Extract mention events and reasons for skipped entries."""
    actionable: list[MentionEvent] = []
    ignored: list[IgnoredMention] = []

    events = payload.get("tweet_create_events")
    if not isinstance(events, list):
        return actionable, [IgnoredMention(post_id=None, reason="missing_tweet_create_events")]

    for_user_id = str(payload.get("for_user_id") or "").strip()

    for event in events:
        if not isinstance(event, dict):
            ignored.append(IgnoredMention(post_id=None, reason="malformed_event"))
            continue

        post_id = str(event.get("id_str") or event.get("id") or "").strip()
        if not post_id:
            ignored.append(IgnoredMention(post_id=None, reason="missing_post_id"))
            continue

        if is_duplicate and is_duplicate(post_id):
            ignored.append(IgnoredMention(post_id=post_id, reason="duplicate_post_id"))
            continue

        text = str(event.get("text") or "").strip()
        if not text:
            ignored.append(IgnoredMention(post_id=post_id, reason="empty_text"))
            continue

        if "retweeted_status" in event or text.startswith("RT @"):
            ignored.append(IgnoredMention(post_id=post_id, reason="retweet_style"))
            continue

        user = event.get("user")
        if not isinstance(user, dict):
            ignored.append(IgnoredMention(post_id=post_id, reason="missing_user"))
            continue

        author_id = str(user.get("id_str") or user.get("id") or "").strip()
        author_handle = str(user.get("screen_name") or user.get("username") or "").strip().lstrip("@")
        if not author_handle:
            ignored.append(IgnoredMention(post_id=post_id, reason="missing_author_handle"))
            continue

        if for_user_id and author_id == for_user_id:
            ignored.append(IgnoredMention(post_id=post_id, reason="self_post"))
            continue

        mention_ids = _extract_mention_ids(event)
        if for_user_id and for_user_id not in mention_ids:
            ignored.append(IgnoredMention(post_id=post_id, reason="not_mentioning_bot"))
            continue

        actionable.append(
            MentionEvent(
                post_id=post_id,
                text=text,
                author_id=author_id,
                author_handle=author_handle,
                permalink=f"https://x.com/{author_handle}/status/{post_id}",
            )
        )

    return actionable, ignored


def _extract_mention_ids(event: dict) -> set[str]:
    entities = event.get("entities")
    if not isinstance(entities, dict):
        return set()

    mentions = entities.get("user_mentions")
    if not isinstance(mentions, list):
        return set()

    ids: set[str] = set()
    for mention in mentions:
        if not isinstance(mention, dict):
            continue
        mention_id = mention.get("id_str") or mention.get("id")
        if mention_id is not None:
            ids.add(str(mention_id))
    return ids
