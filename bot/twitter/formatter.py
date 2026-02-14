from decimal import Decimal

from bot.links import make_adastat_link
from bot.metadata.fetcher import sanitise_url
from bot.models import CcVote, GaExpiration, GovAction, TreasuryDonation

VOTES_MAPPING = {
    "YES": "Constitutional",
    "NO": "Unconstitutional",
    "ABSTAIN": "Abstain",
}


def _vote_display(vote: str) -> str:
    return VOTES_MAPPING.get(vote.upper(), vote)


# ---------------------------------------------------------------------------
# Governance Action
# ---------------------------------------------------------------------------


def format_gov_action_tweet(action: GovAction, metadata: dict | None) -> str:
    lines = ["🚨 NEW GOVERNANCE ACTION ALERT! 🚨\n"]

    if metadata:
        title = metadata.get("body", {}).get("title")
        if title:
            lines.append(f"📢 Title: {title}")

    lines.append(f"🏷️ Type: {action.action_type_display}")
    lines.append(f"🔗 Details: {make_adastat_link(action.tx_hash, action.index)}\n\n")
    lines.append("#Cardano #Blockchain #Governance")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CC Vote
# ---------------------------------------------------------------------------


def format_cc_vote_tweet(vote: CcVote, metadata: dict | None) -> str:
    lines = ["📜 CC MEMBER VOTE ALERT! 📜\n"]
    lines.append(f"🗳️ The vote is: {_vote_display(vote.vote)}")

    if metadata:
        authors = metadata.get("authors")
        if authors and len(authors) > 0:
            names = ", ".join(a.get("name", "") for a in authors)
            lines.append(f"👥 Voted by: {names}\n")

    url = sanitise_url(vote.raw_url)
    lines.append(f"🔗 Gov Action: {make_adastat_link(vote.ga_tx_hash, vote.ga_index)}")
    lines.append(f"🔗 The vote rationale: {url}\n\n")
    lines.append("#Cardano #Blockchain #Governance")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# GA Expiration
# ---------------------------------------------------------------------------


def format_ga_expiration_tweet(expiration: GaExpiration) -> str:
    lines = [
        "⏳ GOVERNANCE ACTION EXPIRY ALERT! ⏳\n\n",
        "Heads up! There is only 1 epoch (5 days) left to vote on this GA:\n",
        f"🔗 {make_adastat_link(expiration.tx_hash, expiration.index)}",
        "Make sure to review and participate if applicable!\n\n",
        "#Cardano #Blockchain #Governance",
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Treasury Donations
# ---------------------------------------------------------------------------


def format_treasury_donations_tweet(donations: list[TreasuryDonation]) -> str:
    total_ada = sum((d.amount_ada for d in donations), start=Decimal(0))

    lines = [
        "💸 PREVIOUS EPOCH TREASURY DONATIONS! 💸\n",
        "Here are the Cardano Treasury donation stats for the last epoch:",
        f"📈 Donations Count: {len(donations)}",
        f"💰 Total Donated: {total_ada} ADA",
        "Thank you to everyone supporting the growth of #Cardano!\n",
        "#Treasury #Blockchain #Governance",
    ]
    return "\n".join(lines)
