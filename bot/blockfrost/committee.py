"""Parse the Blockfrost ``/governance/committee`` snapshot.

The snapshot supplies everything the threshold logic needs about the
Constitutional Committee: the voting ``quorum``, whether the committee has been
dissolved by a ``NoConfidence`` action, the seated members (for the
minimum-size check) and the hot→cold credential mapping used to resolve a
vote's cold-key identity.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class CommitteeSnapshot:
    """Parsed view of the currently active constitutional committee."""

    quorum: float | None = None
    is_dissolved: bool = False
    members: tuple[dict, ...] = ()
    # hot credential (bech32 id and hex) -> cold-key hex.
    hot_to_cold: dict[str, str] = field(default_factory=dict)

    def active_member_count(self, current_epoch: int | None = None) -> int:
        """Number of members able to vote: authorized hot key, not expired.

        When ``current_epoch`` is unknown, expiration is not applied (the
        authorized count is returned).
        """
        count = 0
        for m in self.members:
            if m.get("status") != "authorized":
                continue
            if current_epoch is not None:
                expiration = m.get("expiration_epoch")
                if isinstance(expiration, int) and current_epoch > expiration:
                    continue
            count += 1
        return count

    def cold_hex_for_hot(self, voter_hot_id: str | None) -> str | None:
        """Resolve a vote's hot credential to its cold-key hex, if known."""
        if not voter_hot_id:
            return None
        return self.hot_to_cold.get(voter_hot_id)


def _quorum_ratio(quorum: dict | None) -> float | None:
    if not isinstance(quorum, dict):
        return None
    numerator = quorum.get("numerator")
    denominator = quorum.get("denominator")
    if not isinstance(numerator, int) or not isinstance(denominator, int) or denominator == 0:
        return None
    return numerator / denominator


def parse_committee_snapshot(data: dict | None) -> CommitteeSnapshot | None:
    """Build a :class:`CommitteeSnapshot` from a ``/governance/committee`` body."""
    if not isinstance(data, dict):
        return None

    members = tuple(m for m in data.get("members", []) if isinstance(m, dict))

    hot_to_cold: dict[str, str] = {}
    for m in members:
        cold_hex = m.get("cc_cold_hex")
        if not cold_hex:
            continue
        for hot_key in (m.get("cc_hot_id"), m.get("cc_hot_hex")):
            if hot_key:
                hot_to_cold[hot_key] = cold_hex

    return CommitteeSnapshot(
        quorum=_quorum_ratio(data.get("quorum")),
        is_dissolved=bool(data.get("is_dissolved", False)),
        members=members,
        hot_to_cold=hot_to_cold,
    )
