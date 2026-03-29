"""Incident service – business logic layer.

Wraps all database operations and state-machine transitions.
Broadcasts state changes via Redis Pub/Sub so that the WebSocket gateway
can fan-out to all connected clients even across multiple processes.
"""
from __future__ import annotations

import asyncio
import json
import logging
import random
import time
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.incident import Incident, IncidentLog, IncidentRole
from app.redis_client import get_redis
from app.schemas.incident import (
    ActionResponse,
    IncidentState,
    JoinResponse,
    LogEntry,
    RoleState,
    RoleStates,
    SosState,
)

settings = get_settings()
logger = logging.getLogger(__name__)

ROLES = ("PRIME", "RUNNER", "GUIDE")
SOS_REDIS_PREFIX = "sos:"
INCIDENT_CHANNEL_PREFIX = "incident:state:"

# Track asyncio SOS tasks per incident (single-process fallback)
_sos_tasks: dict[str, asyncio.Task] = {}


def _now_ms() -> int:
    return int(time.time() * 1000)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _append_log(db: AsyncSession, incident_id: str, msg: str, user_id: Optional[str] = None, action: Optional[str] = None) -> None:
    log = IncidentLog(incident_id=incident_id, msg=msg, user_id=user_id, action=action)
    db.add(log)


async def _get_incident_or_404(db: AsyncSession, incident_id: str) -> Incident:
    result = await db.execute(
        select(Incident).where(Incident.id == incident_id)
    )
    incident = result.scalar_one_or_none()
    if not incident:
        raise ValueError(f"Incident {incident_id} not found")
    return incident


async def _load_incident_state(db: AsyncSession, incident: Incident) -> IncidentState:
    """Convert ORM Incident → IncidentState schema."""
    # Eager-load roles and logs if not already loaded
    roles_result = await db.execute(
        select(IncidentRole).where(IncidentRole.incident_id == incident.id)
    )
    roles = roles_result.scalars().all()

    logs_result = await db.execute(
        select(IncidentLog)
        .where(IncidentLog.incident_id == incident.id)
        .order_by(IncidentLog.ts)
    )
    logs = logs_result.scalars().all()

    role_map: dict[str, RoleState] = {r: RoleState() for r in ROLES}
    for r in roles:
        role_map[r.role] = RoleState(status=r.status, userId=r.user_id)

    # Read SOS state from Redis
    redis = get_redis()
    sos_raw = await redis.get(f"{SOS_REDIS_PREFIX}{incident.id}")
    if sos_raw:
        sos_data = json.loads(sos_raw)
        sos = SosState(**sos_data)
    else:
        sos = SosState(status="MONITORING", durationSec=settings.sos_duration_sec)

    return IncidentState(
        incidentId=incident.id,
        phase=incident.phase,
        sos=sos,
        roles=RoleStates(**role_map),
        logs=[
            LogEntry(ts=int(log.ts.timestamp() * 1000), msg=log.msg)
            for log in logs
        ],
    )


async def _broadcast(incident_id: str, state: IncidentState) -> None:
    """Publish state to Redis channel for WebSocket gateway fan-out."""
    redis = get_redis()
    payload = json.dumps({"type": "STATE", "payload": state.model_dump()})
    await redis.publish(f"{INCIDENT_CHANNEL_PREFIX}{incident_id}", payload)


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------

# In-memory cache for "current incident" (single-process mode)
_current_incident_id: Optional[str] = None


async def create_incident(db: AsyncSession, lat: Optional[float] = None, lng: Optional[float] = None) -> IncidentState:
    global _current_incident_id
    incident = Incident(phase="CREATED", lat=lat, lng=lng)
    db.add(incident)
    await db.flush()
    await _append_log(db, incident.id, "Incident created")
    await db.commit()
    await db.refresh(incident)
    _current_incident_id = incident.id
    state = await _load_incident_state(db, incident)
    return state


async def get_current_incident(db: AsyncSession) -> IncidentState:
    global _current_incident_id
    if _current_incident_id:
        result = await db.execute(select(Incident).where(Incident.id == _current_incident_id))
        incident = result.scalar_one_or_none()
        if incident:
            return await _load_incident_state(db, incident)
    # Auto-create if none
    return await create_incident(db)


async def get_incident(db: AsyncSession, incident_id: str) -> IncidentState:
    incident = await _get_incident_or_404(db, incident_id)
    return await _load_incident_state(db, incident)


