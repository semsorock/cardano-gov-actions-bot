"""Archive governance rationale files to GitHub via PR."""

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


def _ensure_branch(repo, branch_name: str, base: str = "main") -> str:
    """Create a branch if it doesn't exist. Returns the branch name."""
    try:
        repo.get_branch(branch_name)
    except GithubException:
        base_ref = repo.get_branch(base)
        repo.create_git_ref(
            ref=f"refs/heads/{branch_name}",
            sha=base_ref.commit.sha,
        )
        logger.info("Created branch: %s", branch_name)
    return branch_name


def _create_or_update_file(
    repo,
    branch: str,
    path: str,
    content: str,
    message: str,
) -> None:
    """Create or update a file on the given branch."""
    try:
        existing = repo.get_contents(path, ref=branch)
        repo.update_file(
            path=path,
            message=message,
            content=content,
            sha=existing.sha,
            branch=branch,
        )
    except GithubException:
        repo.create_file(
            path=path,
            message=message,
            content=content,
            branch=branch,
        )


def _open_pr(repo, branch: str, title: str) -> None:
    """Open a PR if one doesn't already exist for this branch."""
    pulls = repo.get_pulls(state="open", head=f"{repo.owner.login}:{branch}")
    if pulls.totalCount > 0:
        logger.debug("PR already exists for branch %s", branch)
        return

    pr = repo.create_pull(
        title=title,
        body="Automated rationale archive update.",
        head=branch,
        base="main",
    )
    logger.info("Opened PR #%d: %s", pr.number, title)


def archive_gov_action(action: GovAction, metadata: dict | None) -> None:
    """Archive a governance action rationale via GitHub PR."""
    gh = _get_github()
    if gh is None:
        logger.debug("GitHub not configured — skipping rationale archive")
        return

    if metadata is None:
        metadata = {"error": "Failed to fetch rationale", "url": action.raw_url}

    try:
        repo = gh.get_repo(config.github_repo)
        action_id = _action_dir(action)
        branch = f"rationale/{action_id}"

        _ensure_branch(repo, branch)

        path = f"rationales/{action_id}/action.json"
        content = json.dumps(metadata, indent=2, ensure_ascii=False) + "\n"

        _create_or_update_file(
            repo,
            branch,
            path,
            content,
            message=f"Add rationale for gov action {action_id}",
        )
        _open_pr(repo, branch, f"Rationale: gov action {action_id}")
    except Exception:
        logger.exception("Failed to archive gov action %s", action.tx_hash)


def archive_cc_vote(vote: CcVote, metadata: dict | None) -> None:
    """Archive a CC vote rationale via GitHub PR."""
    gh = _get_github()
    if gh is None:
        logger.debug("GitHub not configured — skipping vote archive")
        return

    if metadata is None:
        metadata = {"error": "Failed to fetch rationale", "url": vote.raw_url}

    try:
        repo = gh.get_repo(config.github_repo)
        action_id = f"{vote.ga_tx_hash}_{vote.ga_index}"
        branch = f"rationale/{action_id}"

        _ensure_branch(repo, branch)

        path = f"rationales/{action_id}/cc_votes/{vote.voter_hash}.json"
        content = json.dumps(metadata, indent=2, ensure_ascii=False) + "\n"

        _create_or_update_file(
            repo,
            branch,
            path,
            content,
            message=f"Add CC vote rationale: {vote.voter_hash[:8]} on {action_id}",
        )
        _open_pr(repo, branch, f"Rationale: gov action {action_id}")
    except Exception:
        logger.exception("Failed to archive CC vote for %s", vote.voter_hash)
