"""
WebSocket manager backed by Redis pub/sub.

FIX: Removed .discard() call on list in disconnect().
     Lists have no .discard() method — this raised AttributeError on
     every WebSocket disconnect, crashing the connection handler.
     (Blocker #4 — AttributeError: 'list' object has no attribute 'discard')

ALSO FIXED: `from backend.config import get_settings` →
            `from backend.core.config import get_settings`
"""
import json
from typing import Dict, List
from fastapi import WebSocket
import redis.asyncio as aioredis
from backend.core.config import get_settings  # FIXED import path
from backend.core.logging import get_logger

settings = get_settings()
logger = get_logger(__name__)


class ConnectionManager:
    def __init__(self):
        self._connections: Dict[int, List[WebSocket]] = {}
        self._redis: aioredis.Redis | None = None

    async def _get_redis(self) -> aioredis.Redis:
        if self._redis is None:
            self._redis = aioredis.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=True,
                socket_connect_timeout=5,
            )
        return self._redis

    async def connect(self, websocket: WebSocket, order_id: int) -> None:
        await websocket.accept()
        self._connections.setdefault(order_id, []).append(websocket)
        logger.info("ws_connect", order_id=order_id,
                    total=len(self._connections[order_id]))

    def disconnect(self, websocket: WebSocket, order_id: int) -> None:
        """
        Remove websocket from connection list.
        FIX: Removed .discard() call — lists don't have .discard().
        Only .remove() is used, wrapped in try/except for safety.
        """
        if order_id in self._connections:
            try:
                self._connections[order_id].remove(websocket)
            except ValueError:
                pass  # Already removed — safe to ignore
            if not self._connections[order_id]:
                del self._connections[order_id]
        logger.info("ws_disconnect", order_id=order_id)

    async def broadcast(self, order_id: int, event: dict) -> None:
        """Send to all local WebSocket connections for this order."""
        connections = list(self._connections.get(order_id, []))
        dead: List[WebSocket] = []
        for ws in connections:
            try:
                await ws.send_json(event)
            except Exception as exc:
                logger.warning("ws_send_error", order_id=order_id, error=str(exc))
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws, order_id)

    async def publish(self, order_id: int, event: dict) -> None:
        """Publish to Redis channel with local broadcast fallback."""
        try:
            redis = await self._get_redis()
            await redis.publish(f"order:{order_id}:events", json.dumps(event))
        except Exception as exc:
            logger.warning("redis_publish_failed", order_id=order_id,
                           error=str(exc), fallback="local_broadcast")
            await self.broadcast(order_id, event)

    async def close(self) -> None:
        """Gracefully close Redis on shutdown."""
        if self._redis is not None:
            await self._redis.aclose()
            self._redis = None


ws_manager = ConnectionManager()