from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache


@dataclass(frozen=True)
class Settings:
    admin_bootstrap_token: str
    api_key_pepper: str
    database_url: str | None
    max_rate_above_loadboard_pct: float
    pg_pool_min: int
    pg_pool_max: int
    pg_connect_timeout: int
    allowed_origins: list[str]
    environment: str


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    origins = os.getenv("ALLOWED_ORIGINS", "*")
    return Settings(
        admin_bootstrap_token=os.getenv("ADMIN_BOOTSTRAP_TOKEN", "dev-admin-bootstrap-token"),
        api_key_pepper=os.getenv("API_KEY_PEPPER", "dev-api-key-pepper"),
        database_url=os.getenv("DATABASE_URL"),
        max_rate_above_loadboard_pct=float(os.getenv("MAX_RATE_ABOVE_LOADBOARD_PCT", "8")),
        pg_pool_min=int(os.getenv("PG_POOL_MIN", "1")),
        pg_pool_max=int(os.getenv("PG_POOL_MAX", "5")),
        pg_connect_timeout=int(os.getenv("PG_CONNECT_TIMEOUT", "10")),
        allowed_origins=[origin.strip() for origin in origins.split(",") if origin.strip()],
        environment=os.getenv("ENVIRONMENT", "local"),
    )
