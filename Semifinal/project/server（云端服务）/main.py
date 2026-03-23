"""Life Reflex Arc – Production-ready FastAPI server.

Entry point: uvicorn main:app --host 0.0.0.0 --port 8080
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import v1_router
from app.config import get_settings
from app.database import init_db
from app.redis_client import init_redis
from app.ws.handler import ws_incident_handler

logging.basicConfig(
    level=logging.DEBUG if get_settings().debug else logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting Life Reflex Arc server…")
    await init_redis(settings.redis_url)
    await init_db()
    logger.info("Server ready. API docs: http://localhost:8080/docs")
    yield


app = FastAPI(
    title=settings.app_name,
    description="Distributed Emergency Response System – Life Reflex Arc",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# ---------------------------------------------------------------------------
# CORS
# ---------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

@app.get("/health", tags=["health"])
async def health() -> dict:
    return {"ok": True, "service": settings.app_name}


# ---------------------------------------------------------------------------
# v1 REST API
# ---------------------------------------------------------------------------

app.include_router(v1_router)

# ---------------------------------------------------------------------------
# Legacy compatibility routes (no /api/v1 prefix) – kept for existing clients
# that still connect to the old demo endpoints.
# ---------------------------------------------------------------------------
from app.api.v1.incidents import router as _inc_router  # noqa: E402
from app.api.v1.auth import router as _auth_router  # noqa: E402
from fastapi import APIRouter as _Router  # noqa: E402

_legacy = _Router(tags=["legacy"])

# Mount incident routes at legacy paths (without /api/v1)
for route in _inc_router.routes:
    _legacy.routes.append(route)

app.include_router(_legacy)

# ---------------------------------------------------------------------------
# WebSocket endpoint
# ---------------------------------------------------------------------------

@app.websocket("/ws")
async def ws_endpoint(websocket: WebSocket, incidentId: str) -> None:
    await ws_incident_handler(websocket, incidentId)
