import os

import pytest

os.environ.setdefault("DB_SYNC_URL", "postgresql://localhost/test")

from bot import main
from bot.models import CcVote, GovAction


@pytest.mark.asyncio
async def test_process_gov_actions_saves_action_state(monkeypatch):
    action = GovAction(
        tx_hash="a" * 64,
        action_type="TreasuryWithdrawal",
        index=0,
        raw_url="ipfs://example",
    )

    async def _fake_get_gov_actions(*_):
        return [action]

    monkeypatch.setattr(main, "get_gov_actions", _fake_get_gov_actions)
    monkeypatch.setattr(main, "sanitise_url", lambda url: url)
    monkeypatch.setattr(main, "fetch_metadata", lambda *_: {"body": {"title": "t"}})
    monkeypatch.setattr(main, "validate_gov_action_rationale", lambda *_: [])
    monkeypatch.setattr(main, "format_gov_action_tweet", lambda *_: "tweet text")
    monkeypatch.setattr(main, "post_tweet", lambda *_: "tweet-123")
    monkeypatch.setattr(main, "archive_gov_action", lambda *_args, **_kwargs: None)

    save_calls = []
    monkeypatch.setattr(
        main,
        "save_action_tweet_id",
        lambda tx_hash, index, tweet_id, source_block=None: save_calls.append((tx_hash, index, tweet_id, source_block)),
    )

    await main._process_gov_actions(321)

    assert save_calls == [(action.tx_hash, action.index, "tweet-123", 321)]


@pytest.mark.asyncio
async def test_process_cc_votes_falls_back_to_github_tweet_id(monkeypatch):
    vote = CcVote(
        ga_tx_hash="b" * 64,
        ga_index=1,
        vote_tx_hash="c" * 64,
        voter_hash="d" * 56,
        vote="YES",
        raw_url="ipfs://vote",
    )

    async def _fake_get_cc_votes(*_):
        return [vote]

    monkeypatch.setattr(main, "get_cc_votes", _fake_get_cc_votes)
    monkeypatch.setattr(main, "sanitise_url", lambda url: url)
    monkeypatch.setattr(main, "fetch_metadata", lambda *_: {"body": {"summary": "s"}})
    monkeypatch.setattr(main, "validate_cc_vote_rationale", lambda *_: [])
    monkeypatch.setattr(main, "get_action_tweet_id", lambda *_: None)
    monkeypatch.setattr(main, "get_action_tweet_id_from_github", lambda *_: "tweet-from-github")
    monkeypatch.setattr(main, "get_x_handle_for_voter_hash", lambda *_: "cc_member")
    monkeypatch.setattr(main, "format_cc_vote_tweet", lambda *_args, **_kwargs: "cc vote tweet")
    monkeypatch.setattr(main, "archive_cc_vote", lambda *_args, **_kwargs: None)

    quote_calls = []
    monkeypatch.setattr(main, "post_quote_tweet", lambda text, quote_id: quote_calls.append((text, quote_id)))
    monkeypatch.setattr(main, "post_tweet", lambda *_: (_ for _ in ()).throw(AssertionError("unexpected post_tweet")))

    cc_state_calls = []
    monkeypatch.setattr(
        main,
        "mark_cc_vote_archived",
        lambda ga_tx_hash, ga_index, voter_hash, source_block=None: cc_state_calls.append(
            (ga_tx_hash, ga_index, voter_hash, source_block)
        ),
    )

    await main._process_cc_votes(654)

    assert quote_calls == [("cc vote tweet", "tweet-from-github")]
    assert cc_state_calls == [(vote.ga_tx_hash, vote.ga_index, vote.voter_hash, 654)]


@pytest.mark.asyncio
async def test_handle_blockfrost_webhook_updates_checkpoint(monkeypatch):
    from httpx import ASGITransport, AsyncClient

    monkeypatch.setattr(main, "verify_webhook_signature", lambda *_: True)

    async def _noop(*_):
        pass

    monkeypatch.setattr(main, "_process_gov_actions", _noop)
    monkeypatch.setattr(main, "_process_cc_votes", _noop)
    monkeypatch.setattr(main, "_check_epoch_transition", _noop)

    checkpoint_calls = []
    monkeypatch.setattr(
        main,
        "set_checkpoint",
        lambda name, block_no, epoch_no=None: checkpoint_calls.append((name, block_no, epoch_no)),
    )

    payload = {"payload": {"height": 111, "epoch": 222, "previous_block": "prev-hash"}}

    transport = ASGITransport(app=main.app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/",
            json=payload,
            headers={"Blockfrost-Signature": "sig"},
        )

    assert response.status_code == 200
    assert checkpoint_calls == [("blockfrost_main", 111, 222)]
