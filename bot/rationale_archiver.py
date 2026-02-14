"""Archive governance rationale files to GitHub."""

from __future__ import annotations

import json

from github import Github, GithubException

from bot.config import config
from bot.logging import get_logger
from bot.models import CcVote, GovAction

logger = get_logger("rationale_archiver")


def _get_github() -> Github | None:
    """Return a GitHub client, or None if not configured."""
    if not config.github_token or not config.github_repo:
        return None
    return Github(config.github_token)


def _action_dir(action: GovAction) -> str:
    return f"{action.tx_hash}_{action.index}"


def _create_or_update_file(
    repo,
    path: str,
    content: str,
    message: str,
    ref: str = "main",
) -> None:
    """Create or update a file on the given ref."""
    try:
        existing = repo.get_contents(path, ref=ref)
        repo.update_file(
            path=path,
            message=message,
            content=content,
            sha=existing.sha,
            branch=ref,
        )
    except GithubException:
        repo.create_file(
            path=path,
            message=message,
            content=content,
            branch=ref,
        )


def archive_gov_action(
    action: GovAction,
    metadata: dict | None,
    tweet_id: str | None = None,
) -> None:
    """Archive a governance action rationale directly on GitHub."""
    gh = _get_github()
    if gh is None:
        logger.debug("GitHub not configured — skipping rationale archive")
        return

    if metadata is None:
        metadata = {"error": "Failed to fetch rationale", "url": action.raw_url}

    try:
        repo = gh.get_repo(config.github_repo)
        action_id = _action_dir(action)

        path = f"rationales/{action_id}/action.json"
        content = json.dumps(metadata, indent=2, ensure_ascii=False) + "\n"

        _create_or_update_file(
            repo,
            path,
            content,
            message=f"Add rationale for gov action {action_id}",
        )

        # Store tweet ID alongside rationale for quote-tweet lookups.
        if tweet_id:
            _create_or_update_file(
                repo,
                f"rationales/{action_id}/tweet_id.txt",
                tweet_id + "\n",
                message=f"Add tweet ID for gov action {action_id}",
            )
    except Exception:
        logger.exception("Failed to archive gov action %s", action.tx_hash)


def get_action_tweet_id(tx_hash: str, index: int) -> str | None:
    """Look up the tweet ID for a governance action from GitHub."""
    gh = _get_github()
    if gh is None:
        return None

    action_id = f"{tx_hash}_{index}"
    path = f"rationales/{action_id}/tweet_id.txt"

    try:
        repo = gh.get_repo(config.github_repo)
        content = repo.get_contents(path, ref="main")
        tweet_id = content.decoded_content.decode().strip()
        logger.debug("Found tweet ID for %s: %s", action_id, tweet_id)
        return tweet_id if tweet_id else None
    except GithubException:
        logger.debug("No tweet ID found for %s", action_id)
        return None
    except Exception:
        logger.exception("Error fetching tweet ID for %s", action_id)
        return None


def archive_cc_vote(vote: CcVote, metadata: dict | None) -> None:
    """Archive a CC vote rationale directly on GitHub."""
    gh = _get_github()
    if gh is None:
        logger.debug("GitHub not configured — skipping vote archive")
        return

    if metadata is None:
        metadata = {"error": "Failed to fetch rationale", "url": vote.raw_url}

    try:
        repo = gh.get_repo(config.github_repo)
        action_id = f"{vote.ga_tx_hash}_{vote.ga_index}"

        path = f"rationales/{action_id}/cc_votes/{vote.voter_hash}.json"
        content = json.dumps(metadata, indent=2, ensure_ascii=False) + "\n"

        _create_or_update_file(
            repo,
            path,
            content,
            message=f"Add CC vote rationale: {vote.voter_hash[:8]} on {action_id}",
        )
    except Exception:
        logger.exception("Failed to archive CC vote for %s", vote.voter_hash)
