from decimal import Decimal

from bot.links import make_governance_action_link
from bot.metadata.fetcher import sanitise_url
from bot.models import CcVote, GaExpiration, GovAction, TreasuryDonation
from bot.twitter import templates

VOTES_MAPPING = {
    "YES": "Constitutional",
    "NO": "Unconstitutional",
    "ABSTAIN": "Abstain",
}


def _vote_display(vote: str) -> str:
    return VOTES_MAPPING.get(vote.upper(), vote)


def _authors_line(metadata: dict | None, *, label: str = "Authors", emoji: str = "") -> str:
    """Extract author names from CIP-100 metadata.

    Returns a formatted line like 'Authors: Name1, Name2\n' or empty string.
    """
    if not metadata:
        return ""
    authors = metadata.get("authors")
    if not authors:
        return ""
    names = [a.get("name", "") for a in authors if isinstance(a, dict)]
    names = [n for n in names if n]  # filter blanks
    if not names:
        return ""
    emoji_prefix = f"{emoji} " if emoji else ""
    return f"{emoji_prefix}{label}: {', '.join(names)}\n"


def format_gov_action_tweet(action: GovAction, metadata: dict | None) -> str:
    title = metadata.get("body", {}).get("title") if metadata else None
    title_line = f"Title: {title}\n" if title else ""
    authors_line = _authors_line(metadata, label="Authors")

    return templates.GOV_ACTION.format(
        title_line=title_line,
        authors_line=authors_line,
        action_type=action.action_type_display,
        link=make_governance_action_link(action.tx_hash, action.index),
    )


def format_cc_vote_tweet(
    vote: CcVote,
    metadata: dict | None,
    *,
    quote_tweet_id: str | None = None,
    voter_x_handle: str | None = None,
) -> str:
    voted_by_line = ""
    if voter_x_handle:
        voted_by_line = f"Voted by: {voter_x_handle}\n"
    else:
        voted_by_line = _authors_line(metadata, label="Voted by")
        if not voted_by_line:
            voted_by_line = f"Voted by: CC member ({vote.voter_hash[:8]})\n"

    if quote_tweet_id:
        # Quote-tweet: no GA link needed (it's embedded in the quoted tweet).
        return templates.CC_VOTE.format(
            vote_display=_vote_display(vote.vote),
            voted_by_line=voted_by_line,
            rationale_url=sanitise_url(vote.raw_url),
        )

    # Fallback: include GA link in the tweet text.
    return templates.CC_VOTE_NO_QUOTE.format(
        vote_display=_vote_display(vote.vote),
        voted_by_line=voted_by_line,
        ga_link=make_governance_action_link(vote.ga_tx_hash, vote.ga_index),
        rationale_url=sanitise_url(vote.raw_url),
    )


def format_ga_expiration_tweet(expiration: GaExpiration) -> str:
    return templates.GA_EXPIRATION.format(
        link=make_governance_action_link(expiration.tx_hash, expiration.index),
    )


def format_treasury_donations_tweet(donations: list[TreasuryDonation]) -> str:
    total_ada = sum((d.amount_ada for d in donations), start=Decimal(0))

    return templates.TREASURY_DONATIONS.format(
        count=len(donations),
        total_ada=total_ada,
    )
