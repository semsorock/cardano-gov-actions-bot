"""Tweet text templates.

Edit these constants to change tweet wording without touching formatter logic.
Use Python str.format() placeholders — see formatter.py for available variables.
"""

GOV_ACTION = """\
🚨 NEW GOVERNANCE ACTION ALERT! 🚨

{title_line}{authors_line}🏷️ Type: {action_type}
🔗 Details: {link}

#Cardano #Blockchain #Governance"""

CC_VOTE = """\
📜 CC MEMBER VOTE ALERT! 📜

🗳️ The vote is: {vote_display}
{voted_by_line}🔗 Gov Action: {ga_link}
🔗 The vote rationale: {rationale_url}

#Cardano #Blockchain #Governance"""

GA_EXPIRATION = """\
⏳ GOVERNANCE ACTION EXPIRY ALERT! ⏳

Heads up! There is only 1 epoch (5 days) left to vote on this GA:

🔗 {link}
Make sure to review and participate if applicable!

#Cardano #Blockchain #Governance"""

TREASURY_DONATIONS = """\
💸 PREVIOUS EPOCH TREASURY DONATIONS! 💸

Here are the Cardano Treasury donation stats for the last epoch:
📈 Donations Count: {count}
💰 Total Donated: {total_ada} ADA
Thank you to everyone supporting the growth of #Cardano!

#Treasury #Blockchain #Governance"""
