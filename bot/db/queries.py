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

QUERY_BLOCK_EPOCH = """
    SELECT b.epoch_no
    FROM block b
    WHERE b.hash = decode(%s, 'hex')
"""

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
    WHERE vp.voter_role = 'ConstitutionalCommittee'
"""

QUERY_ACTIVE_GOV_ACTIONS = """
    SELECT
        encode(t.hash, 'hex') AS tx_hash,
        gap.index,
        b.epoch_no AS created_epoch,
        gap.expiration
    FROM gov_action_proposal gap
    JOIN tx t ON gap.tx_id = t.id
    JOIN block b ON t.block_id = b.id
    WHERE b.epoch_no < %s
    AND gap.ratified_epoch IS NULL
    AND gap.enacted_epoch IS NULL
    AND gap.dropped_epoch IS NULL
    AND gap.expired_epoch IS NULL
    AND (gap.expiration IS NULL OR gap.expiration >= %s)
"""

QUERY_VOTING_STATS = """
    WITH active_committee AS (
        SELECT COUNT(DISTINCT cm.committee_hash_id) as total_members
        FROM committee c
        JOIN committee_member cm ON c.id = cm.committee_id
        WHERE cm.expiration_epoch >= %s
        AND c.gov_action_proposal_id IS NULL
    ),
    cc_votes_for_action AS (
        SELECT COUNT(DISTINCT vp.committee_voter) as voted_count
        FROM voting_procedure vp
        JOIN gov_action_proposal gap ON vp.gov_action_proposal_id = gap.id
        JOIN tx t ON gap.tx_id = t.id
        WHERE encode(t.hash, 'hex') = %s
        AND gap.index = %s
        AND vp.voter_role = 'ConstitutionalCommittee'
    ),
    total_dreps AS (
        SELECT COUNT(DISTINCT hash_id) as total_count
        FROM drep_distr
        WHERE epoch_no = %s - 1
        AND amount > 0
    ),
    drep_votes_for_action AS (
        SELECT COUNT(DISTINCT vp.drep_voter) as voted_count
        FROM voting_procedure vp
        JOIN gov_action_proposal gap ON vp.gov_action_proposal_id = gap.id
        JOIN tx t ON gap.tx_id = t.id
        WHERE encode(t.hash, 'hex') = %s
        AND gap.index = %s
        AND vp.voter_role = 'DRep'
    )
    SELECT
        COALESCE(cc_votes.voted_count, 0) as cc_voted,
        COALESCE(active_committee.total_members, 0) as cc_total,
        COALESCE(drep_votes.voted_count, 0) as drep_voted,
        COALESCE(total_dreps.total_count, 0) as drep_total
    FROM active_committee, cc_votes_for_action cc_votes, total_dreps, drep_votes_for_action drep_votes
"""
