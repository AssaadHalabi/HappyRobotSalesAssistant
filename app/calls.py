from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from app.utils import integer, normalize_tag, number_value, pick, text


def unpack_summary(payload: dict[str, Any]) -> dict[str, Any]:
    data = dict(payload)
    for key in ("extract", "extracted", "fields", "data"):
        nested = payload.get(key)
        if isinstance(nested, dict):
            data.update(nested)
    for key in ("classification", "classify", "classifiers", "analysis"):
        nested = payload.get(key)
        if isinstance(nested, dict):
            data.update(nested)
    return data


def build_call_summary(payload: dict[str, Any]) -> dict[str, Any]:
    data = unpack_summary(payload)
    duration = pick(data, "duration_seconds", "duration", "call_duration")
    if duration is not None:
        try:
            duration = int(float(str(duration).strip()))
        except (TypeError, ValueError):
            duration = None

    now = datetime.now(timezone.utc).isoformat()

    return {
        "call_id": text(pick(data, "call_id", "conversation_id", "session_id")) or str(uuid4()),
        "called_at": now,
        "mc_number": text(pick(data, "mc_number", "mc")),
        "carrier_name": text(pick(data, "carrier_name", "company_name")),
        "carrier_eligibility": normalize_tag(pick(data, "carrier_eligibility", "eligibility_status")),
        "eligibility_reason": text(pick(data, "eligibility_reason", "eligibility_notes")),
        "reference_number": text(pick(data, "reference_number", "load_reference", "load_id")),
        "origin": text(pick(data, "origin")),
        "destination": text(pick(data, "destination")),
        "equipment_type": text(pick(data, "equipment_type", "trailer_type")),
        "loadboard_rate": number_value(pick(data, "loadboard_rate", "listed_rate"), "loadboard_rate"),
        "offer_rate": number_value(pick(data, "offer_rate", "carrier_offer", "initial_offer_rate"), "offer_rate"),
        "final_rate": number_value(pick(data, "final_rate", "agreed_rate", "accepted_rate"), "final_rate"),
        "negotiation_rounds": integer(pick(data, "negotiation_rounds", "rounds"), "negotiation_rounds", 0),
        "transfer_status": normalize_tag(pick(data, "transfer_status")),
        "call_outcome": derive_outcome(data),
        "carrier_sentiment": normalize_tag(pick(data, "carrier_sentiment", "sentiment", "caller_sentiment")),
        "decline_reason": text(pick(data, "decline_reason", "reason")),
        "notes": text(pick(data, "notes", "summary")),
        "transcript": text(pick(data, "transcript")),
        "duration_seconds": duration,
    }


def build_call_event(payload: dict[str, Any]) -> dict[str, str]:
    return {
        "call_id": text(pick(payload, "call_id", "conversation_id", "session_id")) or str(uuid4()),
        "event_type": text(pick(payload, "event_type", "type")) or "event",
    }


def derive_outcome(data: dict[str, Any]) -> str | None:
    explicit = normalize_tag(pick(data, "call_outcome", "outcome", "booking_outcome"))
    if explicit:
        return explicit

    decision = pick(data, "booking_decision", "accepted")
    if isinstance(decision, bool):
        return "booked" if decision else "declined"
    if isinstance(decision, str):
        normalized = decision.strip().lower()
        if normalized in {"yes", "true", "booked", "accepted", "success"}:
            return "booked"
        if normalized in {"no", "false", "declined", "rejected"}:
            return "declined"

    transfer_status = normalize_tag(pick(data, "transfer_status"))
    if transfer_status and "success" in transfer_status:
        return "transferred"

    eligibility = normalize_tag(pick(data, "carrier_eligibility", "eligibility_status"))
    if eligibility in {"ineligible", "not_eligible", "rejected"}:
        return "not_eligible"

    return None
