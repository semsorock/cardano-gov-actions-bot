from __future__ import annotations

import asyncio
from collections.abc import Callable

import psycopg

from bot.config import config
from bot.db.queries import (
    QUERY_ACTIVE_COMMITTEE_QUORUM,
    QUERY_ALL_CC_VOTES,
    QUERY_ALL_GOV_ACTIONS,
    QUERY_BLOCK_EPOCH,
    QUERY_CC_VOTES,
    QUERY_GOV_ACTIONS,
    QUERY_LATEST_THRESHOLDS,
    QUERY_PARAM_CHANGE_GROUPS,
    QUERY_TREASURY_DONATIONS,
)
from bot.logging import get_logger
from bot.models import CcVote, GovAction, TreasuryDonation
from bot.thresholds import (
    EpochThresholds,
    GovThresholds,
    ParamChangeGroups,
    compute_thresholds,
)

logger = get_logger("db_repository")

_conn: psycopg.AsyncConnection | None = None
_lock = asyncio.Lock()
_effective_db_url: str = config.db_sync_url
_db_url_provider: Callable[[], str] | None = None
_conn_db_url: str | None = None


def set_db_url(url: str) -> None:
    """Override the DB connection URL (e.g. after SSH tunnel setup)."""
    global _effective_db_url
    _effective_db_url = url


def set_db_url_provider(provider: Callable[[], str] | None) -> None:
    """Set a callable that returns the current effective DB URL."""
    global _db_url_provider
    _db_url_provider = provider


def _resolve_db_url() -> str:
    """Return the current DB URL, consulting the provider when configured."""
    global _effective_db_url
    if _db_url_provider is not None:
        _effective_db_url = _db_url_provider()
    return _effective_db_url


async def _reset_conn() -> None:
    """Close and clear the shared connection, ignoring close errors."""
    global _conn, _conn_db_url
    conn = _conn
    _conn = None
    _conn_db_url = None
    if conn is None or conn.closed:
        return
    try:
        await conn.close()
    except Exception:
        logger.warning("Failed to close database connection cleanly", exc_info=True)


async def _get_conn() -> psycopg.AsyncConnection:
    """Return the shared connection, creating it lazily on first use."""
    global _conn, _conn_db_url
    db_url = _resolve_db_url()
    if _conn is not None and not _conn.closed and _conn_db_url == db_url:
        return _conn

    if _conn is not None:
        await _reset_conn()

    _conn = await psycopg.AsyncConnection.connect(
        conninfo=db_url,
        autocommit=True,
    )
    _conn_db_url = db_url
    return _conn


async def close_conn() -> None:
    """Close the shared connection, if open."""
    async with _lock:
        await _reset_conn()


async def _query_once(sql: str, params: tuple) -> list[tuple]:
    conn = await _get_conn()
    async with conn.cursor() as cur:
        await cur.execute(sql, params)
        return await cur.fetchall()


async def _query(sql: str, params: tuple) -> list[tuple]:
    """Execute a read query and return all rows.

    Acquires the shared lock so only one query runs at a time.
    Other callers await the lock asynchronously (non-blocking).
    Retries once after resetting the shared connection, which is safe because
    all repository queries are read-only.
    """
    async with _lock:
        for attempt in range(2):
            try:
                return await _query_once(sql, params)
            except psycopg.Error:
                await _reset_conn()
                if attempt == 0:
                    logger.warning("Database query failed; resetting connection and retrying once", exc_info=True)
                    continue
                raise
            except Exception:
                await _reset_conn()
                raise
    raise RuntimeError("Database query retry loop exited unexpectedly")


async def get_gov_actions(block_no: int) -> list[GovAction]:
    rows = await _query(QUERY_GOV_ACTIONS, (block_no,))
    return [
        GovAction(
            tx_hash=row[0],
            action_type=row[1],
            index=row[2],
            raw_url=row[3],
        )
        for row in rows
    ]


async def _get_epoch_thresholds() -> EpochThresholds | None:
    """Fetch the current epoch's governance voting thresholds."""
    rows = await _query(QUERY_LATEST_THRESHOLDS, ())
    if not rows:
        return None
    return EpochThresholds(*rows[0])


async def _get_committee_quorum() -> float | None:
    """Fetch the active Constitutional Committee's approval ratio."""
    rows = await _query(QUERY_ACTIVE_COMMITTEE_QUORUM, ())
    return rows[0][0] if rows and rows[0] else None


async def _get_param_change_groups(action: GovAction) -> ParamChangeGroups | None:
    """Fetch which protocol-parameter groups a ParameterChange action touches."""
    rows = await _query(QUERY_PARAM_CHANGE_GROUPS, (action.tx_hash, action.index))
    if not rows:
        return None
    network, economic, technical, governance, security = rows[0]
    return ParamChangeGroups(
        network=bool(network),
        economic=bool(economic),
        technical=bool(technical),
        governance=bool(governance),
        security=bool(security),
    )


async def get_gov_thresholds(action: GovAction) -> GovThresholds | None:
    """Return the ratification thresholds applicable to a governance action.

    Reads live protocol parameters and committee quorum from DB-Sync. Returns
    ``None`` if thresholds are unavailable (e.g. pre-Conway data), so callers
    can omit the line rather than show wrong numbers.
    """
    params = await _get_epoch_thresholds()
    if params is None:
        return None

    committee_quorum = await _get_committee_quorum()
    param_groups = None
    if action.action_type == "ParameterChange":
        param_groups = await _get_param_change_groups(action)

    return compute_thresholds(
        action.action_type,
        params,
        committee_quorum,
        param_groups=param_groups,
    )


async def get_cc_votes(block_no: int) -> list[CcVote]:
    rows = await _query(QUERY_CC_VOTES, (block_no,))
    return [
        CcVote(
            ga_tx_hash=row[0],
            ga_index=row[1],
            vote_tx_hash=row[2],
            voter_hash=row[3],
            vote=row[4],
            raw_url=row[5],
        )
        for row in rows
    ]


async def get_treasury_donations(epoch_no: int) -> list[TreasuryDonation]:
    rows = await _query(QUERY_TREASURY_DONATIONS, (epoch_no,))
    return [
        TreasuryDonation(
            block_no=row[0],
            tx_hash=row[1],
            amount_lovelace=row[2],
        )
        for row in rows
    ]


async def get_block_epoch(block_hash: str) -> int | None:
    """Return the epoch number for a block identified by its hex hash."""
    rows = await _query(QUERY_BLOCK_EPOCH, (block_hash,))
    return rows[0][0] if rows else None


async def get_all_gov_actions() -> list[GovAction]:
    """Return all governance actions (for backfill)."""
    rows = await _query(QUERY_ALL_GOV_ACTIONS, ())
    return [GovAction(tx_hash=row[0], action_type=row[1], index=row[2], raw_url=row[3]) for row in rows]


async def get_all_cc_votes() -> list[CcVote]:
    """Return all CC member votes (for backfill)."""
    rows = await _query(QUERY_ALL_CC_VOTES, ())
    return [
        CcVote(
            ga_tx_hash=row[0],
            ga_index=row[1],
            vote_tx_hash=row[2],
            voter_hash=row[3],
            vote=row[4],
            raw_url=row[5],
        )
        for row in rows
    ]
