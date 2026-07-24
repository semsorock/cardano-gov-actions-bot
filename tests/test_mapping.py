"""Tests for Blockfrost payload -> domain model mapping."""

from bot.blockfrost.mapping import (
    action_type_for,
    build_cc_vote,
    build_gov_action,
    committee_vote_key,
    proposal_key,
)


class TestActionTypeFor:
    def test_known_types(self):
        assert action_type_for("parameter_change") == "ParameterChange"
        assert action_type_for("treasury_withdrawals") == "TreasuryWithdrawals"
        assert action_type_for("hard_fork_initiation") == "HardForkInitiation"
        assert action_type_for("info_action") == "InfoAction"
        assert action_type_for("no_confidence") == "NoConfidence"
        assert action_type_for("new_committee") == "NewCommittee"
        assert action_type_for("new_constitution") == "NewConstitution"

    def test_unknown_type_passes_through(self):
        assert action_type_for("some_future_type") == "some_future_type"


class TestKeys:
    def test_proposal_key_prefers_id(self):
        assert proposal_key({"id": "gov_action1abc", "tx_hash": "aa", "cert_index": 1}) == "gov_action1abc"

    def test_proposal_key_falls_back_to_tx_and_index(self):
        assert proposal_key({"tx_hash": "aa", "cert_index": 1}) == "aa_1"

    def test_committee_vote_key_is_unique_per_vote(self):
        item = {
            "tx_hash": "votetx",
            "proposal_tx_hash": "proptx",
            "proposal_index": 0,
            "voter_hot_id": "cc_hot1abc",
        }
        assert committee_vote_key(item) == "votetx_proptx_0_cc_hot1abc"


class TestBuildModels:
    def test_build_gov_action_maps_type(self):
        action = build_gov_action(tx_hash="aa", cert_index=2, governance_type="parameter_change", raw_url="ipfs://x")
        assert action.tx_hash == "aa"
        assert action.index == 2
        assert action.action_type == "ParameterChange"
        assert action.action_type_display == "Parameter Change"
        assert action.raw_url == "ipfs://x"

    def test_build_cc_vote_maps_fields(self):
        item = {
            "tx_hash": "votetx",
            "proposal_tx_hash": "proptx",
            "proposal_index": 3,
            "voter_hot_id": "cc_hot1abc",
            "vote": "yes",
            "metadata_url": "ipfs://rationale",
        }
        vote = build_cc_vote(item, voter_cold_hex="coldhex")
        assert vote.ga_tx_hash == "proptx"
        assert vote.ga_index == 3
        assert vote.vote_tx_hash == "votetx"
        assert vote.voter_hash == "coldhex"
        assert vote.vote == "yes"
        assert vote.raw_url == "ipfs://rationale"

    def test_build_cc_vote_handles_null_metadata_url(self):
        item = {
            "tx_hash": "votetx",
            "proposal_tx_hash": "proptx",
            "proposal_index": 0,
            "voter_hot_id": "cc_hot1abc",
            "vote": "abstain",
            "metadata_url": None,
        }
        vote = build_cc_vote(item, voter_cold_hex="coldhex")
        assert vote.raw_url == ""
