from __future__ import annotations

import asyncio
import math
import random
import time
import uuid
from typing import Dict, List

from fastapi import FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel


class JoinReq(BaseModel):
    role: str
    userId: str


class ActionReq(BaseModel):
    action: str
    userId: str


class AutoJoinReq(BaseModel):
    userId: str


class LocationUpdateReq(BaseModel):
    userId: str
    role: str
    provider: str
    latitude: float
    longitude: float
    accuracyMeters: float | None = None
    speedMetersPerSecond: float | None = None
    bearingDegrees: float | None = None
    updatedTs: int
    incidentId: str | None = None


class HealthSnapshotReq(BaseModel):
    userId: str
    source: str
    providerStatus: str
    heartRate: int | None = None
    bloodOxygen: int | None = None
    riskLevel: str
    alertType: str | None = None
    incidentId: str | None = None
    updatedTs: int


app = FastAPI(title="Life Reflex Arc - Distributed Emergency Response MVP")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

incidents: Dict[str, dict] = {}
ws_connections: Dict[str, List[WebSocket]] = {}
current_incident_id: str | None = None
sos_tasks: Dict[str, asyncio.Task] = {}
location_snapshots: Dict[str, dict] = {}
route_states: Dict[str, dict] = {}
health_snapshots: Dict[str, dict] = {}
latest_health_alerts: Dict[str, dict | None] = {}

SOS_DURATION_SEC = 10
EARTH_RADIUS_METERS = 6_371_000
ROUTE_SPEED_MPS = {
    "PRIME": 1.8,
    "RUNNER": 3.6,
    "GUIDE": 1.5,
}
SCENE_POINTS = {
    "PATIENT": {
        "key": "PATIENT",
        "label": "Patient",
        "latitude": 22.543096,
        "longitude": 114.057865,
    },
    "AED": {
        "key": "AED",
        "label": "AED Station",
        "latitude": 22.544182,
        "longitude": 114.056431,
    },
    "AMBULANCE_GATE": {
        "key": "AMBULANCE_GATE",
        "label": "Ambulance Gate",
        "latitude": 22.540538,
        "longitude": 114.058927,
    },
}


def now_ms() -> int:
    return int(time.time() * 1000)


def _append_log(incident_id: str, message: str) -> None:
    state = incidents.get(incident_id)
    if not state:
        return
    state["logs"].append({"ts": now_ms(), "msg": message})


def _new_incident() -> str:
    incident_id = str(uuid.uuid4())
    incidents[incident_id] = {
        "incidentId": incident_id,
        "phase": "CREATED",
        "sos": {"status": "MONITORING", "startTs": None, "durationSec": SOS_DURATION_SEC},
        "roles": {
            "PRIME": {"status": "IDLE", "userId": None},
            "RUNNER": {"status": "IDLE", "userId": None},
            "GUIDE": {"status": "IDLE", "userId": None},
        },
        "logs": [{"ts": now_ms(), "msg": "Incident created"}],
    }
    ws_connections.setdefault(incident_id, [])
    latest_health_alerts[incident_id] = None
    return incident_id


def _ensure_incident_id(candidate: str | None) -> str:
    global current_incident_id
    if candidate and candidate in incidents:
        return candidate
    if current_incident_id and current_incident_id in incidents:
        return current_incident_id
    current_incident_id = _new_incident()
    return current_incident_id


