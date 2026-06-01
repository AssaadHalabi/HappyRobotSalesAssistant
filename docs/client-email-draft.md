# Email Draft To Prospect Client

Subject: Inbound Carrier Sales Automation — Ready for Demo

Hi Carlos,

I wanted to share a quick update ahead of our walkthrough.

The inbound carrier sales workflow is fully built and live. Carriers can call in through the web call trigger, the agent verifies their MC number with FMCSA, retrieves load details, pitches the load conversationally, and handles up to three rounds of rate negotiation — all automated.

On the infrastructure side, I deployed a FastAPI service on Railway (with a private PostgreSQL database) that enforces configurable pricing policy in real time and powers a custom operational dashboard. The dashboard shows conversion funnel, booked revenue, negotiation savings, sentiment breakdown, and call-level detail — all refreshing live as calls come in.

In the demo, I will walk through:

- A live inbound carrier call (web call trigger)
- MC verification and load lookup
- Counter-offer handling with the external pricing policy
- Post-call extraction and classification (outcome + sentiment)
- The live dashboard with real call data

The dashboard is already accessible at:
https://happyrobotsalesassistant-production.up.railway.app/dashboard

Looking forward to the conversation.

Best,
Assaad
