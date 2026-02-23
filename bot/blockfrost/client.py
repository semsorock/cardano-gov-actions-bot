"""Blockfrost API client for Cardano blockchain data access using blockfrost-python library."""

from __future__ import annotations

from blockfrost import ApiUrls, BlockFrostApi

from bot.config import config
from bot.logging import get_logger

logger = get_logger("blockfrost.client")


# Singleton instance
_client: BlockFrostApi | None = None


def get_client() -> BlockFrostApi:
    """Get or create the singleton Blockfrost client instance using blockfrost-python library."""
    global _client
    if _client is None:
        # Map network name to API URL
        network_urls = {
            "mainnet": ApiUrls.mainnet.value,
            "preprod": ApiUrls.preprod.value,
            "preview": ApiUrls.preview.value,
        }

        base_url = network_urls.get(config.blockfrost_network, ApiUrls.mainnet.value)

        _client = BlockFrostApi(project_id=config.blockfrost_project_id, base_url=base_url)
        logger.info("Initialized Blockfrost client for network: %s", config.blockfrost_network)

    return _client
