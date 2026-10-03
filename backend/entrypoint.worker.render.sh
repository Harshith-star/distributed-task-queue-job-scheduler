#!/bin/sh
set -e

echo "[worker] Starting Celery worker..."

exec celery -A app.workers.celery_app.celery_app worker \
  --loglevel=info \
  --concurrency=4 \
  --queues=default,email,http,maintenance \
  --hostname=worker@%h