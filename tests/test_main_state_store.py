"""Orchestration tests for the webhook handler and feed processing."""

import os

import pytest

os.environ.setdefault("BLOCKFROST_PROJECT_ID", "test-project-id")

from bot import main
from bot.blockfrost import client as bf_client
from bot.blockfrost.committee import parse_committee_snapshot


class FakeBF:
    """Minimal stand-in for BlockfrostClient used by the orchestration tests."""

    def __init__(self, **responses):
        self._r = responses

    async def get_proposals(self, *, page=1, count=100, order="desc"):
        return self._r.get("proposals_pages", {}).get(page, [])

    async def get_committee_votes(self, *, page=1, count=100, order="desc"):
        return self._r.get("committee_votes_pages", {}).get(page, [])

    async def get_committee(self):
        return self._r.get("committee")

    async def get_epoch_parameters(self, epoch):
        return self._r.get("epoch_params")

    async def get_proposal_metadata(self, tx_hash, cert_index):
        return self._r.get("proposal_metadata", {}).get((tx_hash, cert_index), {"url": "", "json_metadata": None})

    async def get_proposal_parameters(self, tx_hash, cert_index):
        return self._r.get("proposal_parameters", {}).get((tx_hash, cert_index), {"parameters": {}})

    async def get_block_txs_cbor(self, ref, *, page=1, count=100, order="asc"):
        return self._r.get("block_txs_cbor", {}).get(page, [])


@pytest.fixture(autouse=True)
def reset_main_state():
    main._epoch_params_cache.clear()
    main._committee_cache.clear()
    bf_client.set_client(None)
    yield
    main._epoch_params_cache.clear()
    main._committee_cache.clear()
    bf_client.set_client(None)


COMMITTEE = {
    "is_dissolved": False,
    "quorum": {"numerator": 2, "denominator": 3},
    "members": [
        {
            "cc_cold_hex": "cold_aa",
            "cc_hot_id": "cc_hot1abc",
            "cc_hot_hex": "hot_aa",
            "status": "authorized",
            "expiration_epoch": 999,
        }
    ],
}

EPOCH_PARAMS = {
    "dvt_treasury_withdrawal": 0.67,
    "dvt_hard_fork_initiation": 0.6,
    "pvt_hard_fork_initiation": 0.51,
    "committee_min_size": "1",
}


# ---------------------------------------------------------------------------
# Governance action processing
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_process_one_proposal_saves_action_state(monkeypatch):
    async def _fake_meta(tx_hash, cert_index):
        return "ipfs://x", {"body": {"title": "t"}}

    async def _fake_thresholds(action, item, epoch_hint):
        return None

    monkeypatch.setattr(main, "_resolve_proposal_metadata", _fake_meta)
    monkeypatch.setattr(main, "_resolve_thresholds", _fake_thresholds)
    monkeypatch.setattr(main, "validate_gov_action_rationale", lambda *_: [])
    monkeypatch.setattr(main, "format_gov_action_tweet", lambda *_: "tweet text")
    monkeypatch.setattr(main, "post_tweet", lambda *_: "tweet-123")

    save_calls = []
    monkeypatch.setattr(
        main,
        "save_action_tweet_id",
        lambda tx_hash, index, tweet_id, source_block=None: save_calls.append((tx_hash, index, tweet_id, source_block)),
    )

    item = {"tx_hash": "aa", "cert_index": 0, "governance_type": "treasury_withdrawals"}
    await main._process_one_proposal(item, epoch_hint=None, block_no=321)

    assert save_calls == [("aa", 0, "tweet-123", 321)]


@pytest.mark.asyncio
async def test_process_one_proposal_shows_current_thresholds(monkeypatch):
    """End-to-end threshold resolution surfaces a 'Current thresholds:' line."""
    bf_client.set_client(
        FakeBF(
            committee=COMMITTEE,
            epoch_params=EPOCH_PARAMS,
            proposal_metadata={("aa", 0): {"url": "ipfs://x", "json_metadata": {"body": {"title": "T"}}}},
        )
    )
    monkeypatch.setattr(main, "validate_gov_action_rationale", lambda *_: [])
    monkeypatch.setattr(main, "save_committee_snapshot", lambda *a, **k: None)
    monkeypatch.setattr(main, "save_action_tweet_id", lambda *a, **k: None)

    posted = []
    monkeypatch.setattr(main, "post_tweet", lambda text: posted.append(text))

    item = {"tx_hash": "aa", "cert_index": 0, "governance_type": "treasury_withdrawals"}
    await main._process_one_proposal(item, epoch_hint=500, block_no=1)

    assert len(posted) == 1
    # Treasury withdrawal: DRep + CC vote, no SPO. Quorum 2/3 = 67%.
    assert "Current thresholds: DRep 67% · CC 67%" in posted[0]


