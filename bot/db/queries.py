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
    SELECT
        encode(t1.hash, 'hex') AS ga_tx_hash,
        gap.index AS ga_index,
        encode(t2.hash, 'hex') AS vote_tx_hash,
        encode(ch.raw, 'hex') AS voter_hash,
        vp."vote",
        va.url
    FROM gov_action_proposal gap
    JOIN voting_procedure vp ON gap.id = vp.gov_action_proposal_id
    JOIN committee_hash ch ON vp.committee_voter = ch.id
    JOIN voting_anchor va ON vp.voting_anchor_id = va.id
    JOIN tx t1 ON gap.tx_id = t1.id
    JOIN tx t2 ON vp.tx_id = t2.id
    JOIN block b ON t2.block_id = b.id
    WHERE vp.voter_role = 'ConstitutionalCommittee'
    AND b.block_no = %s
"""

QUERY_GA_EXPIRATIONS = """
    SELECT
        encode(t.hash, 'hex') AS tx_hash,
        gap.index
    FROM gov_action_proposal gap
    JOIN tx t ON gap.tx_id = t.id
    WHERE gap.expiration = %s
    AND gap.ratified_epoch IS NULL
    AND gap.enacted_epoch IS NULL
    AND gap.dropped_epoch IS NULL
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
