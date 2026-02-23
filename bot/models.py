import re
from dataclasses import dataclass


def camel_case_to_spaced(value: str | None) -> str | None:
    """Convert CamelCase to 'Camel Case'. Returns None for non-string input."""
    if not isinstance(value, str):
        return None
    if not value:
        return ""
    return re.sub(r"(?<!^)(?=[A-Z])", " ", value)


@dataclass(frozen=True)
class ProposalMetadata:
    """Metadata for a governance proposal."""

    url: str
    hash: str
    json_metadata: dict | None = None


@dataclass(frozen=True)
class GovAction:
    tx_hash: str
    action_type: str
    index: int
    id: str  # Governance action ID (CIP-0129)
    metadata: ProposalMetadata | None = None

    @property
    def action_type_display(self) -> str | None:
        return camel_case_to_spaced(self.action_type)

    @property
    def raw_url(self) -> str:
        """Legacy property for backward compatibility."""
        return self.metadata.url if self.metadata else ""


@dataclass(frozen=True)
class CcVote:
    ga_tx_hash: str
    ga_index: int
    vote_tx_hash: str
    voter_hash: str
    vote: str
    raw_url: str


@dataclass(frozen=True)
class GaExpiration:
    tx_hash: str
    index: int


@dataclass(frozen=True)
class ActiveGovAction:
    tx_hash: str
    index: int
    created_epoch: int
    expiration: int


@dataclass(frozen=True)
class VotingProgress:
    tx_hash: str
    index: int
    cc_voted: int
    cc_total: int
    drep_voted: int
    drep_total: int
    current_epoch: int
    created_epoch: int
    expiration: int

    @property
    def drep_percentage(self) -> float:
        """Calculate percentage of DReps that have voted."""
        if self.drep_total == 0:
            return 0.0
        return (self.drep_voted / self.drep_total) * 100

    @property
    def epoch_progress(self) -> str:
        """Return epoch progress string (e.g., 'Epoch 3 of 5')."""
        total_epochs = self.expiration - self.created_epoch
        current_epoch_num = self.current_epoch - self.created_epoch + 1
        return f"Epoch {current_epoch_num} of {total_epochs}"
