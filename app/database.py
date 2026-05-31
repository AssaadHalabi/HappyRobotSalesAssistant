from __future__ import annotations

import logging
import time
from contextlib import contextmanager
from decimal import Decimal
from pathlib import Path
from typing import Any, Iterator
from urllib.parse import quote_plus, unquote, urlparse

from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

from app.config import get_settings

logger = logging.getLogger(__name__)

_pool: ConnectionPool | None = None
_schema_ready = False
EXPECTED_TABLES = ("calls", "call_events", "offer_evaluations", "api_keys")

MAX_CONNECT_RETRIES = 5
RETRY_BASE_DELAY_S = 2.0


def normalize_database_url(raw_url: str) -> str:
    """Normalize a DATABASE_URL for psycopg3 compatibility.

    Handles two common Railway/provider issues:
    1. postgres:// scheme → postgresql:// (psycopg3 requirement)
    2. Special characters in password that break URI parsing

    Uses regex-based extraction because stdlib urlparse treats '?' as a netloc
    delimiter, breaking passwords that contain '?' or '@'.
    """
    import re

    url = raw_url.strip()

    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://"):]

    m = re.match(
        r"^(?P<scheme>postgresql)://"
        r"(?P<user>[^:]+):(?P<password>.+)"
        r"@(?P<host>[^/:?]+)"
        r"(?::(?P<port>\d+))?"
        r"(?P<rest>/.*)?$",
        url,
    )
    if not m:
        return url

    user = quote_plus(unquote(m.group("user")))
    password = quote_plus(unquote(m.group("password")))
    host = m.group("host")
    port = f":{m.group('port')}" if m.group("port") else ""
    rest = m.group("rest") or ""

    return f"postgresql://{user}:{password}@{host}{port}{rest}"


def get_pool() -> ConnectionPool:
    global _pool
    if _pool is not None:
        return _pool

    settings = get_settings()
    if not settings.database_url:
        raise RuntimeError("DATABASE_URL is not configured.")

    conninfo = normalize_database_url(settings.database_url)
    logger.info("Initializing connection pool (host=%s)", urlparse(conninfo).hostname)

    pool = ConnectionPool(
        conninfo=conninfo,
        min_size=settings.pg_pool_min,
        max_size=settings.pg_pool_max,
        kwargs={"autocommit": True, "row_factory": dict_row, "prepare_threshold": None},
        open=False,
    )

    for attempt in range(1, MAX_CONNECT_RETRIES + 1):
        try:
            pool.open(wait=True, timeout=10.0)
            pool.check()
            logger.info("Connection pool ready (attempt %d/%d)", attempt, MAX_CONNECT_RETRIES)
            _pool = pool
            return _pool
        except Exception as exc:
            if attempt == MAX_CONNECT_RETRIES:
                logger.error("Failed to connect after %d attempts: %s", MAX_CONNECT_RETRIES, exc)
                raise RuntimeError(
                    f"Could not establish database connection after {MAX_CONNECT_RETRIES} attempts: {exc}"
                ) from exc
            delay = RETRY_BASE_DELAY_S * (2 ** (attempt - 1))
            logger.warning(
                "Connection attempt %d/%d failed (%s), retrying in %.1fs...",
                attempt, MAX_CONNECT_RETRIES, exc, delay,
            )
            time.sleep(delay)

    raise RuntimeError("Unreachable")


@contextmanager
def connection() -> Iterator[Any]:
    with get_pool().connection() as conn:
        yield conn


def ensure_schema(force: bool = False) -> dict[str, Any]:
    global _schema_ready
    if _schema_ready and not force:
        return {"schema_ready": True, "statements_executed": 0, "tables": table_status()}
    schema_sql = (Path(__file__).resolve().parent.parent / "db" / "schema.sql").read_text(encoding="utf-8")
    statements = split_sql_statements(schema_sql)
    with connection() as conn:
        for statement in statements:
            conn.execute(statement)
    _schema_ready = True
    return {"schema_ready": True, "statements_executed": len(statements), "tables": table_status()}


def split_sql_statements(schema_sql: str) -> list[str]:
    return [statement.strip() for statement in schema_sql.split(";") if statement.strip()]


def table_status() -> dict[str, bool]:
    with connection() as conn:
        rows = conn.execute(
            """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
              AND table_name = ANY(%s)
            """,
            (list(EXPECTED_TABLES),),
        ).fetchall()
    existing = {row["table_name"] for row in rows}
    return {table: table in existing for table in EXPECTED_TABLES}


def database_status() -> dict[str, Any]:
    with connection() as conn:
        row = conn.execute(
            """
            SELECT
              current_database() AS database,
              current_user AS user_name,
              version() AS version
            """
        ).fetchone()
    return {**normalize_row(row), "tables": table_status()}


def execute(sql: str, params: tuple[Any, ...] = ()) -> None:
    ensure_schema()
    with connection() as conn:
        conn.execute(sql, params)


def fetch_all(sql: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
    ensure_schema()
    with connection() as conn:
        rows = conn.execute(sql, params).fetchall()
    return [normalize_row(row) for row in rows]


def fetch_value(sql: str, params: tuple[Any, ...] = ()) -> Any:
    ensure_schema()
    with connection() as conn:
        row = conn.execute(sql, params).fetchone()
    if not row:
        return None
    return normalize_value(row.get("value"))


def normalize_row(row: dict[str, Any]) -> dict[str, Any]:
    return {key: normalize_value(value) for key, value in row.items()}


def normalize_value(value: Any) -> Any:
    if isinstance(value, Decimal):
        return float(value)
    return value


def close_pool() -> None:
    global _pool
    if _pool is not None:
        _pool.close()
        _pool = None
