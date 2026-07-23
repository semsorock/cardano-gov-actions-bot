# Cardano Governance Actions Bot - AI Agent Instructions

## Project Purpose

This is a **Cardano blockchain governance monitoring bot** that watches for new governance actions and Constitutional Committee (CC) votes, and posts summaries to Twitter/X. It's deployed as a Google Cloud Run service (FastAPI + uvicorn) triggered by Blockfrost block webhooks (`POST /`).

**Blockfrost is the sole Cardano data provider.** There is no DB-Sync / PostgreSQL / SSH dependency (removed in the issue #34 migration).

## Architecture Overview

### Core Data Flow

1. **Blockfrost webhook** → Cloud Run `/` endpoint (one webhook per new block)
2. **Scan Blockfrost feeds** — governance proposals + committee votes — processing items newer than the persisted watermarks (primary discovery)
3. **Read block CBOR** (`/blocks/{hash}/txs/cbor`) to accumulate treasury donations (transaction-body key `22`)
4. **Fetch metadata** — from Blockfrost's validated `json_metadata`, falling back to fetching the IPFS/HTTP anchor ourselves
5. **Validate metadata** against CIP-0108/CIP-0136 standards (warnings only)
6. **Post tweets** via X API (XDK) with formatted summaries
   - **Gov Actions**: posted as new tweets (with a `Current thresholds:` line when available)
   - **CC Votes**: posted as quote-tweets when the action tweet ID is known, else normal tweets
7. **Persist runtime state** to Firestore (tweet IDs, feed watermarks, committee snapshots, treasury accumulation, checkpoints)

Feed watermarks bound how far each scan pages back; per-item idempotency keys make duplicate and out-of-order webhook deliveries safe.

### Project Structure

```
├── main.py                      # Entry point shim — re-exports FastAPI `app` from bot.main
├── bot/
│   ├── __init__.py
│   ├── cc_profiles.py           # CC voter (cold) hash -> X handle lookup loader
│   ├── config.py                # Centralised config (.env via dotenv), validation + feature flags
│   ├── logging.py               # Logging setup (setup_logging, get_logger)
│   ├── models.py                # Dataclasses: GovAction, CcVote, TreasuryDonation
│   ├── links.py                 # External link builders (AdaStat, GovTools, CExplorer)
│   ├── main.py                  # FastAPI app + async webhook handler / orchestration
│   ├── webhook_auth.py          # Blockfrost HMAC-SHA256 signature verification
│   ├── state_store.py           # Firestore-backed runtime state helpers
│   ├── rationale_validator.py   # CIP-0108/CIP-0136 metadata validation
│   ├── thresholds.py            # Ratification-threshold engine + param-group classification
│   ├── blockfrost/
│   │   ├── __init__.py
│   │   ├── client.py            # Async httpx client + bounded retry/backoff
│   │   ├── feeds.py             # Feed pagination + watermark scanning
│   │   ├── mapping.py           # governance_type/vote mapping -> domain models
│   │   ├── committee.py         # /governance/committee snapshot parsing
│   │   └── cbor.py              # Treasury-donation extraction from tx CBOR
│   ├── metadata/
│   │   ├── __init__.py
│   │   └── fetcher.py           # IPFS URL sanitisation & JSON metadata fetching
│   └── twitter/
│       ├── __init__.py
│       ├── client.py            # XDK wrapper with TWEET_POSTING_ENABLED gate
│       ├── formatter.py         # Tweet text builders for all event types
│       └── templates.py         # Editable tweet text templates
├── scripts/
│   └── backfill_rationales.py   # One-off: archive historical rationales from Blockfrost
├── data/
│   └── cc_profiles.yaml         # CC profile mappings (cold voter hash -> X handle)
├── rationales/                  # Archived rationale JSON files
│   └── <tx_hash>_<index>/
│       ├── action.json           # Gov action rationale (CIP-0108)
│       └── cc_votes/
│           └── <voter_hash>.json # CC vote rationale (CIP-0136)
├── tests/                       # Pytest test suite
├── .github/workflows/ci.yml     # CI pipeline (ruff + pytest)
├── .env.example                 # Template for required env vars
├── pyproject.toml               # Project config, dependencies, ruff & pytest settings
├── uv.lock                      # Locked dependency versions
├── Dockerfile                   # Container image (uses uv, non-root user)
└── docs/                        # Reference docs (CIP-0108, CIP-0136)
```

### Key Components

- `bot/config.py`: All env vars loaded into a frozen `Config` dataclass. `BLOCKFROST_PROJECT_ID` is required; Twitter creds required only when `TWEET_POSTING_ENABLED=true`.

- `bot/models.py`: Typed frozen dataclasses — `GovAction`, `CcVote`, `TreasuryDonation`.

- `bot/blockfrost/client.py`: `BlockfrostClient` — async `httpx` wrapper. Every request carries the `project_id` header and retries transient failures (timeouts, `429`, `5xx`) with bounded exponential backoff, honouring `Retry-After`. `404` raises `BlockfrostNotFound`. A module-level singleton (`get_client`/`set_client`/`close_client`) is owned by the FastAPI lifespan.

- `bot/blockfrost/feeds.py`: `collect_new_items()` — scans a desc-ordered feed against a watermark. Steady state is one request (tip == watermark). On first run it adopts the tip as the watermark and processes nothing (history is the backfill script's job). The returned watermark is only persisted by the caller *after* processing succeeds.

- `bot/blockfrost/committee.py`: `parse_committee_snapshot()` → `CommitteeSnapshot` (quorum, dissolution, active-member count, hot→cold credential map).

- `bot/blockfrost/cbor.py`: `extract_block_donations()` — decodes each transaction's CBOR and reads body key `22` (treasury donation, Lovelace).

- `bot/blockfrost/mapping.py`: translates Blockfrost `governance_type`/`vote` strings to the CIP-1694 PascalCase names used elsewhere, and builds `GovAction`/`CcVote` records. Stable feed identities via `proposal_key()` / `committee_vote_key()`.

- `bot/thresholds.py`: `compute_thresholds()` maps an action type + `ThresholdContext` (epoch params + committee state) to the bodies that vote. `classify_parameters()` classifies a proposal's changed `parameters` into voting groups. No fabricated fallbacks. `min_fee_ref_script_cost_per_byte` is Economic + Security.

- `bot/metadata/fetcher.py`: `fetch_metadata()` with retry (tenacity) and `sanitise_url()` for IPFS.

- `bot/twitter/client.py`: `post_tweet()` / `post_quote_tweet()` / `post_reply_tweet()` — logs content and only posts when `TWEET_POSTING_ENABLED=true`. Returns the tweet ID or `None`.

- `bot/twitter/formatter.py` & `templates.py`: pure tweet-text builders + editable templates.

- `bot/state_store.py`: Firestore persistence — action tweet IDs + idempotency (`gov_action_state`), CC vote idempotency (`cc_vote_state`), feed watermarks (`feed_watermarks`), committee snapshots per epoch (`committee_snapshots`), treasury accumulation (`treasury_epoch_donations`), checkpoints. Every helper degrades to a no-op when Firestore is unavailable.

- `bot/main.py`: FastAPI `app` with async `POST /` webhook handler. Primary discovery (`_process_governance`) scans both feeds; a failure returns `500` so Blockfrost retries. Secondary work (`_process_treasury`, epoch summaries) never fails the webhook.

## Blockfrost Integration

### Endpoints used

- `GET /governance/proposals?order=desc` — proposals feed (`{id, tx_hash, cert_index, governance_type}`)
- `GET /governance/proposals/{tx}/{cert}` / `/metadata` / `/parameters` — proposal detail, anchor + `json_metadata`, proposed params
- `GET /governance/committee` — committee snapshot (quorum, `is_dissolved`, members, hot/cold)
- `GET /governance/committee/votes?order=desc` — committee votes feed
- `GET /epochs/{epoch}/parameters` — epoch-specific DRep/SPO thresholds + `committee_min_size`
- `GET /blocks/{hash}/txs/cbor` — block transactions' CBOR (treasury donation = body key `22`)
- `GET /txs/{hash}` + `GET /blocks/{hash_or_number}` — resolve a proposal's inclusion epoch (backfill only)

**Important**: Governance actions are identified by `tx_hash + cert_index`, a compound key.

### Feeds, watermarks and idempotency

- Feeds are scanned newest-first; items newer than the watermark are processed oldest-first.
- Watermarks (`feed_watermarks`) bound the scan; correctness comes from per-item domain idempotency (`gov_action_state.archived_action`, `cc_vote_state.archived_vote`).
- A watermark is advanced only after the batch processes successfully; on failure the webhook returns `500` and Blockfrost retries.

## External Dependencies & Patterns

### Metadata Handling

- Prefer Blockfrost's already-validated `json_metadata`; fall back to fetching the anchor URL over IPFS/HTTP via `sanitise_url()` + `fetch_metadata()`.
- `ipfs://` URIs are rewritten to the `https://ipfs.io/ipfs/` gateway.
- Metadata follows CIP-100/CIP-108/CIP-136 JSON-LD standards.

**Governance Action** (CIP-108): `{ "body": { "title", "abstract", "motivation", "rationale" }, "authors": [{"name"}] }`

**CC Vote** (CIP-136): `{ "body": { "summary", "rationaleStatement" }, "authors": [{"name"}] }`

## Development Patterns

### Reliability

- `bot/blockfrost/client.py` retries timeouts / `429` / `5xx` with bounded exponential backoff + `Retry-After`.
- Primary feed-discovery failure → `500` (Blockfrost retries; watermarks unadvanced). Metadata/threshold enrichment failures degrade gracefully (omit the line / title).

### Environment Variables

```bash
# Required
BLOCKFROST_PROJECT_ID              # Blockfrost mainnet project ID
BLOCKFROST_WEBHOOK_AUTH_TOKEN      # Blockfrost webhook HMAC secret

# Optional
BLOCKFROST_API_BASE_URL            # API base URL override (default: mainnet)

# Twitter (required if TWEET_POSTING_ENABLED=true)
API_KEY, API_SECRET_KEY            # Twitter OAuth 1.0a
ACCESS_TOKEN, ACCESS_TOKEN_SECRET  # Twitter access credentials
TWEET_POSTING_ENABLED              # "true" to enable tweet posting (default: false)

# Firestore runtime state (optional override, uses ADC project by default)
FIRESTORE_PROJECT_ID               # optional GCP project override
FIRESTORE_DATABASE                 # Firestore DB id (default: (default))
```

### Code Style & Patterns

- **Formatter & linter**: ruff (configured in `pyproject.toml`). Line length 120. Rules: `E`, `F`, `W`, `I`, `UP`.
- All domain objects are frozen dataclasses in `bot/models.py`.
- Tweet formatting is pure (functions return strings, no side effects).
- `post_tweet()` is the single point for Twitter output — gated by config flag.
- Uses stdlib `logging` everywhere (no `print()`).

## Workflow & Commands

### Deployment Target

Google Cloud Run (FastAPI + uvicorn, containerized), continuously deployed from GitHub. Entry point: `uvicorn bot.main:app` (root `main.py` re-exports `app`). `POST /` handles Blockfrost block events.

**Bootstrapping**: first deploy with `TWEET_POSTING_ENABLED=false` so feed watermarks anchor at the current tips (history left to the backfill script); observe dry-run logs ~24h, then enable posting.

### Local Development

```bash
uv sync
uv run uvicorn bot.main:app --reload --port 8080   # POST / (Blockfrost)
uv run pytest -v
uv run ruff format . && uv run ruff check --fix .
```

## When Modifying Code

### Adding a New Governance Event Type

1. Add mapping in `bot/blockfrost/mapping.py` (governance_type ↔ action type)
2. Add/extend data model in `bot/models.py`
3. Add formatter function in `bot/twitter/formatter.py` (+ template)
4. Wire orchestration in `bot/main.py`

### Changing Tweet Format

- Modify `bot/twitter/formatter.py` / `templates.py`. Keep under 280 characters.

## Dependencies Summary

Managed via `uv` (see `pyproject.toml`, lockfile `uv.lock`).

```text
# Production
fastapi                     # Async web framework
uvicorn[standard]           # ASGI server
httpx                       # Async HTTP client (Blockfrost)
cbor2                       # Transaction CBOR decoding (treasury donations)
requests                    # HTTP client for IPFS metadata
tenacity                    # Retry/backoff decorator (metadata fetch)
python-dotenv               # .env file loading
google-cloud-firestore      # Firestore state store client
xdk                         # X API SDK (OAuth 1.0a + posts client)

# Dev
pytest, pytest-asyncio, ruff
```

## Related Documentation

- [CIP-1694](https://github.com/cardano-foundation/CIPs/blob/master/CIP-1694/README.md): Conway governance
- [CIP-100](https://github.com/cardano-foundation/CIPs/blob/master/CIP-0100/README.md): Governance metadata standard
- [CIP-108](https://github.com/cardano-foundation/CIPs/blob/master/CIP-0108/README.md): Governance action metadata
- [CIP-136](https://github.com/cardano-foundation/CIPs/blob/master/CIP-0136/README.md): CC vote rationale metadata
- [Blockfrost API](https://docs.blockfrost.io/): Cardano data provider
