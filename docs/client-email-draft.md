# Email Draft To Prospect Client

Subject: Inbound Carrier Sales Automation - Build Progress Ahead Of Demo

Hi Carlos,

I wanted to share a quick update ahead of our walkthrough.

I have the inbound carrier sales workflow mapped around the web call trigger, with the agent collecting the carrier MC number, checking carrier information through the configured FMCSA integration, retrieving load details from the configured load API, and guiding the carrier through the booking conversation.

The remaining build work is focused on the pieces that matter most for evaluating the operating model: negotiation handling, post-call extraction, outcome and sentiment classification, and a custom dashboard outside of the HappyRobot analytics surface. I am adding an external service that evaluates carrier counter-offers, records call outcomes, and gives the brokerage team a view into booking rate, eligibility rate, rate exceptions, negotiation rounds, and caller sentiment.

In the demo, I will show:

- A web-call inbound carrier conversation
- MC verification and load lookup
- Counter-offer handling with up to three negotiation rounds
- A mocked successful transfer when the rate is agreed
- Post-call extraction and classification
- A custom dashboard with call and offer metrics

Best,
Assaad
