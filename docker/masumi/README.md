# Masumi Node — FarmWise

Runs **Masumi Registry Service** (port 3100) and **Masumi Payment Service** (port 3101) on Cardano.

## Quick Setup (8 steps)

### 1. Prerequisites

- Docker Engine 24+ with Compose plugin
- **Blockfrost project ID** for Preprod — free at https://blockfrost.io

  Blockfrost uses **project IDs** (not API keys). Create a project, select **Preprod** network, copy the `project_id`.

### 2. Configure

```bash
cd docker/masumi
# Edit .env — set these THREE values:
```

| Variable | What it is | How to get |
|---|---|---|
| `ENCRYPTION_KEY` | Wallet encryption key (20+ chars) | `openssl rand -hex 32` |
| `ADMIN_KEY` | Admin panel password (15+ chars) | Any string you make up |
| `NETWORK` | `Preprod` or `Mainnet` | Must match your Blockfrost project |
| `BLOCKFROST_API_KEY_PREPROD` | Blockfrost **project ID** (despite the name) | https://blockfrost.io → Create Project → Preprod → copy ID |

> **Note on naming:** Masumi's env var is called `BLOCKFROST_API_KEY_PREPROD` but Blockfrost
> actually calls it a `project_id`. The value you paste is the project ID from your
> Blockfrost dashboard, not a traditional API key. See
> [Blockfrost docs](https://blockfrost.dev/start-building/cardano/#usage) for details:
> ```bash
> export PROJECT_ID=preprod...   # This is what you put in BLOCKFROST_API_KEY_PREPROD
> curl -H "project_id: $PROJECT_ID" https://cardano-preprod.blockfrost.io/api/v0/...
> ```

### 3. Start services

```bash
docker compose up -d
```

First pull: ~2GB, takes 2-5 minutes. Auto-migrates + seeds on first boot.

### 4. Check health

```bash
curl http://localhost:3100/api/v1/health    # Registry → {"status":"ok"}
curl http://localhost:3101/api/v1/health    # Payment  → {"status":"ok"}
```

### 5. Get your Payment API key

Open the **Payment Service admin panel** in your browser:

```
http://localhost:3101/admin
```

Click **Login** and enter the `ADMIN_KEY` you set in `.env`.

Then:
- Navigate to **API Keys** → **Create New**
- Name: `farmwise-backend`
- Copy the generated key

This is your `MASUMI_PAYMENT_API_KEY`.

### 6. Register your agent

```bash
ADMIN_KEY="the_admin_key_from_your_env"    # Paste your ADMIN_KEY

curl -X POST http://localhost:3100/api/v1/agents \
  -H "Content-Type: application/json" \
  -H "x-api-key: $ADMIN_KEY" \
  -d '{
    "name": "FarmWise Daily Diagnostic",
    "description": "Crop diagnostic agent for potato monitoring",
    "network": "Preprod",
    "pricing": { "amount": "0", "currency": "ADA", "period": "per_request" }
  }'
```

Copy the `id` field from the response — this is your `MASUMI_AGENT_IDENTIFIER`.

### 7. Configure backend `.env`

Add to `backend/.env`:

```bash
MASUMI_PAYMENT_SERVICE_URL=http://localhost:3101/api/v1
MASUMI_PAYMENT_API_KEY=<key_from_admin_panel_step_5>
MASUMI_AGENT_IDENTIFIER=<agent_id_from_registry_step_6>
MASUMI_NETWORK=Preprod
```

Remove the old `MASUMI_SECRET_KEY` line — it's unused by the current SDK.

### 8. Test the connection

```bash
cd backend && source venv/bin/activate
python3 -c "
from services.masumi import log_decision
import asyncio
tx = asyncio.run(log_decision({
    'plotId': 'test-123', 'action': 'spray_fungicide',
    'cause': 'late_blight', 'urgencyHours': 48,
    'stage': 'Tuber Bulking', 'forecastedYieldKg': 7200, 'timestamp': ''
}))
print(f'Tx hash: {tx}')
"
```

If Masumi is reachable → returns a real Cardano tx hash.
If unreachable → returns a `demo-tx-` placeholder.

Verify real tx hashes at:
```
https://preprod.cardanoscan.io/transaction/<TX_HASH>
```

## Useful commands

```bash
docker compose down          # Stop (data preserved)
docker compose down -v       # Stop + delete all data (fresh start)
docker compose logs -f payment-service   # Watch payment logs
docker compose logs -f registry-service  # Watch registry logs
```

## Service reference

| Service | URL |
|---|---|
| Registry API | http://localhost:3100/api/v1 |
| Registry Swagger | http://localhost:3100/docs |
| Payment API | http://localhost:3101/api/v1 |
| **Payment Admin** | **http://localhost:3101/admin** |
| Payment Swagger | http://localhost:3101/docs |
| Postgres (Registry) | localhost:5442, user/pass: postgres/postgres |
| Postgres (Payment) | localhost:5443, user/pass: postgres/postgres |

## Blockfrost reference

Blockfrost docs: https://blockfrost.dev/start-building/cardano/

```bash
# Testing your project ID directly:
curl -H "project_id: <your_project_id>" \
  https://cardano-preprod.blockfrost.io/api/v0/health
# → {"is_healthy":true}
```
