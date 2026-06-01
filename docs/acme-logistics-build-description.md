# Inbound Carrier Sales Automation — Build Description

**Prepared for:** Acme Logistics
**Prepared by:** Assaad Halabi, Field Deployment Engineer
**Platform:** HappyRobot
**Date:** June 2026

---

## Executive Summary

This document describes a working proof of concept that automates inbound carrier calls for Acme Logistics. Carriers call in, the AI agent verifies their credentials, matches them to an available load, negotiates pricing within policy limits, and either books the load or ends politely. Every call is classified, extracted, and reported on a live operational dashboard — no manual data entry required.

The solution is production-ready: containerized, deployed on Railway with a PostgreSQL database, secured with API key authentication, and integrated end-to-end with the HappyRobot voice AI platform.

---

## What It Does

When a carrier calls in looking for a load:

1. **Greeting** — The AI agent (Paul) answers naturally and asks what load they're calling about.
2. **Load identification** — Paul asks for the load reference number (or lane + trailer type as a fallback).
3. **Carrier verification** — Paul asks for the carrier's MC number and verifies it against the FMCSA database in real time. If the carrier isn't authorized, Paul declines politely.
4. **Load pitch** — Paul retrieves the load details and pitches them conversationally: origin, destination, dates, commodity, weight, equipment, and rate.
5. **Negotiation** — If the carrier counters, Paul evaluates the offer against a configurable pricing policy (up to 3 rounds). The policy is enforced by an external API — not hardcoded in the prompt — making it adjustable without redeploying the voice agent.
6. **Booking or decline** — If a price is agreed, Paul transfers to a sales rep. If not, Paul ends the call politely and invites the carrier to check back.
7. **Post-call processing** — After the call ends, the system automatically classifies the outcome, classifies carrier sentiment, extracts structured data from the conversation, and sends everything to the dashboard.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    HappyRobot Platform                        │
│                                                              │
│  Web Call → Voice Agent (Paul, gpt-4.1)                      │
│    ├── verify_carrier → FMCSA API (GET)                      │
│    ├── find_available_loads → Loads API (GET)                 │
│    ├── evaluate_offer → Dashboard API (POST)   ← live policy │
│    └── transfer_to_colleague (mock)                          │
│                                                              │
│  Post-Call Pipeline:                                          │
│    Classify Outcome → Classify Sentiment → Extract (13 fields)│
│      └── POST Call Summary → Dashboard API                   │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│              Dashboard API (Railway + PostgreSQL)             │
│                                                              │
│  POST /api/offers/evaluate    — real-time negotiation policy │
│  POST /api/calls/summary      — post-call data ingestion     │
│  GET  /dashboard              — live operational dashboard    │
│  GET  /api/metrics            — JSON metrics endpoint         │
└─────────────────────────────────────────────────────────────┘
```

---

## Negotiation Policy

The pricing engine enforces a graduated authority model:

| Round | Authority | Behavior |
|-------|-----------|----------|
| 1 | 25% of max | Counter at 2% above loadboard (at default 8% max) |
| 2 | 62.5% of max | Counter at 5% above loadboard |
| 3 | 100% of max | Accept up to 8% above loadboard, reject above |

- **Configurable** via the `MAX_RATE_ABOVE_LOADBOARD_PCT` environment variable (default: 8%)
- **Walkaway rate** = loadboard rate × (1 + max %) — the absolute ceiling
- Every offer evaluation is stored in the database for audit and dashboard analytics

This means the broker controls the pricing ceiling at the infrastructure level. The AI agent never goes rogue on rates.

---

## Dashboard

**Live URL:** https://happyrobotsalesassistant-production.up.railway.app/dashboard

The dashboard is publicly accessible (no login required for viewing) and auto-refreshes every 30 seconds.

### What it reports:

| Section | Metrics |
|---------|---------|
| **Revenue KPIs** | Total booked revenue, negotiation savings vs. carrier first offers |
| **Operations KPIs** | Total calls, unique carriers, booked count + conversion %, avg negotiation rounds, avg call duration, rate spread |
| **Conversion Funnel** | Total Calls → Carrier Verified → Load Matched → Negotiated → Booked |
| **Call Volume Trend** | 14-day bar chart showing daily call volume |
| **Outcome Breakdown** | Success / Rate Too High / Not Interested |
| **Sentiment Breakdown** | Positive / Neutral / Negative / Frustrated |
| **Decline Reasons** | Grouped reasons why carriers said no |
| **Offer Decisions** | Accept / Counter / Reject distribution from the pricing API |
| **Recent Calls Table** | Carrier name, MC#, reference, lane, listed rate, final rate, rounds, outcome, sentiment, duration |

Time-range filtering is available: `/dashboard?days=7` or `/dashboard?days=30`.

---

## Data Extracted Per Call

After every call, the system automatically extracts:

| Field | Description |
|-------|-------------|
| reference_number | Load reference number discussed |
| mc_number | Carrier's MC number |
| carrier_name | Verified company name |
| booking_decision | Whether they agreed to book (yes/no) |
| decline_reason | Why they declined (if applicable) |
| final_rate | Final agreed or last discussed rate |
| origin | Pickup city/state |
| destination | Delivery city/state |
| loadboard_rate | Listed rate pitched to carrier |
| offer_rate | Carrier's first counter-offer |
| negotiation_rounds | Number of pricing exchanges |
| equipment_type | Trailer type |
| carrier_eligibility | FMCSA verification result |

Plus: full transcript, call duration, outcome classification, and sentiment classification.

---

## Call Outcome Classification

Every call is tagged with one of:

- **Success** — Carrier agreed to book the load
- **Rate too high** — Carrier declined due to rate
- **Not interested** — Carrier declined for other reasons

## Carrier Sentiment Classification

Every call is also tagged with the carrier's emotional tone:

- **Positive** — Friendly, cooperative
- **Neutral** — Professional, business-like
- **Negative** — Dissatisfied, unhappy
- **Frustrated** — Impatient, upset about rates/process

---

## Security

- All API endpoints (data ingestion, offer evaluation, admin) are protected with scoped API keys
- Keys are generated, HMAC-hashed with a server-side pepper, and stored in the database — raw keys are never stored
- The dashboard view is public for easy stakeholder access
- HTTPS is enforced by Railway's edge proxy
- Admin operations use a separate bootstrap token (one-time use)

---

## Deployment

| Component | Technology |
|-----------|-----------|
| Voice AI | HappyRobot platform (web call trigger) |
| Dashboard API | FastAPI + Uvicorn |
| Database | Railway PostgreSQL (internal networking) |
| Container | Docker (python:3.12-slim) |
| Hosting | Railway (auto-deploy from GitHub) |
| Schema management | Auto-migration on startup |

### Access Points

| What | URL |
|------|-----|
| Dashboard | https://happyrobotsalesassistant-production.up.railway.app/dashboard |
| Health check | https://happyrobotsalesassistant-production.up.railway.app/health |
| Metrics JSON | https://happyrobotsalesassistant-production.up.railway.app/api/metrics |
| HappyRobot workflow | https://platform.happyrobot.ai/fdeassaadhalabi/workflows/vjolmwnehgzu/editor/yy6cjt05z80q |
| Source code | https://github.com/assaadhalabi/HappyRobot (private) |

### Reproducing the Deployment

1. Fork or clone the repository
2. Create a Railway project with a PostgreSQL plugin
3. Set environment variables:
   - `DATABASE_URL=${{Postgres.DATABASE_URL}}`
   - `ADMIN_BOOTSTRAP_TOKEN` (generate with `python scripts/generate_secrets.py`)
   - `API_KEY_PEPPER` (same script)
   - `MAX_RATE_ABOVE_LOADBOARD_PCT=8`
   - `ENVIRONMENT=production`
4. Railway auto-detects the Dockerfile and deploys
5. The schema is created automatically on first startup
6. Bootstrap the first admin key, then create the HappyRobot API key

---

## What This Proves

1. **End-to-end automation** — From carrier greeting to data extraction, zero human touch required
2. **Policy enforcement** — Pricing rules are external and configurable, not baked into AI prompts
3. **Operational visibility** — Live dashboard shows conversion, revenue impact, and call quality without relying on platform analytics
4. **Production-grade infrastructure** — Containerized, auto-deployed, retries on cold start, proper error handling
5. **Extensible design** — Adding new load sources, changing pricing policy, or connecting a CRM requires no changes to the voice workflow
