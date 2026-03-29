from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


# ---------------------------------------------------------------------------
# Request bodies
# ---------------------------------------------------------------------------

class JoinRequest(BaseModel):
    role: str
    userId: str


class AutoJoinRequest(BaseModel):
    userId: str


class ActionRequest(BaseModel):
    action: str
    userId: str


class CreateIncidentRequest(BaseModel):
    lat: Optional[float] = None
    lng: Optional[float] = None


# ---------------------------------------------------------------------------
# Response shapes
# ---------------------------------------------------------------------------

class RoleState(BaseModel):
    status: Optional[str] = "IDLE"
    userId: Optional[str] = None


class RoleStates(BaseModel):
    PRIME: RoleState = RoleState()
    RUNNER: RoleState = RoleState()
    GUIDE: RoleState = RoleState()


class SosState(BaseModel):
    status: str = "MONITORING"
    startTs: Optional[int] = None
    durationSec: int = 10


class LogEntry(BaseModel):
    ts: int
    msg: str


class IncidentState(BaseModel):
    incidentId: str
    phase: str
    sos: SosState
    roles: RoleStates
    logs: list[LogEntry]


class CreateIncidentResponse(BaseModel):
    incidentId: str


class JoinResponse(BaseModel):
    ok: bool
    incidentId: str
    role: str


class ActionResponse(BaseModel):
    ok: bool
    incidentId: str
    phase: str


class NearbyAed(BaseModel):
    id: str
    name: Optional[str] = None
    lat: float
    lng: float
    address: Optional[str] = None
    floor: Optional[str] = None
    distM: float


class LocationUpdate(BaseModel):
    lat: float
    lng: float
    userId: str