async def reset_current_incident(db: AsyncSession) -> IncidentState:
    global _current_incident_id
    if not _current_incident_id:
        return await create_incident(db)

    result = await db.execute(select(Incident).where(Incident.id == _current_incident_id))
    incident = result.scalar_one_or_none()
    if not incident:
        return await create_incident(db)

    # Cancel SOS task
    _cancel_sos_task(_current_incident_id)
    redis = get_redis()
    await redis.delete(f"{SOS_REDIS_PREFIX}{incident.id}")

    incident.phase = "CREATED"

    # Remove existing roles and logs
    await db.execute(
        IncidentRole.__table__.delete().where(IncidentRole.incident_id == incident.id)
    )
    await db.execute(
        IncidentLog.__table__.delete().where(IncidentLog.incident_id == incident.id)
    )
    await _append_log(db, incident.id, "Incident reset")
    await db.commit()
    await db.refresh(incident)

    state = await _load_incident_state(db, incident)
    await _broadcast(incident.id, state)
    return state


# ---------------------------------------------------------------------------
# SOS
# ---------------------------------------------------------------------------

def _cancel_sos_task(incident_id: str) -> None:
    task = _sos_tasks.pop(incident_id, None)
    if task and not task.done():
        task.cancel()


async def _auto_trigger_after(db_factory, incident_id: str, start_ts: int) -> None:
    await asyncio.sleep(settings.sos_duration_sec)
    from app.database import AsyncSessionLocal
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Incident).where(Incident.id == incident_id))
        incident = result.scalar_one_or_none()
        if not incident or incident.phase != "CREATED":
            return
        redis = get_redis()
        sos_raw = await redis.get(f"{SOS_REDIS_PREFIX}{incident_id}")
        if not sos_raw:
            return
        sos_data = json.loads(sos_raw)
        if sos_data.get("status") != "ALERTING" or sos_data.get("startTs") != start_ts:
            return
        incident.phase = "DISPATCHED"
        await _append_log(db, incident_id, "Incident auto-triggered by SOS timeout")
        await redis.delete(f"{SOS_REDIS_PREFIX}{incident_id}")
        await db.commit()
        await db.refresh(incident)
        state = await _load_incident_state(db, incident)
        await _broadcast(incident_id, state)


async def sos_start(db: AsyncSession, incident_id: str) -> IncidentState:
    incident = await _get_incident_or_404(db, incident_id)
    if incident.phase != "CREATED":
        raise ValueError("Incident already dispatched")
    start_ts = _now_ms()
    sos_data = {"status": "ALERTING", "startTs": start_ts, "durationSec": settings.sos_duration_sec}
    redis = get_redis()
    await redis.set(f"{SOS_REDIS_PREFIX}{incident_id}", json.dumps(sos_data), ex=settings.sos_duration_sec + 5)
    await _append_log(db, incident_id, "SOS alerting started")
    await db.commit()

    _cancel_sos_task(incident_id)
    _sos_tasks[incident_id] = asyncio.create_task(
        _auto_trigger_after(None, incident_id, start_ts)
    )

    state = await _load_incident_state(db, incident)
    await _broadcast(incident_id, state)
    return state


async def sos_cancel(db: AsyncSession, incident_id: str) -> IncidentState:
    incident = await _get_incident_or_404(db, incident_id)
    if incident.phase != "CREATED":
        state = await _load_incident_state(db, incident)
        return state
    _cancel_sos_task(incident_id)
    redis = get_redis()
    await redis.delete(f"{SOS_REDIS_PREFIX}{incident_id}")
    await _append_log(db, incident_id, "SOS alerting canceled")
    await db.commit()
    state = await _load_incident_state(db, incident)
    await _broadcast(incident_id, state)
    return state


# ---------------------------------------------------------------------------
# Roles
# ---------------------------------------------------------------------------

async def join_incident(db: AsyncSession, incident_id: str, role: str, user_id: str) -> JoinResponse:
    role = role.upper()
    if role not in ROLES:
        raise ValueError(f"Invalid role: {role}")
    incident = await _get_incident_or_404(db, incident_id)

    # Check if role is already taken by a different user
    result = await db.execute(
        select(IncidentRole).where(
            IncidentRole.incident_id == incident_id,
            IncidentRole.role == role,
        )
    )
    existing = result.scalar_one_or_none()
    if existing and existing.user_id != user_id:
        raise LookupError(f"Role {role} already occupied")

    if existing:
        existing.status = "JOINED"
        existing.user_id = user_id
    else:
        db.add(IncidentRole(incident_id=incident_id, role=role, user_id=user_id, status="JOINED"))

    if incident.phase == "CREATED":
        incident.phase = "DISPATCHED"
    await _append_log(db, incident_id, f"{role} joined ({user_id})", user_id=user_id, action="JOIN")
    await db.commit()
    await db.refresh(incident)
    state = await _load_incident_state(db, incident)
    await _broadcast(incident_id, state)
    return JoinResponse(ok=True, incidentId=incident_id, role=role)


