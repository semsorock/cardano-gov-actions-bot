from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from bot.logging import get_logger

logger = get_logger("cc_profiles")

_DEFAULT_PROFILE_PATH = Path(__file__).resolve().parent.parent / "data" / "cc_profiles.yaml"


def _strip_quotes(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value


def _normalise_handle(handle: str) -> str:
    handle = handle.strip()
    if not handle:
        return ""
    return handle if handle.startswith("@") else f"@{handle}"


def _parse_hash_to_handle(text: str) -> dict[str, str]:
    """Parse a narrow YAML shape and return voter_hash -> X handle map."""
    mappings: dict[str, str] = {}
    current_hash: str | None = None
    current_handle: str | None = None

    def _flush() -> None:
        nonlocal current_hash, current_handle
        if current_hash and current_handle:
            mappings[current_hash] = current_handle
        current_hash = None
        current_handle = None

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue

        if line.startswith("- member_id:"):
            _flush()
            continue

        if line.startswith("voter_hash:"):
            value = _strip_quotes(line.split(":", 1)[1].strip())
            if value and value.lower() != "null":
                current_hash = value.lower()
            continue

        if line.startswith("x_handle:"):
            value = _strip_quotes(line.split(":", 1)[1].strip())
            current_handle = _normalise_handle(value)
            continue

    _flush()
    return mappings


@lru_cache(maxsize=4)
def _load_hash_to_handle(path: str) -> dict[str, str]:
    profile_path = Path(path)
    if not profile_path.exists():
        logger.warning("CC profile file not found: %s", profile_path)
        return {}

    try:
        return _parse_hash_to_handle(profile_path.read_text(encoding="utf-8"))
    except Exception:
        logger.exception("Failed to load CC profile file: %s", profile_path)
        return {}


def get_x_handle_for_voter_hash(voter_hash: str, *, path: Path | None = None) -> str | None:
    profile_path = path or _DEFAULT_PROFILE_PATH
    mappings = _load_hash_to_handle(str(profile_path))
    return mappings.get(voter_hash.lower())


def clear_profile_cache() -> None:
    _load_hash_to_handle.cache_clear()
