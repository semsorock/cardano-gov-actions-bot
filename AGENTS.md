# Cardano Governance Actions Bot - AI Agent Instructions

## Project Purpose

This is a **Cardano blockchain governance monitoring bot** that watches for new governance actions and Constitutional Committee (CC) votes, then automatically posts summaries to Twitter/X. It's deployed as a Google Cloud Function that responds to webhook events from Blockfrost.

## Architecture Overview

### Core Data Flow

1. **Blockfrost webhook** → Cloud Function endpoint (`/block` or `/epoch`)

2. **Query Cardano DB-Sync** (PostgreSQL) for governance data

3. **Fetch metadata** from IPFS URLs (governance action details, vote rationales)

4. **Post tweet** via Twitter API with formatted summaries and external links

### Key Components

- `main.py`: Main cloud function handler with webhook processors (569 lines)

- `ipfs.py`: Standalone IPFS gateway fetcher (not integrated into main bot)

- `docs/db_sync_schema.sql`: Full Cardano DB-Sync schema reference

- `drafts/samples/actions/` & `drafts/samples/votes/`: Sample JSONLD metadata files for testing

## Database Integration

### DB-Sync Schema (PostgreSQL)

The bot queries a **Cardano DB-Sync instance** - a full blockchain database. Key tables:

- `gov_action_proposal`: Governance actions with type, index, voting anchor, expiration

- `voting_procedure`: Individual votes from CC members, DReps, SPOs

- `voting_anchor`: IPFS/web URLs containing governance metadata

- `tx` / `block`: Transaction and block data including `treasury_donation` field

- `committee_hash`: Constitutional Committee member identifiers

### Critical Queries

```python
# QUERY_GA: Get governance actions by block number
# QUERY_VOTE: Get CC votes by block number  
# QUERY_EXPIRATIONS: Get actions expiring next epoch
# QUERY_TREASURY_DONATION_TOTAL_PER_EPOCH: Sum donations per epoch
```

**Important**: Governance actions are identified by `tx_hash + index`, forming a compound key.

## External Dependencies & Patterns

### IPFS URL Handling

- Governance actions/votes reference metadata via `voting_anchor.url`

- URLs may be `ipfs://` URIs → convert to `https://ipfs.io/ipfs/` gateway

- Use `_sanitise_url()` before fetching

- Metadata follows CIP-100/CIP-108/CIP-136 JSON-LD standards

### Metadata Structure Examples

**Governance Action** (CIP-108):

```json
{
  "body": {
    "title": "...",
    "abstract": "...",
    "motivation": "...",
    "rationale": "..."
  },
  "authors": [{"name": "..."}]
}
```

**CC Vote** (CIP-136):

```json
{
  "body": {
    "summary": "...",
    "rationaleStatement": "..."
  },
  "authors": [{"name": "..."}]
}
```

### External Links

The bot generates links to governance explorers:

- **GovTools**: `_make_gov_tools_link(tx_hash, index)` (commented out in current code)

- **AdaStat**: `_make_adastat_link(tx_hash, index)` - ACTIVE

- **CExplorer**: `_make_vote_tx_link(tx_hash)` for vote transactions

## Development Patterns

### Error Handling & Resilience

- Uses `tenacity` library with `@retry` decorator (3 attempts, exponential backoff)

- Applied to `get_url_content()` for IPFS gateway requests (30s timeout)

- Database connection pooling via `psycopg2.pool.SimpleConnectionPool`

  - Pattern: `conn = DB_POOL.getconn()` → use → `DB_POOL.putconn(conn)` in finally block

  - **Critical**: Always return connections to pool to avoid exhaustion

### Environment Variables (Required)

```bash
API_KEY, API_SECRET_KEY           # Twitter OAuth 1.0a
ACCESS_TOKEN, ACCESS_TOKEN_SECRET # Twitter access credentials  
DB_SYNC_URL                       # PostgreSQL connection string (e.g., postgresql://user:pass@host:5432/dbname)
```

### Code Style & Patterns

