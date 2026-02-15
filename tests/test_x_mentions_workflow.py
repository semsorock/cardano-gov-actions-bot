import os
from dataclasses import replace

import pytest

os.environ.setdefault("DB_SYNC_URL", "postgresql://localhost/test")

from bot import main
from bot.github_issues import GithubIssueResult
from bot.llm_triage import TriageResult


def _payload(post_id: str, text: str = "@GovActions please help") -> dict:
    return {
        "for_user_id": "999",
        "tweet_create_events": [
            {
                "id_str": post_id,
                "text": text,
                "user": {"id_str": "111", "screen_name": "alice"},
                "entities": {"user_mentions": [{"id_str": "999", "screen_name": "GovActions"}]},
            }
        ],
    }


class TestXMentionsWorkflow:
    @pytest.fixture(autouse=True)
    def _stub_mention_state_store(self, monkeypatch):
        processed: set[str] = set()
        monkeypatch.setattr(main, "was_mention_processed", lambda post_id: post_id in processed)
        monkeypatch.setattr(
            main,
            "mark_mention_processed",
            lambda post_id, decision, issue_number=None: processed.add(post_id),
        )

    def test_bug_mention_creates_issue_and_replies(self, monkeypatch):
        cfg = replace(main.config, llm_model="mock-model", llm_issue_confidence_threshold=0.8)
        monkeypatch.setattr(main, "config", cfg)

        monkeypatch.setattr(
            main,
            "classify_mention",
            lambda *_args, **_kwargs: TriageResult(
                decision="bug_report",
                confidence=0.95,
                reason="clear bug report",
                issue_title="Bug: crash",
                issue_body_markdown="Steps to reproduce...",
            ),
        )
        monkeypatch.setattr(
            main,
            "create_or_get_issue_for_mention",
            lambda *_args, **_kwargs: GithubIssueResult(
                issue_url="https://github.com/org/repo/issues/1",
                issue_number=1,
                created=True,
            ),
        )

        replies = []
        monkeypatch.setattr(main, "post_reply_tweet", lambda text, post_id: replies.append((text, post_id)))

        main._process_x_mentions(_payload("1001", "@GovActions this is broken"))

        assert len(replies) == 1
        assert replies[0][1] == "1001"
        assert "https://github.com/org/repo/issues/1" in replies[0][0]

    def test_no_issue_mention_replies_without_creating_issue(self, monkeypatch):
        cfg = replace(main.config, llm_model="mock-model", llm_issue_confidence_threshold=0.8)
        monkeypatch.setattr(main, "config", cfg)

        monkeypatch.setattr(
            main,
            "classify_mention",
            lambda *_args, **_kwargs: TriageResult(
                decision="no_issue",
                confidence=0.9,
                reason="question only",
                short_reply="Thanks - this is noted but not an issue request.",
            ),
        )
        monkeypatch.setattr(
            main,
            "create_or_get_issue_for_mention",
            lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("should not create issue")),
        )

        replies = []
        monkeypatch.setattr(main, "post_reply_tweet", lambda text, post_id: replies.append((text, post_id)))

        main._process_x_mentions(_payload("1002", "@GovActions what does this do?"))

        assert len(replies) == 1
        assert replies[0][1] == "1002"
        assert replies[0][0].startswith("@alice ")

    def test_ignore_mention_does_not_reply(self, monkeypatch):
        cfg = replace(main.config, llm_model="mock-model", llm_issue_confidence_threshold=0.8)
        monkeypatch.setattr(main, "config", cfg)

        monkeypatch.setattr(
            main,
            "classify_mention",
            lambda *_args, **_kwargs: TriageResult(
                decision="ignore",
                confidence=0.99,
                reason="spam-like",
            ),
        )

        replies = []
        monkeypatch.setattr(main, "post_reply_tweet", lambda text, post_id: replies.append((text, post_id)))

        main._process_x_mentions(_payload("1003", "@GovActions buy followers now"))

        assert replies == []

    def test_duplicate_post_id_does_not_create_second_issue(self, monkeypatch):
        cfg = replace(main.config, llm_model="mock-model", llm_issue_confidence_threshold=0.8)
        monkeypatch.setattr(main, "config", cfg)

        monkeypatch.setattr(
            main,
            "classify_mention",
            lambda *_args, **_kwargs: TriageResult(
                decision="feature_request",
                confidence=0.92,
                reason="clear feature request",
                issue_title="Feature: improve formatting",
                issue_body_markdown="Detailed feature request...",
            ),
        )
        monkeypatch.setattr(
            main,
            "create_or_get_issue_for_mention",
            lambda *_args, **_kwargs: GithubIssueResult(
                issue_url="https://github.com/org/repo/issues/2",
                issue_number=2,
                created=False,
            ),
        )

        replies = []
        monkeypatch.setattr(main, "post_reply_tweet", lambda text, post_id: replies.append((text, post_id)))

        main._process_x_mentions(_payload("1004", "@GovActions can we add this feature?"))

        assert replies == []

    def test_duplicate_post_id_is_ignored_on_second_delivery(self, monkeypatch):
        cfg = replace(main.config, llm_model="mock-model", llm_issue_confidence_threshold=0.8)
        monkeypatch.setattr(main, "config", cfg)

        processed: set[str] = set()
        monkeypatch.setattr(main, "was_mention_processed", lambda post_id: post_id in processed)
        monkeypatch.setattr(
            main,
            "mark_mention_processed",
            lambda post_id, decision, issue_number=None: processed.add(post_id),
        )

        monkeypatch.setattr(
            main,
            "classify_mention",
            lambda *_args, **_kwargs: TriageResult(
                decision="no_issue",
                confidence=0.9,
                reason="question only",
                short_reply="Thanks for the mention.",
            ),
        )

        replies = []
        monkeypatch.setattr(main, "post_reply_tweet", lambda text, post_id: replies.append((text, post_id)))
        monkeypatch.setattr(
            main,
            "create_or_get_issue_for_mention",
            lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("should not create issue")),
        )

        payload = _payload("1005", "@GovActions what changed?")
        main._process_x_mentions(payload)
        main._process_x_mentions(payload)

        assert len(replies) == 1
        assert replies[0][1] == "1005"

    def test_llm_failure_marks_processed_to_prevent_retry_loop(self, monkeypatch):
        cfg = replace(main.config, llm_model="mock-model", llm_issue_confidence_threshold=0.8)
        monkeypatch.setattr(main, "config", cfg)

        processed: set[str] = set()
        monkeypatch.setattr(main, "was_mention_processed", lambda post_id: post_id in processed)
        monkeypatch.setattr(
            main,
            "mark_mention_processed",
            lambda post_id, decision, issue_number=None: processed.add(post_id),
        )

        # Simulate LLM failure
        def raise_llm_error(*_args, **_kwargs):
            raise RuntimeError("LLM timeout")

        monkeypatch.setattr(main, "classify_mention", raise_llm_error)

        replies = []
        monkeypatch.setattr(main, "post_reply_tweet", lambda text, post_id: replies.append((text, post_id)))
        monkeypatch.setattr(
            main,
            "create_or_get_issue_for_mention",
            lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("should not create issue")),
        )

        payload = _payload("1006", "@GovActions this needs attention")
        main._process_x_mentions(payload)

        # Verify the mention was marked as processed despite the LLM failure
        assert "1006" in processed
        # Verify no reply was sent (because LLM failed before we could determine what to say)
        assert len(replies) == 0

        # Second delivery should be ignored
        main._process_x_mentions(payload)
        assert len(replies) == 0

    def test_issue_creation_failure_marks_processed_to_prevent_retry_loop(self, monkeypatch):
        cfg = replace(main.config, llm_model="mock-model", llm_issue_confidence_threshold=0.8)
        monkeypatch.setattr(main, "config", cfg)

        processed: set[str] = set()
        monkeypatch.setattr(main, "was_mention_processed", lambda post_id: post_id in processed)
        monkeypatch.setattr(
            main,
            "mark_mention_processed",
            lambda post_id, decision, issue_number=None: processed.add(post_id),
        )

        monkeypatch.setattr(
            main,
            "classify_mention",
            lambda *_args, **_kwargs: TriageResult(
                decision="bug_report",
                confidence=0.95,
                reason="clear bug report",
                issue_title="Bug: crash",
                issue_body_markdown="Steps to reproduce...",
            ),
        )

        # Simulate GitHub API failure
        def raise_github_error(*_args, **_kwargs):
            raise RuntimeError("GitHub API error")

        monkeypatch.setattr(main, "create_or_get_issue_for_mention", raise_github_error)

        replies = []
        monkeypatch.setattr(main, "post_reply_tweet", lambda text, post_id: replies.append((text, post_id)))

        payload = _payload("1007", "@GovActions found a bug")
        main._process_x_mentions(payload)

        # Verify the mention was marked as processed despite the issue creation failure
        assert "1007" in processed
        # Verify no reply was sent (because issue creation failed)
        assert len(replies) == 0

        # Second delivery should be ignored
        main._process_x_mentions(payload)
        assert len(replies) == 0
