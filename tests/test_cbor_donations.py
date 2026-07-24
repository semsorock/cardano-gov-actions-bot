"""Tests for treasury-donation extraction from transaction CBOR (body key 22)."""

import cbor2

from bot.blockfrost.cbor import extract_block_donations, extract_donation_lovelace

# A Conway transaction is [body, witness_set, is_valid, auxiliary_data]; the
# donation lives at body map key 22 (a positive Coin, in Lovelace).


def _tx_cbor(body: dict) -> str:
    return cbor2.dumps([body, {}, True, None]).hex()


def test_extracts_donation_from_body_key_22():
    cbor_hex = _tx_cbor({0: [], 1: [], 2: 180_000, 22: 500_000_000})
    assert extract_donation_lovelace(cbor_hex) == 500_000_000


def test_no_donation_key_returns_none():
    cbor_hex = _tx_cbor({0: [], 1: [], 2: 180_000})
    assert extract_donation_lovelace(cbor_hex) is None


def test_zero_and_negative_donation_rejected():
    assert extract_donation_lovelace(_tx_cbor({22: 0})) is None
    assert extract_donation_lovelace(_tx_cbor({22: -5})) is None


def test_boolean_value_rejected():
    # bool is an int subclass — must not be treated as a donation amount.
    assert extract_donation_lovelace(_tx_cbor({22: True})) is None


def test_malformed_cbor_returns_none():
    assert extract_donation_lovelace("not-hex") is None
    assert extract_donation_lovelace("deadbeef") is None


def test_non_array_transaction_returns_none():
    assert extract_donation_lovelace(cbor2.dumps({22: 100}).hex()) is None


def test_conway_tagged_set_inputs_do_not_break_extraction():
    # Conway encodes input sets with CBOR tag 258; the donation still lives at
    # body key 22 and must be read regardless of how other keys are encoded.
    body = {
        0: cbor2.CBORTag(258, [[b"\xaa" * 32, 0]]),  # set<transaction_input>
        1: [],
        2: 170_000,
        22: 250_000_000_000,
    }
    cbor_hex = cbor2.dumps([body, {}, True, None]).hex()
    assert extract_donation_lovelace(cbor_hex) == 250_000_000_000


def test_extract_block_donations_filters_and_labels():
    txs = [
        {"tx_hash": "aa", "cbor": _tx_cbor({2: 100, 22: 1_000_000})},
        {"tx_hash": "bb", "cbor": _tx_cbor({2: 100})},  # no donation
        {"tx_hash": "cc", "cbor": _tx_cbor({22: 2_500_000})},
        {"tx_hash": "dd", "cbor": ""},  # empty cbor skipped
    ]

    donations = extract_block_donations(9001, txs)

    assert [(d.tx_hash, d.amount_lovelace) for d in donations] == [
        ("aa", 1_000_000),
        ("cc", 2_500_000),
    ]
    assert all(d.block_no == 9001 for d in donations)


def test_extract_block_donations_empty():
    assert extract_block_donations(1, []) == []
