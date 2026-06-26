QUERY_GOV_ACTIONS = """
    SELECT
        encode(t.hash, 'hex') AS tx_hash,
        gap."type",
        gap.index,
        va.url
    FROM gov_action_proposal gap
    JOIN voting_anchor va ON gap.voting_anchor_id = va.id
    JOIN tx t ON gap.tx_id = t.id
    JOIN block b ON t.block_id = b.id
    WHERE b.block_no = %s
"""

QUERY_CC_VOTES = """
    SELECT DISTINCT
        encode(t1.hash, 'hex') AS ga_tx_hash,
        gap.index AS ga_index,
        encode(t2.hash, 'hex') AS vote_tx_hash,
        encode(cold_ch.raw, 'hex') AS voter_hash,
        vp."vote",
        va.url
    FROM gov_action_proposal gap
    JOIN voting_procedure vp ON gap.id = vp.gov_action_proposal_id
    JOIN committee_hash ch ON vp.committee_voter = ch.id
    JOIN committee_registration cr ON cr.hot_key_id = ch.id
    JOIN committee_hash cold_ch ON cr.cold_key_id = cold_ch.id
    JOIN voting_anchor va ON vp.voting_anchor_id = va.id
    JOIN tx t1 ON gap.tx_id = t1.id
    JOIN tx t2 ON vp.tx_id = t2.id
    JOIN block b ON t2.block_id = b.id
    WHERE vp.voter_role = 'ConstitutionalCommittee'
    AND b.block_no = %s
"""

QUERY_TREASURY_DONATIONS = """
    SELECT
        b.block_no,
        encode(t.hash, 'hex') AS tx_hash,
        t.treasury_donation
    FROM tx t
    JOIN block b ON t.block_id = b.id
    WHERE t.treasury_donation > 0
    AND b.epoch_no = %s
"""

QUERY_BLOCK_EPOCH = """
    SELECT b.epoch_no
    FROM block b
    WHERE b.hash = decode(%s, 'hex')
"""

QUERY_LATEST_THRESHOLDS = """
    SELECT
        dvt_motion_no_confidence,
        dvt_committee_normal,
        dvt_committee_no_confidence,
        dvt_update_to_constitution,
        dvt_hard_fork_initiation,
        dvt_p_p_network_group,
        dvt_p_p_economic_group,
        dvt_p_p_technical_group,
        dvt_p_p_gov_group,
        dvt_treasury_withdrawal,
        pvt_motion_no_confidence,
        pvt_committee_normal,
        pvt_committee_no_confidence,
        pvt_hard_fork_initiation,
        pvtpp_security_group
    FROM epoch_param
    ORDER BY epoch_no DESC
    LIMIT 1
"""

# Approval ratio of the currently active Constitutional Committee. Prefers the
# most recently enacted committee, falling back to the genesis committee
# (gov_action_proposal_id IS NULL). Pending (un-enacted) committee proposals
# are excluded.
QUERY_ACTIVE_COMMITTEE_QUORUM = """
    SELECT c.quorum_numerator::float8 / NULLIF(c.quorum_denominator, 0)
    FROM committee c
    LEFT JOIN gov_action_proposal gap ON c.gov_action_proposal_id = gap.id
    WHERE c.gov_action_proposal_id IS NULL OR gap.enacted_epoch IS NOT NULL
    ORDER BY gap.enacted_epoch DESC NULLS LAST, c.id DESC
    LIMIT 1
"""


def _group_predicate(columns: tuple[str, ...]) -> str:
    """Build a SQL boolean: true when any of the given pp columns is set."""
    return "(" + " OR ".join(f"pp.{c} IS NOT NULL" for c in columns) + ")"


def build_param_change_groups_query() -> str:
    """SQL returning which protocol-parameter groups a ParameterChange touches.

    Identified by the action's tx hash (hex) and index. Returns one row of five
    booleans (network, economic, technical, governance, security).
    """
    from bot.thresholds import (
        ECONOMIC_PARAMS,
        GOVERNANCE_PARAMS,
        NETWORK_PARAMS,
        SECURITY_PARAMS,
        TECHNICAL_PARAMS,
    )

    return f"""
    SELECT
        {_group_predicate(NETWORK_PARAMS)} AS network,
        {_group_predicate(ECONOMIC_PARAMS)} AS economic,
        {_group_predicate(TECHNICAL_PARAMS)} AS technical,
        {_group_predicate(GOVERNANCE_PARAMS)} AS governance,
        {_group_predicate(SECURITY_PARAMS)} AS security
    FROM gov_action_proposal gap
    JOIN tx t ON gap.tx_id = t.id
    LEFT JOIN param_proposal pp ON gap.param_proposal = pp.id
    WHERE t.hash = decode(%s, 'hex') AND gap.index = %s
    """


QUERY_PARAM_CHANGE_GROUPS = build_param_change_groups_query()

QUERY_ALL_GOV_ACTIONS = """
    SELECT
        encode(t.hash, 'hex') AS tx_hash,
        gap."type",
        gap.index,
        va.url
    FROM gov_action_proposal gap
    JOIN voting_anchor va ON gap.voting_anchor_id = va.id
    JOIN tx t ON gap.tx_id = t.id
"""

QUERY_ALL_CC_VOTES = """
    SELECT DISTINCT
        encode(t1.hash, 'hex') AS ga_tx_hash,
        gap.index AS ga_index,
        encode(t2.hash, 'hex') AS vote_tx_hash,
        encode(cold_ch.raw, 'hex') AS voter_hash,
        vp."vote",
        va.url
    FROM gov_action_proposal gap
    JOIN voting_procedure vp ON gap.id = vp.gov_action_proposal_id
    JOIN committee_hash ch ON vp.committee_voter = ch.id
    JOIN committee_registration cr ON cr.hot_key_id = ch.id
    JOIN committee_hash cold_ch ON cr.cold_key_id = cold_ch.id
    JOIN voting_anchor va ON vp.voting_anchor_id = va.id
    JOIN tx t1 ON gap.tx_id = t1.id
    JOIN tx t2 ON vp.tx_id = t2.id
    WHERE vp.voter_role = 'ConstitutionalCommittee'
"""
