# Cardano Governance Actions Bot - AI Agent Instructions

## Project Purpose

This is a **Cardano blockchain governance monitoring bot** that watches for new governance actions and Constitutional Committee (CC) votes, then automatically posts summaries to Twitter/X. It's deployed as a Google Cloud Function that responds to webhook events from Blockfrost.

## Architecture Overview

### Core Data Flow

1. **Blockfrost webhook** → Cloud Run endpoint (`/block` or `/epoch`)

2. **Query Cardano DB-Sync** (PostgreSQL) for governance data

3. **Fetch metadata** from IPFS URLs (governance action details, vote rationales)

4. **Post tweet** via Twitter API with formatted summaries and external links

### Project Structure

```
├── main.py                      # Thin shim — re-exports handle_webhook from bot.main
├── bot/
│   ├── __init__.py
│   ├── config.py                # Centralised config from env vars + feature flags
│   ├── logging.py               # Logging setup (setup_logging, get_logger)
│   ├── models.py                # Dataclasses: GovAction, CcVote, GaExpiration, TreasuryDonation
│   ├── links.py                 # External link builders (AdaStat, GovTools, CExplorer)
│   ├── main.py                  # Webhook router & orchestration (handle_webhook entry point)
│   ├── db/
│   │   ├── __init__.py
│   │   ├── queries.py           # SQL query constants
│   │   └── repository.py        # Data access layer (typed query functions)
│   ├── metadata/
│   │   ├── __init__.py
│   │   └── fetcher.py           # IPFS URL sanitisation & JSON metadata fetching
│   └── twitter/
│       ├── __init__.py
│       ├── client.py            # Tweepy wrapper with TWEET_POSTING_ENABLED gate
│       └── formatter.py         # Tweet text builders for all event types
├── tests/                       # Pytest test suite
│   ├── test_models.py
│   ├── test_links.py
│   ├── test_formatter.py
│   └── test_fetcher.py
├── pyproject.toml               # Project config, dependencies, ruff & pytest settings
├── uv.lock                      # Locked dependency versions
├── Dockerfile                   # Container image definition (uses uv)
├── docs/                        # Reference documentation (DB-Sync schema)
└── drafts/                      # Development drafts and sample data (not deployed)
```

### Key Components

- `bot/config.py`: All env vars loaded into a frozen `Config` dataclass. Includes `TWEET_POSTING_ENABLED` feature flag.

- `bot/models.py`: Typed dataclasses for all domain objects. Replaces raw tuple indexing.

- `bot/db/repository.py`: Data access functions returning typed model instances. Lazy connection pool init.

- `bot/metadata/fetcher.py`: `fetch_metadata()` with retry (tenacity) and `sanitise_url()` for IPFS.

- `bot/twitter/client.py`: `post_tweet()` — always logs the tweet, only posts when `TWEET_POSTING_ENABLED=true`.

- `bot/twitter/formatter.py`: Pure functions that build tweet text strings for each event type.

- `bot/links.py`: URL builders for AdaStat, GovTools, CExplorer.

- `bot/main.py`: Webhook router (`handle_webhook`) and orchestration (`process_block`, `process_epoch`).

- `bot/logging.py`: `setup_logging()` + `get_logger()` — stdlib logging, structured for Cloud Run.

## Database Integration

### DB-Sync Schema (PostgreSQL)

The bot queries a **Cardano DB-Sync instance** - a full blockchain database. Key tables:

- `gov_action_proposal`: Governance actions with type, index, voting anchor, expiration

- `voting_procedure`: Individual votes from CC members, DReps, SPOs

- `voting_anchor`: IPFS/web URLs containing governance metadata

- `tx` / `block`: Transaction and block data including `treasury_donation` field

- `committee_hash`: Constitutional Committee member identifiers

### Queries

All SQL is in `bot/db/queries.py`:

- `QUERY_GOV_ACTIONS`: Get governance actions by block number
- `QUERY_CC_VOTES`: Get CC votes by block number
- `QUERY_GA_EXPIRATIONS`: Get actions expiring next epoch
- `QUERY_TREASURY_DONATIONS`: Sum donations per epoch

**Important**: Governance actions are identified by `tx_hash + index`, forming a compound key.

## External Dependencies & Patterns

### IPFS URL Handling

- Governance actions/votes reference metadata via `voting_anchor.url`

- URLs may be `ipfs://` URIs → convert to `https://ipfs.io/ipfs/` gateway

- Use `sanitise_url()` from `bot/metadata/fetcher.py` before fetching

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

The bot generates links to governance explorers via `bot/links.py`:

- **AdaStat**: `make_adastat_link(tx_hash, index)` - ACTIVE
- **GovTools**: `make_gov_tools_link(tx_hash, index)`
- **CExplorer**: `make_vote_tx_link(tx_hash)` for vote transactions

## Development Patterns

### Error Handling & Resilience

- Uses `tenacity` library with `@retry` decorator (3 attempts, exponential backoff)

