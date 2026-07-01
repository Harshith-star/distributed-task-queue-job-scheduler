"""Authentication endpoint tests."""
import pytest

@pytest.mark.asyncio
async def test_register_and_login(client):
    r = await client.post("/api/v1/auth/register", json={"email": "alice@t.com", "full_name": "Alice", "password": "Password1"})
    assert r.status_code == 201
    r = await client.post("/api/v1/auth/login", json={"email": "alice@t.com", "password": "Password1"})
    assert r.status_code == 200
    assert "access_token" in r.json()

@pytest.mark.asyncio
async def test_duplicate_email(client):
    body = {"email": "dup@t.com", "full_name": "Dup", "password": "Password1"}
    await client.post("/api/v1/auth/register", json=body)
    r = await client.post("/api/v1/auth/register", json=body)
    assert r.status_code == 409

@pytest.mark.asyncio
async def test_wrong_password(client):
    await client.post("/api/v1/auth/register", json={"email": "bob@t.com", "full_name": "Bob", "password": "Password1"})
    r = await client.post("/api/v1/auth/login", json={"email": "bob@t.com", "password": "Wrong1234"})
    assert r.status_code == 401

@pytest.mark.asyncio
async def test_me_requires_token(client):
    r = await client.get("/api/v1/auth/me")
    assert r.status_code == 401

@pytest.mark.asyncio
async def test_me_with_token(client, auth_headers):
    r = await client.get("/api/v1/auth/me", headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["email"] == "user@test.com"
