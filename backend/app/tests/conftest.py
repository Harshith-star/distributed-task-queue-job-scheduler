"""Test fixtures — async SQLite, no real Postgres or Redis needed."""
import asyncio, os, sys, tempfile
import pytest, pytest_asyncio
os.environ["DATABASE_URL"]        = f"sqlite+aiosqlite:///{tempfile.mktemp(suffix='.db')}"
os.environ["SECRET_KEY"]          = "test-secret-key-not-for-production-at-all"
os.environ["CELERY_BROKER_URL"]   = "memory://"
os.environ["CELERY_RESULT_BACKEND"] = "cache+memory://"
os.environ["REDIS_URL"]           = "redis://localhost:6379/0"

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

import fakeredis.aioredis
from httpx import ASGITransport, AsyncClient
from app.main import create_app
from app.core.database import Base, engine
import app.core.redis as redis_module

app = create_app()
# FakeRedis is set per-test via autouse fixture

@pytest_asyncio.fixture(autouse=True, scope="session")
async def _schema():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

@pytest_asyncio.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c

@pytest_asyncio.fixture
async def auth_headers(client):
    await client.post("/api/v1/auth/register", json={"email": "user@test.com", "full_name": "Test User", "password": "Password1"})
    resp = await client.post("/api/v1/auth/login", json={"email": "user@test.com", "password": "Password1"})
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}

@pytest.fixture(autouse=True)
def _fresh_fake_redis():
    redis_module._redis_client = fakeredis.aioredis.FakeRedis(decode_responses=True)
    yield
    redis_module._redis_client = None
