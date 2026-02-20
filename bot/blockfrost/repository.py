"""Blockfrost-based data repository for governance actions and votes.

This module provides async data access functions using Blockfrost's dedicated
governance API endpoints. The webhook serves as a trigger only - we poll the
/governance/proposals endpoint and track state in Firestore.
"""

from __future__ import annotations

import asyncio
from typing import Any

import requests

from bot.blockfrost.client import get_client
from bot.logging import get_logger
from bot.models import ActiveGovAction, CcVote, GaExpiration, GovAction, VotingProgress
from bot.state_store import (
    get_last_processed_proposal,
    get_last_processed_vote,
    set_last_processed_proposal,
    set_last_processed_vote,
)

logger = get_logger("blockfrost.repository")

# Cache for storing block->epoch mapping
_epoch_cache: dict[str, int] = {}
_lock = asyncio.Lock()


async def _run_in_executor(func, *args) -> Any:
    """Run a blocking function in an executor to avoid blocking the event loop."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, func, *args)


async def get_gov_actions(block_no: int) -> list[GovAction]:
    """Get new governance actions since last check.

    The block_no parameter is now used for logging only - we poll the proposals
    API and track state in Firestore instead of iterating through block transactions.

    Strategy:
    1. Get last processed proposal from Firestore
    2. Query /governance/proposals endpoint in ascending order
    3. Process new proposals since last checkpoint
    4. Update Firestore checkpoint
    """
    async with _lock:
        client = get_client()
        gov_actions = []

        try:
            # Get last processed proposal from Firestore
            last_checkpoint = get_last_processed_proposal()
            last_tx_hash = last_checkpoint.get("tx_hash") if last_checkpoint else None
            last_cert_index = last_checkpoint.get("cert_index") if last_checkpoint else None

            # Fetch proposals in ascending order (oldest first)
            page = 1
            found_checkpoint = last_tx_hash is None  # If no checkpoint, process all
            latest_proposal = None

            while page <= 10:  # Limit to 10 pages per webhook call
                proposals = await _run_in_executor(client.list_governance_proposals, page=page, count=100, order="asc")

                if not proposals:
                    break

                for proposal in proposals:
                    tx_hash = proposal.get("tx_hash", "")
                    cert_index = proposal.get("cert_index", 0)

                    # Skip until we find our checkpoint
                    if not found_checkpoint:
                        if tx_hash == last_tx_hash and cert_index == last_cert_index:
                            found_checkpoint = True
                        continue

                    # Process this new proposal
                    try:
                        # Get proposal metadata for the anchor URL
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

                    # Track the latest proposal for checkpoint update
                    latest_proposal = (tx_hash, cert_index)

                page += 1

            # Update checkpoint to latest processed proposal
            if latest_proposal:
                set_last_processed_proposal(latest_proposal[0], latest_proposal[1])

            logger.info("Found %d new governance actions (triggered by block %s)", len(gov_actions), block_no)
            return gov_actions

        except Exception as e:
            logger.error("Error fetching governance actions: %s", e)
            return []


async def get_cc_votes(block_no: int) -> list[CcVote]:
    """Get new Constitutional Committee votes since last check.

    The block_no parameter is now used for logging only - we track votes via
    the proposals API and Firestore state instead of iterating through blocks.

    Strategy:
    1. Get recent proposals (up to 100)
    2. For each proposal, get votes
    3. Track which votes we've already processed in Firestore
    4. Return only new CC votes
    """
    async with _lock:
        client = get_client()
        cc_votes = []

        try:
            # Get last processed vote transaction from Firestore
            last_vote_checkpoint = get_last_processed_vote()
            last_vote_tx = last_vote_checkpoint.get("tx_hash") if last_vote_checkpoint else None

            # Get recent proposals (descending order - newest first)
            proposals = await _run_in_executor(client.list_governance_proposals, page=1, count=100, order="desc")

            latest_vote_tx = None
            found_checkpoint = last_vote_tx is None

            for proposal in proposals:
                tx_hash = proposal.get("tx_hash", "")
                cert_index = proposal.get("cert_index", 0)

                try:
                    # Get votes for this proposal
                    votes = await _run_in_executor(client.get_proposal_votes, tx_hash, cert_index, page=1, count=100)

                    for vote in votes:
                        vote_tx_hash = vote.get("tx_hash", "")

                        # Skip until we find our checkpoint
                        if not found_checkpoint:
                            if vote_tx_hash == last_vote_tx:
                                found_checkpoint = True
                            continue

                        # Track latest vote for checkpoint
                        if latest_vote_tx is None:
                            latest_vote_tx = vote_tx_hash

                        # Filter for Constitutional Committee votes
                        voter_role = vote.get("voter_role")
                        if voter_role == "constitutional_committee":
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
                                    voter_hash=vote.get("voter", ""),
                                    vote=vote.get("vote", ""),
                                    raw_url=raw_url,
                                )
                            )

                except requests.HTTPError as e:
                    if e.response.status_code != 404:
                        logger.debug("Error fetching votes for proposal %s#%s: %s", tx_hash, cert_index, e)
                except Exception as e:
                    logger.debug("Error processing votes %s#%s: %s", tx_hash, cert_index, e)

            # Update checkpoint to latest processed vote
            if latest_vote_tx:
                set_last_processed_vote(latest_vote_tx)

            logger.info("Found %d new CC votes (triggered by block %s)", len(cc_votes), block_no)
            return cc_votes

        except Exception as e:
            logger.error("Error fetching CC votes: %s", e)
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
