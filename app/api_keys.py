from __future__ import annotations

import hashlib
import hmac
import secrets
from typing import Any

from app.config import get_settings
from app.database import execute, fetch_all


KEY_PREFIX = "hr_live_"
LOOKUP_PREFIX_LENGTH = 18
ALLOWED_SCOPES = {"admin", "happyrobot"}


def generate_api_key() -> str:
    return f"{KEY_PREFIX}{secrets.token_urlsafe(32)}"


def lookup_prefix(api_key: str) -> str:
    return api_key[:LOOKUP_PREFIX_LENGTH]


def hash_api_key(api_key: str) -> str:
    pepper = get_settings().api_key_pepper
    return hmac.new(pepper.encode("utf-8"), api_key.encode("utf-8"), hashlib.sha256).hexdigest()


def create_api_key(name: str, expires_at: str | None = None, scopes: list[str] | None = None) -> dict[str, Any]:
    api_key = generate_api_key()
    prefix = lookup_prefix(api_key)
    key_hash = hash_api_key(api_key)
    normalized_scopes = normalize_scopes(scopes)

    rows = fetch_all(
        """
        INSERT INTO api_keys (name, prefix, key_hash, scopes, expires_at, active, created_at)
        VALUES (%s, %s, %s, %s, %s::timestamptz, true, now())
        RETURNING id, name, prefix, scopes, active, expires_at, created_at, last_used_at
        """,
        (name, prefix, key_hash, normalized_scopes, expires_at),
    )
    record = rows[0]
    return {**record, "api_key": api_key}


def normalize_scopes(scopes: list[str] | None) -> list[str]:
    normalized = sorted({str(scope).strip().lower() for scope in (scopes or ["happyrobot"]) if str(scope).strip()})
    invalid_scopes = sorted(set(normalized) - ALLOWED_SCOPES)
    if invalid_scopes:
        raise ValueError(f"Invalid API key scopes: {', '.join(invalid_scopes)}")
    return normalized or ["happyrobot"]


def list_api_keys() -> list[dict[str, Any]]:
    return fetch_all(
        """
        SELECT id, name, prefix, scopes, active, expires_at, created_at, last_used_at
        FROM api_keys
        ORDER BY created_at DESC
        """
    )


def revoke_api_key(key_id: int) -> bool:
    rows = fetch_all(
        """
        UPDATE api_keys
        SET active = false
        WHERE id = %s AND active = true
        RETURNING id
        """,
        (key_id,),
    )
    return bool(rows)


def has_active_admin_key() -> bool:
    rows = fetch_all(
        """
        SELECT id
        FROM api_keys
        WHERE active = true
          AND 'admin' = ANY(scopes)
          AND (expires_at IS NULL OR expires_at > now())
        LIMIT 1
        """
    )
    return bool(rows)


def validate_api_key(api_key: str | None, required_scope: str) -> bool:
    if not api_key:
        return False

    prefix = lookup_prefix(api_key)
    supplied_hash = hash_api_key(api_key)
    rows = fetch_all(
        """
        SELECT id, key_hash, scopes
        FROM api_keys
        WHERE prefix = %s
          AND active = true
          AND (expires_at IS NULL OR expires_at > now())
        LIMIT 1
        """,
        (prefix,),
    )
    if not rows:
        return False

    record = rows[0]
    if not hmac.compare_digest(str(record["key_hash"]), supplied_hash):
        return False

    scopes = set(record.get("scopes") or [])
    if required_scope not in scopes and "admin" not in scopes:
        return False

    execute("UPDATE api_keys SET last_used_at = now() WHERE id = %s", (record["id"],))
    return True
