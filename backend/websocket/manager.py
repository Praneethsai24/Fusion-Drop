"""
WebSocket Connection Manager
------------------------------
Manages active connections grouped by order_id.
Broadcasts delivery status and rider location updates
to all clients watching a specific order.

Usage (from any router or background task):
    from backend.websocket.manager import ws_manager
    await ws_manager.broadcast_order_update(order_id, {...})
"""
import logging
from typing import Dict, List
from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Thread-safe (asyncio-safe) WebSocket connection registry."""

    def __init__(self):
        # { order_id: [WebSocket, ...] }
        self.active: Dict[int, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, order_id: int):
        await websocket.accept()
        self.active.setdefault(order_id, []).append(websocket)
        logger.info(
            f"WS connected: order={order_id}, "
            f"total_connections={len(self.active[order_id])}"
        )

    def disconnect(self, websocket: WebSocket, order_id: int):
        conns = self.active.get(order_id, [])
        if websocket in conns:
            conns.remove(websocket)
        if not conns:
            self.active.pop(order_id, None)
        logger.info(f"WS disconnected: order={order_id}")

    async def _send_to_order(self, order_id: int, payload: dict):
        """Send JSON payload to every client watching order_id."""
        dead = []
        for ws in self.active.get(order_id, []):
            try:
                await ws.send_json(payload)
            except Exception as exc:
                logger.warning(f"WS send failed (order {order_id}): {exc}")
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws, order_id)

    async def broadcast_order_update(self, order_id: int, data: dict):
        """Broadcast an order status change."""
        await self._send_to_order(order_id, {"event": "order_update", "data": data})

    async def broadcast_rider_location(
        self, order_id: int, lat: float, lng: float, eta_minutes: int
    ):
        """Broadcast a rider GPS position update."""
        await self._send_to_order(order_id, {
            "event": "rider_location",
            "data": {
                "order_id": order_id,
                "lat": lat,
                "lng": lng,
                "eta_minutes": eta_minutes,
            },
        })


# Global singleton — import this everywhere
ws_manager = ConnectionManager()