def _haversine_distance_meters(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)
    a = (
        math.sin(d_phi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    )
    return 2 * EARTH_RADIUS_METERS * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _interpolate_waypoints(
    lat1: float,
    lon1: float,
    lat2: float,
    lon2: float,
    steps: int = 12,
) -> List[dict]:
    count = max(2, steps)
    points: List[dict] = []
    for index in range(count + 1):
        ratio = index / count
        points.append(
            {
                "latitude": lat1 + (lat2 - lat1) * ratio,
                "longitude": lon1 + (lon2 - lon1) * ratio,
            }
        )
    return points


def _scene_payload() -> List[dict]:
    return list(SCENE_POINTS.values())


def _resolve_target(role: str, incident_id: str | None) -> dict:
    role_upper = role.upper()
    phase = incidents.get(incident_id or "", {}).get("phase")
    if role_upper == "RUNNER" and phase not in {"AED_PICKED", "AED_DELIVERED"}:
        return SCENE_POINTS["AED"]
    if role_upper == "GUIDE":
        return SCENE_POINTS["AMBULANCE_GATE"]
    return SCENE_POINTS["PATIENT"]


def _build_route_state(
    user_id: str,
    role: str,
    latitude: float,
    longitude: float,
    incident_id: str | None,
) -> dict:
    target = _resolve_target(role, incident_id)
    distance = _haversine_distance_meters(
        latitude,
        longitude,
        target["latitude"],
        target["longitude"],
    )
    speed = ROUTE_SPEED_MPS.get(role.upper(), 1.5)
    eta_seconds = max(5, int(distance / max(speed, 0.5)))
    return {
        "userId": user_id,
        "role": role.upper(),
        "targetKey": target["key"],
        "targetLabel": target["label"],
        "distanceMeters": round(distance, 1),
        "etaSeconds": eta_seconds,
        "polyline": _interpolate_waypoints(
            latitude,
            longitude,
            target["latitude"],
            target["longitude"],
        ),
    }


def _location_payload(incident_id: str) -> dict:
    return {
        "incidentId": incident_id,
        "scene": _scene_payload(),
        "locations": [
            value
            for value in location_snapshots.values()
            if value.get("incidentId") == incident_id
        ],
        "routes": [
            value
            for value in route_states.values()
            if value.get("incidentId") == incident_id
        ],
    }


def _health_payload(incident_id: str) -> dict:
    return {
        "incidentId": incident_id,
        "snapshots": [
            value
            for value in health_snapshots.values()
            if value.get("incidentId") == incident_id
        ],
        "latestAlert": latest_health_alerts.get(incident_id),
    }


async def _broadcast_json(incident_id: str, payload: dict) -> None:
    conns = ws_connections.get(incident_id, [])
    alive: List[WebSocket] = []
    for ws in conns:
        try:
            await ws.send_json(payload)
            alive.append(ws)
        except Exception:
            pass
    ws_connections[incident_id] = alive


async def _broadcast_state_async(incident_id: str) -> None:
    if incident_id not in incidents:
        return
    await _broadcast_json(incident_id, {"type": "STATE", "payload": incidents[incident_id]})


async def _broadcast_location_async(incident_id: str) -> None:
    await _broadcast_json(incident_id, {"type": "LOCATION_STATE", "payload": _location_payload(incident_id)})


async def _broadcast_health_async(incident_id: str) -> None:
    await _broadcast_json(incident_id, {"type": "HEALTH_STATE", "payload": _health_payload(incident_id)})


async def _broadcast_health_alert_async(incident_id: str, alert_payload: dict) -> None:
    await _broadcast_json(incident_id, {"type": "HEALTH_ALERT", "payload": alert_payload})


async def _auto_trigger_after(incident_id: str, start_ts: int) -> None:
    await asyncio.sleep(SOS_DURATION_SEC)
    state = incidents.get(incident_id)
    if not state:
        return
    if state["phase"] != "CREATED":
        return
    sos = state.get("sos") or {}
    if sos.get("status") != "ALERTING" or sos.get("startTs") != start_ts:
        return
    state["phase"] = "DISPATCHED"
    _append_log(incident_id, "Incident auto-triggered")
    await _broadcast_state_async(incident_id)


async def _start_sos_if_needed(incident_id: str, reason: str) -> None:
    state = incidents.get(incident_id)
    if not state or state["phase"] != "CREATED":
        return
    if state["sos"]["status"] == "ALERTING":
        return
    start_ts = now_ms()
    state["sos"] = {"status": "ALERTING", "startTs": start_ts, "durationSec": SOS_DURATION_SEC}
    _append_log(incident_id, f"SOS alerting started ({reason})")
    task = sos_tasks.get(incident_id)
    if task and not task.done():
        task.cancel()
    sos_tasks[incident_id] = asyncio.create_task(_auto_trigger_after(incident_id, start_ts))
    await _broadcast_state_async(incident_id)


@app.get("/health")
async def health():
    return {"ok": True}


@app.post("/incidents")
async def create_incident():
    global current_incident_id
    incident_id = _new_incident()
    current_incident_id = incident_id
    return {"incidentId": incident_id}


@app.get("/incidents/current")
async def get_current_incident():
    global current_incident_id
    if not current_incident_id or current_incident_id not in incidents:
        current_incident_id = _new_incident()
    return incidents[current_incident_id]


@app.post("/incidents/current/reset")
async def reset_current_incident():
    global current_incident_id
    incident_id = _ensure_incident_id(current_incident_id)
    state = incidents[incident_id]
    state["phase"] = "CREATED"
    state["sos"] = {"status": "MONITORING", "startTs": None, "durationSec": SOS_DURATION_SEC}
    state["roles"] = {
        "PRIME": {"status": "IDLE", "userId": None},
        "RUNNER": {"status": "IDLE", "userId": None},
        "GUIDE": {"status": "IDLE", "userId": None},
    }
    state["logs"] = [{"ts": now_ms(), "msg": "Incident reset"}]

    for store in (location_snapshots, route_states, health_snapshots):
        keys = [key for key, value in store.items() if value.get("incidentId") == incident_id]
        for key in keys:
            del store[key]
    latest_health_alerts[incident_id] = None

    task = sos_tasks.get(incident_id)
    if task and not task.done():
        task.cancel()

    await _broadcast_state_async(incident_id)
    await _broadcast_location_async(incident_id)
    await _broadcast_health_async(incident_id)
    return {"incidentId": incident_id, "phase": state["phase"]}


@app.post("/incidents/{incident_id}/sos_start")
async def sos_start(incident_id: str):
    if incident_id not in incidents:
        raise HTTPException(status_code=404, detail="Incident not found")
    await _start_sos_if_needed(incident_id, "manual")
    return {"ok": True, "incidentId": incident_id}


@app.post("/incidents/{incident_id}/sos_cancel")
async def sos_cancel(incident_id: str):
    if incident_id not in incidents:
        raise HTTPException(status_code=404, detail="Incident not found")
    state = incidents[incident_id]
    if state["phase"] != "CREATED":
        return {"ok": True, "incidentId": incident_id}
    state["sos"] = {"status": "MONITORING", "startTs": None, "durationSec": SOS_DURATION_SEC}
    _append_log(incident_id, "SOS alerting canceled")
    task = sos_tasks.get(incident_id)
    if task and not task.done():
        task.cancel()
    await _broadcast_state_async(incident_id)
    return {"ok": True, "incidentId": incident_id}


@app.post("/incidents/current/join_auto")
async def join_current_auto(req: AutoJoinReq):
    global current_incident_id
    current_incident_id = _ensure_incident_id(current_incident_id)
    state = incidents[current_incident_id]

    for role in ("PRIME", "RUNNER", "GUIDE"):
        if state["roles"][role]["userId"] == req.userId:
            return {"ok": True, "incidentId": current_incident_id, "role": role}

    available = [role for role in ("PRIME", "RUNNER", "GUIDE") if state["roles"][role]["userId"] is None]
    if not available:
        raise HTTPException(status_code=409, detail="No available roles")

    assigned = random.choice(available)
    state["roles"][assigned]["status"] = "JOINED"
    state["roles"][assigned]["userId"] = req.userId
    if state["phase"] == "CREATED":
        state["phase"] = "DISPATCHED"

    _append_log(current_incident_id, f"{assigned} auto-joined ({req.userId})")
    await _broadcast_state_async(current_incident_id)
    return {"ok": True, "incidentId": current_incident_id, "role": assigned}


@app.get("/incidents/{incident_id}")
async def get_incident(incident_id: str):
    if incident_id not in incidents:
        raise HTTPException(status_code=404, detail="Incident not found")
    return incidents[incident_id]


@app.post("/incidents/{incident_id}/join")
async def join_incident(incident_id: str, req: JoinReq):
    if incident_id not in incidents:
        raise HTTPException(status_code=404, detail="Incident not found")

    role = req.role.upper()
    if role not in ("PRIME", "RUNNER", "GUIDE"):
        raise HTTPException(status_code=400, detail="Invalid role")

    state = incidents[incident_id]
    state["roles"][role]["status"] = "JOINED"
    state["roles"][role]["userId"] = req.userId
    if state["phase"] == "CREATED":
        state["phase"] = "DISPATCHED"

    _append_log(incident_id, f"{role} joined ({req.userId})")
    await _broadcast_state_async(incident_id)
    return {"ok": True, "incidentId": incident_id, "phase": state["phase"]}


@app.post("/incidents/{incident_id}/actions")
async def post_action(incident_id: str, req: ActionReq):
    if incident_id not in incidents:
        raise HTTPException(status_code=404, detail="Incident not found")

    state = incidents[incident_id]
    action = req.action.upper()

    if action == "CPR_STARTED":
        state["phase"] = "CPR"
        state["roles"]["PRIME"]["status"] = "CPR_STARTED"
        _append_log(incident_id, f"CPR started by {req.userId}")
    elif action == "AED_PICKED":
        state["phase"] = "AED_PICKED"
        state["roles"]["RUNNER"]["status"] = "AED_PICKED"
        _append_log(incident_id, f"AED picked by {req.userId}")
    elif action == "AED_DELIVERED":
        state["phase"] = "AED_DELIVERED"
        state["roles"]["RUNNER"]["status"] = "AED_DELIVERED"
        _append_log(incident_id, f"AED delivered by {req.userId}")
    elif action == "AMBULANCE_ARRIVED":
        state["phase"] = "HANDOVER"
        state["roles"]["GUIDE"]["status"] = "AMBULANCE_ARRIVED"
        _append_log(incident_id, f"Ambulance arrived (reported by {req.userId})")
    else:
        _append_log(incident_id, f"Unknown action: {action} by {req.userId}")

    await _broadcast_state_async(incident_id)
    await _broadcast_location_async(incident_id)
    return {"ok": True, "incidentId": incident_id, "phase": state["phase"]}


@app.post("/incidents/{incident_id}/trigger")
async def trigger_incident(incident_id: str):
    if incident_id not in incidents:
        raise HTTPException(status_code=404, detail="Incident not found")

    state = incidents[incident_id]
    if state["phase"] == "CREATED":
        state["phase"] = "DISPATCHED"
        _append_log(incident_id, "Incident triggered")

    await _broadcast_state_async(incident_id)
    return {"ok": True, "incidentId": incident_id, "phase": state["phase"]}


@app.post("/location/update")
async def update_location(req: LocationUpdateReq):
    incident_id = _ensure_incident_id(req.incidentId)
    snapshot = req.model_dump()
    snapshot["role"] = req.role.upper()
    snapshot["incidentId"] = incident_id
    location_snapshots[req.userId] = snapshot

    route = _build_route_state(
        user_id=req.userId,
        role=req.role,
        latitude=req.latitude,
        longitude=req.longitude,
        incident_id=incident_id,
    )
    route["incidentId"] = incident_id
    route_states[req.userId] = route

    await _broadcast_location_async(incident_id)
    return {"ok": True, "location": snapshot, "route": route}


@app.get("/location/current/{user_id}")
async def get_location_current(user_id: str):
    snapshot = location_snapshots.get(user_id)
    if not snapshot:
        raise HTTPException(status_code=404, detail="Location not found")
    return snapshot


@app.get("/route/plan")
async def get_route_plan(
    userId: str = Query(...),
    role: str = Query(...),
    lat: float = Query(...),
    lng: float = Query(...),
    incidentId: str | None = Query(default=None),
):
    incident_id = _ensure_incident_id(incidentId)
    route = _build_route_state(
        user_id=userId,
        role=role,
        latitude=lat,
        longitude=lng,
        incident_id=incident_id,
    )
    route["incidentId"] = incident_id
    route_states[userId] = route
    return {"scene": _scene_payload(), "route": route}


@app.post("/health/sync/snapshot")
async def sync_health_snapshot(req: HealthSnapshotReq):
    incident_id = _ensure_incident_id(req.incidentId)
    snapshot = req.model_dump()
    snapshot["incidentId"] = incident_id
    health_snapshots[req.userId] = snapshot

    alert_payload = None
    if req.alertType:
        alert_payload = {
            "userId": req.userId,
            "alertType": req.alertType,
            "riskLevel": req.riskLevel,
            "message": f"{req.alertType} from {req.source}",
            "updatedTs": req.updatedTs,
            "incidentId": incident_id,
        }
        latest_health_alerts[incident_id] = alert_payload
        _append_log(incident_id, f"Health alert: {req.alertType} ({req.riskLevel})")

        if req.alertType in {"FALL_DETECTED", "HEART_RATE_EXCEPTION"}:
            await _start_sos_if_needed(incident_id, req.alertType.lower())

    await _broadcast_health_async(incident_id)
    if alert_payload:
        await _broadcast_health_alert_async(incident_id, alert_payload)
    return {"ok": True, "snapshot": snapshot, "latestAlert": latest_health_alerts.get(incident_id)}


@app.websocket("/ws")
async def ws_endpoint(websocket: WebSocket, incidentId: str):
    await websocket.accept()

    if incidentId not in incidents:
        await websocket.send_json({"type": "ERROR", "payload": "Incident not found"})
        await websocket.close()
        return

    ws_connections.setdefault(incidentId, []).append(websocket)

    await websocket.send_json({"type": "STATE", "payload": incidents[incidentId]})
    await websocket.send_json({"type": "LOCATION_STATE", "payload": _location_payload(incidentId)})
    await websocket.send_json({"type": "HEALTH_STATE", "payload": _health_payload(incidentId)})

    try:
        while True:
            await asyncio.sleep(30)
    except WebSocketDisconnect:
        pass
    finally:
        conns = ws_connections.get(incidentId, [])
        ws_connections[incidentId] = [ws for ws in conns if ws is not websocket]
