# Railway Deployment

This service deploys to Railway as a Dockerized FastAPI application.

## Architecture

- Railway web service + Railway Postgres plugin (same project)
- Root `Dockerfile`
- FastAPI + Uvicorn
- PostgreSQL connection via Railway service reference variable
- DB-backed generated API keys for business and admin access
- HappyRobot remains responsible for voice AI, extraction, and classification

## Required Railway Variables

```text
ADMIN_BOOTSTRAP_TOKEN=YOUR_LONG_RANDOM_ONE_TIME_BOOTSTRAP_TOKEN
API_KEY_PEPPER=YOUR_LONG_RANDOM_SERVER_SIDE_PEPPER
DATABASE_URL=${{Postgres.DATABASE_URL}}
MAX_RATE_ABOVE_LOADBOARD_PCT=8
PG_POOL_MIN=1
PG_POOL_MAX=5
ALLOWED_ORIGINS=*
ENVIRONMENT=production
```

Generate the two secrets with:

```bash
python scripts/generate_secrets.py
```

`DATABASE_URL` uses Railway's reference variable syntax to automatically resolve
to the internal Postgres connection string. The app handles `postgres://` →
`postgresql://` conversion and URL-encodes special characters in the password
automatically.

The app disables psycopg prepared statements (`prepare_threshold=None`) for
pooler compatibility.

`ADMIN_BOOTSTRAP_TOKEN` is only for creating the first admin API key. After an active admin key exists, the bootstrap endpoint returns `409`.
`API_KEY_PEPPER` is used to hash generated API keys before storing them.

## Deploy Steps

1. Push this repo to GitHub.
2. Create a new Railway project.
3. Add a **Postgres** plugin to the project (right-click canvas → Database → PostgreSQL).
4. Add a new service → **Deploy from GitHub repo**.
5. In the service's Variables tab, add all variables above. Use `${{Postgres.DATABASE_URL}}` to reference the plugin.
6. Railway detects the root `Dockerfile` and deploys.
7. Generate or attach a Railway domain.
8. Confirm `GET /health` returns `{"ok": true, ...}`.
9. Bootstrap the first admin API key.
10. Use the admin API key to generate a HappyRobot API key.

The start command uses Railway's injected `PORT` variable:

```text
uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
```

## Database

The app creates the required tables on startup when `DATABASE_URL` is present
(with retry logic for Railway cold-start race conditions):

- `calls`
- `call_events`
- `offer_evaluations`
- `api_keys`

You can also run [db/schema.sql](../db/schema.sql) manually against the Railway
Postgres instance via `railway connect postgres`.

## API Key Management

If the database tables were not created on startup, force schema initialization:

```bash
curl -X POST https://YOUR-RAILWAY-DOMAIN/api/admin/database/init \
  -H "x-bootstrap-token: YOUR_LONG_RANDOM_ONE_TIME_BOOTSTRAP_TOKEN"
```

You can also inspect database connectivity and table presence:

```bash
curl https://YOUR-RAILWAY-DOMAIN/api/admin/database/status \
  -H "x-bootstrap-token: YOUR_LONG_RANDOM_ONE_TIME_BOOTSTRAP_TOKEN"
```

Bootstrap the first admin key:

```bash
curl -X POST https://YOUR-RAILWAY-DOMAIN/api/admin/bootstrap-key \
  -H "x-bootstrap-token: YOUR_LONG_RANDOM_ONE_TIME_BOOTSTRAP_TOKEN" \
  -H "content-type: application/json" \
  -d '{"name":"primary-admin"}'
```

The response includes an `api_key` with the `admin` scope. Store it securely. It is returned only once.

Generate the HappyRobot key:

```bash
curl -X POST https://YOUR-RAILWAY-DOMAIN/api/admin/api-keys \
  -H "x-admin-key: GENERATED_ADMIN_API_KEY" \
  -H "content-type: application/json" \
  -d '{"name":"happyrobot-production","scopes":["happyrobot"]}'
```

List keys:

```bash
curl https://YOUR-RAILWAY-DOMAIN/api/admin/api-keys \
  -H "x-admin-key: GENERATED_ADMIN_API_KEY"
```

Revoke a key:

```bash
curl -X DELETE https://YOUR-RAILWAY-DOMAIN/api/admin/api-keys/1 \
  -H "x-admin-key: GENERATED_ADMIN_API_KEY"
```

## HappyRobot URLs

Use your Railway domain in HappyRobot:

```text
POST https://YOUR-RAILWAY-DOMAIN/api/offers/evaluate
POST https://YOUR-RAILWAY-DOMAIN/api/calls/events
POST https://YOUR-RAILWAY-DOMAIN/api/calls/summary
```

Headers:

```text
x-api-key: GENERATED_HAPPYROBOT_API_KEY
content-type: application/json
```

Dashboard:

```text
https://YOUR-RAILWAY-DOMAIN/dashboard?api_key=GENERATED_HAPPYROBOT_API_KEY
```
