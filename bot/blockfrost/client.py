"""Async Blockfrost HTTP client.

A thin ``httpx`` wrapper over the Blockfrost API endpoints the bot needs. All
requests carry the ``project_id`` header and are retried with bounded
exponential backoff on transient failures (timeouts, ``429`` and ``5xx``),
honouring a ``Retry-After`` header when present.

The client is intentionally low-level: it returns parsed JSON (or raw text for
CBOR) and leaves mapping to domain objects to the sibling modules.
"""

from __future__ import annotations

import asyncio

import httpx

from bot.config import config
from bot.logging import get_logger

logger = get_logger("blockfrost.client")

# Blockfrost paginates at up to 100 items per page.
MAX_PAGE_SIZE = 100

# Retry policy for transient failures.
_MAX_ATTEMPTS = 5
_BACKOFF_BASE_SECONDS = 0.5
_BACKOFF_MAX_SECONDS = 30.0
_RETRY_STATUS = frozenset({408, 429, 500, 502, 503, 504})


class BlockfrostError(Exception):
    """Raised when a Blockfrost request ultimately fails (after retries)."""


class BlockfrostNotFound(BlockfrostError):
    """Raised for a ``404`` response — a resource that does not (yet) exist."""


def _parse_retry_after(value: str | None) -> float | None:
    """Parse a ``Retry-After`` header value in seconds. Ignores HTTP-date form."""
    if not value:
        return None
    try:
        seconds = float(value.strip())
    except ValueError:
        return None
    return max(0.0, seconds)


def _backoff_seconds(attempt: int, retry_after: float | None) -> float:
    """Return the delay before the next attempt (0-indexed ``attempt``)."""
    if retry_after is not None:
        return min(retry_after, _BACKOFF_MAX_SECONDS)
    return min(_BACKOFF_BASE_SECONDS * (2**attempt), _BACKOFF_MAX_SECONDS)


class BlockfrostClient:
    """Async client for the subset of Blockfrost endpoints the bot consumes."""

    def __init__(
        self,
        *,
        project_id: str | None = None,
        base_url: str | None = None,
        client: httpx.AsyncClient | None = None,
        sleep=asyncio.sleep,
    ) -> None:
        self._project_id = project_id if project_id is not None else config.blockfrost_project_id
        self._base_url = (base_url if base_url is not None else config.blockfrost_api_base_url).rstrip("/")
        self._sleep = sleep
        self._owns_client = client is None
        self._client = client or httpx.AsyncClient(
            base_url=self._base_url,
            timeout=httpx.Timeout(30.0),
        )

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    # -- low-level request with retry ---------------------------------------

    async def _request(self, path: str, *, params: dict | None = None) -> httpx.Response:
        last_exc: Exception | None = None
        headers = {"project_id": self._project_id}
        for attempt in range(_MAX_ATTEMPTS):
            try:
                response = await self._client.get(path, params=params, headers=headers)
            except httpx.TimeoutException as exc:
                last_exc = exc
                delay = _backoff_seconds(attempt, None)
                logger.warning("Blockfrost timeout on %s (attempt %d) — retrying in %.1fs", path, attempt + 1, delay)
                await self._sleep(delay)
                continue
            except httpx.HTTPError as exc:
                # Non-timeout transport errors (connection reset, DNS, etc).
                last_exc = exc
                delay = _backoff_seconds(attempt, None)
                logger.warning("Blockfrost transport error on %s (attempt %d): %s", path, attempt + 1, exc)
                await self._sleep(delay)
                continue

            if response.status_code == 404:
                raise BlockfrostNotFound(f"404 for {path}")

            if response.status_code in _RETRY_STATUS:
                retry_after = _parse_retry_after(response.headers.get("Retry-After"))
                delay = _backoff_seconds(attempt, retry_after)
                logger.warning(
                    "Blockfrost %s on %s (attempt %d) — retrying in %.1fs",
                    response.status_code,
                    path,
                    attempt + 1,
                    delay,
                )
                await self._sleep(delay)
                continue

            if response.status_code >= 400:
                raise BlockfrostError(f"{response.status_code} for {path}: {response.text[:200]}")

            return response

        raise BlockfrostError(f"Exhausted retries for {path}") from last_exc

    async def _get_json(self, path: str, *, params: dict | None = None):
        response = await self._request(path, params=params)
        return response.json()

    # -- governance feeds ---------------------------------------------------

    async def get_proposals(self, *, page: int = 1, count: int = MAX_PAGE_SIZE, order: str = "desc") -> list[dict]:
        return await self._get_json("/governance/proposals", params={"page": page, "count": count, "order": order})

    async def get_proposal(self, tx_hash: str, cert_index: int) -> dict:
        return await self._get_json(f"/governance/proposals/{tx_hash}/{cert_index}")

    async def get_proposal_metadata(self, tx_hash: str, cert_index: int) -> dict:
        return await self._get_json(f"/governance/proposals/{tx_hash}/{cert_index}/metadata")

    async def get_proposal_parameters(self, tx_hash: str, cert_index: int) -> dict:
        return await self._get_json(f"/governance/proposals/{tx_hash}/{cert_index}/parameters")

    async def get_committee_votes(
        self, *, page: int = 1, count: int = MAX_PAGE_SIZE, order: str = "desc"
    ) -> list[dict]:
        return await self._get_json(
            "/governance/committee/votes", params={"page": page, "count": count, "order": order}
        )

    async def get_committee(self) -> dict:
        return await self._get_json("/governance/committee")

    # -- epochs / blocks / txs ---------------------------------------------

    async def get_epoch_parameters(self, epoch: int) -> dict:
        return await self._get_json(f"/epochs/{epoch}/parameters")

    async def get_latest_epoch(self) -> dict:
        return await self._get_json("/epochs/latest")

    async def get_tx(self, tx_hash: str) -> dict:
        return await self._get_json(f"/txs/{tx_hash}")

    async def get_block(self, hash_or_number: str | int) -> dict:
        return await self._get_json(f"/blocks/{hash_or_number}")

    async def get_block_txs_cbor(
        self, hash_or_number: str | int, *, page: int = 1, count: int = MAX_PAGE_SIZE, order: str = "asc"
    ) -> list[dict]:
        return await self._get_json(
            f"/blocks/{hash_or_number}/txs/cbor", params={"page": page, "count": count, "order": order}
        )


# --- module-level singleton -------------------------------------------------

_client: BlockfrostClient | None = None


def get_client() -> BlockfrostClient:
    """Return the shared client, creating it lazily on first use."""
    global _client  # noqa: PLW0603
    if _client is None:
        _client = BlockfrostClient()
    return _client


def set_client(client: BlockfrostClient | None) -> None:
    """Override the shared client (used by the app lifespan and tests)."""
    global _client  # noqa: PLW0603
    _client = client


async def close_client() -> None:
    """Close and clear the shared client, if any."""
    global _client  # noqa: PLW0603
    if _client is not None:
        await _client.aclose()
        _client = None
