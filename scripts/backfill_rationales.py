"""Backfill governance rationale files from Blockfrost.

Paginates the governance-proposals and committee-votes feeds and archives each
rationale under ``rationales/``. Existing files are left untouched, so this is
safe to re-run and preserves previously archived rationales.

Reads configuration from .env (or environment variables) — only
``BLOCKFROST_PROJECT_ID`` (and optionally ``BLOCKFROST_API_BASE_URL``) is
required; Twitter/Firestore are not used.

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

from bot.blockfrost.client import MAX_PAGE_SIZE, BlockfrostClient, BlockfrostNotFound
from bot.blockfrost.committee import parse_committee_snapshot
from bot.logging import get_logger, setup_logging
from bot.metadata.fetcher import fetch_metadata, sanitise_url

setup_logging()
logger = get_logger("backfill")

RATIONALES_DIR = Path(__file__).resolve().parent.parent / "rationales"

PLACEHOLDER = {"error": "Failed to fetch rationale"}


def _save_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")


async def _paginate(fetch_page) -> list[dict]:
    """Collect every item from an asc-ordered feed."""
    items: list[dict] = []
    page = 1
    while True:
        batch = await fetch_page(page)
        if not batch:
            break
        items.extend(batch)
        if len(batch) < MAX_PAGE_SIZE:
            break
        page += 1
    return items


async def _proposal_metadata(client: BlockfrostClient, tx_hash: str, cert_index: int) -> dict | None:
    """Return a proposal's rationale JSON (Blockfrost first, IPFS fallback)."""
    try:
        meta = await client.get_proposal_metadata(tx_hash, cert_index)
    except BlockfrostNotFound:
        return None
    json_metadata = meta.get("json_metadata")
    if isinstance(json_metadata, dict):
        return json_metadata
    url = meta.get("url")
    if url:
        return fetch_metadata(sanitise_url(url))
    return None


async def _backfill_gov_actions(client: BlockfrostClient) -> tuple[int, int, int]:
    """Archive all governance-action rationales. Returns (total, skipped, failed)."""
    proposals = await _paginate(lambda page: client.get_proposals(page=page, order="asc"))
    logger.info("Found %d governance proposals", len(proposals))

    skipped = 0
    failed = 0

    for i, proposal in enumerate(proposals, 1):
        tx_hash = proposal["tx_hash"]
        cert_index = proposal["cert_index"]
        target = RATIONALES_DIR / f"{tx_hash}_{cert_index}" / "action.json"

        if target.exists():
            skipped += 1
            continue

        metadata = await _proposal_metadata(client, tx_hash, cert_index)
        if metadata:
            _save_json(target, metadata)
        else:
            _save_json(target, {**PLACEHOLDER, "tx_hash": tx_hash, "cert_index": cert_index})
            failed += 1

        if i % 50 == 0:
            logger.info("Gov actions progress: %d / %d", i, len(proposals))

    return len(proposals), skipped, failed


async def _backfill_cc_votes(client: BlockfrostClient) -> tuple[int, int, int]:
    """Archive all CC vote rationales. Returns (total, skipped, failed)."""
    snapshot = parse_committee_snapshot(await client.get_committee())
    votes = await _paginate(lambda page: client.get_committee_votes(page=page, order="asc"))
    logger.info("Found %d committee votes", len(votes))

    skipped = 0
    failed = 0

    for i, vote in enumerate(votes, 1):
        ga_tx_hash = vote["proposal_tx_hash"]
        ga_index = vote["proposal_index"]
        hot_id = vote.get("voter_hot_id", "")
        voter_key = (snapshot.cold_hex_for_hot(hot_id) if snapshot else None) or hot_id

        target = RATIONALES_DIR / f"{ga_tx_hash}_{ga_index}" / "cc_votes" / f"{voter_key}.json"

        if target.exists():
            skipped += 1
            continue

        url = vote.get("metadata_url")
        metadata = fetch_metadata(sanitise_url(url)) if url else None

        if metadata:
            _save_json(target, metadata)
        else:
            _save_json(target, {**PLACEHOLDER, "metadata_url": url})
            failed += 1

        if i % 50 == 0:
            logger.info("CC votes progress: %d / %d", i, len(votes))

    return len(votes), skipped, failed


async def _main() -> None:
    logger.info("Starting rationale backfill...")
    logger.info("Output directory: %s", RATIONALES_DIR)

    client = BlockfrostClient()
    try:
        ga_total, ga_skipped, ga_failed = await _backfill_gov_actions(client)
        logger.info(
            "Gov actions — total: %d, fetched: %d, skipped: %d, failed: %d",
            ga_total,
            ga_total - ga_skipped - ga_failed,
            ga_skipped,
            ga_failed,
        )

        cc_total, cc_skipped, cc_failed = await _backfill_cc_votes(client)
        logger.info(
            "CC votes — total: %d, fetched: %d, skipped: %d, failed: %d",
            cc_total,
            cc_total - cc_skipped - cc_failed,
            cc_skipped,
            cc_failed,
        )
    finally:
        await client.aclose()

    total_failed = ga_failed + cc_failed
    if total_failed:
        logger.warning("Completed with %d failed fetches (placeholders created)", total_failed)
    else:
        logger.info("Backfill complete — all rationales fetched successfully")

    sys.exit(1 if total_failed else 0)


if __name__ == "__main__":
    asyncio.run(_main())
