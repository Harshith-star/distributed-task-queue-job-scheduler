#!/bin/sh
# entrypoint.flower.sh — FLOWER (Celery monitoring UI)
#
# Does NOT run migrations.
# Waits for the backend /ready endpoint so Flower only starts once there
# are workers registered and the broker is confirmed healthy.
set -e

BACKEND_URL="${BACKEND_URL:-http://backend:8000}"
RETRY_INTERVAL=3
MAX_WAIT=120
elapsed=0

echo "[flower] Waiting for backend to be ready at ${BACKEND_URL}/ready ..."
until python -c "
import urllib.request, sys
try:
    urllib.request.urlopen('${BACKEND_URL}/ready', timeout=5)
    sys.exit(0)
except Exception:
    sys.exit(1)
" 2>/dev/null; do
  if [ "$elapsed" -ge "$MAX_WAIT" ]; then
    echo "[flower] Backend did not become ready within ${MAX_WAIT}s — aborting."
    exit 1
  fi
  echo "[flower] Backend not ready yet — retrying in ${RETRY_INTERVAL}s (${elapsed}s elapsed)"
  sleep "$RETRY_INTERVAL"
  elapsed=$((elapsed + RETRY_INTERVAL))
done

echo "[flower] Backend is ready. Starting Flower monitoring UI on :5555 ..."
exec celery -A app.workers.celery_app.celery_app flower \
  --port=5555 \
  --broker="${CELERY_BROKER_URL:-redis://redis:6379/1}"
