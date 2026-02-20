"""Blockfrost API client for Cardano blockchain data access."""

from __future__ import annotations

import requests
from tenacity import retry, stop_after_attempt, wait_exponential

from bot.config import config
from bot.logging import get_logger

logger = get_logger("blockfrost.client")


class BlockfrostClient:
    """Wrapper around Blockfrost REST API for Cardano governance data."""

    def __init__(self, project_id: str | None = None, network: str | None = None):
        self.project_id = project_id or config.blockfrost_project_id
        self.network = network or config.blockfrost_network

        # Base URL mapping for different networks
        network_urls = {
            "mainnet": "https://cardano-mainnet.blockfrost.io/api/v0",
            "preprod": "https://cardano-preprod.blockfrost.io/api/v0",
            "preview": "https://cardano-preview.blockfrost.io/api/v0",
        }

        self.base_url = network_urls.get(self.network, network_urls["mainnet"])
        self.headers = {"project_id": self.project_id}

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def _request(self, method: str, endpoint: str, params: dict | None = None) -> dict | list:
        """Make HTTP request to Blockfrost API with retry logic.

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint path (without base URL)
            params: Query parameters

        Returns:
            Parsed JSON response

        Raises:
            requests.HTTPError: On HTTP errors
        """
        url = f"{self.base_url}{endpoint}"
        logger.debug("Blockfrost API request: %s %s params=%s", method, url, params)

        response = requests.request(
            method=method,
            url=url,
            headers=self.headers,
            params=params,
            timeout=30,
        )
        response.raise_for_status()
        return response.json()

    def get_block(self, block_hash_or_number: str | int) -> dict:
        """Get block information by hash or number."""
        return self._request("GET", f"/blocks/{block_hash_or_number}")

    def get_block_transactions(self, block_hash_or_number: str | int, page: int = 1, count: int = 100) -> list[dict]:
        """Get all transactions in a block."""
        return self._request("GET", f"/blocks/{block_hash_or_number}/txs", params={"page": page, "count": count})

    def get_transaction(self, tx_hash: str) -> dict:
        """Get transaction details."""
        return self._request("GET", f"/txs/{tx_hash}")

    def get_transaction_utxos(self, tx_hash: str) -> dict:
        """Get transaction UTXOs (inputs and outputs)."""
        return self._request("GET", f"/txs/{tx_hash}/utxos")

    def get_transaction_metadata(self, tx_hash: str) -> list[dict]:
        """Get transaction metadata."""
        return self._request("GET", f"/txs/{tx_hash}/metadata")

    def get_epoch(self, epoch_number: int) -> dict:
        """Get epoch information."""
        return self._request("GET", f"/epochs/{epoch_number}")

    def get_latest_block(self) -> dict:
        """Get the latest block."""
        return self._request("GET", "/blocks/latest")

    # Governance endpoints - using Blockfrost's dedicated governance API

    def list_governance_proposals(self, page: int = 1, count: int = 100, order: str = "asc") -> list[dict]:
        """List all governance proposals.

        Returns:
            List of proposals with tx_hash, cert_index, and other proposal data
        """
        return self._request("GET", "/governance/proposals", params={"page": page, "count": count, "order": order})

    def get_proposal_by_tx(self, tx_hash: str, cert_index: int) -> dict:
        """Get specific governance proposal by transaction hash and certificate index.

        Args:
            tx_hash: Transaction hash containing the proposal
            cert_index: Index of the certificate within the transaction

        Returns:
            Proposal details including type, status, anchor URL, etc.
        """
        return self._request("GET", f"/governance/proposals/{tx_hash}/{cert_index}")

    def get_proposal_by_gov_action_id(self, gov_action_id: str) -> dict:
        """Get specific governance proposal by GovActionID (CIP-0129 bech32 format).

        Args:
            gov_action_id: Bech32-encoded governance action identifier

        Returns:
            Proposal details
        """
        return self._request("GET", f"/governance/proposals/{gov_action_id}")

    def get_proposal_metadata(self, tx_hash: str, cert_index: int) -> dict:
        """Get metadata for a specific proposal.

        Args:
            tx_hash: Transaction hash containing the proposal
            cert_index: Index of the certificate within the transaction

        Returns:
            Proposal metadata including URL, hash, and body
        """
        return self._request("GET", f"/governance/proposals/{tx_hash}/{cert_index}/metadata")

    def get_proposal_votes(
        self, tx_hash: str, cert_index: int, page: int = 1, count: int = 100, order: str = "asc"
    ) -> list[dict]:
        """Get votes for a governance proposal.

        Args:
            tx_hash: Transaction hash containing the proposal
            cert_index: Index of the certificate within the transaction
            page: Page number for pagination
            count: Number of results per page
            order: Sort order (asc or desc)

        Returns:
            List of votes with voter, vote decision, and transaction info
        """
        return self._request(
            "GET",
            f"/governance/proposals/{tx_hash}/{cert_index}/votes",
            params={"page": page, "count": count, "order": order},
        )

    def get_drep(self, drep_id: str) -> dict:
        """Get information about a specific DRep.

        Args:
            drep_id: Bech32 or hexadecimal DRep ID

        Returns:
            DRep information
        """
        return self._request("GET", f"/governance/dreps/{drep_id}")

    def get_drep_votes(self, drep_id: str, page: int = 1, count: int = 100, order: str = "asc") -> list[dict]:
        """Get voting history for a specific DRep.

        Args:
            drep_id: Bech32 or hexadecimal DRep ID
            page: Page number for pagination
            count: Number of results per page
            order: Sort order (asc or desc)

        Returns:
            List of votes by this DRep
        """
        return self._request(
            "GET", f"/governance/dreps/{drep_id}/votes", params={"page": page, "count": count, "order": order}
        )


# Singleton instance
_client: BlockfrostClient | None = None


def get_client() -> BlockfrostClient:
    """Get or create the singleton Blockfrost client instance."""
    global _client
    if _client is None:
        _client = BlockfrostClient()
    return _client
