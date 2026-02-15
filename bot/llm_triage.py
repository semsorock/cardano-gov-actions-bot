"""LLM-based triage for X mention events."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Literal

from bot.logging import get_logger
from bot.x_mentions import MentionEvent

logger = get_logger("llm_triage")

Decision = Literal["bug_report", "feature_request", "no_issue", "ignore"]

# Maximum length for mention text to prevent excessive LLM token usage
MAX_MENTION_LENGTH = 2000

# Patterns that may indicate prompt injection attempts
SUSPICIOUS_PATTERNS = [
    re.compile(
        r"(ignore|forget|disregard).{0,20}(previous|prior|above).{0,20}(instruction|prompt|rule|command)",
        re.IGNORECASE,
    ),
    re.compile(r"system\s*:\s*", re.IGNORECASE),
    re.compile(r"(you\s+are|act\s+as|pretend\s+to\s+be|behave\s+like)\s+(a|an|now)", re.IGNORECASE),
    re.compile(r"[{}\[\]]{5,}"),  # Excessive braces/brackets
    re.compile(r"(.)\1{9,}"),  # Same character repeated 10+ times (e.g., !!!!!!!!!!)
]


@dataclass(frozen=True)
class TriageResult:
    decision: Decision
    confidence: float
    reason: str
    issue_title: str = ""
    issue_body_markdown: str = ""
    short_reply: str = ""


class LlmTriageError(Exception):
    """Raised when triage output cannot be parsed or validated."""


def _sanitize_mention_text(text: str, post_id: str) -> str:
    """Sanitize user-provided mention text before including in LLM prompt.

    Args:
        text: Raw mention text from user
        post_id: Post ID for logging purposes

    Returns:
        Sanitized text safe for inclusion in prompt
    """
    # Normalize whitespace
    sanitized = " ".join(text.split())

    # Apply length limit
    if len(sanitized) > MAX_MENTION_LENGTH:
        logger.warning(
            "Mention text exceeds max length (%d > %d) for post %s, truncating",
            len(sanitized),
            MAX_MENTION_LENGTH,
            post_id,
        )
        sanitized = sanitized[:MAX_MENTION_LENGTH]

    # Check for suspicious patterns
    for pattern in SUSPICIOUS_PATTERNS:
        if pattern.search(sanitized):
            logger.warning(
                "Mention text contains suspicious pattern (possible injection attempt) for post %s: %s",
                post_id,
                pattern.pattern,
            )

    return sanitized


def classify_mention(mention: MentionEvent, *, model: str) -> TriageResult:
    """Classify a mention and optionally draft GitHub issue content."""
    if not model:
        raise LlmTriageError("LLM model is required for mention triage")

    try:
        from litellm import completion
    except Exception as exc:
        raise LlmTriageError("litellm is not installed or failed to import") from exc

    # Sanitize user input before including in prompt
    sanitized_text = _sanitize_mention_text(mention.text, mention.post_id)

    messages = [
        {
            "role": "system",
            "content": (
                "You triage X mentions for a software project. Output only valid JSON with keys: "
                "decision, confidence, reason, issue_title, issue_body_markdown, short_reply. "
                "decision must be one of: bug_report, feature_request, no_issue, ignore. "
                "Use bug_report only for clear defects, feature_request for clear enhancements, "
                "no_issue for support/unclear/non-actionable that still deserves a brief response, "
                "ignore for spam/irrelevant content that should be silently ignored. "
                "confidence must be between 0 and 1."
            ),
        },
        {
            "role": "user",
            "content": (
                "Analyze this mention and return JSON only.\n"
                f"author_handle: @{mention.author_handle}\n"
                f"post_id: {mention.post_id}\n"
                f"text: {sanitized_text}\n"
            ),
        },
    ]

    response = completion(model=model, messages=messages, temperature=0)
    content = _extract_content(response)
    payload = _parse_payload(content)

    return _validate_result(payload)


def _extract_content(response: object) -> str:
    if isinstance(response, dict):
        choices = response.get("choices")
    else:
        choices = getattr(response, "choices", None)

    if not choices:
        raise LlmTriageError("LLM response missing choices")

    first_choice = choices[0]
    if isinstance(first_choice, dict):
        message = first_choice.get("message", {})
    else:
        message = getattr(first_choice, "message", None)

    if isinstance(message, dict):
        content = message.get("content", "")
    else:
        content = getattr(message, "content", "")

    if not isinstance(content, str) or not content.strip():
        raise LlmTriageError("LLM response content was empty")

    return content.strip()


def _parse_payload(content: str) -> dict:
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        pass

    # Accept fenced JSON and best-effort extract object body.
    stripped = content.strip()
    if stripped.startswith("```"):
        stripped = stripped.strip("`")
        if stripped.startswith("json"):
            stripped = stripped[4:].strip()
        try:
            return json.loads(stripped)
        except json.JSONDecodeError:
            pass

    start = content.find("{")
    end = content.rfind("}")
    if start != -1 and end != -1 and end > start:
        candidate = content[start : end + 1]
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            pass

    raise LlmTriageError("LLM returned non-JSON triage output")


def _validate_result(payload: dict) -> TriageResult:
    decision = payload.get("decision")
    if decision not in {"bug_report", "feature_request", "no_issue", "ignore"}:
        raise LlmTriageError(f"Invalid triage decision: {decision!r}")

    try:
        confidence = float(payload.get("confidence"))
    except (TypeError, ValueError) as exc:
        raise LlmTriageError("confidence must be a number") from exc

    if not 0 <= confidence <= 1:
        raise LlmTriageError("confidence must be between 0 and 1")

    reason = str(payload.get("reason") or "").strip()
    issue_title = str(payload.get("issue_title") or "").strip()
    issue_body = str(payload.get("issue_body_markdown") or "").strip()
    short_reply = str(payload.get("short_reply") or "").strip()

    if not reason:
        raise LlmTriageError("reason is required")

    if decision in {"bug_report", "feature_request"}:
        if not issue_title:
            raise LlmTriageError("issue_title is required for issue decisions")
        if not issue_body:
            raise LlmTriageError("issue_body_markdown is required for issue decisions")

    if decision == "no_issue" and not short_reply:
        raise LlmTriageError("short_reply is required for no_issue decisions")

    result = TriageResult(
        decision=decision,
        confidence=confidence,
        reason=reason,
        issue_title=issue_title,
        issue_body_markdown=issue_body,
        short_reply=short_reply,
    )
    logger.debug("Triage result for %s: %s", payload.get("post_id", "unknown"), result)
    return result
