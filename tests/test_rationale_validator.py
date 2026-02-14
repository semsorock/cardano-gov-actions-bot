"""Tests for bot.rationale_validator."""

from bot.rationale_validator import validate_cc_vote_rationale, validate_gov_action_rationale


class TestValidateGovActionRationale:
    """CIP-0108 validation tests."""

    def test_valid_metadata(self):
        metadata = {
            "body": {
                "title": "Short title",
                "abstract": "A brief abstract.",
                "motivation": "Why this matters.",
                "rationale": "How it works.",
            }
        }
        assert validate_gov_action_rationale(metadata) == []

    def test_none_metadata(self):
        result = validate_gov_action_rationale(None)
        assert result == ["Metadata could not be fetched"]

    def test_missing_body(self):
        result = validate_gov_action_rationale({"hashAlgorithm": "blake2b-256"})
        assert "Missing 'body' object (CIP-0108)" in result

    def test_missing_title(self):
        metadata = {"body": {"abstract": "ok", "motivation": "ok", "rationale": "ok"}}
        result = validate_gov_action_rationale(metadata)
        assert any("body.title" in w for w in result)

    def test_title_too_long(self):
        metadata = {
            "body": {
                "title": "x" * 81,
                "abstract": "ok",
                "motivation": "ok",
                "rationale": "ok",
            }
        }
        result = validate_gov_action_rationale(metadata)
        assert any("exceeds 80" in w for w in result)

    def test_missing_abstract(self):
        metadata = {"body": {"title": "ok", "motivation": "ok", "rationale": "ok"}}
        result = validate_gov_action_rationale(metadata)
        assert any("body.abstract" in w for w in result)

    def test_abstract_too_long(self):
        metadata = {
            "body": {
                "title": "ok",
                "abstract": "x" * 2501,
                "motivation": "ok",
                "rationale": "ok",
            }
        }
        result = validate_gov_action_rationale(metadata)
        assert any("exceeds 2500" in w for w in result)

    def test_missing_motivation(self):
        metadata = {"body": {"title": "ok", "abstract": "ok", "rationale": "ok"}}
        result = validate_gov_action_rationale(metadata)
        assert any("body.motivation" in w for w in result)

    def test_missing_rationale(self):
        metadata = {"body": {"title": "ok", "abstract": "ok", "motivation": "ok"}}
        result = validate_gov_action_rationale(metadata)
        assert any("body.rationale" in w for w in result)

    def test_multiple_missing_fields(self):
        metadata = {"body": {"@context": "ignored"}}
        result = validate_gov_action_rationale(metadata)
        assert len(result) == 4


class TestValidateCcVoteRationale:
    """CIP-0136 validation tests."""

    def test_valid_metadata(self):
        metadata = {
            "body": {
                "summary": "We vote yes.",
                "rationaleStatement": "Because reasons.",
            }
        }
        assert validate_cc_vote_rationale(metadata) == []

    def test_none_metadata(self):
        result = validate_cc_vote_rationale(None)
        assert result == ["Metadata could not be fetched"]

    def test_missing_body(self):
        result = validate_cc_vote_rationale({})
        assert "Missing 'body' object (CIP-0136)" in result

    def test_missing_summary(self):
        metadata = {"body": {"rationaleStatement": "ok"}}
        result = validate_cc_vote_rationale(metadata)
        assert any("body.summary" in w for w in result)

    def test_summary_too_long(self):
        metadata = {"body": {"summary": "x" * 301, "rationaleStatement": "ok"}}
        result = validate_cc_vote_rationale(metadata)
        assert any("exceeds 300" in w for w in result)

    def test_missing_rationale_statement(self):
        metadata = {"body": {"summary": "ok"}}
        result = validate_cc_vote_rationale(metadata)
        assert any("body.rationaleStatement" in w for w in result)

    def test_multiple_missing_fields(self):
        metadata = {"body": {"@context": "ignored"}}
        result = validate_cc_vote_rationale(metadata)
        assert len(result) == 2
