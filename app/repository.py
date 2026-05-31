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
            notes, transcript, duration_seconds, created_at, updated_at
        )
        VALUES (
            %s, %s, %s, %s, %s,
            %s, %s, %s, %s,
            %s, %s, %s, %s, %s,
            %s, %s, %s, %s,
            %s, %s, %s, %s,
            %s, %s, %s, now(), now()
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
            duration_seconds = EXCLUDED.duration_seconds,
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
            "duration_seconds",
        )),
    )


def _time_filter(days: int | None) -> str:
    if days is None:
        return ""
    return f"AND created_at >= now() - interval '{int(days)} days'"


def get_metrics(days: int | None = None) -> dict[str, Any]:
    tf = _time_filter(days)

    total_calls = int(fetch_value(
        f"SELECT COUNT(*) AS value FROM calls WHERE 1=1 {tf}"
    ) or 0)
    booked_calls = int(fetch_value(
        f"""
        SELECT COUNT(*) AS value FROM calls
        WHERE LOWER(COALESCE(call_outcome, '')) IN ('booked', 'success', 'sucess', 'transferred') {tf}
        """
    ) or 0)
    eligible_calls = int(fetch_value(
        f"""
        SELECT COUNT(*) AS value FROM calls
        WHERE LOWER(COALESCE(carrier_eligibility, '')) IN ('eligible', 'approved', 'active') {tf}
        """
    ) or 0)
    negotiated_calls = int(fetch_value(
        f"""
        SELECT COUNT(*) AS value FROM calls
        WHERE negotiation_rounds > 0 {tf}
        """
    ) or 0)
    load_matched_calls = int(fetch_value(
        f"""
        SELECT COUNT(*) AS value FROM calls
        WHERE load_id IS NOT NULL OR reference_number IS NOT NULL {tf}
        """
    ) or 0)

    avg_rounds = fetch_value(
        f"SELECT AVG(NULLIF(negotiation_rounds, 0)) AS value FROM calls WHERE 1=1 {tf}"
    )
    avg_rate_spread = fetch_value(
        f"""
        SELECT AVG(loadboard_rate - final_rate) AS value FROM calls
        WHERE loadboard_rate IS NOT NULL AND final_rate IS NOT NULL {tf}
        """
    )
    avg_duration = fetch_value(
        f"""
        SELECT AVG(duration_seconds) AS value FROM calls
        WHERE duration_seconds IS NOT NULL AND duration_seconds > 0 {tf}
        """
    )

    # Revenue metrics (for booked calls only)
    total_booked_revenue = fetch_value(
        f"""
        SELECT COALESCE(SUM(final_rate), 0) AS value FROM calls
        WHERE LOWER(COALESCE(call_outcome, '')) IN ('booked', 'success', 'transferred')
          AND final_rate IS NOT NULL {tf}
        """
    )
    negotiation_savings = fetch_value(
        f"""
        SELECT COALESCE(SUM(offer_rate - final_rate), 0) AS value FROM calls
        WHERE LOWER(COALESCE(call_outcome, '')) IN ('booked', 'success', 'transferred')
          AND offer_rate IS NOT NULL AND final_rate IS NOT NULL
          AND offer_rate > final_rate {tf}
        """
    )

    outcome_counts = fetch_all(
        f"""
        SELECT COALESCE(call_outcome, 'unclassified') AS name, COUNT(*)::int AS count
        FROM calls WHERE 1=1 {tf}
        GROUP BY COALESCE(call_outcome, 'unclassified')
        ORDER BY count DESC, name ASC
        """
    )
    sentiment_counts = fetch_all(
        f"""
        SELECT COALESCE(carrier_sentiment, 'unclassified') AS name, COUNT(*)::int AS count
        FROM calls WHERE 1=1 {tf}
        GROUP BY COALESCE(carrier_sentiment, 'unclassified')
        ORDER BY count DESC, name ASC
        """
    )
    offer_decisions = fetch_all(
        f"""
        SELECT decision AS name, COUNT(*)::int AS count
        FROM offer_evaluations WHERE 1=1 {tf.replace('created_at', 'offer_evaluations.created_at')}
        GROUP BY decision
        ORDER BY count DESC, name ASC
        """
    )
    decline_reasons = fetch_all(
        f"""
        SELECT COALESCE(decline_reason, 'unspecified') AS name, COUNT(*)::int AS count
        FROM calls
        WHERE LOWER(COALESCE(call_outcome, '')) NOT IN ('booked', 'success', 'transferred')
          AND decline_reason IS NOT NULL {tf}
        GROUP BY COALESCE(decline_reason, 'unspecified')
        ORDER BY count DESC, name ASC
        LIMIT 8
        """
    )

    # Daily call volume (last 14 days always, regardless of filter)
    calls_per_day = fetch_all(
        """
        SELECT created_at::date::text AS day, COUNT(*)::int AS count
        FROM calls
        WHERE created_at >= now() - interval '14 days'
        GROUP BY created_at::date
        ORDER BY created_at::date ASC
        """
    )

    recent_calls = fetch_all(
        f"""
        SELECT call_id, carrier_name, mc_number, load_id, origin, destination,
               loadboard_rate, final_rate, negotiation_rounds, call_outcome,
               carrier_sentiment, duration_seconds, updated_at
        FROM calls WHERE 1=1 {tf}
        ORDER BY updated_at DESC
        LIMIT 10
        """
    )

    # Unique carriers
    unique_carriers = int(fetch_value(
        f"""
        SELECT COUNT(DISTINCT mc_number) AS value FROM calls
        WHERE mc_number IS NOT NULL {tf}
        """
    ) or 0)

    return {
        "total_calls": total_calls,
        "booked_calls": booked_calls,
        "eligible_calls": eligible_calls,
        "negotiated_calls": negotiated_calls,
        "load_matched_calls": load_matched_calls,
        "acceptance_rate": booked_calls / total_calls if total_calls else 0,
        "eligibility_rate": eligible_calls / total_calls if total_calls else 0,
        "avg_rounds": avg_rounds,
        "avg_rate_spread": avg_rate_spread,
        "avg_duration": avg_duration,
        "total_booked_revenue": float(total_booked_revenue or 0),
        "negotiation_savings": float(negotiation_savings or 0),
        "unique_carriers": unique_carriers,
        "outcome_counts": outcome_counts,
        "sentiment_counts": sentiment_counts,
        "offer_decisions": offer_decisions,
        "decline_reasons": decline_reasons,
        "calls_per_day": calls_per_day,
        "recent_calls": recent_calls,
    }
