"""Backfill governance rationale files from DB-Sync.

Reads configuration from .env (or environment variables).

Usage:
    uv run python scripts/backfill_rationales.py
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

# Ensure the project root is on the import path.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from bot.db.repository import get_all_cc_votes, get_all_gov_actions
from bot.logging import get_logger, setup_logging
from bot.metadata.fetcher import fetch_metadata, sanitise_url

setup_logging()
logger = get_logger("backfill")

RATIONALES_DIR = Path(__file__).resolve().parent.parent / "rationales"

PLACEHOLDER = {"error": "Failed to fetch rationale"}


def _save_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")


async def _backfill_gov_actions() -> tuple[int, int, int]:
    """Fetch and save all governance action rationales. Returns (total, skipped, failed)."""
    actions = await get_all_gov_actions()
    logger.info("Found %d governance actions", len(actions))

    skipped = 0
    failed = 0

    for i, action in enumerate(actions, 1):
        action_dir = RATIONALES_DIR / f"{action.tx_hash}_{action.index}"
        target = action_dir / "action.json"

        if target.exists():
            skipped += 1
            continue

        url = sanitise_url(action.raw_url)
        metadata = fetch_metadata(url)

        if metadata:
            _save_json(target, metadata)
        else:
            _save_json(target, {**PLACEHOLDER, "url": url})
            failed += 1

        if i % 50 == 0:
            logger.info("Gov actions progress: %d / %d", i, len(actions))

    return len(actions), skipped, failed


async def _backfill_cc_votes() -> tuple[int, int, int]:
    """Fetch and save all CC vote rationales. Returns (total, skipped, failed)."""
    votes = await get_all_cc_votes()
    logger.info("Found %d CC votes", len(votes))

    skipped = 0
    failed = 0

    for i, vote in enumerate(votes, 1):
        action_dir = RATIONALES_DIR / f"{vote.ga_tx_hash}_{vote.ga_index}"
        target = action_dir / "cc_votes" / f"{vote.voter_hash}.json"

        if target.exists():
            skipped += 1
            continue

        url = sanitise_url(vote.raw_url)
        metadata = fetch_metadata(url)

        if metadata:
            _save_json(target, metadata)
        else:
            _save_json(target, {**PLACEHOLDER, "url": url})
            failed += 1

        if i % 50 == 0:
            logger.info("CC votes progress: %d / %d", i, len(votes))

    return len(votes), skipped, failed


async def _main() -> None:
    logger.info("Starting rationale backfill...")
    logger.info("Output directory: %s", RATIONALES_DIR)

    ga_total, ga_skipped, ga_failed = await _backfill_gov_actions()
    logger.info(
        "Gov actions — total: %d, fetched: %d, skipped: %d, failed: %d",
        ga_total,
        ga_total - ga_skipped - ga_failed,
        ga_skipped,
        ga_failed,
    )

    cc_total, cc_skipped, cc_failed = await _backfill_cc_votes()
    logger.info(
        "CC votes — total: %d, fetched: %d, skipped: %d, failed: %d",
        cc_total,
        cc_total - cc_skipped - cc_failed,
        cc_skipped,
        cc_failed,
    )

    total_failed = ga_failed + cc_failed
    if total_failed:
        logger.warning("Completed with %d failed fetches (placeholders created)", total_failed)
    else:
        logger.info("Backfill complete — all rationales fetched successfully")

    sys.exit(1 if total_failed else 0)


if __name__ == "__main__":
    asyncio.run(_main())
