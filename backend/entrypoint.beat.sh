#!/bin/sh
# entrypoint.beat.sh — CELERY BEAT
#
# Does NOT run migrations.
# Waits for the backend /ready endpoint so that:
#   - Redis is confirmed reachable (Beat needs it for RedBeat storage)
#   - Schema exists before Beat tries to register schedules
# Beat does not need a direct PostgreSQL connection itself.
set -e

BACKEND_URL="${BACKEND_URL:-http://backend:8000}"
RETRY_INTERVAL=3
MAX_WAIT=120
elapsed=0

echo "[beat] Waiting for backend to be ready at ${BACKEND_URL}/ready ..."
until python -c "
import urllib.request, sys
try:
    urllib.request.urlopen('${BACKEND_URL}/ready', timeout=5)
    sys.exit(0)
except Exception:
    sys.exit(1)
" 2>/dev/null; do
  if [ "$elapsed" -ge "$MAX_WAIT" ]; then
    echo "[beat] Backend did not become ready within ${MAX_WAIT}s — aborting."
    exit 1
  fi
  echo "[beat] Backend not ready yet — retrying in ${RETRY_INTERVAL}s (${elapsed}s elapsed)"
  sleep "$RETRY_INTERVAL"
  elapsed=$((elapsed + RETRY_INTERVAL))
done

echo "[beat] Backend is ready. Starting Celery Beat scheduler..."
exec celery -A app.workers.celery_app.celery_app beat \
  --loglevel=info \
  --scheduler redbeat.RedBeatScheduler
