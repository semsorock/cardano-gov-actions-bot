from __future__ import annotations

import asyncio

import psycopg

from bot.config import config
from bot.db.queries import (
    QUERY_ACTIVE_GOV_ACTIONS,
    QUERY_ALL_CC_VOTES,
    QUERY_ALL_GOV_ACTIONS,
    QUERY_BLOCK_EPOCH,
    QUERY_CC_VOTES,
    QUERY_GA_EXPIRATIONS,
    QUERY_GOV_ACTIONS,
    QUERY_TREASURY_DONATIONS,
    QUERY_VOTING_STATS,
)
from bot.models import ActiveGovAction, CcVote, GaExpiration, GovAction, TreasuryDonation, VotingProgress

_conn: psycopg.AsyncConnection | None = None
_lock = asyncio.Lock()


async def _get_conn() -> psycopg.AsyncConnection:
    """Return the shared connection, creating it lazily on first use."""
    global _conn
    if _conn is None or _conn.closed:
        _conn = await psycopg.AsyncConnection.connect(
            conninfo=config.db_sync_url,
            autocommit=True,
        )
    return _conn


async def _query(sql: str, params: tuple) -> list[tuple]:
    """Execute a read query and return all rows.

    Acquires the shared lock so only one query runs at a time.
    Other callers await the lock asynchronously (non-blocking).
    """
    async with _lock:
        conn = await _get_conn()
        try:
            async with conn.cursor() as cur:
                await cur.execute(sql, params)
                return await cur.fetchall()
        except Exception:
            # Connection may be in a bad state.  Close it so the next
            # call to _get_conn() creates a fresh one.
            global _conn
            await conn.close()
            _conn = None
            raise


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


async def get_ga_expirations(epoch_no: int) -> list[GaExpiration]:
    rows = await _query(QUERY_GA_EXPIRATIONS, (epoch_no,))
    return [GaExpiration(tx_hash=row[0], index=row[1]) for row in rows]


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


async def get_active_gov_actions(epoch_no: int) -> list[ActiveGovAction]:
    """Return all active governance actions for the given epoch."""
    rows = await _query(QUERY_ACTIVE_GOV_ACTIONS, (epoch_no, epoch_no))
    return [ActiveGovAction(tx_hash=row[0], index=row[1]) for row in rows]


async def get_voting_stats(tx_hash: str, index: int, epoch_no: int) -> VotingProgress | None:
    """Return voting statistics for a specific governance action."""
    rows = await _query(QUERY_VOTING_STATS, (epoch_no, tx_hash, index, epoch_no, tx_hash, index))
    if not rows:
        return None
    row = rows[0]
    return VotingProgress(
        tx_hash=tx_hash,
        index=index,
        cc_voted=row[0],
        cc_total=row[1],
        drep_voted=row[2],
        drep_total=row[3],
    )
