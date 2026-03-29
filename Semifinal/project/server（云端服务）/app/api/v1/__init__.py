from fastapi import APIRouter

from app.api.v1.auth import router as auth_router
from app.api.v1.incidents import router as incidents_router
from app.api.v1.geo import router as geo_router

v1_router = APIRouter(prefix="/api/v1")
v1_router.include_router(auth_router)
v1_router.include_router(incidents_router)
v1_router.include_router(geo_router)
