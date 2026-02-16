def make_adastat_link(tx_hash: str, gov_action_index: int) -> str:
    """Build an explorer.cardano.org governance action link.

    Example: https://explorer.cardano.org/governance-action/0b1947...00
    """
    index_hex = format(gov_action_index, "x")
    if len(index_hex) % 2:
        index_hex = "0" + index_hex
    return f"https://explorer.cardano.org/governance-action/{tx_hash}{index_hex}"


def make_gov_tools_link(tx_hash: str, gov_action_index: int) -> str:
    """Build a GovTools governance action link.

    Example: https://gov.tools/governance_actions/0b1947...#0
    """
    return f"https://gov.tools/governance_actions/{tx_hash}#{gov_action_index}"


def make_vote_tx_link(tx_hash: str) -> str:
    """Build a CExplorer vote transaction link.

    Example: https://cexplorer.io/tx/<hash>/governance#data
    """
    return f"https://cexplorer.io/tx/{tx_hash}/governance#data"
