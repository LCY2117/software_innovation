"""Geo / AED endpoints: /api/v1/geo/"""
from __future__ import annotations

import json
import math
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.incident import AedLocation
from app.redis_client import get_redis
from app.schemas import ApiResponse, ERR_VALIDATION, LocationUpdate, NearbyAed

router = APIRouter(prefix="/geo", tags=["geo"])

EARTH_RADIUS_M = 6_371_000.0


def _haversine(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Return distance in metres between two WGS-84 coordinates."""
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lng2 - lng1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
    return 2 * EARTH_RADIUS_M * math.asin(math.sqrt(a))


@router.post("/location")
async def report_location(req: LocationUpdate) -> ApiResponse[dict]:
    """User reports their current location; stored in Redis GEO."""
    redis = get_redis()
    await redis.set(f"geo:user:{req.userId}", json.dumps({"lat": req.lat, "lng": req.lng}), ex=120)
    return ApiResponse.ok({"ok": True})


@router.get("/aed/nearby")
async def nearby_aed(
    lat: float = Query(..., description="Latitude"),
    lng: float = Query(..., description="Longitude"),
    r: float = Query(1000.0, description="Search radius in metres"),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[list[NearbyAed]]:
    """Return up to 5 active AEDs within radius r of (lat, lng)."""
    result = await db.execute(
        select(AedLocation).where(AedLocation.is_active.is_(True))
    )
    aeds = result.scalars().all()

    nearby = []
    for aed in aeds:
        dist = _haversine(lat, lng, aed.lat, aed.lng)
        if dist <= r:
            nearby.append(
                NearbyAed(
                    id=aed.id,
                    name=aed.name,
                    lat=aed.lat,
                    lng=aed.lng,
                    address=aed.address,
                    floor=aed.floor,
                    distM=round(dist, 1),
                )
            )
    nearby.sort(key=lambda x: x.distM)
    return ApiResponse.ok(nearby[:5])


@router.get("/route")
async def get_route(
    fromLat: float = Query(...),
    fromLng: float = Query(...),
    toLat: float = Query(...),
    toLng: float = Query(...),
    mode: str = Query("walking"),
) -> ApiResponse[dict]:
    """Return a stub walking route. In production, delegate to Amap/Google Maps."""
    dist = _haversine(fromLat, fromLng, toLat, toLng)
    walking_speed_ms = 1.4  # m/s average walking speed
    duration_sec = int(dist / walking_speed_ms)
    return ApiResponse.ok({
        "distanceM": round(dist, 1),
        "durationSec": duration_sec,
        "mode": mode,
        "note": "Stub route – integrate Amap/Google Maps in production",
    })
