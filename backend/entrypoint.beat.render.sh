#!/bin/sh
set -e

echo "[beat] Starting Celery Beat..."

exec celery -A app.workers.celery_app.celery_app beat \
  --loglevel=info \
  --scheduler redbeat.RedBeatScheduler