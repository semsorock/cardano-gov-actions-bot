from pathlib import Path

from bot.cc_profiles import clear_profile_cache, get_x_handle_for_voter_hash


class TestCcProfiles:
    def test_lookup_by_hash(self, tmp_path: Path):
        profile = tmp_path / "cc_profiles.yaml"
        profile.write_text(
            """\
members:
  - member_id: "member-a"
    voter_hash: "aa11"
    x_handle: "@aaa"
  - member_id: "member-b"
    voter_hash: "bb22"
    x_handle: "bbb"
""",
            encoding="utf-8",
        )
        clear_profile_cache()

        assert get_x_handle_for_voter_hash("aa11", path=profile) == "@aaa"
        assert get_x_handle_for_voter_hash("BB22", path=profile) == "@bbb"

    def test_missing_file_returns_none(self, tmp_path: Path):
        missing = tmp_path / "missing.yaml"
        clear_profile_cache()

        assert get_x_handle_for_voter_hash("aa11", path=missing) is None
