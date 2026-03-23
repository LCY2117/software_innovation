"""Incident endpoints: /api/v1/incidents/"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas import (
    ApiResponse,
    ERR_NOT_FOUND, ERR_ROLE_OCCUPIED, ERR_VALIDATION,
    ActionRequest, AutoJoinRequest, CreateIncidentRequest, JoinRequest,
    ActionResponse, CreateIncidentResponse, IncidentState, JoinResponse,
)
from app.services import incident_service as svc

router = APIRouter(prefix="/incidents", tags=["incidents"])


@router.post("", response_model=ApiResponse[CreateIncidentResponse])
async def create_incident(
    req: CreateIncidentRequest = CreateIncidentRequest(),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[CreateIncidentResponse]:
    state = await svc.create_incident(db, lat=req.lat, lng=req.lng)
    return ApiResponse.ok(CreateIncidentResponse(incidentId=state.incidentId))


@router.get("/current", response_model=ApiResponse[IncidentState])
async def get_current(db: AsyncSession = Depends(get_db)) -> ApiResponse[IncidentState]:
    state = await svc.get_current_incident(db)
    return ApiResponse.ok(state)


@router.post("/current/reset", response_model=ApiResponse[IncidentState])
async def reset_current(db: AsyncSession = Depends(get_db)) -> ApiResponse[IncidentState]:
    state = await svc.reset_current_incident(db)
    return ApiResponse.ok(state)


@router.post("/current/join_auto", response_model=ApiResponse[JoinResponse])
async def join_current_auto(req: AutoJoinRequest, db: AsyncSession = Depends(get_db)) -> ApiResponse[JoinResponse]:
    try:
        result = await svc.join_current_auto(db, req.userId)
        return ApiResponse.ok(result)
    except LookupError as exc:
        return ApiResponse.error(ERR_ROLE_OCCUPIED, str(exc))


@router.get("/{incident_id}", response_model=ApiResponse[IncidentState])
async def get_incident(incident_id: str, db: AsyncSession = Depends(get_db)) -> ApiResponse[IncidentState]:
    try:
        state = await svc.get_incident(db, incident_id)
        return ApiResponse.ok(state)
    except ValueError:
        return ApiResponse.error(ERR_NOT_FOUND, "Incident not found")


@router.post("/{incident_id}/sos_start", response_model=ApiResponse[IncidentState])
async def sos_start(incident_id: str, db: AsyncSession = Depends(get_db)) -> ApiResponse[IncidentState]:
    try:
        state = await svc.sos_start(db, incident_id)
        return ApiResponse.ok(state)
    except ValueError as exc:
        code = ERR_NOT_FOUND if "not found" in str(exc).lower() else ERR_VALIDATION
        return ApiResponse.error(code, str(exc))


@router.post("/{incident_id}/sos_cancel", response_model=ApiResponse[IncidentState])
async def sos_cancel(incident_id: str, db: AsyncSession = Depends(get_db)) -> ApiResponse[IncidentState]:
    try:
        state = await svc.sos_cancel(db, incident_id)
        return ApiResponse.ok(state)
    except ValueError:
        return ApiResponse.error(ERR_NOT_FOUND, "Incident not found")


@router.post("/{incident_id}/join", response_model=ApiResponse[JoinResponse])
async def join_incident(incident_id: str, req: JoinRequest, db: AsyncSession = Depends(get_db)) -> ApiResponse[JoinResponse]:
    try:
        result = await svc.join_incident(db, incident_id, req.role, req.userId)
        return ApiResponse.ok(result)
    except LookupError as exc:
        return ApiResponse.error(ERR_ROLE_OCCUPIED, str(exc))
    except ValueError as exc:
        code = ERR_NOT_FOUND if "not found" in str(exc).lower() else ERR_VALIDATION
        return ApiResponse.error(code, str(exc))


@router.post("/{incident_id}/actions", response_model=ApiResponse[ActionResponse])
async def post_action(incident_id: str, req: ActionRequest, db: AsyncSession = Depends(get_db)) -> ApiResponse[ActionResponse]:
    try:
        result = await svc.post_action(db, incident_id, req.action, req.userId)
        return ApiResponse.ok(result)
    except ValueError:
        return ApiResponse.error(ERR_NOT_FOUND, "Incident not found")


@router.post("/{incident_id}/trigger", response_model=ApiResponse[ActionResponse])
async def trigger_incident(incident_id: str, db: AsyncSession = Depends(get_db)) -> ApiResponse[ActionResponse]:
    try:
        result = await svc.trigger_incident(db, incident_id)
        return ApiResponse.ok(result)
    except ValueError:
        return ApiResponse.error(ERR_NOT_FOUND, "Incident not found")


@router.get("/{incident_id}/logs")
async def get_logs(incident_id: str, db: AsyncSession = Depends(get_db)) -> ApiResponse[list]:
    try:
        state = await svc.get_incident(db, incident_id)
        return ApiResponse.ok(state.logs)
    except ValueError:
        return ApiResponse.error(ERR_NOT_FOUND, "Incident not found")