@pytest.mark.asyncio
async def test_resolve_proposal_metadata_prefers_json_then_ipfs_fallback(monkeypatch):
    bf_client.set_client(
        FakeBF(
            proposal_metadata={
                ("j", 0): {"url": "ipfs://a", "json_metadata": {"body": {"title": "J"}}},
                ("n", 0): {"url": "ipfs://b", "json_metadata": None},
            }
        )
    )
    monkeypatch.setattr(main, "fetch_metadata", lambda url: {"body": {"title": "fetched"}})
    monkeypatch.setattr(main, "sanitise_url", lambda url: url)

    _, meta = await main._resolve_proposal_metadata("j", 0)
    assert meta == {"body": {"title": "J"}}  # Blockfrost json_metadata preferred

    _, meta2 = await main._resolve_proposal_metadata("n", 0)
    assert meta2 == {"body": {"title": "fetched"}}  # fell back to IPFS


@pytest.mark.asyncio
async def test_resolve_thresholds_degrades_when_committee_unavailable(monkeypatch):
    # Epoch params present but no committee snapshot -> omit the threshold line.
    bf_client.set_client(FakeBF(committee=None, epoch_params=EPOCH_PARAMS))
    monkeypatch.setattr(main, "save_committee_snapshot", lambda *a, **k: None)

    action = main.build_gov_action(tx_hash="aa", cert_index=0, governance_type="treasury_withdrawals")
    result = await main._resolve_thresholds(action, {"tx_hash": "aa", "cert_index": 0}, epoch_hint=500)
    assert result is None


@pytest.mark.asyncio
async def test_process_new_proposals_bootstraps_watermark(monkeypatch):
    bf_client.set_client(FakeBF(proposals_pages={1: [{"id": "g3"}, {"id": "g2"}, {"id": "g1"}]}))
    monkeypatch.setattr(main, "get_feed_watermark", lambda name: None)

    set_calls = []
    monkeypatch.setattr(main, "set_feed_watermark", lambda name, wm: set_calls.append((name, wm)))

    processed = []

    async def _fake_one(item, **kwargs):
        processed.append(item)

    monkeypatch.setattr(main, "_process_one_proposal", _fake_one)

    await main._process_new_proposals(epoch_hint=500, block_no=1)

    assert processed == []  # bootstrap processes nothing
    assert set_calls == [(main.PROPOSALS_FEED, "g3")]


@pytest.mark.asyncio
async def test_process_new_proposals_skips_archived_duplicate(monkeypatch):
    # Feed has a new item g2 and the already-seen g1 (watermark).
    bf_client.set_client(
        FakeBF(
            proposals_pages={
                1: [
                    {"id": "g2", "tx_hash": "bb", "cert_index": 0, "governance_type": "info_action"},
                    {"id": "g1", "tx_hash": "aa", "cert_index": 0, "governance_type": "info_action"},
                ]
            }
        )
    )
    monkeypatch.setattr(main, "get_feed_watermark", lambda name: "g1")
    # Simulate g2 already processed (duplicate delivery / retry).
    monkeypatch.setattr(main, "is_action_archived", lambda tx, idx: True)

    processed = []

    async def _fake_one(item, **kwargs):
        processed.append(item)

    monkeypatch.setattr(main, "_process_one_proposal", _fake_one)

    set_calls = []
    monkeypatch.setattr(main, "set_feed_watermark", lambda name, wm: set_calls.append((name, wm)))

    await main._process_new_proposals(epoch_hint=500, block_no=1)

    assert processed == []  # archived item skipped, not re-posted
    assert set_calls == [(main.PROPOSALS_FEED, "g2")]  # watermark still advances


