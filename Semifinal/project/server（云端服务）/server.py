from __future__ import annotations

import asyncio
import time
import uuid
import random
from typing import Dict, List

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel


# ----------------------------
# Request Models
# ----------------------------
class JoinReq(BaseModel):
    role: str
    userId: str


class ActionReq(BaseModel):
    action: str
    userId: str


class AutoJoinReq(BaseModel):
    userId: str


# ----------------------------
# App
# ----------------------------
app = FastAPI(title="Life Reflex Arc - Distributed Emergency Response MVP")

# ✅ CORS: allow local dev dashboard
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

# ----------------------------
# In-memory Stores
# ----------------------------
incidents: Dict[str, dict] = {}
ws_connections: Dict[str, List[WebSocket]] = {}
current_incident_id: str | None = None
sos_tasks: Dict[str, asyncio.Task] = {}
SOS_DURATION_SEC = 10


def now_ms() -> int:
    return int(time.time() * 1000)


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
    return incident_id


async def _broadcast_state_async(incident_id: str) -> None:
    """Broadcast full incident state to all connected WS clients."""
    if incident_id not in incidents:
        return

    payload = {"type": "STATE", "payload": incidents[incident_id]}
    conns = ws_connections.get(incident_id, [])

    alive: List[WebSocket] = []
    for ws in conns:
        try:
            await ws.send_json(payload)
            alive.append(ws)
        except Exception:
            # drop broken websocket
            pass

    ws_connections[incident_id] = alive


# ----------------------------
# REST Endpoints
# ----------------------------
@app.get("/health")
async def health():
    return {"ok": True}


@app.post("/incidents")
async def create_incident():
    global current_incident_id
    incident_id = _new_incident()
    current_incident_id = incident_id

    # front-end expects this exact field name
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
    if not current_incident_id or current_incident_id not in incidents:
        current_incident_id = _new_incident()
        await _broadcast_state_async(current_incident_id)
        return {"incidentId": current_incident_id, "phase": incidents[current_incident_id]["phase"]}

    st = incidents[current_incident_id]
    st["phase"] = "CREATED"
    st["sos"] = {"status": "MONITORING", "startTs": None, "durationSec": SOS_DURATION_SEC}
    st["roles"] = {
        "PRIME": {"status": "IDLE", "userId": None},
        "RUNNER": {"status": "IDLE", "userId": None},
        "GUIDE": {"status": "IDLE", "userId": None},
    }
    st["logs"] = [{"ts": now_ms(), "msg": "Incident reset"}]

    task = sos_tasks.get(current_incident_id)
    if task and not task.done():
        task.cancel()

    await _broadcast_state_async(current_incident_id)
    return {"incidentId": current_incident_id, "phase": st["phase"]}


async def _auto_trigger_after(incident_id: str, start_ts: int) -> None:
    await asyncio.sleep(SOS_DURATION_SEC)
    st = incidents.get(incident_id)
    if not st:
        return
    if st["phase"] != "CREATED":
        return
    sos = st.get("sos") or {}
    if sos.get("status") != "ALERTING" or sos.get("startTs") != start_ts:
        return
    st["phase"] = "DISPATCHED"
    st["logs"].append({"ts": now_ms(), "msg": "Incident auto-triggered"})
    await _broadcast_state_async(incident_id)


@app.post("/incidents/{incident_id}/sos_start")
async def sos_start(incident_id: str):
    if incident_id not in incidents:
        raise HTTPException(status_code=404, detail="Incident not found")
    st = incidents[incident_id]
    if st["phase"] != "CREATED":
        raise HTTPException(status_code=400, detail="Incident already dispatched")
    start_ts = now_ms()
    st["sos"] = {"status": "ALERTING", "startTs": start_ts, "durationSec": SOS_DURATION_SEC}
    st["logs"].append({"ts": start_ts, "msg": "SOS alerting started"})
    await _broadcast_state_async(incident_id)
    task = sos_tasks.get(incident_id)
    if task and not task.done():
        task.cancel()
    sos_tasks[incident_id] = asyncio.create_task(_auto_trigger_after(incident_id, start_ts))
    return {"ok": True, "incidentId": incident_id}


@app.post("/incidents/{incident_id}/sos_cancel")
async def sos_cancel(incident_id: str):
    if incident_id not in incidents:
        raise HTTPException(status_code=404, detail="Incident not found")
    st = incidents[incident_id]
    if st["phase"] != "CREATED":
        return {"ok": True, "incidentId": incident_id}
    st["sos"] = {"status": "MONITORING", "startTs": None, "durationSec": SOS_DURATION_SEC}
    st["logs"].append({"ts": now_ms(), "msg": "SOS alerting canceled"})
    await _broadcast_state_async(incident_id)
    task = sos_tasks.get(incident_id)
    if task and not task.done():
        task.cancel()
    return {"ok": True, "incidentId": incident_id}


