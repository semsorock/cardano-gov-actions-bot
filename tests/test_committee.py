"""Tests for parsing the Blockfrost /governance/committee snapshot."""

from bot.blockfrost.committee import parse_committee_snapshot

SNAPSHOT = {
    "proposal_tx_hash": None,
    "proposal_index": None,
    "gov_action_id": None,
    "is_dissolved": False,
    "quorum": {"numerator": 2, "denominator": 3},
    "members": [
        {
            "cc_cold_id": "cc_cold1abc",
            "cc_cold_hex": "aaaa",
            "cc_cold_has_script": False,
            "cc_hot_id": "cc_hot1abc",
            "cc_hot_hex": "hhhh",
            "cc_hot_has_script": False,
            "status": "authorized",
            "expiration_epoch": 580,
        },
        {
            "cc_cold_id": "cc_cold1def",
            "cc_cold_hex": "bbbb",
            "cc_cold_has_script": False,
            "cc_hot_id": None,
            "cc_hot_hex": None,
            "cc_hot_has_script": None,
            "status": "not_authorized",
            "expiration_epoch": 580,
        },
    ],
}


def test_parses_quorum_ratio():
    snap = parse_committee_snapshot(SNAPSHOT)
    assert snap.quorum == 2 / 3
    assert snap.is_dissolved is False


def test_hot_to_cold_mapping_by_id_and_hex():
    snap = parse_committee_snapshot(SNAPSHOT)
    assert snap.cold_hex_for_hot("cc_hot1abc") == "aaaa"
    assert snap.cold_hex_for_hot("hhhh") == "aaaa"
    assert snap.cold_hex_for_hot("unknown") is None
    assert snap.cold_hex_for_hot(None) is None


def test_active_member_count_counts_authorized_only():
    snap = parse_committee_snapshot(SNAPSHOT)
    # Only the first member is authorized.
    assert snap.active_member_count() == 1


def test_active_member_count_excludes_expired():
    snap = parse_committee_snapshot(SNAPSHOT)
    assert snap.active_member_count(current_epoch=581) == 0  # past expiration
    assert snap.active_member_count(current_epoch=580) == 1  # at expiration, still valid


def test_dissolved_flag():
    dissolved = {**SNAPSHOT, "is_dissolved": True}
    snap = parse_committee_snapshot(dissolved)
    assert snap.is_dissolved is True


def test_missing_quorum_is_none():
    snap = parse_committee_snapshot({"members": []})
    assert snap.quorum is None


def test_zero_denominator_is_none():
    snap = parse_committee_snapshot({"quorum": {"numerator": 1, "denominator": 0}, "members": []})
    assert snap.quorum is None


def test_none_input_returns_none():
    assert parse_committee_snapshot(None) is None
