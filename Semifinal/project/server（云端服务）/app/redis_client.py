"""Redis client with graceful in-memory fallback.

When REDIS_URL is not configured the system uses a simple in-memory dict-based
implementation so the server works out of the box without a Redis instance.
Real Redis is required for multi-instance / production deployments.
"""
from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# In-memory fallback
# ---------------------------------------------------------------------------

class _InMemoryRedis:
    """Minimal Redis-like store for single-process dev/test."""

    def __init__(self) -> None:
        self._data: dict[str, Any] = {}
        self._expiry: dict[str, float] = {}
        self._pubsub_listeners: dict[str, list[asyncio.Queue]] = {}

    async def _is_expired(self, key: str) -> bool:
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            return False
        exp = self._expiry.get(key)
        if exp is None:
            return False
        return loop.time() > exp

    async def set(self, key: str, value: str, ex: Optional[int] = None) -> None:
        self._data[key] = value
        if ex is not None:
            try:
                loop = asyncio.get_running_loop()
                self._expiry[key] = loop.time() + ex
            except RuntimeError:
                pass
        else:
            self._expiry.pop(key, None)

    async def get(self, key: str) -> Optional[str]:
        if await self._is_expired(key):
            self._data.pop(key, None)
            self._expiry.pop(key, None)
            return None
        return self._data.get(key)

    async def delete(self, *keys: str) -> None:
        for key in keys:
            self._data.pop(key, None)
            self._expiry.pop(key, None)

    async def exists(self, key: str) -> bool:
        if await self._is_expired(key):
            self._data.pop(key, None)
            return False
        return key in self._data

    async def publish(self, channel: str, message: str) -> None:
        for q in self._pubsub_listeners.get(channel, []):
            await q.put(message)

    def pubsub(self) -> "_InMemoryPubSub":
        return _InMemoryPubSub(self)


class _InMemoryPubSub:
    def __init__(self, store: _InMemoryRedis) -> None:
        self._store = store
        self._queue: asyncio.Queue = asyncio.Queue()
        self._channels: set[str] = set()

    async def subscribe(self, *channels: str) -> None:
        for ch in channels:
            self._store._pubsub_listeners.setdefault(ch, []).append(self._queue)
            self._channels.add(ch)

    async def unsubscribe(self, *channels: str) -> None:
        for ch in channels:
            listeners = self._store._pubsub_listeners.get(ch, [])
            if self._queue in listeners:
                listeners.remove(self._queue)
            self._channels.discard(ch)

    async def get_message(self, timeout: float = 0.1) -> Optional[dict]:
        try:
            msg = await asyncio.wait_for(self._queue.get(), timeout=timeout)
            return {"type": "message", "data": msg}
        except asyncio.TimeoutError:
            return None

    async def close(self) -> None:
        await self.unsubscribe(*list(self._channels))


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

_redis_client: Any = None
_fallback: _InMemoryRedis = _InMemoryRedis()


async def init_redis(redis_url: Optional[str] = None) -> None:
    """Initialize Redis connection. Falls back to in-memory if URL is absent."""
    global _redis_client
    if redis_url:
        try:
            import redis.asyncio as aioredis  # type: ignore
            _redis_client = aioredis.from_url(redis_url, decode_responses=True)
            await _redis_client.ping()
            logger.info("Redis connected: %s", redis_url)
        except Exception as exc:
            logger.warning("Redis connection failed (%s) — using in-memory fallback", exc)
            _redis_client = None
    else:
        logger.info("REDIS_URL not set — using in-memory fallback")


def get_redis() -> Any:
    return _redis_client or _fallback


def get_pubsub() -> Any:
    client = _redis_client or _fallback
    return client.pubsub()
