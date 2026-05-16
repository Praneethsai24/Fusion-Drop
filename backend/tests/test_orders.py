"""
Full test suite for the Orders router.
Covers: checkout, order history, order fetch, status update, access control.
"""
import pytest


# ── Checkout ──────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_checkout_creates_order(client, customer_headers, seeded_restaurant):
    menu_resp = await client.get(f"/restaurants/{seeded_restaurant['id']}/menu")
    # If dedicated menu endpoint doesn't exist, fetch the restaurant and use menu_items
    if menu_resp.status_code == 404:
        rest_resp = await client.get(f"/restaurants/{seeded_restaurant['id']}")
        menu_items = rest_resp.json().get("menu_items", [])
    else:
        menu_items = menu_resp.json()

    assert len(menu_items) > 0, "No menu items available for checkout test"
    item_id = menu_items[0]["id"]

    resp = await client.post("/orders/checkout", headers=customer_headers, json={
        "items": [{"menu_item_id": item_id, "quantity": 2}],
        "delivery_address": "456 Test Avenue, Bengaluru",
        "delivery_lat": 12.9300,
        "delivery_lng": 77.6200,
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["status"] == "order_received"
    assert data["total_amount"] > 0
    assert data["delivery_fee"] >= 0
    assert isinstance(data["items"], list)
    assert len(data["items"]) == 1
    assert data["items"][0]["quantity"] == 2


@pytest.mark.asyncio
async def test_checkout_requires_auth(client, seeded_restaurant):
    resp = await client.post("/orders/checkout", json={
        "items": [{"menu_item_id": 1, "quantity": 1}],
        "delivery_address": "Test",
        "delivery_lat": 12.97,
        "delivery_lng": 77.59,
    })
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_checkout_empty_items(client, customer_headers):
    resp = await client.post("/orders/checkout", headers=customer_headers, json={
        "items": [],
        "delivery_address": "Test Address",
        "delivery_lat": 12.97,
        "delivery_lng": 77.59,
    })
    assert resp.status_code in (400, 422)


@pytest.mark.asyncio
async def test_checkout_nonexistent_menu_item(client, customer_headers):
    resp = await client.post("/orders/checkout", headers=customer_headers, json={
        "items": [{"menu_item_id": 999999, "quantity": 1}],
        "delivery_address": "Test Address",
        "delivery_lat": 12.97,
        "delivery_lng": 77.59,
    })
    assert resp.status_code in (400, 404, 422)


@pytest.mark.asyncio
async def test_checkout_zero_quantity(client, customer_headers, seeded_restaurant):
    rest_resp = await client.get(f"/restaurants/{seeded_restaurant['id']}")
    menu_items = rest_resp.json().get("menu_items", [])
    if not menu_items:
        pytest.skip("No menu items available")

    resp = await client.post("/orders/checkout", headers=customer_headers, json={
        "items": [{"menu_item_id": menu_items[0]["id"], "quantity": 0}],
        "delivery_address": "Test",
        "delivery_lat": 12.97,
        "delivery_lng": 77.59,
    })
    assert resp.status_code in (400, 422)


# ── Order History ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_my_orders_empty(client, customer_headers):
    resp = await client.get("/orders/my", headers=customer_headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_my_orders_after_checkout(client, customer_headers, seeded_restaurant):
    rest_resp = await client.get(f"/restaurants/{seeded_restaurant['id']}")
    menu_items = rest_resp.json().get("menu_items", [])
    if not menu_items:
        pytest.skip("No menu items available")

    await client.post("/orders/checkout", headers=customer_headers, json={
        "items": [{"menu_item_id": menu_items[0]["id"], "quantity": 1}],
        "delivery_address": "History Test",
        "delivery_lat": 12.97,
        "delivery_lng": 77.59,
    })
    resp = await client.get("/orders/my", headers=customer_headers)
    assert resp.status_code == 200
    orders = resp.json()
    assert len(orders) >= 1


@pytest.mark.asyncio
async def test_my_orders_requires_auth(client):
    resp = await client.get("/orders/my")
    assert resp.status_code == 401


# ── Get Single Order ──────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_order_success(client, customer_headers, seeded_restaurant):
    rest_resp = await client.get(f"/restaurants/{seeded_restaurant['id']}")
    menu_items = rest_resp.json().get("menu_items", [])
    if not menu_items:
        pytest.skip("No menu items available")

    checkout_resp = await client.post("/orders/checkout", headers=customer_headers, json={
        "items": [{"menu_item_id": menu_items[0]["id"], "quantity": 1}],
        "delivery_address": "Single Order Test",
        "delivery_lat": 12.97,
        "delivery_lng": 77.59,
    })
    order_id = checkout_resp.json()["id"]

    resp = await client.get(f"/orders/{order_id}", headers=customer_headers)
    assert resp.status_code == 200
    assert resp.json()["id"] == order_id


@pytest.mark.asyncio
async def test_get_order_not_found(client, customer_headers):
    resp = await client.get("/orders/999999", headers=customer_headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_order_other_user_denied(client, seeded_restaurant):
    """A second customer should NOT be able to view another customer's order."""
    # Sign up customer A
    await client.post("/auth/customer/signup", json={
        "name": "Customer A",
        "email": "cust_a@fusiondrop.in",
        "password": "passA1234",
    })
    resp_a = await client.post("/auth/login", json={
        "email": "cust_a@fusiondrop.in", "password": "passA1234"
    })
    headers_a = {"Authorization": f"Bearer {resp_a.json()['access_token']}"}

    # Sign up customer B
    await client.post("/auth/customer/signup", json={
        "name": "Customer B",
        "email": "cust_b@fusiondrop.in",
        "password": "passB1234",
    })
    resp_b = await client.post("/auth/login", json={
        "email": "cust_b@fusiondrop.in", "password": "passB1234"
    })
    headers_b = {"Authorization": f"Bearer {resp_b.json()['access_token']}"}

    # Customer A places an order
    rest_resp = await client.get(f"/restaurants/{seeded_restaurant['id']}")
    menu_items = rest_resp.json().get("menu_items", [])
    if not menu_items:
        pytest.skip("No menu items available")

    checkout = await client.post("/orders/checkout", headers=headers_a, json={
        "items": [{"menu_item_id": menu_items[0]["id"], "quantity": 1}],
        "delivery_address": "A's address",
        "delivery_lat": 12.97,
        "delivery_lng": 77.59,
    })
    order_id = checkout.json()["id"]

    # Customer B tries to access A's order
    resp = await client.get(f"/orders/{order_id}", headers=headers_b)
    assert resp.status_code == 403


# ── Status Update ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_update_order_status(client, customer_headers, rider_headers, seeded_restaurant):
    rest_resp = await client.get(f"/restaurants/{seeded_restaurant['id']}")
    menu_items = rest_resp.json().get("menu_items", [])
    if not menu_items:
        pytest.skip("No menu items available")

    checkout = await client.post("/orders/checkout", headers=customer_headers, json={
        "items": [{"menu_item_id": menu_items[0]["id"], "quantity": 1}],
        "delivery_address": "Status Update Test",
        "delivery_lat": 12.97,
        "delivery_lng": 77.59,
    })
    order_id = checkout.json()["id"]

    resp = await client.patch(
        f"/orders/{order_id}/status",
        headers=rider_headers,
        json={"status": "rider_assigned"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "rider_assigned"


@pytest.mark.asyncio
async def test_update_order_status_invalid(client, customer_headers, seeded_restaurant):
    rest_resp = await client.get(f"/restaurants/{seeded_restaurant['id']}")
    menu_items = rest_resp.json().get("menu_items", [])
    if not menu_items:
        pytest.skip("No menu items available")

    checkout = await client.post("/orders/checkout", headers=customer_headers, json={
        "items": [{"menu_item_id": menu_items[0]["id"], "quantity": 1}],
        "delivery_address": "Invalid Status Test",
        "delivery_lat": 12.97,
        "delivery_lng": 77.59,
    })
    order_id = checkout.json()["id"]

    resp = await client.patch(
        f"/orders/{order_id}/status",
        headers=customer_headers,
        json={"status": "flying_to_moon"},
    )
    assert resp.status_code == 400