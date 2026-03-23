"""Unit tests for the /api/v1/incidents endpoints."""
from __future__ import annotations

import pytest
import pytest_asyncio


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def assert_ok(resp, *, path: str = "") -> dict:
    assert resp.status_code == 200, f"{path}: {resp.text}"
    body = resp.json()
    assert body["code"] == 0, f"{path}: {body}"
    return body["data"]


# ---------------------------------------------------------------------------
# Incident lifecycle
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_incident(client):
    data = assert_ok(await client.post("/api/v1/incidents"), path="POST /incidents")
    assert "incidentId" in data


@pytest.mark.asyncio
async def test_get_current_incident(client):
    data = assert_ok(await client.get("/api/v1/incidents/current"), path="GET /incidents/current")
    assert data["phase"] == "CREATED"
    assert "roles" in data
    assert "sos" in data


@pytest.mark.asyncio
async def test_full_incident_lifecycle(client):
    # Create
    data = assert_ok(await client.post("/api/v1/incidents"), path="create")
    incident_id = data["incidentId"]

    # Get
    data = assert_ok(await client.get(f"/api/v1/incidents/{incident_id}"), path="get")
    assert data["phase"] == "CREATED"

    # SOS start
    data = assert_ok(await client.post(f"/api/v1/incidents/{incident_id}/sos_start"), path="sos_start")
    assert data["sos"]["status"] == "ALERTING"

    # SOS cancel
    data = assert_ok(await client.post(f"/api/v1/incidents/{incident_id}/sos_cancel"), path="sos_cancel")
    assert data["sos"]["status"] == "MONITORING"

    # Join as PRIME
    resp = await client.post(
        f"/api/v1/incidents/{incident_id}/join",
        json={"role": "PRIME", "userId": "user-1"},
    )
    data = assert_ok(resp, path="join PRIME")
    assert data["role"] == "PRIME"

    # State should now be DISPATCHED
    data = assert_ok(await client.get(f"/api/v1/incidents/{incident_id}"), path="after join")
    assert data["phase"] == "DISPATCHED"

    # CPR_STARTED action
    resp = await client.post(
        f"/api/v1/incidents/{incident_id}/actions",
        json={"action": "CPR_STARTED", "userId": "user-1"},
    )
    data = assert_ok(resp, path="CPR_STARTED")
    assert data["phase"] == "CPR"

    # AED_PICKED
    resp = await client.post(
        f"/api/v1/incidents/{incident_id}/actions",
        json={"action": "AED_PICKED", "userId": "user-2"},
    )
    data = assert_ok(resp, path="AED_PICKED")
    assert data["phase"] == "AED_PICKED"

    # AED_DELIVERED
    resp = await client.post(
        f"/api/v1/incidents/{incident_id}/actions",
        json={"action": "AED_DELIVERED", "userId": "user-2"},
    )
    data = assert_ok(resp, path="AED_DELIVERED")
    assert data["phase"] == "AED_DELIVERED"

    # AMBULANCE_ARRIVED → HANDOVER
    resp = await client.post(
        f"/api/v1/incidents/{incident_id}/actions",
        json={"action": "AMBULANCE_ARRIVED", "userId": "user-3"},
    )
    data = assert_ok(resp, path="AMBULANCE_ARRIVED")
    assert data["phase"] == "HANDOVER"


@pytest.mark.asyncio
async def test_join_auto(client):
    # Ensure a current incident exists
    await client.post("/api/v1/incidents")

    resp = await client.post(
        "/api/v1/incidents/current/join_auto",
        json={"userId": "auto-user-1"},
    )
    data = assert_ok(resp, path="join_auto")
    assert data["role"] in ("PRIME", "RUNNER", "GUIDE")


@pytest.mark.asyncio
async def test_reset_current_incident(client):
    # Create + join
    await client.post("/api/v1/incidents")
    await client.post(
        "/api/v1/incidents/current/join_auto",
        json={"userId": "reset-user"},
    )
    data = assert_ok(await client.post("/api/v1/incidents/current/reset"), path="reset")
    assert data["phase"] == "CREATED"


@pytest.mark.asyncio
async def test_trigger_incident(client):
    cr = assert_ok(await client.post("/api/v1/incidents"), path="create for trigger")
    incident_id = cr["incidentId"]
    data = assert_ok(await client.post(f"/api/v1/incidents/{incident_id}/trigger"), path="trigger")
    assert data["phase"] == "DISPATCHED"


