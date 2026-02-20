"""Blockfrost-based data repository for governance actions and votes.

This module provides async data access functions that replicate the interface
of the DB-Sync repository, but using Blockfrost API instead of PostgreSQL queries.
"""

from __future__ import annotations

import asyncio
from typing import Any

import requests

from bot.blockfrost.client import get_client
from bot.logging import get_logger
from bot.models import ActiveGovAction, CcVote, GaExpiration, GovAction, VotingProgress

logger = get_logger("blockfrost.repository")

# Cache for storing block->epoch mapping
_epoch_cache: dict[str, int] = {}
_lock = asyncio.Lock()


async def _run_in_executor(func, *args) -> Any:
    """Run a blocking function in an executor to avoid blocking the event loop."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, func, *args)


async def get_gov_actions(block_no: int) -> list[GovAction]:
    """Get governance actions submitted in a specific block.

    Strategy:
    1. Get all transactions in the block
    2. Query the governance proposals endpoint for each transaction
    3. Parse governance action data from proposals
    """
    async with _lock:
        client = get_client()

        try:
            # Get block details
            block_data = await _run_in_executor(client.get_block, block_no)
            block_hash = block_data.get("hash")

            # Get all transactions in this block
            txs = await _run_in_executor(client.get_block_transactions, block_hash, page=1, count=100)

            gov_actions = []

            # For each transaction, check if it contains governance proposals
            for tx in txs:
                tx_hash = tx.get("hash") if isinstance(tx, dict) else tx

                # Try to find proposals in this transaction
                # Blockfrost uses tx_hash + cert_index for proposals
                # We need to try different cert_index values since we don't know in advance
                for cert_index in range(10):  # Try up to 10 certificates per transaction
                    try:
                        proposal = await _run_in_executor(client.get_proposal_by_tx, tx_hash, cert_index)

                        # Get proposal metadata for the anchor URL
                        try:
                            metadata = await _run_in_executor(client.get_proposal_metadata, tx_hash, cert_index)
                            raw_url = metadata.get("url", "")
                        except Exception:
                            raw_url = ""

                        gov_actions.append(
                            GovAction(
                                tx_hash=tx_hash,
                                action_type=proposal.get("type", ""),
                                index=cert_index,
                                raw_url=raw_url,
                            )
                        )
                    except requests.HTTPError as e:
                        if e.response.status_code == 404:
                            # No more proposals in this transaction
                            break
                        # Other errors should be logged but not break the loop
                        logger.debug("Error fetching proposal %s#%s: %s", tx_hash, cert_index, e)
                        break
                    except Exception as e:
                        logger.debug("Error processing proposal %s#%s: %s", tx_hash, cert_index, e)
                        break

            logger.debug("Found %d governance actions in block %s", len(gov_actions), block_no)
            return gov_actions

        except Exception as e:
            logger.error("Error fetching governance actions for block %s: %s", block_no, e)
            return []


async def get_cc_votes(block_no: int) -> list[CcVote]:
    """Get Constitutional Committee votes submitted in a specific block.

    Strategy:
    1. Get all transactions in the block
    2. For each transaction that contains a governance proposal, get its votes
    3. Filter for CC votes only
    """
    async with _lock:
        client = get_client()

        try:
            # Get block hash
            block_data = await _run_in_executor(client.get_block, block_no)
            block_hash = block_data.get("hash")

            # Get transactions in block
            txs = await _run_in_executor(client.get_block_transactions, block_hash, page=1, count=100)

            cc_votes = []

            # For each transaction, check if it contains governance proposals and get votes
            for tx in txs:
                tx_hash = tx.get("hash") if isinstance(tx, dict) else tx

                # Try to find proposals in this transaction
                for cert_index in range(10):  # Try up to 10 certificates
                    try:
                        # Check if this transaction/cert has a proposal (will raise 404 if not)
                        await _run_in_executor(client.get_proposal_by_tx, tx_hash, cert_index)

                        # Get votes for this proposal
                        votes = await _run_in_executor(
                            client.get_proposal_votes, tx_hash, cert_index, page=1, count=100
                        )

                        for vote in votes:
                            # Filter for Constitutional Committee votes
                            voter_role = vote.get("voter_role")
                            if voter_role == "constitutional_committee":
                                # Get the vote transaction hash and voter ID
                                vote_tx_hash = vote.get("tx_hash", "")
                                voter = vote.get("voter", "")

                                # Get metadata URL if available
                                try:
                                    vote_metadata = vote.get("metadata", {})
                                    raw_url = vote_metadata.get("url", "") if isinstance(vote_metadata, dict) else ""
                                except Exception:
                                    raw_url = ""

                                cc_votes.append(
                                    CcVote(
                                        ga_tx_hash=tx_hash,
                                        ga_index=cert_index,
                                        vote_tx_hash=vote_tx_hash,
                                        voter_hash=voter,
                                        vote=vote.get("vote", ""),
                                        raw_url=raw_url,
                                    )
                                )

                    except requests.HTTPError as e:
                        if e.response.status_code == 404:
                            # No more proposals in this transaction
                            break
                        logger.debug("Error fetching proposal votes %s#%s: %s", tx_hash, cert_index, e)
                        break
                    except Exception as e:
                        logger.debug("Error processing votes %s#%s: %s", tx_hash, cert_index, e)
                        break

            logger.debug("Found %d CC votes in block %s", len(cc_votes), block_no)
            return cc_votes

        except Exception as e:
            logger.error("Error fetching CC votes for block %s: %s", block_no, e)
            return []


async def get_ga_expirations(epoch_no: int) -> list[GaExpiration]:
    """Get governance actions expiring at the specified epoch.

    Note: This requires iterating through all active proposals and checking
    their expiration epochs.
    """
    async with _lock:
        client = get_client()

        try:
            proposals = await _run_in_executor(client.list_governance_proposals, page=1, count=100, order="desc")

            expirations = []

            for proposal in proposals:
                expiration = proposal.get("expiration_epoch")
                status = proposal.get("status", "").lower()

                # Only include proposals expiring at this epoch that aren't already enacted/ratified/dropped
                if expiration == epoch_no and status not in ["ratified", "enacted", "dropped", "expired"]:
                    expirations.append(
                        GaExpiration(
                            tx_hash=proposal.get("tx_hash", ""),
                            index=proposal.get("index", 0),
                        )
                    )

            logger.debug("Found %d expiring actions for epoch %s", len(expirations), epoch_no)
            return expirations

        except Exception as e:
            logger.error("Error fetching expirations for epoch %s: %s", epoch_no, e)
            return []


async def get_block_epoch(block_hash: str) -> int | None:
    """Return the epoch number for a block identified by its hex hash."""
    async with _lock:
        # Check cache first
        if block_hash in _epoch_cache:
            return _epoch_cache[block_hash]

        client = get_client()

        try:
            block_data = await _run_in_executor(client.get_block, block_hash)
            epoch = block_data.get("epoch")

            if epoch is not None:
                _epoch_cache[block_hash] = epoch

            return epoch

        except Exception as e:
            logger.error("Error fetching epoch for block %s: %s", block_hash, e)
            return None


async def get_all_gov_actions() -> list[GovAction]:
    """Return all governance actions (for backfill).

    Note: This will paginate through all proposals in Blockfrost.
    """
    async with _lock:
        client = get_client()

        all_actions = []
        page = 1

        try:
            while True:
                proposals = await _run_in_executor(client.list_governance_proposals, page=page, count=100, order="asc")

                if not proposals:
                    break

                for proposal in proposals:
                    all_actions.append(
                        GovAction(
                            tx_hash=proposal.get("tx_hash", ""),
                            action_type=proposal.get("type", ""),
                            index=proposal.get("index", 0),
                            raw_url=proposal.get("anchor", {}).get("url", "")
                            if isinstance(proposal.get("anchor"), dict)
                            else "",
                        )
                    )

                page += 1

                # Safety limit to prevent infinite loops
                if page > 1000:
                    logger.warning("Reached page limit (1000) while fetching all governance actions")
                    break

            logger.info("Fetched %d total governance actions", len(all_actions))
            return all_actions

        except Exception as e:
            logger.error("Error fetching all governance actions: %s", e)
            return all_actions  # Return what we have so far


async def get_all_cc_votes() -> list[CcVote]:
    """Return all CC member votes (for backfill)."""
    async with _lock:
        client = get_client()

        all_votes = []

        try:
            # Get all proposals first
            proposals = await get_all_gov_actions()

            # For each proposal, get votes
            for action in proposals:
                try:
                    votes = await _run_in_executor(
                        client.get_proposal_votes, action.tx_hash, action.index, page=1, count=100
                    )

                    for vote in votes:
                        voter_role = vote.get("voter_role")

                        if voter_role == "constitutional_committee":
                            # Get metadata URL if available
                            try:
                                vote_metadata = vote.get("metadata", {})
                                raw_url = vote_metadata.get("url", "") if isinstance(vote_metadata, dict) else ""
                            except Exception:
                                raw_url = ""

                            all_votes.append(
                                CcVote(
                                    ga_tx_hash=action.tx_hash,
                                    ga_index=action.index,
                                    vote_tx_hash=vote.get("tx_hash", ""),
                                    voter_hash=vote.get("voter", ""),
                                    vote=vote.get("vote", ""),
                                    raw_url=raw_url,
                                )
                            )
                except Exception as e:
                    logger.debug("Error fetching votes for proposal %s#%s: %s", action.tx_hash, action.index, e)
                    continue

            logger.info("Fetched %d total CC votes", len(all_votes))
            return all_votes

        except Exception as e:
            logger.error("Error fetching all CC votes: %s", e)
            return all_votes


async def get_active_gov_actions(epoch_no: int) -> list[ActiveGovAction]:
    """Return all active governance actions for the given epoch."""
    async with _lock:
        client = get_client()

        try:
            proposals = await _run_in_executor(client.list_governance_proposals, page=1, count=100, order="desc")

            active_actions = []

            for proposal in proposals:
                created_epoch = proposal.get("created_epoch")
                expiration = proposal.get("expiration_epoch")
                status = proposal.get("status", "").lower()

                # Include if created before this epoch, not yet ratified/enacted/dropped/expired,
                # and expiration is at or after this epoch
                if (
                    created_epoch is not None
                    and created_epoch < epoch_no
                    and status not in ["ratified", "enacted", "dropped", "expired"]
                    and (expiration is None or expiration >= epoch_no)
                ):
                    active_actions.append(
                        ActiveGovAction(
                            tx_hash=proposal.get("tx_hash", ""),
                            index=proposal.get("index", 0),
                            created_epoch=created_epoch,
                            expiration=expiration or 0,
                        )
                    )

            logger.debug("Found %d active actions for epoch %s", len(active_actions), epoch_no)
            return active_actions

        except Exception as e:
            logger.error("Error fetching active actions for epoch %s: %s", epoch_no, e)
            return []


async def get_voting_stats(
    tx_hash: str, index: int, epoch_no: int, created_epoch: int, expiration: int
) -> VotingProgress | None:
    """Return voting statistics for a specific governance action.

    Note: This is a simplified implementation. Full stats would require:
    - Active CC member count from chain state
    - DRep distribution data
    - Vote counts from proposal votes
    """
    async with _lock:
        client = get_client()

        try:
            # Get votes for this proposal using proper endpoint format
            votes = await _run_in_executor(client.get_proposal_votes, tx_hash, index, page=1, count=100)

            # Count votes by role
            cc_voted = 0
            drep_voted = 0

            for vote in votes:
                voter_role = vote.get("voter_role")

                if voter_role == "constitutional_committee":
                    cc_voted += 1
                elif voter_role == "drep":
                    drep_voted += 1

            # Note: Getting total CC members and DReps requires additional Blockfrost calls
            # For now, we'll use placeholder values or make additional API calls
            # TODO: Implement proper CC member and DRep count queries

            return VotingProgress(
                tx_hash=tx_hash,
                index=index,
                cc_voted=cc_voted,
                cc_total=7,  # Placeholder - would need to query active CC members
                drep_voted=drep_voted,
                drep_total=100,  # Placeholder - would need to query active DReps
                current_epoch=epoch_no,
                created_epoch=created_epoch,
                expiration=expiration,
            )

        except Exception as e:
            logger.error("Error fetching voting stats for %s#%s: %s", tx_hash, index, e)
            return None
