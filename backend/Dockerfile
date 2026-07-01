FROM python:3.12-slim

WORKDIR /app

# postgresql-client  →  provides pg_isready (used in entrypoint.sh)
# gcc + libpq-dev    →  required by asyncpg and psycopg2 to compile from source
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
         gcc \
         libpq-dev \
         postgresql-client \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Create runtime directories
RUN mkdir -p /app/backups

# Make all four entrypoint scripts executable in one layer.
# Each script is responsible for exactly one service:
#   entrypoint.sh        → backend  (runs Alembic migrations, then uvicorn)
#   entrypoint.worker.sh → worker   (waits for /ready, then celery worker)
#   entrypoint.beat.sh   → beat     (waits for /ready, then celery beat)
#   entrypoint.flower.sh → flower   (waits for /ready, then celery flower)
RUN chmod +x \
      entrypoint.sh \
      entrypoint.worker.sh \
      entrypoint.beat.sh \
      entrypoint.flower.sh

EXPOSE 8000

# Liveness/readiness probe — used by Docker healthcheck and k8s probes.
# The /ready endpoint returns 200 only after Postgres + Redis are both reachable,
# which means it also guarantees migrations have been applied (the backend runs
# them before it starts accepting requests).
HEALTHCHECK \
    --interval=15s \
    --timeout=5s \
    --start-period=60s \
    --retries=5 \
    CMD python -c \
        "import urllib.request; urllib.request.urlopen('http://localhost:8000/ready')" \
    || exit 1

# No default ENTRYPOINT or CMD here — every service in docker-compose.yml
# specifies its own entrypoint explicitly. This prevents any service from
# accidentally inheriting the migration-running backend entrypoint.
