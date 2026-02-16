from decimal import Decimal

from bot.models import GaExpiration, GovAction, TreasuryDonation, VotingProgress, camel_case_to_spaced

# ---------------------------------------------------------------------------
# camel_case_to_spaced
# ---------------------------------------------------------------------------


class TestCamelCaseToSpaced:
    def test_basic(self):
        assert camel_case_to_spaced("ParameterChange") == "Parameter Change"

    def test_multiple_words(self):
        assert camel_case_to_spaced("HardForkInitiation") == "Hard Fork Initiation"

    def test_single_word(self):
        assert camel_case_to_spaced("Treasury") == "Treasury"

    def test_empty_string(self):
        assert camel_case_to_spaced("") == ""

    def test_none(self):
        assert camel_case_to_spaced(None) is None

    def test_non_string(self):
        assert camel_case_to_spaced(123) is None


# ---------------------------------------------------------------------------
# GovAction
# ---------------------------------------------------------------------------


class TestGovAction:
    def test_action_type_display(self):
        action = GovAction(tx_hash="abc", action_type="ParameterChange", index=0, raw_url="http://example.com")
        assert action.action_type_display == "Parameter Change"

    def test_action_type_display_single_word(self):
        action = GovAction(tx_hash="abc", action_type="InfoAction", index=0, raw_url="http://example.com")
        assert action.action_type_display == "Info Action"


# ---------------------------------------------------------------------------
# TreasuryDonation
# ---------------------------------------------------------------------------


class TestTreasuryDonation:
    def test_amount_ada_basic(self):
        donation = TreasuryDonation(block_no=1, tx_hash="abc", amount_lovelace=1_000_000)
        assert donation.amount_ada == Decimal("1")

    def test_amount_ada_fractional(self):
        donation = TreasuryDonation(block_no=1, tx_hash="abc", amount_lovelace=1_500_000)
        assert donation.amount_ada == Decimal("1.5")

    def test_amount_ada_small(self):
        donation = TreasuryDonation(block_no=1, tx_hash="abc", amount_lovelace=1)
        assert donation.amount_ada == Decimal("0.000001")

    def test_amount_ada_zero(self):
        donation = TreasuryDonation(block_no=1, tx_hash="abc", amount_lovelace=0)
        assert donation.amount_ada == Decimal("0")


# ---------------------------------------------------------------------------
# GaExpiration (basic sanity)
# ---------------------------------------------------------------------------


class TestGaExpiration:
    def test_creation(self):
        exp = GaExpiration(tx_hash="deadbeef", index=3)
        assert exp.tx_hash == "deadbeef"
        assert exp.index == 3


# ---------------------------------------------------------------------------
# VotingProgress
# ---------------------------------------------------------------------------


class TestVotingProgress:
    def test_drep_percentage_basic(self):
        progress = VotingProgress(
            tx_hash="abc",
            index=0,
            cc_voted=3,
            cc_total=7,
            drep_voted=1234,
            drep_total=5000,
            current_epoch=500,
            created_epoch=495,
            expiration=505,
        )
        # 1234 / 5000 = 0.2468 = 24.68%
        assert abs(progress.drep_percentage - 24.68) < 0.01

    def test_drep_percentage_zero_total(self):
        progress = VotingProgress(
            tx_hash="abc",
            index=0,
            cc_voted=0,
            cc_total=7,
            drep_voted=0,
            drep_total=0,
            current_epoch=500,
            created_epoch=495,
            expiration=505,
        )
        assert progress.drep_percentage == 0.0

    def test_drep_percentage_full_participation(self):
        progress = VotingProgress(
            tx_hash="abc",
            index=0,
            cc_voted=7,
            cc_total=7,
            drep_voted=1000,
            drep_total=1000,
            current_epoch=500,
            created_epoch=495,
            expiration=505,
        )
        assert progress.drep_percentage == 100.0

    def test_drep_percentage_no_votes(self):
        progress = VotingProgress(
            tx_hash="abc",
            index=0,
            cc_voted=0,
            cc_total=7,
            drep_voted=0,
            drep_total=5000,
            current_epoch=500,
            created_epoch=495,
            expiration=505,
        )
        assert progress.drep_percentage == 0.0

    def test_epoch_progress_with_expiration(self):
        progress = VotingProgress(
            tx_hash="abc",
            index=0,
            cc_voted=3,
            cc_total=7,
            drep_voted=1234,
            drep_total=5000,
            current_epoch=500,
            created_epoch=495,
            expiration=505,
        )
        # Current epoch 500, created 495, expiration 505
        # Total epochs = 505 - 495 = 10
        # Current epoch num = 500 - 495 + 1 = 6
        assert progress.epoch_progress == "Epoch 6 of 10"

    def test_epoch_progress_without_expiration(self):
        progress = VotingProgress(
            tx_hash="abc",
            index=0,
            cc_voted=3,
            cc_total=7,
            drep_voted=1234,
            drep_total=5000,
            current_epoch=500,
            created_epoch=495,
            expiration=None,
        )
        # Current epoch 500, created 495, no expiration
        # Current epoch num = 500 - 495 + 1 = 6
        assert progress.epoch_progress == "Epoch 6"
