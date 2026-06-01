# Deployment Notes

The active deployment path is Railway with a Dockerized FastAPI service and Railway PostgreSQL (private internal network).

See [Railway deployment](railway-deployment.md).

HappyRobot webhook targets after deploy:

```text
POST https://YOUR-RAILWAY-DOMAIN/api/offers/evaluate
POST https://YOUR-RAILWAY-DOMAIN/api/calls/summary
```

Headers:

```text
x-api-key: GENERATED_HAPPYROBOT_API_KEY
content-type: application/json
```

Dashboard (public):

```text
https://YOUR-RAILWAY-DOMAIN/dashboard
```
