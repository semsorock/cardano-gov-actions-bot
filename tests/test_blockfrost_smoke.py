"""Optional credentialed mainnet smoke test.

Skipped by default. To run against real Blockfrost mainnet:

    RUN_BLOCKFROST_SMOKE=1 BLOCKFROST_PROJECT_ID=mainnet... uv run pytest tests/test_blockfrost_smoke.py -v

Validates that the live API shapes still match what the adapters expect. Kept
out of CI (network + credentials) via the environment guard below.
"""

import os

import pytest

from bot.blockfrost.client import BlockfrostClient
from bot.blockfrost.committee import parse_committee_snapshot
from bot.blockfrost.feeds import collect_new_items
from bot.blockfrost.mapping import committee_vote_key, proposal_key
from bot.thresholds import epoch_thresholds_from_params

pytestmark = pytest.mark.skipif(
    not os.environ.get("RUN_BLOCKFROST_SMOKE"),
    reason="set RUN_BLOCKFROST_SMOKE=1 (and BLOCKFROST_PROJECT_ID) to run the mainnet smoke test",
)


@pytest.fixture
async def client():
    c = BlockfrostClient()
    try:
        yield c
    finally:
        await c.aclose()


@pytest.mark.asyncio
async def test_proposals_feed_shape(client):
    proposals = await client.get_proposals(count=3, order="desc")
    assert isinstance(proposals, list)
    for p in proposals:
        assert {"id", "tx_hash", "cert_index", "governance_type"} <= p.keys()
        assert proposal_key(p)


@pytest.mark.asyncio
async def test_committee_votes_feed_shape(client):
    votes = await client.get_committee_votes(count=3, order="desc")
    assert isinstance(votes, list)
    for v in votes:
        assert {"tx_hash", "proposal_tx_hash", "proposal_index", "voter_hot_id", "vote"} <= v.keys()
        assert committee_vote_key(v)


@pytest.mark.asyncio
async def test_committee_snapshot_shape(client):
    snapshot = parse_committee_snapshot(await client.get_committee())
    assert snapshot is not None
    assert snapshot.quorum is None or 0 < snapshot.quorum <= 1


@pytest.mark.asyncio
async def test_epoch_parameters_shape(client):
    latest = await client.get_latest_epoch()
    params = await client.get_epoch_parameters(latest["epoch"])
    thresholds = epoch_thresholds_from_params(params)
    # Conway epochs expose DRep/SPO thresholds.
    assert thresholds.dvt_treasury_withdrawal is not None


@pytest.mark.asyncio
async def test_feed_scan_bootstraps(client):
    scan = await collect_new_items(
        lambda page: client.get_proposals(page=page, order="desc"),
        None,
        proposal_key,
    )
    assert scan.bootstrapped is True
    assert scan.watermark is not None
