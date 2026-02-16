# Cardano Governance Actions Bot - AI Agent Instructions

## Project Purpose

This is a **Cardano blockchain governance monitoring bot** that watches for new governance actions and Constitutional Committee (CC) votes, posts summaries to Twitter/X, and archives governance rationale files to GitHub. It's deployed as a Google Cloud Run service (FastAPI + uvicorn) triggered by Blockfrost block webhooks (`POST /`).

## Architecture Overview

### Core Data Flow

1. **Blockfrost webhook** → Cloud Run `/` endpoint
2. **Query Cardano DB-Sync** (PostgreSQL) for governance data
3. **Fetch metadata** from IPFS URLs (governance action details, vote rationales)
4. **Validate metadata** against CIP-0108/CIP-0136 standards (warnings only)
5. **Post tweets** via X API (XDK) with formatted summaries
   - **Gov Actions**: posted as new tweets
   - **CC Votes**: posted as quote-tweets when action tweet ID is known, else normal tweets
6. **Persist runtime state** to Firestore (`tweet_id`, checkpoints)
7. **Archive rationale** JSON to GitHub (direct commit to `main`)

### Project Structure

```
├── main.py                      # Entry point shim — re-exports FastAPI `app` from bot.main
├── bot/
│   ├── __init__.py
│   ├── cc_profiles.py           # CC voter hash -> X handle lookup loader
│   ├── config.py                # Centralised config (.env via dotenv), validation + feature flags
│   ├── logging.py               # Logging setup (setup_logging, get_logger)
│   ├── models.py                # Dataclasses: GovAction, CcVote, GaExpiration, TreasuryDonation
│   ├── links.py                 # External link builders (AdaStat, GovTools, CExplorer)
│   ├── main.py                  # FastAPI app + async webhook handler
│   ├── webhook_auth.py          # Blockfrost HMAC-SHA256 signature verification
│   ├── state_store.py           # Firestore-backed runtime state helpers
│   ├── rationale_archiver.py    # Archive rationales to GitHub via direct commits (PyGithub)
│   ├── rationale_validator.py   # CIP-0108/CIP-0136 metadata validation
│   ├── db/
│   │   ├── __init__.py
│   │   ├── queries.py           # SQL query constants
│   │   └── repository.py        # Async data access layer (typed query functions)
│   ├── metadata/
│   │   ├── __init__.py
│   │   └── fetcher.py           # IPFS URL sanitisation & JSON metadata fetching
│   └── twitter/
│       ├── __init__.py
│       ├── client.py            # XDK wrapper with TWEET_POSTING_ENABLED gate
│       ├── formatter.py         # Tweet text builders for all event types
│       └── templates.py         # Editable tweet text templates
├── scripts/
│   ├── backfill_rationales.py   # One-off: fetch all historical rationales from DB-Sync
│   └── backfill_tweet_ids.py    # One-off: backfill tweet_id.txt from historical posts
├── data/
│   └── cc_profiles.yaml         # CC profile mappings (voter hash -> X handle)
├── rationales/                  # Archived rationale JSON files
│   └── <tx_hash>_<index>/
│       ├── action.json           # Gov action rationale (CIP-0108)
│       └── cc_votes/
│           └── <voter_hash>.json # CC vote rationale (CIP-0136)
├── tests/                       # Pytest test suite (currently 78 tests)
├── .github/workflows/ci.yml     # CI pipeline (ruff + pytest)
├── .env.example                 # Template for required env vars
├── .dockerignore                # Docker build context exclusions
├── pyproject.toml               # Project config, dependencies, ruff & pytest settings
├── uv.lock                      # Locked dependency versions
├── Dockerfile                   # Container image (uses uv, non-root user)
├── docs/                        # Reference docs (DB-Sync schema, CIP-0108, CIP-0136)
└── drafts/                      # Development drafts and sample data (not deployed)
```

### Key Components

- `bot/config.py`: All env vars loaded into a frozen `Config` dataclass via `python-dotenv` (`.env` overrides system vars). Includes feature flags.

- `bot/models.py`: Typed dataclasses for all domain objects. Replaces raw tuple indexing.

- `bot/db/repository.py`: Async data access functions returning typed model instances. Uses a shared `psycopg.AsyncConnection` (lazy init) with an `asyncio.Lock` to serialise queries. On connection errors, closes and resets the connection so the next call reconnects.

- `bot/metadata/fetcher.py`: `fetch_metadata()` with retry (tenacity) and `sanitise_url()` for IPFS.

- `bot/twitter/client.py`: `post_tweet()` / `post_quote_tweet()` / `post_reply_tweet()` via XDK — logs content and only posts when `TWEET_POSTING_ENABLED=true`. All post functions return the tweet ID (extracted via `_extract_post_id()`) or `None`.

- `bot/twitter/formatter.py`: Pure functions that build tweet text strings for each event type.

- `bot/twitter/templates.py`: Centralised tweet copy templates used by formatters.