# ---------------------------------------------------------------------------
# CC vote processing
# ---------------------------------------------------------------------------


def _cc_item(**overrides):
    item = {
        "tx_hash": "vt",
        "proposal_tx_hash": "pt",
        "proposal_index": 1,
        "voter_hot_id": "cc_hot1abc",
        "vote": "yes",
        "metadata_url": "ipfs://r",
    }
    item.update(overrides)
    return item


@pytest.mark.asyncio
async def test_process_cc_vote_posts_regular_tweet_when_no_action_tweet(monkeypatch):
    snapshot = parse_committee_snapshot(COMMITTEE)

    monkeypatch.setattr(main, "fetch_metadata", lambda *_: {"body": {"summary": "s"}})
    monkeypatch.setattr(main, "sanitise_url", lambda url: url)
    monkeypatch.setattr(main, "validate_cc_vote_rationale", lambda *_: [])
    monkeypatch.setattr(main, "get_action_tweet_id", lambda *_: None)
    monkeypatch.setattr(main, "get_x_handle_for_voter_hash", lambda *_: None)
    monkeypatch.setattr(main, "format_cc_vote_tweet", lambda *a, **k: "cc vote tweet")

    def _unexpected_quote(*_a, **_k):
        raise AssertionError("unexpected post_quote_tweet")

    monkeypatch.setattr(main, "post_quote_tweet", _unexpected_quote)

    posts = []
    monkeypatch.setattr(main, "post_tweet", lambda text: posts.append(text))

    archived = []
    monkeypatch.setattr(
        main,
        "mark_cc_vote_archived",
        lambda vote_key, **kwargs: archived.append((vote_key, kwargs)),
    )

    item = _cc_item()
    vote_key = "vt_pt_1_cc_hot1abc"
    await main._process_one_cc_vote(item, vote_key, snapshot, block_no=654)

    assert posts == ["cc vote tweet"]
    assert archived[0][0] == vote_key
    assert archived[0][1]["voter_hash"] == "cold_aa"  # resolved hot->cold
    assert archived[0][1]["source_block"] == 654


@pytest.mark.asyncio
async def test_process_cc_vote_quote_tweets_when_action_known(monkeypatch):
    snapshot = parse_committee_snapshot(COMMITTEE)

    monkeypatch.setattr(main, "fetch_metadata", lambda *_: None)
    monkeypatch.setattr(main, "sanitise_url", lambda url: url)
    monkeypatch.setattr(main, "validate_cc_vote_rationale", lambda *_: [])
    monkeypatch.setattr(main, "get_action_tweet_id", lambda *_: "999")
    monkeypatch.setattr(main, "get_x_handle_for_voter_hash", lambda *_: "@CCMember")
    monkeypatch.setattr(main, "format_cc_vote_tweet", lambda *a, **k: "cc vote tweet")
    monkeypatch.setattr(main, "mark_cc_vote_archived", lambda *a, **k: None)

    quote_calls = []
    monkeypatch.setattr(main, "post_quote_tweet", lambda text, quote_id: quote_calls.append((text, quote_id)))
    monkeypatch.setattr(main, "post_tweet", lambda *_: (_ for _ in ()).throw(AssertionError("should quote")))

    await main._process_one_cc_vote(_cc_item(), "vt_pt_1_cc_hot1abc", snapshot, block_no=1)

    assert quote_calls == [("cc vote tweet", "999")]


# ---------------------------------------------------------------------------
# Treasury epoch summaries
# ---------------------------------------------------------------------------


def test_maybe_summarize_epochs_posts_completed_epoch(monkeypatch):
    monkeypatch.setattr(main, "get_checkpoint", lambda name: {"last_epoch": 509})
    monkeypatch.setattr(main, "get_donation_start_epoch", lambda: 500)
    monkeypatch.setattr(
        main, "get_treasury_epoch", lambda epoch: {"donations": {"aa": 1_000_000}} if epoch == 509 else None
    )

    posts = []
    monkeypatch.setattr(main, "post_tweet", lambda text: posts.append(text))
    summarized = []
    monkeypatch.setattr(main, "mark_treasury_epoch_summarized", lambda epoch: summarized.append(epoch))

    main._maybe_summarize_epochs(510)

    assert summarized == [509]
    assert len(posts) == 1
    assert "Treasury Donations Summary" in posts[0]


