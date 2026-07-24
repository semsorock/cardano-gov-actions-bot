"""Governance action ratification thresholds.

Cardano ratifies a governance action only when the relevant voting bodies
(DReps, SPOs, the Constitutional Committee) each reach a minimum approval
ratio. Those ratios are protocol parameters (the ``dvt_*`` / ``pvt_*`` fields of
an epoch's parameters) and the CC quorum (from the committee snapshot), so they
can themselves be changed by governance. We therefore read the *live* values
from Blockfrost rather than hard-coding them:

* ``/epochs/{epoch}/parameters`` — the epoch-specific DRep/SPO thresholds.
* ``/governance/committee`` — the CC quorum, dissolution state, minimum-size
  input and hot→cold identities.

Which bodies vote — and which threshold applies — depends on the action type
(see CIP-1694). This module turns the raw values into a :class:`GovThresholds`
describing only the bodies that actually vote on a given action, and classifies
a ParameterChange's touched protocol-parameter groups from the proposed
``parameters`` object.
"""

from __future__ import annotations

from dataclasses import dataclass

# ---------------------------------------------------------------------------
# Protocol-parameter groups (CIP-1694), keyed by the field names Blockfrost
# uses in a proposal's ``parameters`` object.
#
# A ParameterChange action's DRep threshold depends on which parameter group(s)
# it touches, and SPOs only vote when a *security-relevant* parameter changes.
# ---------------------------------------------------------------------------

NETWORK_PARAMS = frozenset(
    {
        "max_block_size",
        "max_tx_size",
        "max_block_header_size",
        "max_val_size",
        "max_tx_ex_mem",
        "max_tx_ex_steps",
        "max_block_ex_mem",
        "max_block_ex_steps",
        "max_collateral_inputs",
    }
)

ECONOMIC_PARAMS = frozenset(
    {
        "min_fee_a",
        "min_fee_b",
        "key_deposit",
        "pool_deposit",
        "rho",
        "tau",
        "min_pool_cost",
        "coins_per_utxo_size",
        "coins_per_utxo_word",
        "price_mem",
        "price_step",
        # Classified as Economic + Security per the migration plan.
        "min_fee_ref_script_cost_per_byte",
    }
)

TECHNICAL_PARAMS = frozenset(
    {
        "a0",
        "n_opt",
        "e_max",
        "collateral_percent",
        "cost_models",
    }
)

GOVERNANCE_PARAMS = frozenset(
    {
        "pvt_motion_no_confidence",
        "pvt_committee_normal",
        "pvt_committee_no_confidence",
        "pvt_hard_fork_initiation",
        "pvtpp_security_group",
        "pvt_p_p_security_group",
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
        "committee_min_size",
        "committee_max_term_length",
        "gov_action_lifetime",
        "gov_action_deposit",
        "drep_deposit",
        "drep_activity",
    }
)

# Parameters the SPOs are entitled to vote on (the "security" group).
SECURITY_PARAMS = frozenset(
    {
        "max_block_size",
        "max_tx_size",
        "max_block_header_size",
        "max_val_size",
        "max_block_ex_mem",
        "max_block_ex_steps",
        "min_fee_a",
        "min_fee_b",
        "coins_per_utxo_size",
        "coins_per_utxo_word",
        "gov_action_deposit",
        "min_fee_ref_script_cost_per_byte",
    }
)

# Keys of a proposal ``parameters`` object that are not protocol parameters.
_NON_PARAM_KEYS = frozenset({"epoch"})


