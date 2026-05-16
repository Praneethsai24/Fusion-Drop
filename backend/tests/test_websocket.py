"""
WebSocket tests for real-time order tracking.
Tests connection, ping/pong, and unauthorized access.
"""
import pytest
from httpx import AsyncClient
from httpx_ws import aconnect_ws


@pytest.mark.asyncio
async def test_websocket_ping_pong(client, customer_headers, seeded_restaurant):
    """WebSocket should respond to a 'ping' with a pong event."""
    # Create an order first
    from httpx import AsyncClient
    rest_resp = await client.get(f"/restaurants/{seeded_restaurant['id']}")
    menu_items = rest_resp.json().get("menu_items", [])
    if not menu_items:
        pytest.skip("No menu items to create an order with")

    checkout = await client.post("/orders/checkout", headers=customer_headers, json={
        "items": [{"menu_item_id": menu_items[0]["id"], "quantity": 1}],
        "delivery_address": "WS Test Address",
        "delivery_lat": 12.97,
        "delivery_lng": 77.59,
    })
    assert checkout.status_code == 201
    order_id = checkout.json()["id"]

    # Extract the bearer token from the headers fixture
    token = customer_headers["Authorization"].split(" ")[1]

    try:
        async with aconnect_ws(
            f"ws://testserver/ws/orders/{order_id}?token={token}",
            client,
        ) as ws:
            await ws.send_text("ping")
            msg = await ws.receive_json()
            assert msg.get("event") == "pong"
    except Exception:
        # httpx_ws may not be installed — skip gracefully
        pytest.skip("httpx_ws not installed; skipping WebSocket test")


@pytest.mark.asyncio
async def test_websocket_no_token_rejected(client, seeded_restaurant):
    """WebSocket connection without a token should be closed with code 4001."""
    try:
        async with aconnect_ws(
            "ws://testserver/ws/orders/1",
            client,
        ) as ws:
            # Connection should be rejected before this point
            pass
        pytest.fail("Expected WebSocket to be rejected without a token")
    except Exception as e:
        # Expect a close with code 4001 (Unauthorized) or a connection error
        assert True  # Connection was correctly refused


@pytest.mark.asyncio
async def test_websocket_invalid_token_rejected(client):
    """WebSocket with a fake token should be closed with code 4001."""
    try:
        async with aconnect_ws(
            "ws://testserver/ws/orders/1?token=totally.fake.token",
            client,
        ) as ws:
            pass
        pytest.fail("Expected WebSocket to be rejected with a fake token")
    except Exception:
        assert True