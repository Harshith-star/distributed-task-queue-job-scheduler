#!/bin/sh
# entrypoint.sh — BACKEND ONLY
#
# Responsibilities:
#   1. Wait for PostgreSQL to accept connections.
#   2. Run Alembic migrations (THIS IS THE ONLY CONTAINER THAT DOES THIS).
#   3. Start the FastAPI server.
#
# Worker / Beat / Flower have their own entrypoint scripts and never run
# migrations. They wait for this container's /ready endpoint instead.
set -e

echo "[backend] Waiting for PostgreSQL at ${PGHOST:-postgres}..."
until pg_isready \
      -h "${PGHOST:-postgres}" \
      -U "${PGUSER:-taskq_user}" \
      -d "${PGDATABASE:-taskq}" \
      -q; do
  echo "[backend] PostgreSQL not ready — retrying in 2s"
  sleep 2
done
echo "[backend] PostgreSQL is ready."

echo "[backend] Running Alembic migrations..."
alembic upgrade head
echo "[backend] Migrations applied."

echo "[backend] Starting API server (uvicorn)..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 2
