# Cardano Governance Actions Bot

A monitoring bot that watches the Cardano blockchain for governance activity and posts summaries to Twitter/X.

X bot account: [@GovActions](https://x.com/GovActions)

## How It Works

```
Blockfrost Webhook (POST /) → FastAPI on Cloud Run → Scan Blockfrost feeds (async) → Fetch IPFS metadata → Post to X
```

1. **Blockfrost** sends block webhooks to `/`
2. On each webhook the bot scans the Blockfrost **governance proposals** and
   **committee votes** feeds, processing items newer than the persisted
   watermarks, and reads the block's transaction CBOR for treasury donations
3. Metadata is fetched from **IPFS** (or Blockfrost's validated `json_metadata`)
   and validated (CIP-0108 / CIP-0136 warnings only)
4. Formatted summaries are posted to **Twitter/X** via `xdk`
5. Mutable runtime state (tweet IDs, feed watermarks, committee snapshots,
   checkpoints) is stored in **Google Cloud Firestore**

**Blockfrost is the sole Cardano data provider.** Feed watermarks plus per-item
idempotency keys make duplicate and out-of-order webhook deliveries safe.

### What It Monitors

- 🚨 **New governance actions** — proposals submitted on-chain
- 📜 **CC member votes** — Constitutional Committee voting activity
- 💸 **Treasury donations** — per-epoch donation statistics

## Prerequisites

- **Google Cloud Platform** account with a project
- **Blockfrost** account (mainnet project ID) with a block webhook configured
- **Twitter/X API** credentials (OAuth 1.0a user tokens + app bearer token)

## Environment Variables

The bot loads `.env` locally (`python-dotenv`) and can also read from Cloud Run environment variables / Secret Manager.

| Variable | Description |
|---|---|
| `API_KEY` | Twitter OAuth 1.0a consumer key |
| `API_SECRET_KEY` | Twitter OAuth 1.0a consumer secret |
| `ACCESS_TOKEN` | Twitter access token |
| `ACCESS_TOKEN_SECRET` | Twitter access token secret |
| `BLOCKFROST_PROJECT_ID` | Blockfrost mainnet project ID (**required**) |
| `BLOCKFROST_API_BASE_URL` | Optional API base URL override (default: `https://cardano-mainnet.blockfrost.io/api/v0`) |
| `BLOCKFROST_WEBHOOK_AUTH_TOKEN` | Shared secret used to verify `Blockfrost-Signature` |
| `TWEET_POSTING_ENABLED` | Set to `true` to enable posting tweets (default: `false`) |
| `FIRESTORE_PROJECT_ID` | Optional Firestore project override; default uses ADC project |
| `FIRESTORE_DATABASE` | Firestore database ID (default: `(default)`) |

## Local Development

```bash
# Clone the repository
git clone https://github.com/semsorock/cardano-gov-actions-bot.git
cd cardano-gov-actions-bot

# Install uv (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Sync dependencies (creates .venv automatically)
uv sync

# Configure environment variables (or copy from .env.example)
cp .env.example .env

# Run locally
uv run uvicorn bot.main:app --reload --port 8080
# Server starts at http://localhost:8080
# Endpoint: POST / (Blockfrost)

# Run tests
uv run pytest -v

# Format & lint
uv run ruff format .
uv run ruff check --fix .
```

### Local Docker Build

```bash
docker build -t gov-actions-bot .
docker run --rm -p 8080:8080 \
  -e API_KEY=your_key \
  -e API_SECRET_KEY=your_secret \
  -e ACCESS_TOKEN=your_token \
  -e ACCESS_TOKEN_SECRET=your_token_secret \
  -e BLOCKFROST_PROJECT_ID=mainnetXXXXXXXX \
  -e BLOCKFROST_WEBHOOK_AUTH_TOKEN=your_webhook_secret \
  -e TWEET_POSTING_ENABLED=false \
  gov-actions-bot
```

## Deployment

The bot is deployed to **Google Cloud Run** with continuous deployment from this GitHub repository.

### One-Time Setup

1. **Store secrets** in Google Secret Manager for your GCP project:
  - `api-key`, `api-secret-key`, `access-token`, `access-token-secret`
  - `bearer-token`
  - `blockfrost-project-id`, `blockfrost-webhook-auth-token`


2. **Create a Cloud Run service**:
   - Go to [Cloud Run Console](https://console.cloud.google.com/run)
   - Click **Create Service** → **Continuously deploy from a repository**
   - Connect to `github.com/semsorock/cardano-gov-actions-bot`, branch: `main`
   - Build type: **Dockerfile**
   - Configure environment variables to reference Secret Manager secrets
   - Allow unauthenticated invocations (required for Blockfrost webhooks)

3. **Configure Blockfrost webhook** to point to your Cloud Run service URL:
   - Block event webhook URL: `https://YOUR_SERVICE_URL/`

### How Deployments Work

Every push to the `main` branch automatically triggers:
1. Cloud Build builds a new Docker image from the `Dockerfile`
2. Cloud Run deploys the new revision
3. Traffic shifts to the new revision once healthy

## Project Structure

```
├── main.py                      # Entry point shim (re-exports FastAPI app)
├── bot/
│   ├── cc_profiles.py           # CC voter hash -> X handle mapping loader
│   ├── config.py                # Centralised env config + feature flags
│   ├── links.py                 # External governance/vote link builders
│   ├── logging.py               # Structured logging setup
│   ├── main.py                  # FastAPI app + async webhook handler
│   ├── models.py                # Domain dataclasses
│   ├── rationale_validator.py   # CIP-0108/CIP-0136 warning-only validation
│   ├── webhook_auth.py          # Blockfrost HMAC signature verification
│   ├── state_store.py           # Firestore runtime state (tweet IDs, watermarks, snapshots)
│   ├── blockfrost/              # Async Blockfrost client + feed/committee/CBOR adapters
│   ├── thresholds.py            # Ratification-threshold engine (epoch params + committee)
│   ├── metadata/                # IPFS URL sanitisation and metadata fetch
│   └── twitter/
│       ├── client.py            # XDK posting client
│       ├── formatter.py         # Tweet composition logic
│       └── templates.py         # Editable tweet templates
├── data/
│   └── cc_profiles.yaml         # CC member profile mappings
├── scripts/
│   └── backfill_rationales.py   # Backfill historical rationales from Blockfrost
├── rationales/                  # Archived rationale files
├── tests/                       # Pytest test suite
├── docs/                        # Reference docs (CIPs)
├── pyproject.toml               # Dependency/tool config
├── uv.lock                      # Locked dependency versions
├── Dockerfile                   # Container image
└── .env.example                 # Environment variable template
```

## Bootstrapping

On first deploy the feeds have no watermarks. Bring the bot up with
`TWEET_POSTING_ENABLED=false` so it adopts the current feed tips as watermarks
and processes only *new* items (history is left to `scripts/backfill_rationales.py`).
Observe the dry-run logs for ~24 hours, then set `TWEET_POSTING_ENABLED=true`.

## License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.
