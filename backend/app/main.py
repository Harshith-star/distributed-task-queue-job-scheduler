"""
app/main.py

FastAPI application factory.

Why a factory function (create_app) instead of a module-level app?
  - Testable: each test can create a fresh app with different settings.
  - No side effects at import time (important for Celery workers that
    also import the app).
  - Clear startup/shutdown lifecycle.
"""
import time
from contextlib import asynccontextmanager

import redis.asyncio as aioredis
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.core.config import get_settings
from app.core.database import engine
from app.core.logging import configure_logging, get_logger
from app.core.redis import close_redis, get_redis
from app.exceptions.handlers import register_exception_handlers


configure_logging()
logger = get_logger(__name__)
settings = get_settings()

_startup_time: float = time.time()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application startup and shutdown."""
    logger.info("TaskQ starting up env=%s", settings.APP_ENV)
    # Warm up the Redis pool at startup rather than on first request.
    await get_redis()
    yield
    logger.info("TaskQ shutting down")
    await close_redis()
    await engine.dispose()

def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="TaskQ — Distributed Task Scheduler",
        description=(
            "Production-grade distributed task queue and job scheduler. "
            "Supports one-time and recurring jobs, multiple task types, "
            "RBAC, email notifications, and audit logging."
        ),
        version="1.0.0",
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json",
        lifespan=lifespan,
    )

    # ── CORS ──────────────────────────────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            origin.strip()
            for origin in settings.ALLOWED_ORIGINS.split(",")
            if origin.strip()
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Exception handlers ────────────────────────────────────────────
    register_exception_handlers(app)

    # ── Routers ───────────────────────────────────────────────────────
    # Imported here (not at module top) to avoid circular imports.
    from app.routers.auth_router import router as auth_router
    from app.routers.task_router import router as task_router
    from app.routers.execution_router import router as execution_router
    from app.routers.dashboard_router import router as dashboard_router
    from app.routers.analytics_router import router as analytics_router
    from app.routers.admin_router import router as admin_router
    from app.routers.audit_router import router as audit_router
    from app.routers.ws_router import router as ws_router

    prefix = "/api/v1"

    app.include_router(auth_router, prefix=prefix)
    app.include_router(task_router, prefix=prefix)
    app.include_router(execution_router, prefix=prefix)
    app.include_router(dashboard_router, prefix=prefix)
    app.include_router(analytics_router, prefix=prefix)
    app.include_router(admin_router, prefix=prefix)
    app.include_router(audit_router, prefix=prefix)
    app.include_router(ws_router, prefix=prefix)

    # ── Ops endpoints ─────────────────────────────────────────────────

    @app.get("/health", tags=["ops"])
    async def health():
        """Liveness probe — process is alive."""
        return {
            "status": "ok",
            "uptime_seconds": round(time.time() - _startup_time, 1),
            "version": "1.0.0",
        }

    @app.get("/ready", tags=["ops"])
    async def ready():
        """Readiness probe — all dependencies reachable."""
        checks: dict[str, str] = {}
        ok = True

        try:
            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
            checks["postgres"] = "ok"
        except Exception as exc:
            checks["postgres"] = f"error: {exc}"
            ok = False

        try:
            redis_client: aioredis.Redis = await get_redis()
            await redis_client.ping()
            checks["redis"] = "ok"
        except Exception as exc:
            checks["redis"] = f"error: {exc}"
            ok = False

        from fastapi.responses import JSONResponse

        return JSONResponse(
            status_code=200 if ok else 503,
            content={
                "status": "ready" if ok else "not_ready",
                "checks": checks,
            },
        )

    return app


# Module-level app for uvicorn / gunicorn
app = create_app()