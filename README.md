# Cardano Governance Actions Bot

A monitoring bot that watches the Cardano blockchain for governance activity, posts summaries to Twitter/X, archives rationale metadata to GitHub, and triages X mentions into GitHub issues.

X bot account: [@GovActions](https://x.com/GovActions)

## How It Works

```
Blockfrost Webhook (`/`) → Cloud Run → Query DB-Sync → Fetch IPFS metadata → Post to X + Archive rationale
X Webhook (`/x/webhook`) → Cloud Run → LLM triage → GitHub issue + X reply
```

1. **Blockfrost** sends block webhooks to `/`
2. The bot queries a **Cardano DB-Sync** PostgreSQL database for governance actions, CC votes, and epoch donations
3. Metadata is fetched from **IPFS** and validated (CIP-0108 / CIP-0136 warnings only)
4. Formatted summaries are posted to **Twitter/X** via `xdk`
5. Rationale JSON is archived to GitHub through automated direct commits to `main`
6. **X** sends mention webhooks to `/x/webhook`; mentions are triaged by an LLM and optionally create GitHub issues

### What It Monitors

- 🚨 **New governance actions** — proposals submitted on-chain
- 📜 **CC member votes** — Constitutional Committee voting activity
- 💸 **Treasury donations** — per-epoch donation statistics
- 🧠 **X mentions** — bug/feature triage with optional GitHub issue creation + reply

## Prerequisites

- **Google Cloud Platform** account with a project
- **Cardano DB-Sync** PostgreSQL database access
- **Twitter/X API** credentials (OAuth 1.0a with read/write access)
- **Blockfrost** account with webhook configured
- **GitHub token + repo access** (optional, for rationale archiving)

## Environment Variables

The bot loads `.env` locally (`python-dotenv`) and can also read from Cloud Run environment variables / Secret Manager.

| Variable | Description |
|---|---|
| `API_KEY` | Twitter OAuth 1.0a consumer key |
| `API_SECRET_KEY` | Twitter OAuth 1.0a consumer secret |
| `ACCESS_TOKEN` | Twitter access token |
| `ACCESS_TOKEN_SECRET` | Twitter access token secret |
| `DB_SYNC_URL` | PostgreSQL connection string (e.g. `postgresql://user:pass@host:5432/dbname`) |
| `BLOCKFROST_WEBHOOK_AUTH_TOKEN` | Shared secret used to verify `Blockfrost-Signature` |
| `TWEET_POSTING_ENABLED` | Set to `true` to enable posting tweets/replies (default: `false`) |
| `X_WEBHOOK_ENABLED` | Enable X webhook handling at `/x/webhook` (default: `false`) |
| `LLM_MODEL` | LiteLLM model name for mention triage (required when `X_WEBHOOK_ENABLED=true`) |
| `LLM_ISSUE_CONFIDENCE_THRESHOLD` | Confidence threshold (0-1) for issue creation (default: `0.80`) |
| `X_WEBHOOK_CALLBACK_URL` | Full callback URL used by `scripts/setup_x_webhook.py` |
| `GITHUB_TOKEN` | GitHub token for rationale archiving commits (optional) |
| `GITHUB_REPO` | Repository in `owner/name` format for rationale archives (optional) |

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
uv run functions-framework --target=handle_webhook --debug
# Server starts at http://localhost:8080
# Endpoints:
#   POST /            (Blockfrost)
#   GET/POST /x/webhook (X CRC + events)

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
  -e DB_SYNC_URL=postgresql://user:pass@host:5432/dbname \
  -e BLOCKFROST_WEBHOOK_AUTH_TOKEN=your_webhook_secret \
  -e TWEET_POSTING_ENABLED=false \
  gov-actions-bot
```

## Deployment

The bot is deployed to **Google Cloud Run** with continuous deployment from this GitHub repository.

### One-Time Setup

1. **Store secrets** in Google Secret Manager for your GCP project:
   - `api-key`, `api-secret-key`, `access-token`, `access-token-secret`
   - `db-sync-url`, `blockfrost-webhook-auth-token`
   - Optional: `github-token`, `github-repo`

2. **Create a Cloud Run service**:
   - Go to [Cloud Run Console](https://console.cloud.google.com/run)
   - Click **Create Service** → **Continuously deploy from a repository**
   - Connect to `github.com/semsorock/cardano-gov-actions-bot`, branch: `main`
   - Build type: **Dockerfile**
   - Configure environment variables to reference Secret Manager secrets
   - Allow unauthenticated invocations (required for Blockfrost webhooks)

3. **Configure Blockfrost webhook** to point to your Cloud Run service URL:
   - Block event webhook URL: `https://YOUR_SERVICE_URL/`

4. **Configure X webhook + subscription** with the helper script:
   - Set `X_WEBHOOK_CALLBACK_URL=https://YOUR_SERVICE_URL/x/webhook`
   - Run:

```bash
uv run python scripts/setup_x_webhook.py
```

The script uses official XDK calls:
- `client.webhooks.get()`
- `client.webhooks.create(...)` (if needed)
- `client.webhooks.validate(...)`
- `client.account_activity.validate_subscription(...)`
- `client.account_activity.create_subscription(...)` (if needed)

### How Deployments Work

Every push to the `main` branch automatically triggers:
1. Cloud Build builds a new Docker image from the `Dockerfile`
2. Cloud Run deploys the new revision
3. Traffic shifts to the new revision once healthy

## Project Structure

```
├── main.py                      # Entry point shim (re-exports handle_webhook)
├── bot/
│   ├── cc_profiles.py           # CC voter hash -> X handle mapping loader
│   ├── config.py                # Centralised env config + feature flags
│   ├── links.py                 # External governance/vote link builders
│   ├── logging.py               # Structured logging setup
│   ├── main.py                  # Unified webhook handler
│   ├── models.py                # Domain dataclasses
│   ├── rationale_archiver.py    # GitHub rationale archiving (direct commits to main)
│   ├── rationale_validator.py   # CIP-0108/CIP-0136 warning-only validation
│   ├── webhook_auth.py          # Blockfrost HMAC signature verification
│   ├── x_webhook_auth.py        # X webhook CRC/signature verification
│   ├── x_mentions.py            # Mention extraction + ignore policy
│   ├── llm_triage.py            # LiteLLM mention classification
│   ├── github_issues.py         # GitHub issue creation + dedupe marker
│   ├── db/                      # SQL constants + repository layer
│   ├── metadata/                # IPFS URL sanitisation and metadata fetch
│   └── twitter/
│       ├── client.py            # XDK posting client
│       ├── formatter.py         # Tweet composition logic
│       └── templates.py         # Editable tweet templates
├── data/
│   └── cc_profiles.yaml         # CC member profile mappings
├── scripts/
│   ├── backfill_rationales.py   # Backfill historical rationales from DB-Sync
│   ├── backfill_tweet_ids.py    # Backfill tweet_id.txt from historical posts
│   └── setup_x_webhook.py       # Create/validate X webhook + account subscription
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
