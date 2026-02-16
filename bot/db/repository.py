from __future__ import annotations

from psycopg2 import pool

from bot.config import config
from bot.db.queries import (
    QUERY_ALL_CC_VOTES,
    QUERY_ALL_GOV_ACTIONS,
    QUERY_BLOCK_EPOCH,
    QUERY_CC_VOTES,
    QUERY_GA_EXPIRATIONS,
    QUERY_GOV_ACTIONS,
    QUERY_TREASURY_DONATIONS,
)
from bot.models import CcVote, GaExpiration, GovAction, TreasuryDonation

_pool: pool.SimpleConnectionPool | None = None


def _get_pool() -> pool.SimpleConnectionPool:
    """Lazily initialise the connection pool on first use."""
    global _pool
    if _pool is None:
        _pool = pool.SimpleConnectionPool(minconn=1, maxconn=1, dsn=config.db_sync_url)
    return _pool


def _query(sql: str, params: tuple) -> list[tuple]:
    """Execute a read query and return all rows."""
    db_pool = _get_pool()
    conn = db_pool.getconn()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            return cur.fetchall()
    finally:
        db_pool.putconn(conn)


def get_gov_actions(block_no: int) -> list[GovAction]:
    rows = _query(QUERY_GOV_ACTIONS, (block_no,))
    return [
        GovAction(
            tx_hash=row[0],
            action_type=row[1],
            index=row[2],
            raw_url=row[3],
        )
        for row in rows
    ]


def get_cc_votes(block_no: int) -> list[CcVote]:
    rows = _query(QUERY_CC_VOTES, (block_no,))
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


def get_ga_expirations(epoch_no: int) -> list[GaExpiration]:
    rows = _query(QUERY_GA_EXPIRATIONS, (epoch_no,))
    return [GaExpiration(tx_hash=row[0], index=row[1]) for row in rows]


def get_treasury_donations(epoch_no: int) -> list[TreasuryDonation]:
    rows = _query(QUERY_TREASURY_DONATIONS, (epoch_no,))
    return [
        TreasuryDonation(
            block_no=row[0],
            tx_hash=row[1],
            amount_lovelace=row[2],
        )
        for row in rows
    ]


def get_block_epoch(block_hash: str) -> int | None:
    """Return the epoch number for a block identified by its hex hash."""
    rows = _query(QUERY_BLOCK_EPOCH, (block_hash,))
    return rows[0][0] if rows else None


def get_all_gov_actions() -> list[GovAction]:
    """Return all governance actions (for backfill)."""
    rows = _query(QUERY_ALL_GOV_ACTIONS, ())
    return [GovAction(tx_hash=row[0], action_type=row[1], index=row[2], raw_url=row[3]) for row in rows]


def get_all_cc_votes() -> list[CcVote]:
    """Return all CC member votes (for backfill)."""
    rows = _query(QUERY_ALL_CC_VOTES, ())
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
