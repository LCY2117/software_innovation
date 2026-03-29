from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


class RegisterRequest(BaseModel):
    phone: str
    code: str          # SMS verification code
    name: Optional[str] = None


class LoginRequest(BaseModel):
    phone: str
    code: str


class SendCodeRequest(BaseModel):
    phone: str


class TokenResponse(BaseModel):
    accessToken: str
    refreshToken: str
    userId: str
    phone: str


class RefreshRequest(BaseModel):
    refreshToken: str
