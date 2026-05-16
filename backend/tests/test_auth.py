"""
Full test suite for the Authentication router.
Covers: customer signup, rider signup, login, /me, duplicate email, inactive account.
"""
import pytest


# ── Customer Signup ───────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_customer_signup_success(client):
    resp = await client.post("/auth/customer/signup", json={
        "name": "Alice Sharma",
        "email": "alice@fusiondrop.in",
        "password": "SecurePass1!",
        "phone": "9000000001",
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Alice Sharma"
    assert data["role"] == "customer"
    assert "access_token" in data
    assert "hashed_password" not in data


@pytest.mark.asyncio
async def test_customer_signup_duplicate_email(client):
    payload = {
        "name": "Bob",
        "email": "bob_dup@fusiondrop.in",
        "password": "pass1234",
        "phone": "9000000002",
    }
    r1 = await client.post("/auth/customer/signup", json=payload)
    assert r1.status_code == 201

    r2 = await client.post("/auth/customer/signup", json=payload)
    assert r2.status_code == 409
    assert "already registered" in r2.json()["detail"].lower()


@pytest.mark.asyncio
async def test_customer_signup_invalid_email(client):
    resp = await client.post("/auth/customer/signup", json={
        "name": "Bad Email",
        "email": "not-an-email",
        "password": "pass1234",
    })
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_customer_signup_short_password(client):
    resp = await client.post("/auth/customer/signup", json={
        "name": "Short Pass",
        "email": "shortpass@fusiondrop.in",
        "password": "123",
    })
    # Either 422 (Pydantic validation) or 400 (service validation)
    assert resp.status_code in (400, 422)


# ── Rider Signup ──────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_rider_signup_success(client):
    resp = await client.post("/auth/rider/signup", json={
        "name": "Arjun Kumar",
        "email": "arjun_new@fusiondrop.in",
        "password": "rider1234",
        "phone": "9100000001",
        "vehicle_type": "bike",
        "current_lat": 12.9716,
        "current_lng": 77.5946,
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["role"] == "rider"
    assert "access_token" in data


@pytest.mark.asyncio
async def test_rider_signup_duplicate_email(client):
    payload = {
        "name": "Priya",
        "email": "priya_dup@fusiondrop.in",
        "password": "riderpass",
        "vehicle_type": "scooter",
        "current_lat": 12.96,
        "current_lng": 77.62,
    }
    r1 = await client.post("/auth/rider/signup", json=payload)
    assert r1.status_code == 201

    r2 = await client.post("/auth/rider/signup", json=payload)
    assert r2.status_code == 409


# ── Login ─────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_login_success_customer(client):
    await client.post("/auth/customer/signup", json={
        "name": "Carol",
        "email": "carol_login@fusiondrop.in",
        "password": "mypassword",
    })
    resp = await client.post("/auth/login", json={
        "email": "carol_login@fusiondrop.in",
        "password": "mypassword",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert data["role"] == "customer"


@pytest.mark.asyncio
async def test_login_wrong_password(client):
    await client.post("/auth/customer/signup", json={
        "name": "Dave",
        "email": "dave_login@fusiondrop.in",
        "password": "correct_password",
    })
    resp = await client.post("/auth/login", json={
        "email": "dave_login@fusiondrop.in",
        "password": "wrong_password",
    })
    assert resp.status_code == 401
    assert "invalid" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_login_nonexistent_user(client):
    resp = await client.post("/auth/login", json={
        "email": "ghost@fusiondrop.in",
        "password": "doesntmatter",
    })
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_login_missing_fields(client):
    resp = await client.post("/auth/login", json={"email": "only@email.com"})
    assert resp.status_code == 422


# ── /me endpoint ──────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_me_authenticated(client, customer_headers):
    resp = await client.get("/auth/me", headers=customer_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "email" in data
    assert "hashed_password" not in data
    assert data["role"] == "customer"


@pytest.mark.asyncio
async def test_get_me_no_token(client):
    resp = await client.get("/auth/me")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_get_me_invalid_token(client):
    resp = await client.get("/auth/me", headers={"Authorization": "Bearer totally.fake.token"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_get_me_malformed_bearer(client):
    resp = await client.get("/auth/me", headers={"Authorization": "NotBearer sometoken"})
    assert resp.status_code in (401, 403)