def make_governance_action_link(tx_hash: str, gov_action_index: int) -> str:
    """Build an explorer.cardano.org governance action link.

    Example: https://explorer.cardano.org/governance-action/0b1947...00
    """
    index_hex = format(gov_action_index, "x")
    if len(index_hex) % 2:
        index_hex = "0" + index_hex
    return f"https://explorer.cardano.org/governance-action/{tx_hash}{index_hex}"


def make_adastat_link(tx_hash: str, gov_action_index: int) -> str:
    """Build an AdaStat governance action link.

    Example: https://adastat.net/governances/0b1947...00
    """
    index_hex = format(gov_action_index, "x")
    if len(index_hex) % 2:
        index_hex = "0" + index_hex
    return f"https://adastat.net/governances/{tx_hash}{index_hex}"


def make_gov_tools_link(tx_hash: str, gov_action_index: int) -> str:
    """Build a GovTools governance action link.

    Example: https://gov.tools/governance_actions/0b1947...#0
    """
    return f"https://gov.tools/governance_actions/{tx_hash}#{gov_action_index}"