@app.post("/incidents/current/join_auto")
async def join_current_auto(req: AutoJoinReq):
    global current_incident_id
    if not current_incident_id or current_incident_id not in incidents:
        current_incident_id = _new_incident()

    st = incidents[current_incident_id]

    # If user already assigned, return existing role
    for role in ("PRIME", "RUNNER", "GUIDE"):
        if st["roles"][role]["userId"] == req.userId:
            return {"ok": True, "incidentId": current_incident_id, "role": role}

    available = [role for role in ("PRIME", "RUNNER", "GUIDE") if st["roles"][role]["userId"] is None]
    if not available:
        raise HTTPException(status_code=409, detail="No available roles")

    assigned = random.choice(available)
    st["roles"][assigned]["status"] = "JOINED"
    st["roles"][assigned]["userId"] = req.userId
    if st["phase"] == "CREATED":
        st["phase"] = "DISPATCHED"

    st["logs"].append({"ts": now_ms(), "msg": f"{assigned} auto-joined ({req.userId})"})
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

    st = incidents[incident_id]

    st["roles"][role]["status"] = "JOINED"
    st["roles"][role]["userId"] = req.userId

    if st["phase"] == "CREATED":
        st["phase"] = "DISPATCHED"

    st["logs"].append({"ts": now_ms(), "msg": f"{role} joined ({req.userId})"})

    # ✅ safe: we are inside the event loop now
    await _broadcast_state_async(incident_id)

    return {"ok": True, "incidentId": incident_id, "phase": st["phase"]}


@app.post("/incidents/{incident_id}/actions")
async def post_action(incident_id: str, req: ActionReq):
    if incident_id not in incidents:
        raise HTTPException(status_code=404, detail="Incident not found")

    st = incidents[incident_id]
    action = req.action.upper()

    if action == "CPR_STARTED":
        st["phase"] = "CPR"
        st["roles"]["PRIME"]["status"] = "CPR_STARTED"
        st["logs"].append({"ts": now_ms(), "msg": f"CPR started by {req.userId}"})

    elif action == "AED_PICKED":
        st["phase"] = "AED_PICKED"
        st["roles"]["RUNNER"]["status"] = "AED_PICKED"
        st["logs"].append({"ts": now_ms(), "msg": f"AED picked by {req.userId}"})

    elif action == "AED_DELIVERED":
        st["phase"] = "AED_DELIVERED"
        st["roles"]["RUNNER"]["status"] = "AED_DELIVERED"
        st["logs"].append({"ts": now_ms(), "msg": f"AED delivered by {req.userId}"})

    elif action == "AMBULANCE_ARRIVED":
        st["phase"] = "HANDOVER"
        st["roles"]["GUIDE"]["status"] = "AMBULANCE_ARRIVED"
        st["logs"].append({"ts": now_ms(), "msg": f"Ambulance arrived (reported by {req.userId})"})

    else:
        st["logs"].append({"ts": now_ms(), "msg": f"Unknown action: {action} by {req.userId}"})

    await _broadcast_state_async(incident_id)
    return {"ok": True, "incidentId": incident_id, "phase": st["phase"]}


@app.post("/incidents/{incident_id}/trigger")
async def trigger_incident(incident_id: str):
    if incident_id not in incidents:
        raise HTTPException(status_code=404, detail="Incident not found")

    st = incidents[incident_id]
    if st["phase"] == "CREATED":
        st["phase"] = "DISPATCHED"
        st["logs"].append({"ts": now_ms(), "msg": "Incident triggered"})

    await _broadcast_state_async(incident_id)
    return {"ok": True, "incidentId": incident_id, "phase": st["phase"]}


# ----------------------------
# WebSocket Endpoint
# ----------------------------
@app.websocket("/ws")
async def ws_endpoint(websocket: WebSocket, incidentId: str):
    await websocket.accept()

    if incidentId not in incidents:
        await websocket.send_json({"type": "ERROR", "payload": "Incident not found"})
        await websocket.close()
        return

    ws_connections.setdefault(incidentId, []).append(websocket)

    # immediately send current state
    await websocket.send_json({"type": "STATE", "payload": incidents[incidentId]})

    try:
        # keep alive without requiring client messages
        while True:
            await asyncio.sleep(30)
    except WebSocketDisconnect:
        pass
    finally:
        conns = ws_connections.get(incidentId, [])
        ws_connections[incidentId] = [ws for ws in conns if ws is not websocket]
