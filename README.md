# HappyRobot Sales Assistant

Railway-hosted FastAPI service for the HappyRobot FDE inbound carrier sales challenge.

## Responsibility Split

HappyRobot owns the AI layer:

- Web call trigger and voice agent
- FMCSA verification tool invocation
- Load lookup tool invocation
- In-call natural language
- AI Extract (13 fields)
- AI Classify (outcome + sentiment)

This FastAPI service owns deterministic external systems:

- Counter-offer evaluation (pricing policy)
- Post-call summary persistence
- Custom metrics API
- Custom dashboard (public)
- Railway deployment with private Postgres

## Stack

- FastAPI + Uvicorn
- Railway PostgreSQL (private internal network)
- Docker (python:3.12-slim)
- Railway auto-deploy from GitHub

## Routes

Business routes require a generated DB-backed `x-api-key` with the `happyrobot` scope.

```text
GET    /health
GET    /dashboard              (public — no auth)
GET    /api/metrics
POST   /api/offers/evaluate
POST   /api/calls/summary
POST   /api/admin/bootstrap-key
POST   /api/admin/database/init
GET    /api/admin/database/status
POST   /api/admin/api-keys
GET    /api/admin/api-keys
DELETE /api/admin/api-keys/{key_id}
```

## API Key Flow

Railway stores two server-side secrets:

```text
ADMIN_BOOTSTRAP_TOKEN=...
API_KEY_PEPPER=...
```

Use the bootstrap token only once to create the first admin API key:

```bash
curl -X POST https://YOUR-RAILWAY-DOMAIN/api/admin/bootstrap-key \
  -H "x-bootstrap-token: YOUR_ADMIN_BOOTSTRAP_TOKEN" \
  -H "content-type: application/json" \
  -d '{"name":"primary-admin"}'
```

Then use the returned admin key to create the HappyRobot key:

```bash
curl -X POST https://YOUR-RAILWAY-DOMAIN/api/admin/api-keys \
  -H "x-admin-key: GENERATED_ADMIN_API_KEY" \
  -H "content-type: application/json" \
  -d '{"name":"happyrobot-production","scopes":["happyrobot"]}'
```

Raw keys are returned once. The database stores only a lookup prefix and HMAC hash.

## Evaluate Offer

```http
POST /api/offers/evaluate
```

```json
{
  "reference_number": "REF09460",
  "loadboard_rate": 2500,
  "offer_rate": 2700,
  "negotiation_round": 1
}
```

Response:

```json
{
  "decision": "counter",
  "counter_rate": 2550,
  "accepted_rate": null,
  "next_action": "ask_carrier_to_accept_counter",
  "say": "I cannot get to $2,700. The best I can do right now is $2,550. Does that work?"
}
```

## Local Run

```powershell
Copy-Item .env.example .env
pip install -r requirements-dev.txt
uvicorn app.main:app --reload
```

Open:

```text
http://127.0.0.1:8000/docs
http://127.0.0.1:8000/dashboard
```

## Railway Deploy

Set Railway variables:

```text
ADMIN_BOOTSTRAP_TOKEN=...
API_KEY_PEPPER=...
DATABASE_URL=${{Postgres.DATABASE_URL}}
MAX_RATE_ABOVE_LOADBOARD_PCT=8
PG_POOL_MIN=1
PG_POOL_MAX=5
ALLOWED_ORIGINS=*
ENVIRONMENT=production
```

`DATABASE_URL` resolves to Railway's private internal Postgres URL (`postgres.railway.internal`).

Generate the Railway secrets locally:

```powershell
& '.venv\Scripts\python.exe' scripts\generate_secrets.py
```

After Railway deploys, call `/api/admin/bootstrap-key` once to create the first admin API key. Then use that admin key to create the HappyRobot API key.

Railway builds from the root `Dockerfile`. The container starts with:

```text
uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
```

## Docs

- [Railway deployment](docs/railway-deployment.md)
- [GitHub and Railway checklist](docs/github-railway-checklist.md)
- [HappyRobot configuration notes](docs/happyrobot-configuration.md)
- [Acme Logistics build description](docs/acme-logistics-build-description.md)
- [Client email draft](docs/client-email-draft.md)