- Max line length: 120 chars (configured in `pyproject.toml`: `[tool.flake8]`)

- Use `encode(hash, 'hex')` for database hash fields (e.g., `encode(t.hash, 'hex')`)

- Lovelace → ADA conversion: divide by `Decimal("1000000")` - always use `Decimal` type for precision

- CamelCase → Spaced: `camel_case_to_spaced()` transforms DB values like "ParameterChange" → "Parameter Change"

- Tweet construction: Build `tweet_text_lines` array, then `"\n".join()` - maintains consistent formatting

## Workflow & Commands

### Deployment Target

Google Cloud Run (`functions-framework` library, containerized)

- Continuously deployed from GitHub via Cloud Run source-based deployment
- Docker image built automatically by Cloud Build on push to `main`
- Entry point: `hello_http(request)`

- Routes: `/block` and `/epoch`

- Returns encoded response string (webhook acknowledgment)

- Webhook triggered by Blockfrost when new blocks/epochs occur

### Local Development

```bash
# Setup virtual environment (recommended)
python -m venv .venv
source .venv/bin/activate  # macOS/Linux

# Install dependencies
pip install -r requirements.txt

# Run locally (functions framework)
functions-framework --target=hello_http --debug
# Access at http://localhost:8080/block or http://localhost:8080/epoch
```

### Testing Workflow

1. **SQL Query Development**: Use `drafts/draft_SELECT.sql` to test queries against DB-Sync

2. **Metadata Testing**: Reference sample files in `drafts/samples/actions/` and `drafts/samples/votes/`

3. **Webhook Simulation**: Sample payloads are in code comments (see `process_block()` line ~360, `process_epoch()` line ~430)

4. **Local Testing**: Set environment variables, then POST webhook JSON to local endpoint

## Important Quirks & Edge Cases

### Skipped Governance Actions

Hard-coded skip logic exists for specific transaction:

```python
if tx_hash == "8ad3d454f..." and gov_action_index < 17:
    return  # Skip early test actions
```

### Vote Classification

Vote strings map to human-readable text:

```python
VOTES_MAPPING = {
    "YES": "Constitutional",
    "NO": "Unconstitutional", 
    "ABSTAIN": "Abstain"
}
```

### Commented-Out Features

- **GA expiration alerts**: `_process_ga_expirations()` disabled in `process_epoch()`

- **CC member Twitter handles**: `CC_MEMBERS_TO_X_HANDLE` mapping exists but unused

- **Author attribution**: Comment parsing logic exists but not included in tweets

## When Modifying Code

### Adding New Governance Event Types

1. Add query to SQL constant section

2. Create `_get_*` database function with connection pooling

3. Create `_process_*` formatter function

4. Add call in `process_block()` or `process_epoch()`

### Changing Tweet Format

- Modify `tweet_text_lines` array construction in processor functions

- Keep under 280 characters (Twitter limit not enforced in code)

- Use emoji consistently: 🚨 (alerts), 📢 (titles), 🔗 (links), 💸 (treasury)

### Database Query Changes

- Test queries in `draft_SELECT.sql` first

- Schema reference in `docs/db_sync_schema.sql`

- Always join through `tx` and `block` tables for block/epoch filtering

## Dependencies Summary

```text
functions-framework==3.*  # Google Cloud Functions runtime
tweepy==4.15.0           # Twitter API v2 client
psycopg2-binary==2.9.10  # PostgreSQL adapter (binary dist)
requests==2.32.3         # HTTP client for IPFS
tenacity==9.0.0          # Retry/backoff decorator
```

## Related Documentation

- [CIP-100](https://github.com/cardano-foundation/CIPs/blob/master/CIP-0100/README.md): Governance metadata standard

- [CIP-108](https://github.com/cardano-foundation/CIPs/blob/master/CIP-0108/README.md): Governance action metadata

- [CIP-136](https://github.com/cardano-foundation/CIPs/blob/master/CIP-0136/README.md): CC vote rationale metadata

- [Cardano DB-Sync](https://github.com/IntersectMBO/cardano-db-sync): Database schema source
