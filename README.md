# Cardano Governance Actions Bot

A monitoring bot that watches the Cardano blockchain for governance activity, posts summaries to Twitter/X, and archives rationale metadata to GitHub.

X bot account: [@GovActions](https://x.com/GovActions)

## How It Works

```
Blockfrost Webhook (POST /) → FastAPI on Cloud Run → Query Blockfrost API → Fetch IPFS metadata → Post to X + Archive rationale
```

1. **Blockfrost** sends block webhooks to `/`
2. The bot queries the **Blockfrost API** for governance actions and CC votes
3. Metadata is fetched from **IPFS** and validated (CIP-0108 / CIP-0136 warnings only)
4. Formatted summaries are posted to **Twitter/X** via `xdk`
5. Mutable runtime state (tweet IDs, checkpoints) is stored in **Google Cloud Firestore**
6. Rationale JSON is archived to GitHub through automated direct commits to `main`

### What It Monitors

- 🚨 **New governance actions** — proposals submitted on-chain
- 📜 **CC member votes** — Constitutional Committee voting activity
- 📊 **Voting progress** — periodic updates on active governance action voting status
- ⏰ **Action expirations** — warnings when governance actions are about to expire

## Prerequisites

- **Google Cloud Platform** account with a project
- **Blockfrost** API project ID (mainnet or testnet)
- **Twitter/X API** credentials (OAuth 1.0a user tokens)
- **Blockfrost webhook** configured to send block events
- **GitHub token + repo access** (optional, for rationale archiving)

## Environment Variables

The bot loads `.env` locally (`python-dotenv`) and can also read from Cloud Run environment variables / Secret Manager.

| Variable | Description |
|---|---|
| `API_KEY` | Twitter OAuth 1.0a consumer key |
| `API_SECRET_KEY` | Twitter OAuth 1.0a consumer secret |
| `ACCESS_TOKEN` | Twitter access token |
| `ACCESS_TOKEN_SECRET` | Twitter access token secret |
| `BLOCKFROST_PROJECT_ID` | Blockfrost API project ID (e.g. `mainnetABC123XYZ`) |
| `BLOCKFROST_NETWORK` | Network to use: `mainnet`, `preprod`, or `preview` (default: `mainnet`) |
| `BLOCKFROST_WEBHOOK_AUTH_TOKEN` | Shared secret used to verify `Blockfrost-Signature` |
| `TWEET_POSTING_ENABLED` | Set to `true` to enable posting tweets (default: `false`) |
| `GITHUB_TOKEN` | GitHub token for rationale archiving (optional) |
| `GITHUB_REPO` | Repository in `owner/name` format for rationale archives (optional) |
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
  -e BLOCKFROST_PROJECT_ID=mainnetABC123XYZ \
  -e BLOCKFROST_NETWORK=mainnet \
  -e BLOCKFROST_WEBHOOK_AUTH_TOKEN=your_webhook_secret \
  -e TWEET_POSTING_ENABLED=false \
  gov-actions-bot
```

## Deployment

The bot is deployed to **Google Cloud Run** with continuous deployment from this GitHub repository.

### One-Time Setup

1. **Store secrets** in Google Secret Manager for your GCP project:
  - `api-key`, `api-secret-key`, `access-token`, `access-token-secret`
  - `blockfrost-project-id`, `blockfrost-webhook-auth-token`
  - Optional: `github-token`, `github-repo` (for rationale archiving)

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
│   ├── rationale_archiver.py    # GitHub rationale archiving (direct commits to main)
│   ├── rationale_validator.py   # CIP-0108/CIP-0136 warning-only validation
│   ├── webhook_auth.py          # Blockfrost HMAC signature verification
│   ├── state_store.py           # Firestore-backed runtime state (tweet IDs, checkpoints)
│   ├── blockfrost/              # Blockfrost API client + async repository layer
│   ├── metadata/                # IPFS URL sanitisation and metadata fetch
│   └── twitter/
│       ├── client.py            # XDK posting client
│       ├── formatter.py         # Tweet composition logic
│       └── templates.py         # Editable tweet templates
├── data/
│   └── cc_profiles.yaml         # CC member profile mappings
├── scripts/
│   ├── backfill_rationales.py   # Backfill historical rationales from DB-Sync
│   └── backfill_tweet_ids.py    # Backfill tweet_id.txt from historical posts
├── rationales/                  # Archived rationale files
├── tests/                       # Pytest test suite
├── docs/                        # Reference docs (schema + CIPs)
├── pyproject.toml               # Dependency/tool config
├── uv.lock                      # Locked dependency versions
├── Dockerfile                   # Container image
└── .env.example                 # Environment variable template
```

## License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.
