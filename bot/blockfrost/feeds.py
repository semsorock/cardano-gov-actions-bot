"""Feed scanning with persisted watermarks.

Governance proposals and committee votes are append-only feeds. On every
webhook the bot scans each feed newest-first (``order=desc``), collecting items
until it reaches the last one it has already seen (the *watermark*), then hands
them back oldest-first so they are processed in chain order.

Design notes:

* Steady state costs a single request per feed — page 1's newest item already
  equals the watermark, so the scan stops immediately.
* The watermark is only an optimisation that bounds how far back we page;
  correctness against duplicate / out-of-order delivery comes from the
  per-item domain idempotency keys the caller checks before acting.
* On the very first run there is no watermark: we adopt the current tip as the
  watermark and process nothing, leaving history to the backfill script rather
  than replaying it through the webhook path.
* The watermark returned here must only be persisted by the caller *after*
  processing succeeds.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from bot.blockfrost.client import MAX_PAGE_SIZE
from bot.logging import get_logger

logger = get_logger("blockfrost.feeds")

# Safety cap: how many pages to walk back looking for a vanished watermark
# (e.g. after a rollback) before giving up and re-anchoring at the tip.
_MAX_PAGES = 50

FetchPage = Callable[[int], Awaitable[list[dict]]]
KeyFn = Callable[[dict], str]


@dataclass(frozen=True)
class FeedScan:
    """Result of scanning a feed against its watermark."""

    items: list[dict]  # unseen items, oldest-first
    watermark: str | None  # new watermark to persist after processing
    bootstrapped: bool  # True when the watermark was just initialised


async def collect_new_items(
    fetch_page: FetchPage,
    watermark: str | None,
    key_fn: KeyFn,
    *,
    page_size: int = MAX_PAGE_SIZE,
    max_pages: int = _MAX_PAGES,
) -> FeedScan:
    """Scan a desc-ordered feed and return items newer than ``watermark``."""
    first_page = await fetch_page(1)
    if not first_page:
        return FeedScan(items=[], watermark=watermark, bootstrapped=False)

    tip = key_fn(first_page[0])

    if watermark is None:
        logger.info("Bootstrapping feed watermark at tip %s (history left to backfill)", tip)
        return FeedScan(items=[], watermark=tip, bootstrapped=True)

    collected: list[dict] = []
    page = first_page
    page_num = 1
    while True:
        found = False
        for item in page:
            if key_fn(item) == watermark:
                found = True
                break
            collected.append(item)

        if found:
            break
        if len(page) < page_size:
            # Reached the end of the feed without finding the watermark.
            logger.warning("Feed watermark %s not found before end of feed — re-anchoring at tip", watermark)
            break
        if page_num >= max_pages:
            logger.warning(
                "Feed watermark %s not found within %d pages — re-anchoring at tip (some items may be re-checked)",
                watermark,
                max_pages,
            )
            break
        page_num += 1
        page = await fetch_page(page_num)
        if not page:
            break

    collected.reverse()  # oldest-first
    return FeedScan(items=collected, watermark=tip, bootstrapped=False)
