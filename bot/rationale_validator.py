"""Validate governance rationale metadata against CIP standards.

CIP-0108: Governance Action rationale (title, abstract, motivation, rationale).
CIP-0136: CC Vote rationale (summary, rationaleStatement).

Validation is non-blocking — issues are returned as a list of warnings.
"""

from __future__ import annotations

from bot.logging import get_logger

logger = get_logger("rationale_validator")


def validate_gov_action_rationale(metadata: dict | None) -> list[str]:
    """Validate governance action metadata against CIP-0108.

    Returns a list of warning messages (empty = valid).
    """
    if metadata is None:
        return ["Metadata could not be fetched"]

    warnings: list[str] = []
    body = metadata.get("body")

    if not body or not isinstance(body, dict):
        warnings.append("Missing 'body' object (CIP-0108)")
        return warnings

    # title — required, ≤80 characters
    title = body.get("title")
    if not title:
        warnings.append("Missing required field 'body.title' (CIP-0108)")
    elif len(title) > 80:
        warnings.append(f"Field 'body.title' exceeds 80 characters ({len(title)}) (CIP-0108)")

    # abstract — required, ≤2500 characters
    abstract = body.get("abstract")
    if not abstract:
        warnings.append("Missing required field 'body.abstract' (CIP-0108)")
    elif len(abstract) > 2500:
        warnings.append(f"Field 'body.abstract' exceeds 2500 characters ({len(abstract)}) (CIP-0108)")

    # motivation — required
    if not body.get("motivation"):
        warnings.append("Missing required field 'body.motivation' (CIP-0108)")

    # rationale — required
    if not body.get("rationale"):
        warnings.append("Missing required field 'body.rationale' (CIP-0108)")

    return warnings


def validate_cc_vote_rationale(metadata: dict | None) -> list[str]:
    """Validate CC vote metadata against CIP-0136.

    Returns a list of warning messages (empty = valid).
    """
    if metadata is None:
        return ["Metadata could not be fetched"]

    warnings: list[str] = []
    body = metadata.get("body")

    if not body or not isinstance(body, dict):
        warnings.append("Missing 'body' object (CIP-0136)")
        return warnings

    # summary — required, ≤300 characters
    summary = body.get("summary")
    if not summary:
        warnings.append("Missing required field 'body.summary' (CIP-0136)")
    elif len(summary) > 300:
        warnings.append(f"Field 'body.summary' exceeds 300 characters ({len(summary)}) (CIP-0136)")

    # rationaleStatement — required
    if not body.get("rationaleStatement"):
        warnings.append("Missing required field 'body.rationaleStatement' (CIP-0136)")

    return warnings
