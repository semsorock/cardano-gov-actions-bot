# Cardano Governance Actions Bot

A monitoring bot that watches the Cardano blockchain for new governance actions and Constitutional Committee (CC) votes, then automatically posts summaries to Twitter/X.

## How It Works

```
Blockfrost Webhook → Cloud Run → Query DB-Sync → Post Tweet
```

1. **Blockfrost** sends webhook events when new blocks or epochs occur
2. The bot queries a **Cardano DB-Sync** PostgreSQL database for governance data
3. Metadata is fetched from **IPFS** (governance action details, vote rationales)
4. Formatted summaries are posted to **Twitter/X**

### What It Monitors

- 🚨 **New governance actions** — proposals submitted on-chain
- 📜 **CC member votes** — Constitutional Committee voting activity
- 💸 **Treasury donations** — per-epoch donation statistics

## Prerequisites

- **Google Cloud Platform** account with a project
- **Cardano DB-Sync** PostgreSQL database access
- **Twitter/X API** credentials (OAuth 1.0a with read/write access)
- **Blockfrost** account with webhook configured
- **Docker** (for local testing)

## Environment Variables

The bot requires the following environment variables, stored in **Google Secret Manager** and linked to the Cloud Run service:

| Variable | Description |
|---|---|
| `API_KEY` | Twitter OAuth 1.0a consumer key |
| `API_SECRET_KEY` | Twitter OAuth 1.0a consumer secret |
| `ACCESS_TOKEN` | Twitter access token |
| `ACCESS_TOKEN_SECRET` | Twitter access token secret |
| `DB_SYNC_URL` | PostgreSQL connection string (e.g. `postgresql://user:pass@host:5432/dbname`) |

## Local Development

```bash
# Clone the repository
git clone https://github.com/semsorock/govactions.git
cd govactions

# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Set environment variables
export API_KEY=your_key
export API_SECRET_KEY=your_secret
export ACCESS_TOKEN=your_token
export ACCESS_TOKEN_SECRET=your_token_secret
export DB_SYNC_URL=postgresql://user:pass@host:5432/dbname

# Run locally (uses main.py by default)
functions-framework --target=hello_http --debug
# Server starts at http://localhost:8080
# Routes: /block and /epoch
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
  gov-actions-bot
```

## Deployment

The bot is deployed to **Google Cloud Run** with continuous deployment from this GitHub repository.

### One-Time Setup

1. **Store secrets** in Google Secret Manager for your GCP project:
   - `api-key`, `api-secret-key`, `access-token`, `access-token-secret`, `db-sync-url`

2. **Create a Cloud Run service**:
   - Go to [Cloud Run Console](https://console.cloud.google.com/run)
   - Click **Create Service** → **Continuously deploy from a repository**
   - Connect to `github.com/semsorock/govactions`, branch: `main`
   - Build type: **Dockerfile**
   - Configure environment variables to reference Secret Manager secrets
   - Allow unauthenticated invocations (required for Blockfrost webhooks)

3. **Configure Blockfrost webhook** to point to your Cloud Run service URL:
   - Block events → `https://YOUR_SERVICE_URL/block`
   - Epoch events → `https://YOUR_SERVICE_URL/epoch`

### How Deployments Work

Every push to the `main` branch automatically triggers:
1. Cloud Build builds a new Docker image from the `Dockerfile`
2. Cloud Run deploys the new revision
3. Traffic shifts to the new revision once healthy

## Project Structure

```
├── main.py              # Main application (webhook handlers, DB queries, tweet logic)
├── ipfs.py              # IPFS gateway utility
├── requirements.txt     # Python dependencies
├── Dockerfile           # Container image definition
├── docs/                # Reference documentation (DB-Sync schema)
└── drafts/              # Development drafts and sample data (not deployed)
```

## License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.
