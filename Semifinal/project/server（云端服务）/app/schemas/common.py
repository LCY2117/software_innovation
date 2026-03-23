from __future__ import annotations

import uuid
from typing import Any, Generic, Optional, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    """Unified API response envelope."""
    code: int = 0
    msg: str = "ok"
    data: Optional[T] = None
    traceId: str = ""

    @classmethod
    def ok(cls, data: T, trace_id: str = "") -> "ApiResponse[T]":
        return cls(code=0, msg="ok", data=data, traceId=trace_id or str(uuid.uuid4())[:8])

    @classmethod
    def error(cls, code: int, msg: str, trace_id: str = "") -> "ApiResponse[None]":
        return cls(code=code, msg=msg, data=None, traceId=trace_id or str(uuid.uuid4())[:8])


# Standard error codes
ERR_VALIDATION = 40001
ERR_UNAUTHENTICATED = 40101
ERR_FORBIDDEN = 40301
ERR_NOT_FOUND = 40401
ERR_ROLE_OCCUPIED = 40901
ERR_INTERNAL = 50001
