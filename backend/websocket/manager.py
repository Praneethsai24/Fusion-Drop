"""
WebSocket manager backed by Redis pub/sub.
Supports horizontal scaling — multiple server instances share state via Redis.
"""
import json
import asyncio
from typing import Dict, List
from fastapi import WebSocket
import redis.asyncio as aioredis
from backend.config import get_settings
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
            )
        return self._redis

    async def connect(self, websocket: WebSocket, order_id: int) -> None:
        await websocket.accept()
        self._connections.setdefault(order_id, []).append(websocket)
        logger.info("ws_connect", order_id=order_id,
                    total=len(self._connections[order_id]))

    def disconnect(self, websocket: WebSocket, order_id: int) -> None:
        if order_id in self._connections:
            self._connections[order_id].discard(websocket) \
                if hasattr(self._connections[order_id], "discard") \
                else None
            try:
                self._connections[order_id].remove(websocket)
            except ValueError:
                pass
            if not self._connections[order_id]:
                del self._connections[order_id]
        logger.info("ws_disconnect", order_id=order_id)

    async def broadcast(self, order_id: int, event: dict) -> None:
        """Send to all local WebSocket connections for this order."""
        connections = self._connections.get(order_id, [])
        dead = []
        for ws in connections:
            try:
                await ws.send_json(event)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws, order_id)

    async def publish(self, order_id: int, event: dict) -> None:
        """Publish to Redis channel — works across multiple server instances."""
        try:
            redis = await self._get_redis()
            channel = f"order:{order_id}:events"
            await redis.publish(channel, json.dumps(event))
        except Exception as e:
            logger.warning("redis_publish_error", order_id=order_id, error=str(e))
            # Fallback: broadcast locally
            await self.broadcast(order_id, event)

    async def subscribe_and_relay(self, order_id: int) -> None:
        """Subscribe to Redis channel and relay messages to local WebSocket clients."""
        try:
            redis = await self._get_redis()
            pubsub = redis.pubsub()
            channel = f"order:{order_id}:events"
            await pubsub.subscribe(channel)
            async for message in pubsub.listen():
                if message["type"] == "message":
                    event = json.loads(message["data"])
                    await self.broadcast(order_id, event)
        except Exception as e:
            logger.error("redis_subscribe_error", order_id=order_id, error=str(e))


ws_manager = ConnectionManager()