@dataclass(frozen=True)
class EpochThresholds:
    """The governance voting thresholds in effect for an epoch.

    Mirrors the ``dvt_*`` / ``pvt_*`` fields of an epoch's parameters. Each value
    is an approval ratio in ``[0, 1]`` (or ``None`` before Conway).
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
class ThresholdContext:
    """Block-level voting context shared by every action being processed.

    The epoch thresholds and committee state are identical for all actions in an
    epoch, so they are fetched once and reused (only ParameterChange group
    detection is per-action).
    """

    params: EpochThresholds
    committee_quorum: float | None = None
    committee_dissolved: bool = False
    committee_active_size: int = 0
    committee_min_size: int | None = None

    @property
    def committee_in_no_confidence(self) -> bool:
        """True when the committee cannot ratify: dissolved or below min size."""
        if self.committee_dissolved:
            return True
        if self.committee_min_size is not None and self.committee_active_size < self.committee_min_size:
            return True
        return False

    @property
    def effective_committee_quorum(self) -> float | None:
        """CC quorum to display, or ``None`` when the committee cannot ratify."""
        return None if self.committee_in_no_confidence else self.committee_quorum


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


def epoch_thresholds_from_params(params: dict) -> EpochThresholds:
    """Build :class:`EpochThresholds` from a Blockfrost epoch-parameters body."""

    def ratio(key: str) -> float | None:
        value = params.get(key)
        return float(value) if isinstance(value, int | float) and not isinstance(value, bool) else None

    # Blockfrost renamed ``pvtpp_security_group`` to ``pvt_p_p_security_group``;
    # accept either.
    security = ratio("pvt_p_p_security_group")
    if security is None:
        security = ratio("pvtpp_security_group")

    return EpochThresholds(
        dvt_motion_no_confidence=ratio("dvt_motion_no_confidence"),
        dvt_committee_normal=ratio("dvt_committee_normal"),
        dvt_committee_no_confidence=ratio("dvt_committee_no_confidence"),
        dvt_update_to_constitution=ratio("dvt_update_to_constitution"),
        dvt_hard_fork_initiation=ratio("dvt_hard_fork_initiation"),
        dvt_p_p_network_group=ratio("dvt_p_p_network_group"),
        dvt_p_p_economic_group=ratio("dvt_p_p_economic_group"),
        dvt_p_p_technical_group=ratio("dvt_p_p_technical_group"),
        dvt_p_p_gov_group=ratio("dvt_p_p_gov_group"),
        dvt_treasury_withdrawal=ratio("dvt_treasury_withdrawal"),
        pvt_motion_no_confidence=ratio("pvt_motion_no_confidence"),
        pvt_committee_normal=ratio("pvt_committee_normal"),
        pvt_committee_no_confidence=ratio("pvt_committee_no_confidence"),
        pvt_hard_fork_initiation=ratio("pvt_hard_fork_initiation"),
        pvtpp_security_group=security,
    )


def build_threshold_context(
    params: dict,
    *,
    committee_quorum: float | None,
    committee_dissolved: bool,
    committee_active_size: int,
) -> ThresholdContext:
    """Assemble a :class:`ThresholdContext` from epoch params + committee state.

    ``params`` is a Blockfrost epoch-parameters body; the committee inputs come
    from a parsed ``/governance/committee`` snapshot.
    """
    min_size = params.get("committee_min_size")
    committee_min_size: int | None
    try:
        committee_min_size = int(min_size) if min_size is not None else None
    except (TypeError, ValueError):
        committee_min_size = None

    return ThresholdContext(
        params=epoch_thresholds_from_params(params),
        committee_quorum=committee_quorum,
        committee_dissolved=committee_dissolved,
        committee_active_size=committee_active_size,
        committee_min_size=committee_min_size,
    )


def classify_parameters(parameters: dict | None) -> ParamChangeGroups:
    """Classify a proposal's non-null ``parameters`` into voting groups.

    Only fields that are present and non-null count. Unknown fields (not in any
    group) are ignored — we never fabricate a group for them.
    """
    if not isinstance(parameters, dict):
        return ParamChangeGroups()

    changed = {key for key, value in parameters.items() if value is not None and key not in _NON_PARAM_KEYS}

    return ParamChangeGroups(
        network=bool(changed & NETWORK_PARAMS),
        economic=bool(changed & ECONOMIC_PARAMS),
        technical=bool(changed & TECHNICAL_PARAMS),
        governance=bool(changed & GOVERNANCE_PARAMS),
        security=bool(changed & SECURITY_PARAMS),
    )


def _max(*values: float | None) -> float | None:
    present = [v for v in values if v is not None]
    return max(present) if present else None


def compute_thresholds(
    action_type: str,
    context: ThresholdContext,
    *,
    param_groups: ParamChangeGroups | None = None,
) -> GovThresholds:
    """Return the thresholds that apply to ``action_type``.

    ``context`` carries the current epoch's voting thresholds and committee
    state; ``param_groups`` (ParameterChange only) the protocol-parameter groups
    the proposal touches.
    """
    params = context.params
    cc_quorum = context.effective_committee_quorum

    if action_type == "InfoAction":
        # Info actions can be voted on but are never enacted — no threshold.
        return GovThresholds(note="none (informational)")

    if action_type == "HardForkInitiation":
        return GovThresholds(
            drep=params.dvt_hard_fork_initiation,
            spo=params.pvt_hard_fork_initiation,
            cc=cc_quorum,
        )

    if action_type == "TreasuryWithdrawals":
        return GovThresholds(drep=params.dvt_treasury_withdrawal, cc=cc_quorum)

    if action_type == "NoConfidence":
        return GovThresholds(
            drep=params.dvt_motion_no_confidence,
            spo=params.pvt_motion_no_confidence,
        )

    if action_type == "NewCommittee":
        # Thresholds differ when the system is in a state of no-confidence.
        if context.committee_in_no_confidence:
            return GovThresholds(
                drep=params.dvt_committee_no_confidence,
                spo=params.pvt_committee_no_confidence,
            )
        return GovThresholds(
            drep=params.dvt_committee_normal,
            spo=params.pvt_committee_normal,
        )

    if action_type == "NewConstitution":
        return GovThresholds(drep=params.dvt_update_to_constitution, cc=cc_quorum)

    if action_type == "ParameterChange":
        groups = param_groups or ParamChangeGroups()
        drep = _max(
            params.dvt_p_p_network_group if groups.network else None,
            params.dvt_p_p_economic_group if groups.economic else None,
            params.dvt_p_p_technical_group if groups.technical else None,
            params.dvt_p_p_gov_group if groups.governance else None,
        )
        # No fabricated fallback: if no group was detected, show no DRep number.
        return GovThresholds(
            drep=drep,
            spo=params.pvtpp_security_group if groups.security else None,
            cc=cc_quorum,
        )

    # Unknown / future action type — show nothing rather than guess.
    return GovThresholds()
