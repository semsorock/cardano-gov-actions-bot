"""Tests for feed pagination + watermark logic (duplicate / out-of-order safety)."""

import pytest

from bot.blockfrost.feeds import collect_new_items

# Feeds are consumed newest-first (order=desc); helpers below model that.


def _make_fetch(desc_items: list[dict], page_size: int):
    """Return an async fetch_page(page) over ``desc_items`` and a call counter."""
    calls = {"count": 0}

    async def fetch_page(page: int) -> list[dict]:
        calls["count"] += 1
        start = (page - 1) * page_size
        return desc_items[start : start + page_size]

    return fetch_page, calls


def _ids(items):
    return [it["id"] for it in items]


def key(item):
    return item["id"]


@pytest.mark.asyncio
async def test_bootstrap_adopts_tip_and_processes_nothing():
    feed = [{"id": "3"}, {"id": "2"}, {"id": "1"}]
    fetch, calls = _make_fetch(feed, page_size=100)

    scan = await collect_new_items(fetch, None, key, page_size=100)

    assert scan.bootstrapped is True
    assert scan.items == []
    assert scan.watermark == "3"
    assert calls["count"] == 1  # a single page-1 fetch


@pytest.mark.asyncio
async def test_nothing_new_costs_one_request():
    feed = [{"id": "3"}, {"id": "2"}, {"id": "1"}]
    fetch, calls = _make_fetch(feed, page_size=100)

    scan = await collect_new_items(fetch, "3", key, page_size=100)

    assert scan.items == []
    assert scan.watermark == "3"
    assert scan.bootstrapped is False
    assert calls["count"] == 1  # steady state: one page, tip == watermark


@pytest.mark.asyncio
async def test_collects_new_items_oldest_first():
    feed = [{"id": "3"}, {"id": "2"}, {"id": "1"}]
    fetch, _ = _make_fetch(feed, page_size=100)

    scan = await collect_new_items(fetch, "1", key, page_size=100)

    assert _ids(scan.items) == ["2", "3"]  # oldest-first
    assert scan.watermark == "3"


@pytest.mark.asyncio
async def test_paginates_until_watermark_found():
    feed = [{"id": "5"}, {"id": "4"}, {"id": "3"}, {"id": "2"}, {"id": "1"}]
    fetch, calls = _make_fetch(feed, page_size=2)

    scan = await collect_new_items(fetch, "2", key, page_size=2)

    assert _ids(scan.items) == ["3", "4", "5"]
    assert scan.watermark == "5"
    assert calls["count"] == 2  # page 1 (5,4) then page 2 (3,2 — found)


@pytest.mark.asyncio
async def test_vanished_watermark_reanchors_at_tip():
    # e.g. a rollback removed the watermark item from the feed.
    feed = [{"id": "5"}, {"id": "4"}, {"id": "3"}]
    fetch, _ = _make_fetch(feed, page_size=100)

    scan = await collect_new_items(fetch, "99", key, page_size=100)

    assert _ids(scan.items) == ["3", "4", "5"]  # everything re-checked
    assert scan.watermark == "5"


@pytest.mark.asyncio
async def test_max_pages_cap_stops_scan():
    feed = [{"id": str(i)} for i in range(20, 0, -1)]  # 20..1 desc
    fetch, calls = _make_fetch(feed, page_size=2)

    scan = await collect_new_items(fetch, "does-not-exist", key, page_size=2, max_pages=2)

    assert scan.watermark == "20"
    assert calls["count"] == 2  # capped at max_pages


@pytest.mark.asyncio
async def test_indexing_lag_then_appears_next_scan():
    # First scan: item "4" not yet indexed — nothing new.
    feed = [{"id": "3"}, {"id": "2"}, {"id": "1"}]
    fetch, _ = _make_fetch(feed, page_size=100)
    scan = await collect_new_items(fetch, "3", key, page_size=100)
    assert scan.items == []

    # Next scan: "4" has now been indexed.
    feed2 = [{"id": "4"}, {"id": "3"}, {"id": "2"}, {"id": "1"}]
    fetch2, _ = _make_fetch(feed2, page_size=100)
    scan2 = await collect_new_items(fetch2, "3", key, page_size=100)
    assert _ids(scan2.items) == ["4"]
    assert scan2.watermark == "4"


@pytest.mark.asyncio
async def test_empty_feed_keeps_watermark():
    fetch, _ = _make_fetch([], page_size=100)
    scan = await collect_new_items(fetch, "3", key, page_size=100)
    assert scan.items == []
    assert scan.watermark == "3"
    assert scan.bootstrapped is False
