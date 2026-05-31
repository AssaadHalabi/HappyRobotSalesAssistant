# Acme Logistics - Inbound Carrier Sales Automation

## Overview

This proof of concept automates inbound carrier calls for Acme Logistics. A carrier can call through the HappyRobot web call experience, provide an MC number, request a load, hear the load details, and negotiate the rate with the AI agent.

The system uses HappyRobot for the voice workflow and conversation experience, existing AWS APIs for FMCSA and load lookup, and a Railway-hosted FastAPI service for negotiation decisions, call outcome ingestion, and reporting.

## Workflow

1. The carrier starts a web call.
2. The agent collects the carrier's MC number.
3. The agent verifies carrier details through the configured FMCSA API tool.
4. If the carrier is eligible, the agent searches for the requested load.
5. The agent pitches origin, destination, pickup, delivery, equipment, commodity, weight, miles, notes, and listed rate.
6. If the carrier accepts, the agent mocks a transfer to a sales rep.
7. If the carrier counters, the agent calls the external offer evaluation API.
8. The negotiation continues for no more than three rounds.
9. After the call, HappyRobot extracts structured data, classifies outcome and sentiment, and sends the result to the custom dashboard API.

## External Service

The external service provides:

- `POST /api/offers/evaluate`: returns accept, counter, or reject decisions for carrier counter-offers.
- `POST /api/calls/events`: stores notable in-call events.
- `POST /api/calls/summary`: stores post-call extraction and classification results.
- `GET /dashboard`: shows custom metrics for the use case.
- `GET /api/metrics`: returns dashboard metrics as JSON.

All business endpoints require `x-api-key` authentication. Dashboard browser access accepts the same key as `?api_key=...`.

## Metrics

The dashboard reports:

- Total calls
- Booking count and acceptance rate
- Eligible carrier count and eligibility rate
- Average negotiation rounds
- Average spread between listed rate and final accepted rate
- Call outcome breakdown
- Sentiment breakdown
- Offer decision breakdown
- Recent call details

## Security And Deployment

The service is deployed as a Dockerized FastAPI application on Railway. API access is protected with an API key header. Supabase Postgres is used for durable storage through the transaction pooler.
