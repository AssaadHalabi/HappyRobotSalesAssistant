# GitHub And Railway Checklist

## What Gets Created When

Before Railway deploy:

- Generate `ADMIN_BOOTSTRAP_TOKEN`.
- Generate `API_KEY_PEPPER`.
- Add both to Railway variables.
- Add `DATABASE_URL=${{Postgres.DATABASE_URL}}` (Railway resolves this to the private internal connection string).

After Railway deploy:

- Call `/api/admin/bootstrap-key` once to create the first generated admin API key.
- Use that admin API key to create the generated HappyRobot API key.
- Put the HappyRobot API key into HappyRobot tool/webhook headers.

The first generated token is created after hosting because the application needs the deployed service and Railway Postgres database to store the hashed key.

## 1. Generate Railway Secrets

From the repo root:

```powershell
& '.venv\Scripts\python.exe' scripts\generate_secrets.py
```

Or with any Python 3:

```bash
python scripts/generate_secrets.py
```

This prints:

```text
ADMIN_BOOTSTRAP_TOKEN=...
API_KEY_PEPPER=...
```

Do not commit these values.

## 2. Confirm Git Status

```powershell
git status --short
```

Expected: source files are staged or unstaged, but `.env`, `.venv`, `data`, caches, and local DB files should not appear.

## 3. Commit And Push To GitHub

```powershell
git add .gitignore .dockerignore Dockerfile railway.json requirements.txt requirements-dev.txt app db docs tests scripts README.md .env.example
git commit -m "Build Railway FastAPI carrier sales service"
git branch -M main
git remote add origin https://github.com/YOUR-USER/YOUR-REPO.git
git push -u origin main
```

If the remote already exists:

```powershell
git remote set-url origin https://github.com/YOUR-USER/YOUR-REPO.git
git push -u origin main
```

## 4. Create Railway Project

1. Open Railway.
2. Create a new project.
3. Add a **Postgres** plugin (right-click canvas → Database → PostgreSQL).
4. Add a new service → **Deploy from GitHub repo**.
5. Choose this repository.
6. Railway detects the root `Dockerfile`.

The app connects to Postgres over Railway's private network (`postgres.railway.internal`) — no public exposure.

Railway provides a `PORT` variable at runtime. The Dockerfile starts Uvicorn with:

```text
uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
```

## 5. Add Railway Variables

Set these on the Railway service:

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

`${{Postgres.DATABASE_URL}}` is Railway's reference variable that resolves to the private internal Postgres URL.

## 6. Deploy And Check Health

After Railway deploys, generate a public domain and verify:

```bash
curl https://YOUR-RAILWAY-DOMAIN/health
```

Expected:

```json
{"ok":true,"service":"happyrobot-carrier-sales"}
```

## 7. Bootstrap First Admin API Key

Run this once:

```bash
curl -X POST https://YOUR-RAILWAY-DOMAIN/api/admin/bootstrap-key \
  -H "x-bootstrap-token: YOUR_ADMIN_BOOTSTRAP_TOKEN" \
  -H "content-type: application/json" \
  -d '{"name":"primary-admin"}'
```

Save the returned `api_key`. It will look like:

```text
hr_live_...
```

This is your generated admin API key. The bootstrap endpoint will return `409` after an active admin key exists.

## 8. Generate HappyRobot API Key

```bash
curl -X POST https://YOUR-RAILWAY-DOMAIN/api/admin/api-keys \
  -H "x-admin-key: GENERATED_ADMIN_API_KEY" \
  -H "content-type: application/json" \
  -d '{"name":"happyrobot-production","scopes":["happyrobot"]}'
```

Save the returned `api_key`. This is the one HappyRobot should use.

## 9. Configure HappyRobot

For the `evaluate_offer` tool and post-call webhook:

```text
x-api-key: GENERATED_HAPPYROBOT_API_KEY
content-type: application/json
```

Endpoints:

```text
POST https://YOUR-RAILWAY-DOMAIN/api/offers/evaluate
POST https://YOUR-RAILWAY-DOMAIN/api/calls/summary
```

Dashboard (public):

```text
https://YOUR-RAILWAY-DOMAIN/dashboard
```

## 10. Smoke Test Offer Evaluation

```bash
curl -X POST https://YOUR-RAILWAY-DOMAIN/api/offers/evaluate \
  -H "x-api-key: GENERATED_HAPPYROBOT_API_KEY" \
  -H "content-type: application/json" \
  -d '{"reference_number":"TEST","loadboard_rate":2500,"offer_rate":2700,"negotiation_round":1}'
```

Expected decision:

```json
{"decision":"counter"}
```
