"""WebSocket handler with Redis Pub/Sub fan-out.

Architecture:
  - Each WS connection subscribes to a Redis channel: incident:state:{id}
  - The incident service publishes state changes to that channel
  - This allows horizontal scaling across multiple server instances
"""
from __future__ import annotations

import asyncio
import json
import logging

from fastapi import WebSocket, WebSocketDisconnect

from app.database import AsyncSessionLocal
from app.redis_client import get_pubsub
from app.services.incident_service import get_incident

logger = logging.getLogger(__name__)

PING_INTERVAL = 30  # seconds


async def ws_incident_handler(websocket: WebSocket, incident_id: str) -> None:
    await websocket.accept()

    # Send initial state snapshot
    try:
        async with AsyncSessionLocal() as db:
            state = await get_incident(db, incident_id)
        await websocket.send_json({"type": "STATE", "payload": state.model_dump()})
    except ValueError:
        await websocket.send_json({"type": "ERROR", "payload": "Incident not found"})
        await websocket.close()
        return

    pubsub = get_pubsub()
    channel = f"incident:state:{incident_id}"
    await pubsub.subscribe(channel)

    async def _relay_messages() -> None:
        """Forward Redis Pub/Sub messages to the WebSocket client."""
        while True:
            msg = await pubsub.get_message(timeout=0.05)
            if msg and msg.get("type") == "message":
                try:
                    await websocket.send_text(msg["data"])
                except Exception:
                    break
            await asyncio.sleep(0)

    async def _ping_loop() -> None:
        """Send periodic PING to keep the connection alive."""
        while True:
            await asyncio.sleep(PING_INTERVAL)
            try:
                await websocket.send_json({"type": "PING"})
            except Exception:
                break

    relay_task = asyncio.create_task(_relay_messages())
    ping_task = asyncio.create_task(_ping_loop())

    try:
        while True:
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=0.1)
                try:
                    msg = json.loads(data)
                    if msg.get("type") == "PING":
                        await websocket.send_json({"type": "PONG"})
                except Exception:
                    pass
            except asyncio.TimeoutError:
                pass
            except WebSocketDisconnect:
                break
    finally:
        relay_task.cancel()
        ping_task.cancel()
        try:
            await pubsub.close()
        except Exception:
            pass
