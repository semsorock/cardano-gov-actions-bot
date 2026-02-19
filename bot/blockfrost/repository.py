"""Blockfrost-based data repository for governance actions and votes.

This module provides async data access functions that replicate the interface
of the DB-Sync repository, but using Blockfrost API instead of PostgreSQL queries.
"""

from __future__ import annotations

import asyncio
from typing import Any

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


def _make_gov_action_id(tx_hash: str, index: int) -> str:
    """Create governance action ID in the format used by Blockfrost API."""
    return f"{tx_hash}#{index}"


async def get_gov_actions(block_no: int) -> list[GovAction]:
    """Get governance actions submitted in a specific block.
    
    Strategy:
    1. Get all transactions in the block
    2. For each transaction, check if it contains governance actions
    3. Parse governance action data from transaction details
    
    Note: This is an approximation since Blockfrost doesn't provide direct
    "get governance actions by block number" endpoint. We fetch recent proposals
    and filter by block number.
    """
    async with _lock:
        client = get_client()
        
        try:
            # Get block details to find its hash
            block_data = await _run_in_executor(client.get_block, block_no)
            block_hash = block_data.get("hash")
            
            # Get all transactions in this block
            txs = await _run_in_executor(client.get_block_transactions, block_hash)
            
            gov_actions = []
            
            # Check each transaction for governance actions
            # Note: We need to call Blockfrost's governance proposals endpoint
            # and filter for this block, as there's no direct tx->proposal mapping
            
            # Alternative approach: Get recent proposals and filter by block
            proposals = await _run_in_executor(
                client.list_governance_proposals,
                page=1,
                count=100,
                order="desc"
            )
            
            # Filter proposals that match this block number
            for proposal in proposals:
                # Blockfrost proposal structure may vary, adapt as needed
                proposal_block = proposal.get("block_height") or proposal.get("block_no")
                if proposal_block == block_no:
                    gov_actions.append(
                        GovAction(
                            tx_hash=proposal.get("tx_hash", ""),
                            action_type=proposal.get("type", ""),
                            index=proposal.get("index", 0),
                            raw_url=proposal.get("anchor", {}).get("url", "") if isinstance(proposal.get("anchor"), dict) else "",
                        )
                    )
            
            logger.debug("Found %d governance actions in block %s", len(gov_actions), block_no)
            return gov_actions
            
        except Exception as e:
            logger.error("Error fetching governance actions for block %s: %s", block_no, e)
            return []


async def get_cc_votes(block_no: int) -> list[CcVote]:
    """Get Constitutional Committee votes submitted in a specific block.
    
    Similar to get_gov_actions, we need to:
    1. Get proposals
    2. For each proposal, get votes
    3. Filter votes by block number and role (CC only)
    """
    async with _lock:
        client = get_client()
        
        try:
            # Get block hash
            block_data = await _run_in_executor(client.get_block, block_no)
            block_hash = block_data.get("hash")
            
            # Get transactions in block
            txs = await _run_in_executor(client.get_block_transactions, block_hash)
            
            cc_votes = []
            
            # Get recent proposals to check for votes
            proposals = await _run_in_executor(
                client.list_governance_proposals,
                page=1,
                count=100,
                order="desc"
            )
            
            # For each proposal, get votes and filter
            for proposal in proposals:
                proposal_id = _make_gov_action_id(
                    proposal.get("tx_hash", ""),
                    proposal.get("index", 0)
                )
                
                try:
                    votes = await _run_in_executor(
                        client.get_proposal_votes,
                        proposal_id,
                        page=1,
                        count=100
                    )
                    
                    for vote in votes:
                        # Filter for CC votes in this block
                        vote_block = vote.get("block_height") or vote.get("block_no")
                        voter_role = vote.get("voter", {}).get("role") if isinstance(vote.get("voter"), dict) else None
                        
                        if vote_block == block_no and voter_role == "constitutional_committee":
                            cc_votes.append(
                                CcVote(
                                    ga_tx_hash=proposal.get("tx_hash", ""),
                                    ga_index=proposal.get("index", 0),
                                    vote_tx_hash=vote.get("tx_hash", ""),
                                    voter_hash=vote.get("voter", {}).get("id", "") if isinstance(vote.get("voter"), dict) else "",
                                    vote=vote.get("vote", ""),
                                    raw_url=vote.get("anchor", {}).get("url", "") if isinstance(vote.get("anchor"), dict) else "",
                                )
                            )
                except Exception as e:
                    logger.debug("Error fetching votes for proposal %s: %s", proposal_id, e)
                    continue
            
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
            proposals = await _run_in_executor(
                client.list_governance_proposals,
                page=1,
                count=100,
                order="desc"
            )
            
            expirations = []
            
            for proposal in proposals:
                expiration = proposal.get("expiration_epoch")
                status = proposal.get("status", "").lower()
                
                # Only include proposals expiring at this epoch that aren't already enacted/ratified/dropped
                if (expiration == epoch_no and 
                    status not in ["ratified", "enacted", "dropped", "expired"]):
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
                proposals = await _run_in_executor(
                    client.list_governance_proposals,
                    page=page,
                    count=100,
                    order="asc"
                )
                
                if not proposals:
                    break
                
                for proposal in proposals:
                    all_actions.append(
                        GovAction(
                            tx_hash=proposal.get("tx_hash", ""),
                            action_type=proposal.get("type", ""),
                            index=proposal.get("index", 0),
                            raw_url=proposal.get("anchor", {}).get("url", "") if isinstance(proposal.get("anchor"), dict) else "",
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
                proposal_id = _make_gov_action_id(action.tx_hash, action.index)
                
                try:
                    votes = await _run_in_executor(
                        client.get_proposal_votes,
                        proposal_id,
                        page=1,
                        count=100
                    )
                    
                    for vote in votes:
                        voter_role = vote.get("voter", {}).get("role") if isinstance(vote.get("voter"), dict) else None
                        
                        if voter_role == "constitutional_committee":
                            all_votes.append(
                                CcVote(
                                    ga_tx_hash=action.tx_hash,
                                    ga_index=action.index,
                                    vote_tx_hash=vote.get("tx_hash", ""),
                                    voter_hash=vote.get("voter", {}).get("id", "") if isinstance(vote.get("voter"), dict) else "",
                                    vote=vote.get("vote", ""),
                                    raw_url=vote.get("anchor", {}).get("url", "") if isinstance(vote.get("anchor"), dict) else "",
                                )
                            )
                except Exception as e:
                    logger.debug("Error fetching votes for proposal %s: %s", proposal_id, e)
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
            proposals = await _run_in_executor(
                client.list_governance_proposals,
                page=1,
                count=100,
                order="desc"
            )
            
            active_actions = []
            
            for proposal in proposals:
                created_epoch = proposal.get("created_epoch")
                expiration = proposal.get("expiration_epoch")
                status = proposal.get("status", "").lower()
                
                # Include if created before this epoch, not yet ratified/enacted/dropped/expired,
                # and expiration is at or after this epoch
                if (created_epoch is not None and created_epoch < epoch_no and
                    status not in ["ratified", "enacted", "dropped", "expired"] and
                    (expiration is None or expiration >= epoch_no)):
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
            proposal_id = _make_gov_action_id(tx_hash, index)
            
            # Get votes for this proposal
            votes = await _run_in_executor(
                client.get_proposal_votes,
                proposal_id,
                page=1,
                count=100
            )
            
            # Count votes by role
            cc_voted = 0
            drep_voted = 0
            
            for vote in votes:
                voter_role = vote.get("voter", {}).get("role") if isinstance(vote.get("voter"), dict) else None
                
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
