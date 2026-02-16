from bot.models import CcVote, GaExpiration, GovAction, TreasuryDonation, VotingProgress
from bot.twitter.formatter import (
    format_cc_vote_tweet,
    format_ga_expiration_tweet,
    format_gov_action_tweet,
    format_treasury_donations_tweet,
    format_voting_progress_tweet,
)

MAX_TWEET_LENGTH = 280


class TestFormatGovActionTweet:
    def _make_action(self, **overrides):
        defaults = dict(tx_hash="aabb", action_type="ParameterChange", index=0, raw_url="http://example.com")
        defaults.update(overrides)
        return GovAction(**defaults)

    def test_with_metadata(self):
        action = self._make_action()
        metadata = {"body": {"title": "Test Proposal"}}
        tweet = format_gov_action_tweet(action, metadata)
        assert "Governance Action Update" in tweet
        assert "Test Proposal" in tweet
        assert "Parameter Change" in tweet
        assert "adastat.net" in tweet
        assert "#Cardano" in tweet
        assert len(tweet) <= MAX_TWEET_LENGTH

    def test_without_metadata(self):
        action = self._make_action()
        tweet = format_gov_action_tweet(action, None)
        assert "Governance Action Update" in tweet
        assert "Parameter Change" in tweet
        assert "Test Proposal" not in tweet
        assert len(tweet) <= MAX_TWEET_LENGTH

    def test_metadata_without_title(self):
        action = self._make_action()
        metadata = {"body": {}}
        tweet = format_gov_action_tweet(action, metadata)
        assert "Title:" not in tweet


class TestFormatCcVoteTweet:
    def _make_vote(self, **overrides):
        defaults = dict(
            ga_tx_hash="aabb",
            ga_index=0,
            vote_tx_hash="ccdd",
            voter_hash="eeff",
            vote="YES",
            raw_url="http://example.com/rationale.json",
        )
        defaults.update(overrides)
        return CcVote(**defaults)

    def test_with_metadata(self):
        vote = self._make_vote()
        metadata = {"authors": [{"name": "Cardano Foundation"}]}
        tweet = format_cc_vote_tweet(vote, metadata)
        assert "CC Vote Update" in tweet
        assert "Constitutional" in tweet
        assert "Cardano Foundation" in tweet
        assert len(tweet) <= MAX_TWEET_LENGTH

    def test_with_x_handle_prefers_handle_over_metadata(self):
        vote = self._make_vote()
        metadata = {"authors": [{"name": "Cardano Foundation"}]}
        tweet = format_cc_vote_tweet(vote, metadata, voter_x_handle="@ExampleCC")
        assert "Voted by: @ExampleCC" in tweet
        assert "Cardano Foundation" not in tweet

    def test_no_vote(self):
        vote = self._make_vote(vote="NO")
        tweet = format_cc_vote_tweet(vote, None)
        assert "Unconstitutional" in tweet

    def test_abstain(self):
        vote = self._make_vote(vote="ABSTAIN")
        tweet = format_cc_vote_tweet(vote, None)
        assert "Abstain" in tweet

    def test_without_handle_or_metadata_uses_hash_fallback(self):
        vote = self._make_vote(voter_hash="deadbeef00112233")
        tweet = format_cc_vote_tweet(vote, None)
        assert "Voted by: CC member (deadbeef)" in tweet


class TestFormatGaExpirationTweet:
    def test_basic(self):
        exp = GaExpiration(tx_hash="aabb", index=0)
        tweet = format_ga_expiration_tweet(exp)
        assert "Expiry Notice" in tweet
        assert "adastat.net" in tweet
        assert len(tweet) <= MAX_TWEET_LENGTH


class TestFormatTreasuryDonationsTweet:
    def test_single_donation(self):
        donations = [TreasuryDonation(block_no=1, tx_hash="aabb", amount_lovelace=5_000_000)]
        tweet = format_treasury_donations_tweet(donations)
        assert "Treasury Donations Summary" in tweet
        assert "Transactions: 1" in tweet
        assert "5" in tweet
        assert len(tweet) <= MAX_TWEET_LENGTH

    def test_multiple_donations(self):
        donations = [
            TreasuryDonation(block_no=1, tx_hash="aabb", amount_lovelace=1_000_000),
            TreasuryDonation(block_no=2, tx_hash="ccdd", amount_lovelace=2_000_000),
        ]
        tweet = format_treasury_donations_tweet(donations)
        assert "Transactions: 2" in tweet
        assert "3" in tweet  # 1 + 2 = 3 ADA


class TestFormatVotingProgressTweet:
    def test_basic_progress(self):
        progress = VotingProgress(
            tx_hash="aabbccdd",
            index=0,
            cc_voted=3,
            cc_total=7,
            drep_voted=1234,
            drep_total=5000,
        )
        tweet = format_voting_progress_tweet(progress)
        assert "Voting Progress Update" in tweet
        assert "CC Members: 3/7" in tweet
        assert "24.7%" in tweet  # 1234/5000 = 24.68%
        assert "adastat.net" in tweet
        assert len(tweet) <= MAX_TWEET_LENGTH

    def test_zero_dreps(self):
        progress = VotingProgress(
            tx_hash="aabbccdd",
            index=1,
            cc_voted=5,
            cc_total=7,
            drep_voted=0,
            drep_total=0,
        )
        tweet = format_voting_progress_tweet(progress)
        assert "CC Members: 5/7" in tweet
        assert "0.0%" in tweet  # No division by zero error
        assert len(tweet) <= MAX_TWEET_LENGTH

    def test_full_participation(self):
        progress = VotingProgress(
            tx_hash="aabbccdd",
            index=2,
            cc_voted=7,
            cc_total=7,
            drep_voted=1000,
            drep_total=1000,
        )
        tweet = format_voting_progress_tweet(progress)
        assert "CC Members: 7/7" in tweet
        assert "100.0%" in tweet
        assert len(tweet) <= MAX_TWEET_LENGTH