@pytest.mark.asyncio
async def test_get_incident_logs(client):
    cr = assert_ok(await client.post("/api/v1/incidents"), path="create for logs")
    incident_id = cr["incidentId"]
    logs = assert_ok(await client.get(f"/api/v1/incidents/{incident_id}/logs"), path="logs")
    assert isinstance(logs, list)
    assert len(logs) >= 1


@pytest.mark.asyncio
async def test_not_found(client):
    resp = await client.get("/api/v1/incidents/nonexistent-id")
    body = resp.json()
    assert body["code"] == 40401


@pytest.mark.asyncio
async def test_health(client):
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["ok"] is True


# ---------------------------------------------------------------------------
# Auth endpoints
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_send_code(client):
    resp = await client.post("/api/v1/auth/send_code", json={"phone": "13800138000"})
    body = resp.json()
    assert body["code"] == 0
    assert "devCode" in body["data"]


@pytest.mark.asyncio
async def test_login_flow(client):
    phone = "13900139000"
    # Send code
    resp = await client.post("/api/v1/auth/send_code", json={"phone": phone})
    code = resp.json()["data"]["devCode"]

    # Login
    resp = await client.post("/api/v1/auth/login", json={"phone": phone, "code": code})
    data = assert_ok(resp, path="login")
    assert "accessToken" in data
    assert "refreshToken" in data
    assert data["phone"] == phone


# ---------------------------------------------------------------------------
# Geo endpoints
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_nearby_aed_empty(client):
    resp = await client.get("/api/v1/geo/aed/nearby?lat=39.9&lng=116.4")
    data = assert_ok(resp, path="nearby_aed")
    assert isinstance(data, list)


@pytest.mark.asyncio
async def test_route_stub(client):
    resp = await client.get("/api/v1/geo/route?fromLat=39.9&fromLng=116.4&toLat=39.91&toLng=116.41")
    data = assert_ok(resp, path="route")
    assert "distanceM" in data
    assert "durationSec" in data


# ---------------------------------------------------------------------------
# Service-layer unit tests (direct, no HTTP)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_service_create_and_get_incident(db_session):
    from app.services import incident_service as svc
    svc._current_incident_id = None
    state = await svc.create_incident(db_session)
    assert state.phase == "CREATED"
    assert state.incidentId

    fetched = await svc.get_incident(db_session, state.incidentId)
    assert fetched.incidentId == state.incidentId


@pytest.mark.asyncio
async def test_service_join_and_action(db_session):
    from app.services import incident_service as svc
    svc._current_incident_id = None
    state = await svc.create_incident(db_session)
    iid = state.incidentId

    join_resp = await svc.join_incident(db_session, iid, "PRIME", "u-prime")
    assert join_resp.role == "PRIME"

    action_resp = await svc.post_action(db_session, iid, "CPR_STARTED", "u-prime")
    assert action_resp.phase == "CPR"


@pytest.mark.asyncio
async def test_service_sos_cycle(db_session):
    from app.services import incident_service as svc
    svc._current_incident_id = None
    state = await svc.create_incident(db_session)
    iid = state.incidentId

    sos_state = await svc.sos_start(db_session, iid)
    assert sos_state.sos.status == "ALERTING"

    cancel_state = await svc.sos_cancel(db_session, iid)
    assert cancel_state.sos.status == "MONITORING"


@pytest.mark.asyncio
async def test_service_join_auto_and_reset(db_session):
    from app.services import incident_service as svc
    svc._current_incident_id = None
    await svc.create_incident(db_session)
    join_resp = await svc.join_current_auto(db_session, "auto-u")
    assert join_resp.role in ("PRIME", "RUNNER", "GUIDE")

    reset_state = await svc.reset_current_incident(db_session)
    assert reset_state.phase == "CREATED"


@pytest.mark.asyncio
async def test_service_not_found(db_session):
    from app.services import incident_service as svc
    with pytest.raises(ValueError, match="not found"):
        await svc.get_incident(db_session, "does-not-exist")


@pytest.mark.asyncio
async def test_location_report(client):
    resp = await client.post(
        "/api/v1/geo/location",
        json={"lat": 39.9, "lng": 116.4, "userId": "loc-user-1"},
    )
    data = assert_ok(resp, path="location")
    assert data["ok"] is True
