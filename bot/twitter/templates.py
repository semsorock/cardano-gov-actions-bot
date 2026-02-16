"""Tweet text templates.

Edit these constants to change tweet wording without touching formatter logic.
Use Python str.format() placeholders — see formatter.py for available variables.
"""

GOV_ACTION = """\
Governance Action Update

{title_line}{authors_line}Type: {action_type}
Action: {link}

@IntersectMBO
#Cardano #Governance"""

CC_VOTE = """\
CC Vote Update

Decision: {vote_display}
{voted_by_line}Rationale: {rationale_url}

@IntersectMBO
#Cardano #Governance"""

CC_VOTE_NO_QUOTE = """\
CC Vote Update

Decision: {vote_display}
{voted_by_line}Governance Action: {ga_link}
Rationale: {rationale_url}

@IntersectMBO
#Cardano #Governance"""

GA_EXPIRATION = """\
Governance Action Expiry Notice

1 epoch (5 days) left to vote on this action.

Action: {link}
Review and vote if applicable.

@IntersectMBO
#Cardano #Governance"""

TREASURY_DONATIONS = """\
Treasury Donations Summary (Previous Epoch)

Transactions: {count}
Total Donated: {total_ada} ADA

@IntersectMBO
#Cardano #Treasury #Governance"""

VOTING_PROGRESS = """\
📊 Voting Progress Update

CC Members: {cc_voted}/{cc_total} voted
DReps: {drep_percentage}% participated

{link}

@IntersectMBO
#Cardano #Governance"""
