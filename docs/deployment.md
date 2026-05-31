# Deployment Notes

The active deployment path is Railway with a Dockerized FastAPI service.

See [Railway deployment](railway-deployment.md).

HappyRobot webhook targets after deploy:

```text
POST https://YOUR-RAILWAY-DOMAIN/api/offers/evaluate
POST https://YOUR-RAILWAY-DOMAIN/api/calls/events
POST https://YOUR-RAILWAY-DOMAIN/api/calls/summary
GET  https://YOUR-RAILWAY-DOMAIN/api/metrics
GET  https://YOUR-RAILWAY-DOMAIN/dashboard?api_key=GENERATED_HAPPYROBOT_API_KEY
```

Headers:

```text
x-api-key: GENERATED_HAPPYROBOT_API_KEY
content-type: application/json
```
