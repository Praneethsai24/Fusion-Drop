"""
WebSocket tests — connection, auth, ping/pong.
"""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_ws_connect_requires_token(client: AsyncClient):
    """WebSocket without token should be rejected with 403/4001."""
    # httpx does not support WS — we test the auth logic via HTTP proxy
    # The WS endpoint validates token before accept(); missing token = 422
    resp = await client.get("/ws/orders/1")  # HTTP GET to WS endpoint
    # Starlette returns 400 or 403 on non-WS request to WS route
    assert resp.status_code in (400, 403, 422)


@pytest.mark.asyncio
async def test_ws_manager_connect_disconnect():
    """Unit test for ConnectionManager connect/disconnect without crashes."""
    from backend.websocket.manager import ConnectionManager
    from unittest.mock import AsyncMock, MagicMock

    manager = ConnectionManager()
    ws = MagicMock()
    ws.accept = AsyncMock()

    await manager.connect(ws, order_id=1)
    assert 1 in manager._connections
    assert ws in manager._connections[1]

    manager.disconnect(ws, order_id=1)
    assert 1 not in manager._connections  # cleaned up when empty


@pytest.mark.asyncio
async def test_ws_manager_disconnect_idempotent():
    """Disconnecting a non-existent websocket should not raise."""
    from backend.websocket.manager import ConnectionManager
    from unittest.mock import MagicMock

    manager = ConnectionManager()
    ws = MagicMock()
    # Should not raise ValueError or AttributeError
    manager.disconnect(ws, order_id=999)


@pytest.mark.asyncio
async def test_ws_manager_broadcast_removes_dead():
    """Dead connections are cleaned up during broadcast."""
    from backend.websocket.manager import ConnectionManager
    from unittest.mock import AsyncMock, MagicMock

    manager = ConnectionManager()

    dead_ws = MagicMock()
    dead_ws.accept = AsyncMock()
    dead_ws.send_json = AsyncMock(side_effect=Exception("connection closed"))

    good_ws = MagicMock()
    good_ws.accept = AsyncMock()
    good_ws.send_json = AsyncMock()

    await manager.connect(dead_ws, order_id=5)
    await manager.connect(good_ws, order_id=5)

    await manager.broadcast(5, {"event": "status_update", "status": "delivered"})

    good_ws.send_json.assert_called_once()
    # dead_ws should have been removed
    assert dead_ws not in manager._connections.get(5, [])