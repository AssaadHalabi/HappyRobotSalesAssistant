# HappyRobot Configuration Notes

## Boundary Decision

Reuse the existing HappyRobot workflow pieces that already work:

- Web call trigger
- Inbound Voice Agent
- Existing FMCSA carrier lookup AWS webhook
- Existing load lookup AWS webhook

Build externally only where the challenge explicitly asks for differentiated implementation:

- Negotiation decision API (`POST /api/offers/evaluate`)
- Post-call summary ingestion (`POST /api/calls/summary`)
- Custom metrics dashboard (`GET /dashboard`)
- Dockerized Railway deployment story

This avoids duplicating the existing AWS FMCSA/load services and keeps the demo focused on the missing product surface.

## Workflow Structure (14 nodes)

```
Web call (trigger)
└── Inbound Voice Agent ("Paul", gpt-4.1)
    ├── Prompt
    │   ├── verify_carrier (tool) → GET MC Number (FMCSA webhook)
    │   ├── find_available_loads (tool) → GET load (Loads webhook)
    │   ├── evaluate_offer (tool) → POST Evaluate Offer (Railway API)
    │   └── transfer_to_colleague (tool, fixed mock message)
    └── [Post-Agent Pipeline]
        Classify Outcome → Classify Sentiment → Extract (13 fields)
            └── POST Call Summary (Railway API)
```

## evaluate_offer Tool

Method: `POST`

URL:

```text
https://happyrobotsalesassistant-production.up.railway.app/api/offers/evaluate
```

Headers:

```text
x-api-key: GENERATED_HAPPYROBOT_API_KEY
content-type: application/json
```

Request body:

```json
{
  "loadboard_rate": "{{evaluate_offer.loadboard_rate}}",
  "offer_rate": "{{evaluate_offer.offer_rate}}",
  "negotiation_round": "{{evaluate_offer.negotiation_round}}",
  "call_id": "{{Inbound Voice Agent.session_id}}",
  "reference_number": "{{evaluate_offer.reference_number}}"
}
```

Expected response:

```json
{
  "decision": "counter",
  "counter_rate": 2550,
  "accepted_rate": null,
  "walkaway_rate": 2646,
  "next_action": "ask_carrier_to_accept_counter",
  "say": "I cannot get to $2,700. The best I can do right now is $2,550. Does that work?"
}
```

## POST Call Summary (after Extract node)

Method: `POST`

URL:

```text
https://happyrobotsalesassistant-production.up.railway.app/api/calls/summary
```

Headers:

```text
x-api-key: GENERATED_HAPPYROBOT_API_KEY
content-type: application/json
```

Request body:

```json
{
  "call_id": "{{Inbound Voice Agent.session_id}}",
  "transcript": "{{Inbound Voice Agent.transcript}}",
  "duration_seconds": "{{Inbound Voice Agent.duration}}",
  "call_outcome": "{{Classify Outcome.response.classification}}",
  "carrier_sentiment": "{{Classify Sentiment.response.classification}}",
  "reference_number": "{{Extract.response.reference_number}}",
  "mc_number": "{{Extract.response.mc_number}}",
  "carrier_name": "{{Extract.response.carrier_name}}",
  "booking_decision": "{{Extract.response.booking_decision}}",
  "decline_reason": "{{Extract.response.decline_reason}}",
  "final_rate": "{{Extract.response.final_rate}}",
  "origin": "{{Extract.response.origin}}",
  "destination": "{{Extract.response.destination}}",
  "loadboard_rate": "{{Extract.response.loadboard_rate}}",
  "offer_rate": "{{Extract.response.offer_rate}}",
  "negotiation_rounds": "{{Extract.response.negotiation_rounds}}",
  "equipment_type": "{{Extract.response.equipment_type}}",
  "carrier_eligibility": "{{Extract.response.carrier_eligibility}}"
}
```

## Call Outcome Classifier

Tags:

- `Success`: carrier agreed to book and transfer was mocked successfully.
- `Rate too high`: carrier declined because rate did not work after negotiation.
- `Not interested`: carrier declined for a non-rate reason.

## Sentiment Classifier

Tags:

- `Positive`: cooperative, friendly, enthusiastic.
- `Neutral`: professional, business-like, no strong emotion.
- `Negative`: dissatisfied, dismissive, unhappy.
- `Frustrated`: impatient, angry, upset about rates/process.
