"""Task API tests — simplified for SQLite test environment."""
import pytest
from unittest.mock import patch, AsyncMock

@pytest.mark.asyncio
async def test_health_endpoint(client):
    r = await client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"

@pytest.mark.asyncio
async def test_ready_endpoint(client):
    r = await client.get("/ready")
    # 503 expected since no real postgres/redis in test, but endpoint must respond
    assert r.status_code in (200, 503)

@pytest.mark.asyncio
async def test_tasks_requires_auth(client):
    r = await client.get("/api/v1/tasks")
    assert r.status_code == 401

@pytest.mark.asyncio
async def test_dashboard_requires_auth(client):
    r = await client.get("/api/v1/dashboard/stats")
    assert r.status_code == 401

@pytest.mark.asyncio
async def test_audit_logs_requires_auth(client):
    r = await client.get("/api/v1/audit/logs")
    assert r.status_code == 401