def test_maybe_summarize_epochs_skips_partial_start_epoch(monkeypatch):
    # We cold-started in epoch 509, so its total is partial — skip it.
    monkeypatch.setattr(main, "get_checkpoint", lambda name: {"last_epoch": 509})
    monkeypatch.setattr(main, "get_donation_start_epoch", lambda: 509)

    calls = []
    monkeypatch.setattr(main, "get_treasury_epoch", lambda epoch: calls.append(epoch))
    monkeypatch.setattr(main, "post_tweet", lambda text: calls.append(("post", text)))

    main._maybe_summarize_epochs(510)

    assert calls == []  # nothing summarised


def test_maybe_summarize_epochs_noop_when_no_transition(monkeypatch):
    monkeypatch.setattr(main, "get_checkpoint", lambda name: {"last_epoch": 510})
    monkeypatch.setattr(main, "get_donation_start_epoch", lambda: 500)
    called = []
    monkeypatch.setattr(main, "get_treasury_epoch", lambda epoch: called.append(epoch))

    main._maybe_summarize_epochs(510)  # same epoch, no boundary crossed
    assert called == []


# ---------------------------------------------------------------------------
# Webhook handler
# ---------------------------------------------------------------------------


async def _post_webhook(monkeypatch, payload):
    from httpx import ASGITransport, AsyncClient

    transport = ASGITransport(app=main.app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        return await client.post("/", json=payload, headers={"Blockfrost-Signature": "sig"})


@pytest.mark.asyncio
async def test_handle_webhook_updates_checkpoint(monkeypatch):
    monkeypatch.setattr(main, "verify_webhook_signature", lambda *_: True)

    async def _noop(*_):
        pass

    monkeypatch.setattr(main, "_process_governance", _noop)
    monkeypatch.setattr(main, "_process_treasury", _noop)

    checkpoint_calls = []
    monkeypatch.setattr(
        main,
        "set_checkpoint",
        lambda name, block_no, epoch_no=None: checkpoint_calls.append((name, block_no, epoch_no)),
    )

    payload = {"payload": {"height": 111, "epoch": 222, "hash": "blockhash"}}
    response = await _post_webhook(monkeypatch, payload)

    assert response.status_code == 200
    assert checkpoint_calls == [("blockfrost_main", 111, 222)]


@pytest.mark.asyncio
async def test_handle_webhook_returns_500_when_primary_fails(monkeypatch):
    monkeypatch.setattr(main, "verify_webhook_signature", lambda *_: True)

    async def _boom(*_):
        raise RuntimeError("blockfrost down")

    monkeypatch.setattr(main, "_process_governance", _boom)

    checkpoint_calls = []
    monkeypatch.setattr(main, "set_checkpoint", lambda **k: checkpoint_calls.append(k))

    payload = {"payload": {"height": 111, "epoch": 222, "hash": "blockhash"}}
    response = await _post_webhook(monkeypatch, payload)

    assert response.status_code == 500
    assert checkpoint_calls == []  # watermark/checkpoint not advanced on failure


@pytest.mark.asyncio
async def test_handle_webhook_treasury_failure_does_not_500(monkeypatch):
    monkeypatch.setattr(main, "verify_webhook_signature", lambda *_: True)

    async def _noop(*_):
        pass

    async def _boom(*_):
        raise RuntimeError("cbor decode blew up")

    monkeypatch.setattr(main, "_process_governance", _noop)
    monkeypatch.setattr(main, "_process_treasury", _boom)

    checkpoint_calls = []
    monkeypatch.setattr(
        main,
        "set_checkpoint",
        lambda name, block_no, epoch_no=None: checkpoint_calls.append((name, block_no, epoch_no)),
    )

    payload = {"payload": {"height": 111, "epoch": 222, "hash": "blockhash"}}
    response = await _post_webhook(monkeypatch, payload)

    assert response.status_code == 200  # secondary failure is swallowed
    assert checkpoint_calls == [("blockfrost_main", 111, 222)]
