"""Extract treasury donations from transaction CBOR.

Rather than requesting each transaction individually to read its
``treasury_donation`` field, the bot fetches a whole block's transactions in
one ``/blocks/{hash}/txs/cbor`` call and decodes the donation locally.

A Conway transaction is a CBOR array ``[body, witness_set, is_valid,
auxiliary_data]``. The transaction *body* is a map whose key ``22`` holds the
treasury donation amount (a positive Coin, in Lovelace); the key is absent when
the transaction makes no donation. See the Conway CDDL ``transaction_body``.
"""

from __future__ import annotations

import cbor2

from bot.logging import get_logger
from bot.models import TreasuryDonation

logger = get_logger("blockfrost.cbor")

# Transaction-body map key for the treasury donation (Conway CDDL).
_DONATION_KEY = 22


def extract_donation_lovelace(cbor_hex: str) -> int | None:
    """Return the treasury donation (Lovelace) of a transaction, or ``None``.

    Decodes the transaction CBOR (hex) and reads body key ``22``. Returns
    ``None`` when the transaction makes no donation or cannot be decoded.
    """
    try:
        raw = bytes.fromhex(cbor_hex)
        tx = cbor2.loads(raw)
    except (ValueError, cbor2.CBORDecodeError):
        logger.warning("Failed to decode transaction CBOR", exc_info=True)
        return None

    # transaction = [body, witness_set, is_valid, auxiliary_data]
    body = tx[0] if isinstance(tx, list) and tx else None
    if not isinstance(body, dict):
        return None

    donation = body.get(_DONATION_KEY)
    if isinstance(donation, bool):  # bool is an int subclass — reject it explicitly.
        return None
    if isinstance(donation, int) and donation > 0:
        return donation
    return None


def extract_block_donations(block_no: int, txs_cbor: list[dict]) -> list[TreasuryDonation]:
    """Build :class:`TreasuryDonation` records for a block's donating txs.

    ``txs_cbor`` is the ``/blocks/{hash}/txs/cbor`` payload — a list of
    ``{"tx_hash": ..., "cbor": ...}`` objects. Transactions with no donation are
    skipped.
    """
    donations: list[TreasuryDonation] = []
    for entry in txs_cbor:
        cbor_hex = entry.get("cbor")
        tx_hash = entry.get("tx_hash", "")
        if not cbor_hex:
            continue
        amount = extract_donation_lovelace(cbor_hex)
        if amount is not None:
            donations.append(TreasuryDonation(block_no=block_no, tx_hash=tx_hash, amount_lovelace=amount))
    return donations
