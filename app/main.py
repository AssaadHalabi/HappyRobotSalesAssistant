from __future__ import annotations

import logging
import sys
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from json import JSONDecodeError
from typing import Annotated, Any

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, RedirectResponse

from app.api_keys import create_api_key, has_active_admin_key, list_api_keys, revoke_api_key, validate_api_key
from app.calls import build_call_event, build_call_summary
from app.config import get_settings
from app.dashboard import render_dashboard
from app.database import close_pool, database_status, ensure_schema
from app.pricing import evaluate_offer_policy
from app.repository import get_metrics, store_call_event, store_offer_evaluation, upsert_call_summary

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    settings = get_settings()
    if settings.environment == "production" and (
        settings.admin_bootstrap_token == "dev-admin-bootstrap-token"
        or settings.api_key_pepper == "dev-api-key-pepper"
    ):
        raise RuntimeError("ADMIN_BOOTSTRAP_TOKEN and API_KEY_PEPPER must be configured in production.")

    if settings.database_url:
        logger.info("Connecting to database...")
        try:
            ensure_schema()
            logger.info("Database schema ready.")
        except Exception:
            logger.exception("Database initialization failed — service will start but DB operations will error.")
    else:
        logger.warning("DATABASE_URL not set — running without persistence.")

    yield
    close_pool()
    logger.info("Connection pool closed.")


app = FastAPI(
    title="HappyRobot Inbound Carrier Sales API",
    version="1.0.0",
    description="Railway-hosted FastAPI service for carrier offer evaluation, call ingestion, and custom metrics.",
    lifespan=lifespan,
)

settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["content-type", "x-api-key", "x-admin-key", "x-bootstrap-token", "authorization"],
)


def require_happyrobot_api_key(
    x_api_key: Annotated[str | None, Header(alias="x-api-key")] = None,
    authorization: Annotated[str | None, Header()] = None,
    api_key: Annotated[str | None, Query()] = None,
) -> None:
    bearer = authorization[7:].strip() if authorization and authorization.lower().startswith("bearer ") else None
    supplied = x_api_key or bearer or api_key
    if not validate_api_key(supplied, required_scope="happyrobot"):
        raise HTTPException(status_code=401, detail="Missing or invalid API key.")


def require_admin_api_key(
    x_admin_key: Annotated[str | None, Header(alias="x-admin-key")] = None,
    x_api_key: Annotated[str | None, Header(alias="x-api-key")] = None,
    authorization: Annotated[str | None, Header()] = None,
) -> None:
    bearer = authorization[7:].strip() if authorization and authorization.lower().startswith("bearer ") else None
    supplied = x_admin_key or x_api_key or bearer
    if not validate_api_key(supplied, required_scope="admin"):
        raise HTTPException(status_code=401, detail="Missing or invalid admin API key.")


def require_bootstrap_token(
    x_bootstrap_token: Annotated[str | None, Header(alias="x-bootstrap-token")] = None,
    authorization: Annotated[str | None, Header()] = None,
) -> None:
    expected = get_settings().admin_bootstrap_token
    bearer = authorization[7:].strip() if authorization and authorization.lower().startswith("bearer ") else None
    supplied = x_bootstrap_token or bearer
    if not supplied or supplied != expected:
        raise HTTPException(status_code=401, detail="Missing or invalid bootstrap token.")


async def read_json_object(request: Request) -> dict[str, Any]:
    try:
        payload = await request.json()
    except JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail="Request body must be valid JSON.") from exc
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="Request JSON body must be an object.")
    return payload


@app.get("/")
def root(api_key: str | None = None) -> RedirectResponse:
    suffix = f"?api_key={api_key}" if api_key else ""
    return RedirectResponse(url=f"/dashboard{suffix}", status_code=302)


@app.get("/health")
def health() -> dict[str, Any]:
    return {
        "ok": True,
        "service": "happyrobot-carrier-sales",
        "runtime": "fastapi-railway",
        "time": datetime.now(timezone.utc).isoformat(),
    }


