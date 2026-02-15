"""GitHub issue creation and deduplication for X mentions."""

from __future__ import annotations

from dataclasses import dataclass

from github import Github, GithubException

from bot.config import config
from bot.llm_triage import TriageResult
from bot.logging import get_logger
from bot.x_mentions import MentionEvent

logger = get_logger("github_issues")


@dataclass(frozen=True)
class GithubIssueResult:
    issue_url: str
    issue_number: int
    created: bool


def create_or_get_issue_for_mention(mention: MentionEvent, triage: TriageResult) -> GithubIssueResult:
    """Create a new issue unless one already exists for the same X post ID."""
    repo = _get_repo()

    existing = find_issue_by_post_id(mention.post_id, repo=repo)
    if existing is not None:
        logger.info("Issue already exists for post %s: #%s", mention.post_id, existing.number)
        return GithubIssueResult(issue_url=existing.html_url, issue_number=int(existing.number), created=False)

    labels = _resolve_labels(repo, triage)
    marker = _marker_for_post_id(mention.post_id)
    body = (
        f"{triage.issue_body_markdown}\n\n"
        "---\n"
        f"Source mention: {mention.permalink}\n"
        f"Author: @{mention.author_handle}\n\n"
        f"{marker}\n"
    )

    issue_kwargs = {"title": triage.issue_title, "body": body}
    if labels:
        issue_kwargs["labels"] = labels

    issue = repo.create_issue(**issue_kwargs)
    logger.info("Created issue #%s for post %s", issue.number, mention.post_id)
    return GithubIssueResult(issue_url=issue.html_url, issue_number=int(issue.number), created=True)


def find_issue_by_post_id(post_id: str, repo=None):
    """Return an existing open issue for an X post ID if found."""
    if repo is None:
        repo = _get_repo()
    marker = _marker_for_post_id(post_id)
    try:
        for issue in repo.get_issues(state="all"):
            body = issue.body or ""
            if marker in body:
                return issue
    except GithubException:
        logger.exception("Failed to query issues while checking dedupe for post %s", post_id)
    return None


def _marker_for_post_id(post_id: str) -> str:
    return f"<!-- x_post_id:{post_id} -->"


def _get_repo():
    if not config.github_token or not config.github_repo:
        raise RuntimeError("GitHub issue integration requires GITHUB_TOKEN and GITHUB_REPO")
    gh = Github(config.github_token)
    return gh.get_repo(config.github_repo)


def _resolve_labels(repo, triage: TriageResult) -> list[str]:
    desired = ["source:x", "bug" if triage.decision == "bug_report" else "enhancement"]
    available = {label.name for label in repo.get_labels()}
    labels = [label for label in desired if label in available]
    missing = [label for label in desired if label not in available]
    for label in missing:
        logger.warning(
            "Label '%s' does not exist in repo %s; issue will be created without it",
            label,
            config.github_repo,
        )
    return labels
