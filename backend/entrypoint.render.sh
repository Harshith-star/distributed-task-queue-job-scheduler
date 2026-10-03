#!/bin/sh
set -e

echo "[backend] Running Alembic migrations..."

alembic upgrade head

echo "[backend] Migrations applied."

echo "[backend] Starting FastAPI..."

exec uvicorn app.main:app \
    --host 0.0.0.0 \
    --port "${PORT:-10000}"