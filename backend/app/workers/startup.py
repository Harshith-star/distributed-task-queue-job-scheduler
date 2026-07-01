"""Celery startup tasks — runs once when the worker process initialises."""
from celery.signals import worker_ready
from app.workers.celery_app import celery_app
from app.core.logging import get_logger

logger = get_logger(__name__)


@worker_ready.connect
def on_worker_ready(sender, **kwargs):
    """Seed a demo admin user if no users exist yet.

    This fires once per worker startup, making the demo immediately usable
    after `docker compose up --build` without any manual setup.
    """
    logger.info("Worker ready — seeding demo data if needed")
    try:
        _seed_demo_data()
    except Exception as exc:
        logger.warning("Demo seed failed (non-fatal): %s", exc)


def _seed_demo_data():
    """Create a demo admin user if the users table is empty."""
    import sqlalchemy as sa
    from app.core.config import get_settings
    from app.core.security import hash_password

    settings = get_settings()
    sync_url = settings.DATABASE_URL.replace("+asyncpg", "")
    engine   = sa.create_engine(sync_url, pool_pre_ping=True)

    with engine.connect() as conn:
        count = conn.execute(sa.text("SELECT COUNT(*) FROM users")).scalar()
        if count and count > 0:
            logger.info("Users exist — skipping demo seed")
            engine.dispose()
            return

        conn.execute(sa.text("""
            INSERT INTO users (email, full_name, hashed_password, role, is_active, created_at, updated_at)
            VALUES (:email, :full_name, :pw, 'admin', true, NOW(), NOW())
        """), {
            "email":     "admin@taskq.io",
            "full_name": "TaskQ Admin",
            "pw":        hash_password("Password1"),
        })
        conn.commit()
        logger.info("Demo admin created: admin@taskq.io / Password1")

    engine.dispose()