- `bot/cc_profiles.py`: Loads `data/cc_profiles.yaml` and maps CC voter hashes to X handles.

- `bot/links.py`: URL builders for AdaStat, GovTools, CExplorer.

- `bot/main.py`: FastAPI `app` instance with async `POST /` webhook handler. All processing functions (`_process_gov_actions`, `_process_cc_votes`, etc.) are async.

- `bot/state_store.py`: Firestore-backed persistence for gov action tweet IDs, CC vote archive state, and block checkpoints.

- `bot/rationale_archiver.py`: Archives rationale JSON to GitHub via PyGithub (create/update files directly on `main`). Skips gracefully if `GITHUB_TOKEN` not set.

- `bot/rationale_validator.py`: Non-blocking CIP-0108/CIP-0136 validation. Returns warning lists — tweets always sent regardless.

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
- `QUERY_BLOCK_EPOCH`: Get epoch number for a block by hash
- `QUERY_ALL_GOV_ACTIONS`: All gov actions (backfill)
- `QUERY_ALL_CC_VOTES`: All CC votes (backfill)

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

- Async PostgreSQL via `psycopg` (v3) with a shared `AsyncConnection` (lazy init, `autocommit=True`)

  - Managed in `bot/db/repository.py` — all queries go through async `_query()` helper, serialised by an `asyncio.Lock`

  - On connection errors, `_query()` closes the broken connection and resets it to `None` so the next call reconnects automatically

### Environment Variables

Loaded from `.env` file (overrides system env vars) via `python-dotenv`.

```bash
# Required
DB_SYNC_URL                        # PostgreSQL connection string
BLOCKFROST_WEBHOOK_AUTH_TOKEN      # Blockfrost webhook HMAC secret

# Twitter (required if TWEET_POSTING_ENABLED=true)
API_KEY, API_SECRET_KEY            # Twitter OAuth 1.0a
ACCESS_TOKEN, ACCESS_TOKEN_SECRET  # Twitter access credentials
TWEET_POSTING_ENABLED              # "true" to enable tweet posting (default: false)

# GitHub (optional for rationale archiving)
GITHUB_TOKEN                       # Personal access token
GITHUB_REPO                        # e.g. "semsorock/cardano-gov-actions-bot"

# Firestore runtime state (optional override, uses ADC project by default)
FIRESTORE_PROJECT_ID               # optional GCP project override
FIRESTORE_DATABASE                 # Firestore DB id (default: (default))
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

Google Cloud Run (FastAPI + uvicorn, containerized)

- Continuously deployed from GitHub via Cloud Run source-based deployment
- Docker image built automatically by Cloud Build on push to `main`
- Entry point: `uvicorn bot.main:app` (root `main.py` re-exports `app`)
- `POST /` handles Blockfrost block events (governance actions, CC votes, epoch donation checks)
- Epoch transitions are detected by comparing current vs previous block epoch
- Returns JSON responses with appropriate HTTP status codes

### Local Development

```bash
# Install uv (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Sync dependencies (creates .venv automatically)
uv sync

# Run locally
uv run uvicorn bot.main:app --reload --port 8080
# Access at http://localhost:8080/
# Endpoint: POST / (Blockfrost)

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

4. **Local Testing**: Set environment variables, then POST webhook JSON to `/` (Blockfrost)

## Important Quirks & Edge Cases

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
- **Rationale archiving**: Controlled by `GITHUB_TOKEN` + `GITHUB_REPO` (skipped if not set)
- **Webhook signature verification**: Skipped if `BLOCKFROST_WEBHOOK_AUTH_TOKEN` not set

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
fastapi>=0.115,<1           # Async web framework
uvicorn[standard]>=0.34,<1  # ASGI server
xdk>=0.8.1                  # X API SDK (OAuth 1.0a + posts client)
psycopg[binary]>=3,<4       # Async PostgreSQL adapter (psycopg v3)
requests>=2.32,<3           # HTTP client for IPFS
tenacity>=9,<10             # Retry/backoff decorator
python-dotenv>=1.2.1        # .env file loading
pygithub>=2,<3              # GitHub API for rationale archiving
google-cloud-firestore>=2.20,<3  # Firestore state store client

# Dev
pytest>=8                   # Test runner
pytest-asyncio>=0.25        # Async test support (asyncio_mode = "auto")
httpx>=0.28                 # Async HTTP client (FastAPI TestClient)
ruff>=0.9                   # Formatter + linter
```

## Related Documentation

- [CIP-100](https://github.com/cardano-foundation/CIPs/blob/master/CIP-0100/README.md): Governance metadata standard

- [CIP-108](https://github.com/cardano-foundation/CIPs/blob/master/CIP-0108/README.md): Governance action metadata

- [CIP-136](https://github.com/cardano-foundation/CIPs/blob/master/CIP-0136/README.md): CC vote rationale metadata

- [Cardano DB-Sync](https://github.com/IntersectMBO/cardano-db-sync): Database schema source
