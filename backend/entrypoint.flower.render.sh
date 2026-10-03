#!/bin/sh
set -e

echo "[flower] Starting Flower..."

exec celery -A app.workers.celery_app.celery_app flower \
  --port="${PORT:-5555}" \
  --broker="${CELERY_BROKER_URL}"