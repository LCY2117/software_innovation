"""Auth endpoints: /api/v1/auth/"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas import (
    ApiResponse, ERR_VALIDATION, ERR_UNAUTHENTICATED,
    LoginRequest, RegisterRequest, RefreshRequest, SendCodeRequest, TokenResponse,
)
from app.services.auth_service import (
    create_access_token, create_refresh_token, get_or_create_user,
    send_sms_code, store_refresh_token, validate_refresh_token, verify_sms_code,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/send_code")
async def send_code(req: SendCodeRequest) -> ApiResponse[dict]:
    """Send an SMS verification code to the given phone number."""
    if not req.phone or len(req.phone) < 7:
        return ApiResponse.error(ERR_VALIDATION, "Invalid phone number")
    code = await send_sms_code(req.phone)
    # In prod the code is sent via SMS; in dev it's returned in response for convenience
    return ApiResponse.ok({"sent": True, "devCode": code})


@router.post("/register")
async def register(req: RegisterRequest, db: AsyncSession = Depends(get_db)) -> ApiResponse[TokenResponse]:
    valid = await verify_sms_code(req.phone, req.code)
    if not valid:
        return ApiResponse.error(ERR_VALIDATION, "Invalid or expired verification code")
    user = await get_or_create_user(db, req.phone, req.name)
    access = create_access_token(user.id)
    refresh = create_refresh_token(user.id)
    await store_refresh_token(user.id, refresh)
    return ApiResponse.ok(TokenResponse(
        accessToken=access, refreshToken=refresh,
        userId=user.id, phone=user.phone,
    ))


@router.post("/login")
async def login(req: LoginRequest, db: AsyncSession = Depends(get_db)) -> ApiResponse[TokenResponse]:
    valid = await verify_sms_code(req.phone, req.code)
    if not valid:
        return ApiResponse.error(ERR_VALIDATION, "Invalid or expired verification code")
    user = await get_or_create_user(db, req.phone)
    access = create_access_token(user.id)
    refresh = create_refresh_token(user.id)
    await store_refresh_token(user.id, refresh)
    return ApiResponse.ok(TokenResponse(
        accessToken=access, refreshToken=refresh,
        userId=user.id, phone=user.phone,
    ))


@router.post("/refresh")
async def refresh_token(req: RefreshRequest, db: AsyncSession = Depends(get_db)) -> ApiResponse[TokenResponse]:
    from sqlalchemy import select
    from app.models.user import User

    user_id = await validate_refresh_token(req.refreshToken)
    if not user_id:
        return ApiResponse.error(ERR_UNAUTHENTICATED, "Invalid or expired refresh token")
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        return ApiResponse.error(ERR_UNAUTHENTICATED, "User not found")
    access = create_access_token(user.id)
    refresh = create_refresh_token(user.id)
    await store_refresh_token(user.id, refresh)
    return ApiResponse.ok(TokenResponse(
        accessToken=access, refreshToken=refresh,
        userId=user.id, phone=user.phone,
    ))


@router.post("/logout")
async def logout() -> ApiResponse[dict]:
    return ApiResponse.ok({"ok": True})
