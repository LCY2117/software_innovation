"""Auth service: phone + JWT authentication.

In dev/demo mode any 6-digit code is accepted so the system works without an
SMS provider. Set REQUIRE_REAL_SMS=true in production to enforce real codes.
"""
from __future__ import annotations

import logging
import random
import string
from datetime import datetime, timedelta, timezone
from typing import Optional

from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.user import User
from app.redis_client import get_redis

settings = get_settings()
logger = logging.getLogger(__name__)

_SMS_CODE_TTL = 300  # 5 minutes
_SMS_CODE_PREFIX = "sms:code:"


def _generate_code() -> str:
    return "".join(random.choices(string.digits, k=6))


async def send_sms_code(phone: str) -> str:
    """Generate and 'send' an SMS code. Returns the code (for dev convenience)."""
    code = _generate_code()
    redis = get_redis()
    await redis.set(f"{_SMS_CODE_PREFIX}{phone}", code, ex=_SMS_CODE_TTL)
    # In production: call SMS provider here
    logger.info("SMS code for %s: %s", phone[:3] + "****" + phone[-2:], code)
    return code


async def verify_sms_code(phone: str, code: str) -> bool:
    """Verify an SMS code. Dev mode accepts any 6-digit code."""
    if settings.debug:
        # Accept any 6-digit code in debug mode
        if len(code) == 6 and code.isdigit():
            return True
    redis = get_redis()
    stored = await redis.get(f"{_SMS_CODE_PREFIX}{phone}")
    if stored and stored == code:
        await redis.delete(f"{_SMS_CODE_PREFIX}{phone}")
        return True
    return False


async def get_or_create_user(db: AsyncSession, phone: str, name: Optional[str] = None) -> User:
    result = await db.execute(select(User).where(User.phone == phone))
    user = result.scalar_one_or_none()
    if not user:
        user = User(phone=phone, name=name)
        db.add(user)
        await db.commit()
        await db.refresh(user)
    return user


def _create_token(payload: dict, expire_delta: timedelta) -> str:
    to_encode = payload.copy()
    expire = datetime.now(timezone.utc) + expire_delta
    to_encode["exp"] = expire
    return jwt.encode(to_encode, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def create_access_token(user_id: str) -> str:
    return _create_token(
        {"sub": user_id, "type": "access"},
        timedelta(minutes=settings.access_token_expire_minutes),
    )


def create_refresh_token(user_id: str) -> str:
    return _create_token(
        {"sub": user_id, "type": "refresh"},
        timedelta(days=settings.refresh_token_expire_days),
    )


async def store_refresh_token(user_id: str, token: str) -> None:
    redis = get_redis()
    await redis.set(
        f"session:refresh:{user_id}",
        token,
        ex=settings.refresh_token_expire_days * 86400,
    )


async def validate_access_token(token: str) -> Optional[str]:
    """Return user_id if token is valid, else None."""
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        if payload.get("type") != "access":
            return None
        return payload.get("sub")
    except JWTError:
        return None


async def validate_refresh_token(token: str) -> Optional[str]:
    """Return user_id if refresh token is valid and matches stored value."""
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        if payload.get("type") != "refresh":
            return None
        user_id = payload.get("sub")
        if not user_id:
            return None
        redis = get_redis()
        stored = await redis.get(f"session:refresh:{user_id}")
        if stored != token:
            return None
        return user_id
    except JWTError:
        return None
