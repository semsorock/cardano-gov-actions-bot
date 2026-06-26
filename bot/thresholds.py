"""Governance action ratification thresholds.

Cardano ratifies a governance action only when the relevant voting bodies
(DReps, SPOs, the Constitutional Committee) each reach a minimum approval
ratio. Those ratios are protocol parameters (the ``dvt_*`` / ``pvt_*`` columns
of ``epoch_param``) and the CC quorum (the ``committee`` table), so they can
themselves be changed by governance. We therefore read the *live* values from
DB-Sync rather than hard-coding them.

Which bodies vote — and which threshold applies — depends on the action type
(see CIP-1694). This module turns the raw DB values into a :class:`GovThresholds`
describing only the bodies that actually vote on a given action.
"""

from __future__ import annotations

from dataclasses import dataclass

# ---------------------------------------------------------------------------
# Protocol-parameter groups (CIP-1694)
#
# A ParameterChange action's DRep threshold depends on which parameter group(s)
# it touches, and SPOs only vote when a *security-relevant* parameter changes.
# These tuples list the ``param_proposal`` columns belonging to each group.
# ---------------------------------------------------------------------------

NETWORK_PARAMS = (
    "max_block_size",
    "max_tx_size",
    "max_bh_size",
    "max_val_size",
    "max_tx_ex_mem",
    "max_tx_ex_steps",
    "max_block_ex_mem",
    "max_block_ex_steps",
    "max_collateral_inputs",
)

ECONOMIC_PARAMS = (
    "min_fee_a",
    "min_fee_b",
    "key_deposit",
    "pool_deposit",
    "monetary_expand_rate",
    "treasury_growth_rate",
    "min_pool_cost",
    "coins_per_utxo_size",
    "price_mem",
    "price_step",
)

TECHNICAL_PARAMS = (
    "influence",
    "optimal_pool_count",
    "max_epoch",
    "collateral_percent",
    "cost_model_id",
    "min_fee_ref_script_cost_per_byte",
)

GOVERNANCE_PARAMS = (
    "gov_action_lifetime",
    "gov_action_deposit",
    "drep_deposit",
    "drep_activity",
    "committee_min_size",
    "committee_max_term_length",
    "dvt_motion_no_confidence",
    "dvt_committee_normal",
    "dvt_committee_no_confidence",
    "dvt_update_to_constitution",
    "dvt_hard_fork_initiation",
    "dvt_p_p_network_group",
    "dvt_p_p_economic_group",
    "dvt_p_p_technical_group",
    "dvt_p_p_gov_group",
    "dvt_treasury_withdrawal",
    "pvt_motion_no_confidence",
    "pvt_committee_normal",
    "pvt_committee_no_confidence",
    "pvt_hard_fork_initiation",
    "pvtpp_security_group",
)

# Parameters the SPOs are entitled to vote on (the "security" group).
SECURITY_PARAMS = (
    "max_block_size",
    "max_tx_size",
    "max_bh_size",
    "max_val_size",
    "max_block_ex_mem",
    "max_block_ex_steps",
    "min_fee_a",
    "min_fee_b",
    "coins_per_utxo_size",
    "gov_action_deposit",
    "min_fee_ref_script_cost_per_byte",
)


@dataclass(frozen=True)
class EpochThresholds:
    """The governance voting thresholds in effect for an epoch.

    Mirrors the ``dvt_*`` / ``pvt_*`` columns of ``epoch_param``. Each value is
    an approval ratio in ``[0, 1]`` (or ``None`` before Conway).
    """

    dvt_motion_no_confidence: float | None = None
    dvt_committee_normal: float | None = None
    dvt_committee_no_confidence: float | None = None
    dvt_update_to_constitution: float | None = None
    dvt_hard_fork_initiation: float | None = None
    dvt_p_p_network_group: float | None = None
    dvt_p_p_economic_group: float | None = None
    dvt_p_p_technical_group: float | None = None
    dvt_p_p_gov_group: float | None = None
    dvt_treasury_withdrawal: float | None = None
    pvt_motion_no_confidence: float | None = None
    pvt_committee_normal: float | None = None
    pvt_committee_no_confidence: float | None = None
    pvt_hard_fork_initiation: float | None = None
    pvtpp_security_group: float | None = None


@dataclass(frozen=True)
class ParamChangeGroups:
    """Which protocol-parameter groups a ParameterChange action touches."""

    network: bool = False
    economic: bool = False
    technical: bool = False
    governance: bool = False
    security: bool = False


@dataclass(frozen=True)
class GovThresholds:
    """Ratification thresholds applicable to a single governance action.

    A body's field is ``None`` when that body does not vote on the action type.
    ``note`` carries free text for actions with no on-chain threshold.
    """

    drep: float | None = None
    spo: float | None = None
    cc: float | None = None
    note: str | None = None

    @property
    def is_empty(self) -> bool:
        return self.drep is None and self.spo is None and self.cc is None and not self.note


def _max(*values: float | None) -> float | None:
    present = [v for v in values if v is not None]
    return max(present) if present else None


def compute_thresholds(
    action_type: str,
    params: EpochThresholds,
    committee_quorum: float | None,
    *,
    param_groups: ParamChangeGroups | None = None,
) -> GovThresholds:
    """Return the thresholds that apply to ``action_type``.

    ``params`` are the current epoch's voting thresholds, ``committee_quorum``
    the active CC's approval ratio, and ``param_groups`` (ParameterChange only)
    the protocol-parameter groups the proposal touches.
    """
    if action_type == "InfoAction":
        # Info actions can be voted on but are never enacted — no threshold.
        return GovThresholds(note="none (informational)")

    if action_type == "HardForkInitiation":
        return GovThresholds(
            drep=params.dvt_hard_fork_initiation,
            spo=params.pvt_hard_fork_initiation,
            cc=committee_quorum,
        )

    if action_type == "TreasuryWithdrawals":
        return GovThresholds(drep=params.dvt_treasury_withdrawal, cc=committee_quorum)

    if action_type == "NoConfidence":
        return GovThresholds(
            drep=params.dvt_motion_no_confidence,
            spo=params.pvt_motion_no_confidence,
        )

    if action_type == "NewCommittee":
        # Thresholds differ in a state of no-confidence; the common (normal)
        # case is shown here.
        return GovThresholds(
            drep=params.dvt_committee_normal,
            spo=params.pvt_committee_normal,
        )

    if action_type == "NewConstitution":
        return GovThresholds(drep=params.dvt_update_to_constitution, cc=committee_quorum)

    if action_type == "ParameterChange":
        groups = param_groups or ParamChangeGroups()
        drep = _max(
            params.dvt_p_p_network_group if groups.network else None,
            params.dvt_p_p_economic_group if groups.economic else None,
            params.dvt_p_p_technical_group if groups.technical else None,
            params.dvt_p_p_gov_group if groups.governance else None,
        )
        if drep is None:
            # No group detected (e.g. param_proposal missing) — fall back to a
            # representative non-governance DRep threshold so we still show
            # something sensible.
            drep = params.dvt_p_p_economic_group
        return GovThresholds(
            drep=drep,
            spo=params.pvtpp_security_group if groups.security else None,
            cc=committee_quorum,
        )

    # Unknown / future action type — show nothing rather than guess.
    return GovThresholds()
