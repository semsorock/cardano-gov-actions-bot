"""Tests for the async Blockfrost client's retry/backoff behaviour."""

import httpx
import pytest

from bot.blockfrost.client import BlockfrostClient, BlockfrostError, BlockfrostNotFound


def _make_client(handler):
    """Build a BlockfrostClient over a MockTransport with a no-wait sleep."""
    recorded_sleeps: list[float] = []

    async def fake_sleep(delay):
        recorded_sleeps.append(delay)

    transport = httpx.MockTransport(handler)
    async_client = httpx.AsyncClient(transport=transport, base_url="https://bf.test/api/v0")
    client = BlockfrostClient(project_id="test", client=async_client, sleep=fake_sleep)
    return client, recorded_sleeps


@pytest.mark.asyncio
async def test_success_no_retry():
    def handler(request):
        assert request.headers["project_id"] == "test"
        return httpx.Response(200, json=[{"id": "gov1"}])

    client, sleeps = _make_client(handler)
    result = await client.get_proposals()
    assert result == [{"id": "gov1"}]
    assert sleeps == []
    await client.aclose()


@pytest.mark.asyncio
async def test_retries_on_429_then_succeeds_and_honours_retry_after():
    state = {"n": 0}

    def handler(request):
        state["n"] += 1
        if state["n"] == 1:
            return httpx.Response(429, headers={"Retry-After": "2"}, text="rate limited")
        return httpx.Response(200, json={"ok": True})

    client, sleeps = _make_client(handler)
    result = await client.get_committee()
    assert result == {"ok": True}
    assert sleeps == [2.0]  # honoured Retry-After
    await client.aclose()


@pytest.mark.asyncio
async def test_retries_on_500_then_succeeds():
    state = {"n": 0}

    def handler(request):
        state["n"] += 1
        if state["n"] <= 2:
            return httpx.Response(503, text="unavailable")
        return httpx.Response(200, json={"cbor": "aa"})

    client, sleeps = _make_client(handler)
    result = await client.get_epoch_parameters(500)
    assert result == {"cbor": "aa"}
    assert len(sleeps) == 2  # backed off twice before success
    await client.aclose()


@pytest.mark.asyncio
async def test_retries_on_timeout_then_succeeds():
    state = {"n": 0}

    def handler(request):
        state["n"] += 1
        if state["n"] == 1:
            raise httpx.ConnectTimeout("boom")
        return httpx.Response(200, json=[])

    client, sleeps = _make_client(handler)
    result = await client.get_committee_votes()
    assert result == []
    assert len(sleeps) == 1
    await client.aclose()


@pytest.mark.asyncio
async def test_404_raises_not_found():
    def handler(request):
        return httpx.Response(404, text="not found")

    client, sleeps = _make_client(handler)
    with pytest.raises(BlockfrostNotFound):
        await client.get_proposal("aa", 0)
    assert sleeps == []  # 404 is not retried
    await client.aclose()


@pytest.mark.asyncio
async def test_exhausts_retries_raises_error():
    def handler(request):
        return httpx.Response(503, text="always down")

    client, sleeps = _make_client(handler)
    with pytest.raises(BlockfrostError):
        await client.get_proposals()
    assert len(sleeps) >= 1  # retried and backed off before giving up
    await client.aclose()


@pytest.mark.asyncio
async def test_client_error_400_raises_without_retry():
    def handler(request):
        return httpx.Response(400, text="bad request")

    client, sleeps = _make_client(handler)
    with pytest.raises(BlockfrostError):
        await client.get_proposals()
    assert sleeps == []
    await client.aclose()
