from __future__ import annotations

from typing import Any

from fastapi import HTTPException


def pick(data: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        value = data.get(key)
        if value not in (None, ""):
            return value
    return None


def text(value: Any) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip()
    return normalized or None


def number_value(value: Any, field_name: str) -> float | None:
    if value in (None, ""):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        cleaned = value.replace("$", "").replace(",", "").strip()
        if not cleaned:
            return None
        try:
            return float(cleaned)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=f"{field_name} must be numeric.") from exc
    raise HTTPException(status_code=400, detail=f"{field_name} must be numeric.")


def required_number(value: Any, field_name: str) -> float:
    parsed = number_value(value, field_name)
    if parsed is None or parsed <= 0:
        raise HTTPException(status_code=400, detail=f"{field_name} is required and must be greater than zero.")
    return parsed


def integer(value: Any, field_name: str, default: int = 0) -> int:
    if value in (None, ""):
        return default
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=f"{field_name} must be an integer.") from exc


def normalize_tag(value: Any) -> str | None:
    normalized = text(value)
    return normalized.lower().replace(" ", "_") if normalized else None
