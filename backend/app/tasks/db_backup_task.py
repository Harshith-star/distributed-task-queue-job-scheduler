"""Database backup task — pg_dump to a file."""
import os, subprocess, datetime
from app.workers.celery_app import celery_app
from app.tasks.base_task import BaseTaskQ


@celery_app.task(bind=True, base=BaseTaskQ, name="app.tasks.db_backup_task.backup")
def db_backup_task(self, execution_id: int, task_id: int, config: dict) -> str:
    return self.run(execution_id, task_id, config)


class DBBackupTask(BaseTaskQ):
    name = "app.tasks.db_backup_task.backup"

    def run_task(self, config: dict) -> str:
        from app.core.config import get_settings
        db_url      = config.get("database_url") or get_settings().DATABASE_URL
        output_dir  = config.get("output_path", "/tmp/backups")
        compress    = config.get("compress", True)
        os.makedirs(output_dir, exist_ok=True)
        timestamp   = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        # Replace asyncpg with psycopg2 for pg_dump env vars
        sync_url    = db_url.replace("postgresql+asyncpg://", "postgresql://")
        filename    = os.path.join(output_dir, f"backup_{timestamp}.sql{'gz' if compress else ''}")
        cmd         = ["pg_dump", sync_url, "-f", filename]
        if compress:
            cmd = ["pg_dump", sync_url, "--compress=9", "-f", filename]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        if result.returncode != 0:
            raise RuntimeError(f"pg_dump failed: {result.stderr}")
        size_mb = os.path.getsize(filename) / (1024 * 1024)
        return f"Backup saved to {filename} ({size_mb:.2f} MB)"
