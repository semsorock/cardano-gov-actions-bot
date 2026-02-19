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

    def get_transaction_metadata(self, tx_hash: str) -> list[dict]:
        """Get transaction metadata."""
        return self._request("GET", f"/txs/{tx_hash}/metadata")

    def get_epoch(self, epoch_number: int) -> dict:
        """Get epoch information."""
        return self._request("GET", f"/epochs/{epoch_number}")

    def get_latest_block(self) -> dict:
        """Get the latest block."""
        return self._request("GET", "/blocks/latest")

    # Governance endpoints (note: these may need adjustment based on actual Blockfrost API availability)

    def list_governance_proposals(self, page: int = 1, count: int = 100, order: str = "desc") -> list[dict]:
        """List all governance proposals.

        Note: This endpoint might not be available in all Blockfrost versions.
        If not available, we'll need to parse transactions for governance actions.
        """
        try:
            return self._request("GET", "/governance/proposals", params={"page": page, "count": count, "order": order})
        except requests.HTTPError as e:
            if e.response.status_code == 404:
                logger.warning("Governance proposals endpoint not available, falling back to transaction parsing")
                return []
            raise

    def get_governance_proposal(self, proposal_id: str) -> dict:
        """Get specific governance proposal details."""
        return self._request("GET", f"/governance/proposals/{proposal_id}")

    def get_proposal_votes(self, proposal_id: str, page: int = 1, count: int = 100) -> list[dict]:
        """Get votes for a governance proposal."""
        return self._request("GET", f"/governance/proposals/{proposal_id}/votes", params={"page": page, "count": count})


# Singleton instance
_client: BlockfrostClient | None = None


def get_client() -> BlockfrostClient:
    """Get or create the singleton Blockfrost client instance."""
    global _client
    if _client is None:
        _client = BlockfrostClient()
    return _client
