from bot import github_issues
from bot.llm_triage import TriageResult
from bot.x_mentions import MentionEvent


class _Label:
    def __init__(self, name: str):
        self.name = name


class _Issue:
    def __init__(self, number: int, body: str):
        self.number = number
        self.body = body
        self.html_url = f"https://github.com/org/repo/issues/{number}"


class _FakeRepo:
    def __init__(self, labels: list[str], issues: list[_Issue] | None = None):
        self._labels = labels
        self._issues = issues or []
        self.created_payloads = []

    def get_labels(self):
        return [_Label(name) for name in self._labels]

    def get_issues(self, state: str = "open"):
        assert state == "all"
        return self._issues

    def create_issue(self, **kwargs):
        self.created_payloads.append(kwargs)
        issue = _Issue(number=42, body=kwargs.get("body", ""))
        self._issues.append(issue)
        return issue


def _mention(post_id: str = "111") -> MentionEvent:
    return MentionEvent(
        post_id=post_id,
        text="@GovActions feature request",
        author_id="123",
        author_handle="alice",
        permalink=f"https://x.com/alice/status/{post_id}",
    )


def test_create_issue_applies_labels_and_marker(monkeypatch):
    repo = _FakeRepo(labels=["source:x", "enhancement", "bug"])
    monkeypatch.setattr(github_issues, "_get_repo", lambda: repo)

    triage = TriageResult(
        decision="feature_request",
        confidence=0.95,
        reason="feature request",
        issue_title="Feature: add export",
        issue_body_markdown="Please add export support.",
    )

    result = github_issues.create_or_get_issue_for_mention(_mention("2001"), triage)

    assert result.created is True
    payload = repo.created_payloads[0]
    assert payload["title"] == "Feature: add export"
    assert "x_post_id:2001" in payload["body"]
    assert payload["labels"] == ["source:x", "enhancement"]


def test_create_issue_is_idempotent_by_post_id(monkeypatch):
    existing = _Issue(number=7, body="Existing\n<!-- x_post_id:3001 -->")
    repo = _FakeRepo(labels=["source:x", "bug"], issues=[existing])
    monkeypatch.setattr(github_issues, "_get_repo", lambda: repo)

    triage = TriageResult(
        decision="bug_report",
        confidence=0.99,
        reason="bug",
        issue_title="Bug: crash",
        issue_body_markdown="Repro steps",
    )

    result = github_issues.create_or_get_issue_for_mention(_mention("3001"), triage)

    assert result.created is False
    assert result.issue_number == 7
    assert repo.created_payloads == []
