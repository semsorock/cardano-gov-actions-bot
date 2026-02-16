from bot.links import make_adastat_link, make_gov_tools_link, make_vote_tx_link


class TestMakeAdastatLink:
    def test_index_zero(self):
        link = make_adastat_link("aabbcc", 0)
        assert link == "https://explorer.cardano.org/governance-action/aabbcc00"

    def test_index_single_digit(self):
        link = make_adastat_link("aabbcc", 5)
        assert link == "https://explorer.cardano.org/governance-action/aabbcc05"

    def test_index_two_digits(self):
        link = make_adastat_link("aabbcc", 16)
        assert link == "https://explorer.cardano.org/governance-action/aabbcc10"

    def test_index_large(self):
        link = make_adastat_link("aabbcc", 255)
        assert link == "https://explorer.cardano.org/governance-action/aabbccff"


class TestMakeGovToolsLink:
    def test_basic(self):
        link = make_gov_tools_link("aabbcc", 0)
        assert link == "https://gov.tools/governance_actions/aabbcc#0"

    def test_with_index(self):
        link = make_gov_tools_link("aabbcc", 5)
        assert link == "https://gov.tools/governance_actions/aabbcc#5"


class TestMakeVoteTxLink:
    def test_basic(self):
        link = make_vote_tx_link("aabbcc")
        assert link == "https://cexplorer.io/tx/aabbcc/governance#data"