async def join_current_auto(db: AsyncSession, user_id: str) -> JoinResponse:
    global _current_incident_id
    if not _current_incident_id:
        await create_incident(db)

    incident_id = _current_incident_id
    result = await db.execute(select(Incident).where(Incident.id == incident_id))
    incident = result.scalar_one_or_none()
    if not incident:
        await create_incident(db)
        incident_id = _current_incident_id
        result = await db.execute(select(Incident).where(Incident.id == incident_id))
        incident = result.scalar_one_or_none()

    # Check if user already has a role
    result = await db.execute(
        select(IncidentRole).where(
            IncidentRole.incident_id == incident_id,
            IncidentRole.user_id == user_id,
        )
    )
    existing = result.scalar_one_or_none()
    if existing:
        return JoinResponse(ok=True, incidentId=incident_id, role=existing.role)

    # Find available roles
    taken_result = await db.execute(
        select(IncidentRole.role).where(IncidentRole.incident_id == incident_id)
    )
    taken = {r for r, in taken_result.all()}
    available = [r for r in ROLES if r not in taken]
    if not available:
        raise LookupError("No available roles")

    assigned = random.choice(available)
    db.add(IncidentRole(incident_id=incident_id, role=assigned, user_id=user_id, status="JOINED"))
    if incident.phase == "CREATED":
        incident.phase = "DISPATCHED"
    await _append_log(db, incident_id, f"{assigned} auto-joined ({user_id})", user_id=user_id)
    await db.commit()
    await db.refresh(incident)
    state = await _load_incident_state(db, incident)
    await _broadcast(incident_id, state)
    return JoinResponse(ok=True, incidentId=incident_id, role=assigned)


# ---------------------------------------------------------------------------
# Actions / State machine
# ---------------------------------------------------------------------------

_ACTION_MAP = {
    "CPR_STARTED": ("CPR", "PRIME", "CPR_STARTED", "CPR started"),
    "AED_PICKED": ("AED_PICKED", "RUNNER", "AED_PICKED", "AED picked"),
    "AED_DELIVERED": ("AED_DELIVERED", "RUNNER", "AED_DELIVERED", "AED delivered"),
    "AMBULANCE_ARRIVED": ("HANDOVER", "GUIDE", "AMBULANCE_ARRIVED", "Ambulance arrived"),
}


async def post_action(db: AsyncSession, incident_id: str, action: str, user_id: str) -> ActionResponse:
    incident = await _get_incident_or_404(db, incident_id)
    action = action.upper()

    if action in _ACTION_MAP:
        new_phase, role, role_status, log_msg = _ACTION_MAP[action]
        incident.phase = new_phase
        # Update role status
        result = await db.execute(
            select(IncidentRole).where(
                IncidentRole.incident_id == incident_id,
                IncidentRole.role == role,
            )
        )
        role_rec = result.scalar_one_or_none()
        if role_rec:
            role_rec.status = role_status
        await _append_log(db, incident_id, f"{log_msg} by {user_id}", user_id=user_id, action=action)
    else:
        await _append_log(db, incident_id, f"Unknown action: {action} by {user_id}", user_id=user_id, action=action)

    await db.commit()
    await db.refresh(incident)
    state = await _load_incident_state(db, incident)
    await _broadcast(incident_id, state)
    return ActionResponse(ok=True, incidentId=incident_id, phase=incident.phase)


async def trigger_incident(db: AsyncSession, incident_id: str) -> ActionResponse:
    incident = await _get_incident_or_404(db, incident_id)
    if incident.phase == "CREATED":
        incident.phase = "DISPATCHED"
        await _append_log(db, incident_id, "Incident triggered")
    await db.commit()
    await db.refresh(incident)
    state = await _load_incident_state(db, incident)
    await _broadcast(incident_id, state)
    return ActionResponse(ok=True, incidentId=incident_id, phase=incident.phase)
