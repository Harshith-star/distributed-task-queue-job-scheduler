#!/bin/sh
# entrypoint.worker.sh — CELERY WORKER
#
# Does NOT run migrations.
# Waits for the backend /ready endpoint, which only returns 200 after:
#   - PostgreSQL is reachable
#   - Redis is reachable
#   - Alembic migrations have been applied
# This guarantees the schema exists before the worker starts processing tasks.
set -e

BACKEND_URL="${BACKEND_URL:-http://backend:8000}"
RETRY_INTERVAL=3
MAX_WAIT=120
elapsed=0

echo "[worker] Waiting for backend to be ready at ${BACKEND_URL}/ready ..."
until python -c "
import urllib.request, sys
try:
    urllib.request.urlopen('${BACKEND_URL}/ready', timeout=5)
    sys.exit(0)
except Exception:
    sys.exit(1)
" 2>/dev/null; do
  if [ "$elapsed" -ge "$MAX_WAIT" ]; then
    echo "[worker] Backend did not become ready within ${MAX_WAIT}s — aborting."
    exit 1
  fi
  echo "[worker] Backend not ready yet — retrying in ${RETRY_INTERVAL}s (${elapsed}s elapsed)"
  sleep "$RETRY_INTERVAL"
  elapsed=$((elapsed + RETRY_INTERVAL))
done

echo "[worker] Backend is ready. Starting Celery worker..."
exec celery -A app.workers.celery_app.celery_app worker \
  --loglevel=info \
  --concurrency=4 \
  --queues=default,email,http,maintenance \
  --hostname=worker@%h