@app.post("/api/admin/database/init", dependencies=[Depends(require_bootstrap_token)])
def initialize_database() -> dict[str, Any]:
    try:
        return ensure_schema(force=True)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Database initialization failed: {exc}") from exc


@app.get("/api/admin/database/status", dependencies=[Depends(require_bootstrap_token)])
def get_database_status() -> dict[str, Any]:
    try:
        return database_status()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Database status check failed: {exc}") from exc


@app.post("/api/admin/bootstrap-key", dependencies=[Depends(require_bootstrap_token)])
async def bootstrap_admin_key(request: Request) -> dict[str, Any]:
    if has_active_admin_key():
        raise HTTPException(status_code=409, detail="An active admin API key already exists.")

    payload = await read_json_object(request)
    name = str(payload.get("name") or "primary-admin").strip()
    if not name:
        raise HTTPException(status_code=400, detail="name is required.")
    expires_at = payload.get("expires_at")
    return create_api_key(name=name, expires_at=str(expires_at) if expires_at else None, scopes=["admin"])


@app.post("/api/admin/api-keys", dependencies=[Depends(require_admin_api_key)])
async def create_key(request: Request) -> dict[str, Any]:
    payload = await read_json_object(request)
    name = str(payload.get("name") or "happyrobot-workflow").strip()
    if not name:
        raise HTTPException(status_code=400, detail="name is required.")
    expires_at = payload.get("expires_at")
    scopes = payload.get("scopes")
    if scopes is not None and not isinstance(scopes, list):
        raise HTTPException(status_code=400, detail="scopes must be a list of strings.")
    try:
        return create_api_key(
            name=name,
            expires_at=str(expires_at) if expires_at else None,
            scopes=[str(scope) for scope in scopes] if scopes else None,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/admin/api-keys", dependencies=[Depends(require_admin_api_key)])
def get_keys() -> dict[str, Any]:
    return {"api_keys": list_api_keys()}


@app.delete("/api/admin/api-keys/{key_id}", dependencies=[Depends(require_admin_api_key)])
def revoke_key(key_id: int) -> dict[str, Any]:
    revoked = revoke_api_key(key_id)
    if not revoked:
        raise HTTPException(status_code=404, detail="Active API key not found.")
    return {"revoked": True, "id": key_id}


@app.post("/api/offers/evaluate", dependencies=[Depends(require_happyrobot_api_key)])
async def evaluate_offer(request: Request) -> dict[str, Any]:
    payload = await read_json_object(request)
    result = evaluate_offer_policy(payload)
    store_offer_evaluation(result)
    return result


@app.post("/api/calls/events", dependencies=[Depends(require_happyrobot_api_key)])
async def create_call_event(request: Request) -> dict[str, Any]:
    payload = await read_json_object(request)
    event = build_call_event(payload)
    store_call_event(payload, event["call_id"], event["event_type"])
    return {"stored": True, **event}


@app.post("/api/calls/summary", dependencies=[Depends(require_happyrobot_api_key)])
async def create_call_summary(request: Request) -> dict[str, Any]:
    payload = await read_json_object(request)
    record = build_call_summary(payload)
    upsert_call_summary(record)
    return {
        "stored": True,
        "call_id": record["call_id"],
        "call_outcome": record["call_outcome"],
        "carrier_sentiment": record["carrier_sentiment"],
    }


@app.get("/api/metrics", dependencies=[Depends(require_happyrobot_api_key)])
def metrics() -> dict[str, Any]:
    data = get_metrics()
    data["generated_at"] = datetime.now(timezone.utc).isoformat()
    return data


@app.get("/dashboard", response_class=HTMLResponse, dependencies=[Depends(require_happyrobot_api_key)])
def dashboard() -> HTMLResponse:
    data = get_metrics()
    data["generated_at"] = datetime.now(timezone.utc).isoformat()
    return HTMLResponse(render_dashboard(data))