- Applied to `fetch_metadata()` in `bot/metadata/fetcher.py` (30s timeout)

- Database connection pooling via `psycopg2.pool.SimpleConnectionPool` (lazy init)

  - Managed in `bot/db/repository.py` — all queries go through `_query()` helper

### Environment Variables (Required)

```bash
API_KEY, API_SECRET_KEY           # Twitter OAuth 1.0a
ACCESS_TOKEN, ACCESS_TOKEN_SECRET # Twitter access credentials
DB_SYNC_URL                       # PostgreSQL connection string
TWEET_POSTING_ENABLED             # "true" to enable tweet posting (default: false)
```

### Code Style & Patterns

- **Formatter & linter**: ruff (configured in `pyproject.toml`)
- Line length: 120 chars
- Lint rules: `E`, `F`, `W`, `I` (isort), `UP` (pyupgrade)
- All domain objects are frozen dataclasses in `bot/models.py`
- Tweet formatting is pure (functions return strings, no side effects)
- `post_tweet()` is the single point for Twitter output — gated by config flag
- Uses stdlib `logging` everywhere (no `print()` calls)

## Workflow & Commands

### Deployment Target

Google Cloud Run (`functions-framework` library, containerized)

- Continuously deployed from GitHub via Cloud Run source-based deployment
- Docker image built automatically by Cloud Build on push to `main`
- Entry point: `handle_webhook(request)` (exposed via root `main.py` shim)

- Routes: `/block` and `/epoch`

- Returns encoded response string (webhook acknowledgment)

- Webhook triggered by Blockfrost when new blocks/epochs occur

### Local Development

```bash
# Install uv (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Sync dependencies (creates .venv automatically)
uv sync

# Run locally
uv run functions-framework --target=handle_webhook --debug
# Access at http://localhost:8080/block or http://localhost:8080/epoch

# Run tests
uv run pytest -v

# Format & lint
uv run ruff format .
uv run ruff check --fix .
```

### Testing Workflow

1. **SQL Query Development**: Use `drafts/draft_SELECT.sql` to test queries against DB-Sync

2. **Metadata Testing**: Reference sample files in `drafts/samples/actions/` and `drafts/samples/votes/`

3. **Webhook Simulation**: Sample payloads are in code comments in `bot/main.py`

4. **Local Testing**: Set environment variables, then POST webhook JSON to local endpoint

## Important Quirks & Edge Cases

### Skipped Governance Actions

Hard-coded skip logic exists in `bot/main.py` for specific transaction:

```python
_SKIP_TX_HASH = "8ad3d454f..."
_SKIP_INDEX_BELOW = 17
```

### Vote Classification

Vote strings map to human-readable text in `bot/twitter/formatter.py`:

```python
VOTES_MAPPING = {
    "YES": "Constitutional",
    "NO": "Unconstitutional",
    "ABSTAIN": "Abstain"
}
```

### Feature Flags

- **Tweet posting**: Controlled by `TWEET_POSTING_ENABLED` env var (default: off)
- **GA expiration alerts**: Disabled in `process_epoch()` — uncomment when ready

## When Modifying Code

### Adding New Governance Event Types

1. Add query constant to `bot/db/queries.py`

2. Add data model to `bot/models.py`

3. Add repository function to `bot/db/repository.py`

4. Add formatter function to `bot/twitter/formatter.py`

5. Add orchestration in `bot/main.py` (`process_block()` or `process_epoch()`)

### Changing Tweet Format

- Modify formatter functions in `bot/twitter/formatter.py`

- Keep under 280 characters (Twitter limit not enforced in code)

- Use emoji consistently: 🚨 (alerts), 📢 (titles), 🔗 (links), 💸 (treasury)

### Database Query Changes

- Test queries in `draft_SELECT.sql` first

- Schema reference in `docs/db_sync_schema.sql`

- Always join through `tx` and `block` tables for block/epoch filtering

## Dependencies Summary

Managed via `uv` (see `pyproject.toml`). Lockfile: `uv.lock`.

```text
# Production
functions-framework>=3,<4   # Google Cloud Functions runtime
tweepy>=4.15,<5             # Twitter API v2 client
psycopg2-binary>=2.9,<3    # PostgreSQL adapter (binary dist)
requests>=2.32,<3           # HTTP client for IPFS
tenacity>=9,<10             # Retry/backoff decorator

# Dev
pytest>=8                   # Test runner
ruff>=0.9                   # Formatter + linter
```

## Related Documentation

- [CIP-100](https://github.com/cardano-foundation/CIPs/blob/master/CIP-0100/README.md): Governance metadata standard

- [CIP-108](https://github.com/cardano-foundation/CIPs/blob/master/CIP-0108/README.md): Governance action metadata

- [CIP-136](https://github.com/cardano-foundation/CIPs/blob/master/CIP-0136/README.md): CC vote rationale metadata

- [Cardano DB-Sync](https://github.com/IntersectMBO/cardano-db-sync): Database schema source
