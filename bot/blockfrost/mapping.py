"""Translate Blockfrost governance payloads into the bot's domain models.

Blockfrost describes proposal/vote kinds with lowercase snake_case strings
(``parameter_change``); the rest of the bot — thresholds, tweet copy — uses the
CIP-1694 PascalCase names (``ParameterChange``). These helpers bridge the two
and build :class:`GovAction` / :class:`CcVote` records.
"""

from __future__ import annotations

from bot.logging import get_logger
from bot.models import CcVote, GovAction

logger = get_logger("blockfrost.mapping")

# Blockfrost governance_type -> CIP-1694 action type used elsewhere in the bot.
GOVERNANCE_TYPE_TO_ACTION_TYPE = {
    "hard_fork_initiation": "HardForkInitiation",
    "new_committee": "NewCommittee",
    "new_constitution": "NewConstitution",
    "info_action": "InfoAction",
    "no_confidence": "NoConfidence",
    "parameter_change": "ParameterChange",
    "treasury_withdrawals": "TreasuryWithdrawals",
}


def action_type_for(governance_type: str) -> str:
    """Return the PascalCase action type for a Blockfrost ``governance_type``.

    Falls back to the raw value (so an unknown/future type is still displayed)
    rather than guessing.
    """
    mapped = GOVERNANCE_TYPE_TO_ACTION_TYPE.get(governance_type)
    if mapped is None:
        logger.warning("Unknown Blockfrost governance_type: %s", governance_type)
        return governance_type
    return mapped


def proposal_key(item: dict) -> str:
    """Stable identity for a proposal feed item (its CIP-129 id when present)."""
    return item.get("id") or f"{item.get('tx_hash', '')}_{item.get('cert_index', '')}"


def committee_vote_key(item: dict) -> str:
    """Stable identity for a committee-vote feed item.

    A committee member casts at most one vote per proposal per transaction, so
    the (vote tx, proposal, voter hot credential) tuple is unique.
    """
    return "_".join(
        [
            item.get("tx_hash", ""),
            item.get("proposal_tx_hash", ""),
            str(item.get("proposal_index", "")),
            item.get("voter_hot_id", ""),
        ]
    )


def build_gov_action(*, tx_hash: str, cert_index: int, governance_type: str, raw_url: str = "") -> GovAction:
    """Build a :class:`GovAction` from a proposal descriptor + resolved anchor URL."""
    return GovAction(
        tx_hash=tx_hash,
        action_type=action_type_for(governance_type),
        index=cert_index,
        raw_url=raw_url or "",
    )


def build_cc_vote(item: dict, *, voter_cold_hex: str) -> CcVote:
    """Build a :class:`CcVote` from a committee-vote feed item.

    ``voter_cold_hex`` is the cold-key hash resolved from the committee snapshot
    (the votes feed only carries the hot credential); it keys the CC-profile
    handle lookup and rationale archive, matching the previous DB-Sync shape.
    """
    return CcVote(
        ga_tx_hash=item.get("proposal_tx_hash", ""),
        ga_index=int(item.get("proposal_index", 0)),
        vote_tx_hash=item.get("tx_hash", ""),
        voter_hash=voter_cold_hex,
        vote=item.get("vote", ""),
        raw_url=item.get("metadata_url") or "",
    )
