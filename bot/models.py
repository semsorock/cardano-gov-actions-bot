import re
from dataclasses import dataclass
from decimal import Decimal


def camel_case_to_spaced(value: str | None) -> str | None:
    """Convert CamelCase to 'Camel Case'. Returns None for non-string input."""
    if not isinstance(value, str):
        return None
    if not value:
        return ""
    return re.sub(r"(?<!^)(?=[A-Z])", " ", value)


@dataclass(frozen=True)
class GovAction:
    tx_hash: str
    action_type: str
    index: int
    raw_url: str

    @property
    def action_type_display(self) -> str | None:
        return camel_case_to_spaced(self.action_type)


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
class TreasuryDonation:
    block_no: int
    tx_hash: str
    amount_lovelace: int

    @property
    def amount_ada(self) -> Decimal:
        return Decimal(self.amount_lovelace) / Decimal("1000000")
