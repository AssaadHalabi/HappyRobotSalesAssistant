from __future__ import annotations

import json
from typing import Any

from app.database import execute, fetch_all, fetch_value


def store_offer_evaluation(result: dict[str, Any]) -> None:
    execute(
        """
        INSERT INTO offer_evaluations (
            call_id, load_id, reference_number, loadboard_rate, offer_rate,
            negotiation_round, decision, counter_rate, accepted_rate,
            walkaway_rate, reason, created_at
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, now())
        """,
        (
            result["call_id"],
            result["load_id"],
            result["reference_number"],
            result["loadboard_rate"],
            result["offer_rate"],
            result["negotiation_round"],
            result["decision"],
            result["counter_rate"],
            result["accepted_rate"],
            result["walkaway_rate"],
            result["reason"],
        ),
    )


def store_call_event(payload: dict[str, Any], call_id: str, event_type: str) -> None:
    execute(
        """
        INSERT INTO call_events (call_id, event_type, payload, created_at)
        VALUES (%s, %s, %s::jsonb, now())
        """,
        (call_id, event_type, json.dumps(payload)),
    )


def upsert_call_summary(record: dict[str, Any]) -> None:
    execute(
        """
        INSERT INTO calls (
            call_id, started_at, ended_at, mc_number, carrier_name,
            carrier_eligibility, eligibility_reason, load_id, reference_number,
            origin, destination, pickup_datetime, delivery_datetime, equipment_type,
            loadboard_rate, offer_rate, final_rate, negotiation_rounds,
            transfer_status, call_outcome, carrier_sentiment, decline_reason,
            notes, transcript, created_at, updated_at
        )
        VALUES (
            %s, %s, %s, %s, %s,
            %s, %s, %s, %s,
            %s, %s, %s, %s, %s,
            %s, %s, %s, %s,
            %s, %s, %s, %s,
            %s, %s, now(), now()
        )
        ON CONFLICT (call_id) DO UPDATE SET
            started_at = EXCLUDED.started_at,
            ended_at = EXCLUDED.ended_at,
            mc_number = EXCLUDED.mc_number,
            carrier_name = EXCLUDED.carrier_name,
            carrier_eligibility = EXCLUDED.carrier_eligibility,
            eligibility_reason = EXCLUDED.eligibility_reason,
            load_id = EXCLUDED.load_id,
            reference_number = EXCLUDED.reference_number,
            origin = EXCLUDED.origin,
            destination = EXCLUDED.destination,
            pickup_datetime = EXCLUDED.pickup_datetime,
            delivery_datetime = EXCLUDED.delivery_datetime,
            equipment_type = EXCLUDED.equipment_type,
            loadboard_rate = EXCLUDED.loadboard_rate,
            offer_rate = EXCLUDED.offer_rate,
            final_rate = EXCLUDED.final_rate,
            negotiation_rounds = EXCLUDED.negotiation_rounds,
            transfer_status = EXCLUDED.transfer_status,
            call_outcome = EXCLUDED.call_outcome,
            carrier_sentiment = EXCLUDED.carrier_sentiment,
            decline_reason = EXCLUDED.decline_reason,
            notes = EXCLUDED.notes,
            transcript = EXCLUDED.transcript,
            updated_at = now()
        """,
        tuple(record[key] for key in (
            "call_id",
            "started_at",
            "ended_at",
            "mc_number",
            "carrier_name",
            "carrier_eligibility",
            "eligibility_reason",
            "load_id",
            "reference_number",
            "origin",
            "destination",
            "pickup_datetime",
            "delivery_datetime",
            "equipment_type",
            "loadboard_rate",
            "offer_rate",
            "final_rate",
            "negotiation_rounds",
            "transfer_status",
            "call_outcome",
            "carrier_sentiment",
            "decline_reason",
            "notes",
            "transcript",
        )),
    )


def get_metrics() -> dict[str, Any]:
    total_calls = int(fetch_value("SELECT COUNT(*) AS value FROM calls") or 0)
    booked_calls = int(fetch_value(
        """
        SELECT COUNT(*) AS value
        FROM calls
        WHERE LOWER(COALESCE(call_outcome, '')) IN ('booked', 'success', 'transferred')
        """
    ) or 0)
    eligible_calls = int(fetch_value(
        """
        SELECT COUNT(*) AS value
        FROM calls
        WHERE LOWER(COALESCE(carrier_eligibility, '')) IN ('eligible', 'approved', 'active')
        """
    ) or 0)
    avg_rounds = fetch_value("SELECT AVG(NULLIF(negotiation_rounds, 0)) AS value FROM calls")
    avg_rate_spread = fetch_value(
        """
        SELECT AVG(loadboard_rate - final_rate) AS value
        FROM calls
        WHERE loadboard_rate IS NOT NULL AND final_rate IS NOT NULL
        """
    )

    outcome_counts = fetch_all(
        """
        SELECT COALESCE(call_outcome, 'unclassified') AS name, COUNT(*)::int AS count
        FROM calls
        GROUP BY COALESCE(call_outcome, 'unclassified')
        ORDER BY count DESC, name ASC
        """
    )
    sentiment_counts = fetch_all(
        """
        SELECT COALESCE(carrier_sentiment, 'unclassified') AS name, COUNT(*)::int AS count
        FROM calls
        GROUP BY COALESCE(carrier_sentiment, 'unclassified')
        ORDER BY count DESC, name ASC
        """
    )
    offer_decisions = fetch_all(
        """
        SELECT decision AS name, COUNT(*)::int AS count
        FROM offer_evaluations
        GROUP BY decision
        ORDER BY count DESC, name ASC
        """
    )
    recent_calls = fetch_all(
        """
        SELECT call_id, carrier_name, mc_number, load_id, origin, destination,
               loadboard_rate, final_rate, negotiation_rounds, call_outcome,
               carrier_sentiment, updated_at
        FROM calls
        ORDER BY updated_at DESC
        LIMIT 10
        """
    )

    return {
        "total_calls": total_calls,
        "booked_calls": booked_calls,
        "eligible_calls": eligible_calls,
        "acceptance_rate": booked_calls / total_calls if total_calls else 0,
        "eligibility_rate": eligible_calls / total_calls if total_calls else 0,
        "avg_rounds": avg_rounds,
        "avg_rate_spread": avg_rate_spread,
        "outcome_counts": outcome_counts,
        "sentiment_counts": sentiment_counts,
        "offer_decisions": offer_decisions,
        "recent_calls": recent_calls,
    }
