from __future__ import annotations

from contextlib import contextmanager
from decimal import Decimal
from pathlib import Path
from typing import Any, Iterator

from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

from app.config import get_settings


_pool: ConnectionPool | None = None
_schema_ready = False
EXPECTED_TABLES = ("calls", "call_events", "offer_evaluations", "api_keys")


def get_pool() -> ConnectionPool:
    global _pool
    if _pool is not None:
        return _pool

    settings = get_settings()
    if not settings.database_url:
        raise RuntimeError("DATABASE_URL is not configured.")

    _pool = ConnectionPool(
        conninfo=settings.database_url,
        min_size=settings.pg_pool_min,
        max_size=settings.pg_pool_max,
        kwargs={"autocommit": True, "row_factory": dict_row, "prepare_threshold": None},
        open=True,
    )
    return _pool


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
