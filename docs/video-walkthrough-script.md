# 5 Minute Walkthrough Script

## 0:00 - 0:45 Setup

Show the HappyRobot workflow named "Inbound Carrier Sales New". Point out the web call trigger, inbound voice agent, existing FMCSA tool, existing load lookup tool, post-call classification, and post-call extraction.

Explain that the existing AWS FMCSA/load APIs are reused, while the custom external service handles negotiation, metrics, and dashboarding.

## 0:45 - 2:30 Demo Call

Start a web call as a carrier.

Cover this path:

- Provide an MC number.
- Confirm the carrier name.
- Provide a load reference number.
- Listen to the load pitch.
- Make a counter-offer.
- Let the agent call the offer evaluation tool.
- Accept the counter or reach an agreed final rate.
- Show the mocked transfer success message.

## 2:30 - 3:30 Post-Call AI

Show the classifier and extraction nodes.

Call out the extracted fields:

- MC number
- Carrier name
- Eligibility
- Load reference
- Lane
- Listed rate
- Carrier offer
- Final rate
- Negotiation rounds
- Transfer status
- Outcome
- Sentiment

## 3:30 - 4:30 Dashboard

Open the custom dashboard.

Highlight:

- Total calls
- Booked calls
- Eligible carriers
- Average rounds
- Outcome breakdown
- Sentiment breakdown
- Recent calls

## 4:30 - 5:00 Deployment

Show the Dockerfile and deployment notes. Explain that `/api/*` endpoints require an API key, cloud HTTPS is handled by the deployment provider, and the service can run locally or in a hosted container.
