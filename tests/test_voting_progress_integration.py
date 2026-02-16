"""Integration test for voting progress feature."""

import os

import pytest

# Set test DB URL before importing bot modules
os.environ.setdefault("DB_SYNC_URL", "postgresql://localhost/test")

from bot.models import ActiveGovAction, VotingProgress
from bot.twitter.formatter import format_voting_progress_tweet


class TestVotingProgressIntegration:
    """Integration tests for voting progress feature."""

    def test_active_gov_action_model(self):
        """Test ActiveGovAction model creation."""
        action = ActiveGovAction(tx_hash="abc123", index=5, created_epoch=495, expiration=505)
        assert action.tx_hash == "abc123"
        assert action.index == 5
        assert action.created_epoch == 495
        assert action.expiration == 505

    def test_voting_progress_model_with_real_data(self):
        """Test VotingProgress model with realistic data."""
        progress = VotingProgress(
            tx_hash="a" * 64,
            index=0,
            cc_voted=5,
            cc_total=7,
            drep_voted=2456,
            drep_total=10000,
            current_epoch=500,
            created_epoch=495,
            expiration=505,
        )
        assert progress.cc_voted == 5
        assert progress.cc_total == 7
        assert progress.drep_voted == 2456
        assert progress.drep_total == 10000
        assert abs(progress.drep_percentage - 24.56) < 0.01
        assert progress.epoch_progress == "Epoch 6 of 10"

    def test_voting_progress_formatter_integration(self):
        """Test that formatter produces valid tweet from VotingProgress."""
        progress = VotingProgress(
            tx_hash="aabbccdd" * 8,  # 64 char hex
            index=0,
            cc_voted=3,
            cc_total=7,
            drep_voted=1234,
            drep_total=5000,
            current_epoch=500,
            created_epoch=495,
            expiration=505,
        )

        tweet = format_voting_progress_tweet(progress)

        # Verify tweet structure (no emoji, no link)
        assert "Voting Progress Update" in tweet
        assert "Epoch 6 of 10" in tweet
        assert "CC Members: 3/7" in tweet
        assert "24.7%" in tweet
        assert "adastat.net" not in tweet  # Link removed
        assert "@IntersectMBO" in tweet
        assert "#Cardano" in tweet
        assert "#Governance" in tweet
        assert len(tweet) <= 280

    def test_voting_progress_with_edge_cases(self):
        """Test voting progress with edge case values."""
        # Zero DReps case
        progress_zero = VotingProgress(
            tx_hash="a" * 64,
            index=0,
            cc_voted=0,
            cc_total=7,
            drep_voted=0,
            drep_total=0,
            current_epoch=500,
            created_epoch=495,
            expiration=505,
        )
        assert progress_zero.drep_percentage == 0.0
        tweet_zero = format_voting_progress_tweet(progress_zero)
        assert "0.0%" in tweet_zero

        # Full participation
        progress_full = VotingProgress(
            tx_hash="b" * 64,
            index=1,
            cc_voted=7,
            cc_total=7,
            drep_voted=5000,
            drep_total=5000,
            current_epoch=500,
            created_epoch=495,
            expiration=505,
        )
        assert progress_full.drep_percentage == 100.0
        tweet_full = format_voting_progress_tweet(progress_full)
        assert "100.0%" in tweet_full
        assert "7/7" in tweet_full

    def test_voting_progress_frozen_dataclass(self):
        """Test that VotingProgress is immutable."""
        progress = VotingProgress(
            tx_hash="a" * 64,
            index=0,
            cc_voted=5,
            cc_total=7,
            drep_voted=1000,
            drep_total=5000,
            current_epoch=500,
            created_epoch=495,
            expiration=505,
        )

        with pytest.raises(Exception):  # FrozenInstanceError
            progress.cc_voted = 10
