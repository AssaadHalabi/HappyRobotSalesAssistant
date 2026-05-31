from __future__ import annotations

from typing import Any

from app.config import get_settings
from app.utils import integer, pick, required_number, text


def money(value: float) -> str:
    return f"${round(value):,}"


def evaluate_offer_policy(payload: dict[str, Any]) -> dict[str, Any]:
    loadboard_rate = required_number(pick(payload, "loadboard_rate", "listed_rate"), "loadboard_rate")
    offer_rate = required_number(pick(payload, "offer_rate", "carrier_offer", "counter_offer"), "offer_rate")
    negotiation_round = max(1, min(3, integer(pick(payload, "negotiation_round", "round"), "negotiation_round", 1)))

    max_pct = get_settings().max_rate_above_loadboard_pct / 100
    round_authority_share = {1: 0.25, 2: 0.625, 3: 1.0}
    walkaway_rate = round(loadboard_rate * (1 + max_pct), 2)
    acceptable_rate = round(loadboard_rate * (1 + max_pct * round_authority_share[negotiation_round]), 2)

    counter_rate = None
    accepted_rate = None
    transfer_message = None

    if offer_rate <= acceptable_rate:
        decision = "accept"
        accepted_rate = round(offer_rate, 2)
        reason = f"Offer is within round {negotiation_round} authority."
        next_action = "mock_transfer"
        transfer_message = "Transfer was successful and now you can wrap up the conversation."
        say = f"We can make {money(accepted_rate)} work. {transfer_message}"
    elif negotiation_round < 3:
        decision = "counter"
        counter_rate = acceptable_rate
        reason = f"Offer is above round {negotiation_round} authority but still negotiable."
        next_action = "ask_carrier_to_accept_counter"
        say = f"I cannot get to {money(offer_rate)}. The best I can do right now is {money(counter_rate)}. Does that work?"
    elif offer_rate <= walkaway_rate:
        decision = "accept"
        accepted_rate = round(offer_rate, 2)
        reason = "Final-round offer is within walkaway authority."
        next_action = "mock_transfer"
        transfer_message = "Transfer was successful and now you can wrap up the conversation."
        say = f"We can make {money(accepted_rate)} work. {transfer_message}"
    else:
        decision = "reject"
        reason = "Final-round offer is above walkaway authority."
        next_action = "end_call_politely"
        say = "I am sorry, we cannot make the rate work on this load today."

    return {
        "call_id": text(pick(payload, "call_id", "conversation_id")),
        "load_id": text(pick(payload, "load_id")),
        "reference_number": text(pick(payload, "reference_number")),
        "loadboard_rate": round(loadboard_rate, 2),
        "offer_rate": round(offer_rate, 2),
        "negotiation_round": negotiation_round,
        "decision": decision,
        "counter_rate": counter_rate,
        "accepted_rate": accepted_rate,
        "walkaway_rate": walkaway_rate,
        "reason": reason,
        "next_action": next_action,
        "say": say,
        "transfer_message": transfer_message,
    }
