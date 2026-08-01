"""
Database Backup Task

Creates a PostgreSQL backup using pg_dump.
"""

from __future__ import annotations

import datetime
import gzip
import os
import shutil
import subprocess

from app.tasks.base_task import BaseTaskQ
from app.workers.celery_app import celery_app


class DBBackupTask(BaseTaskQ):
    """
    PostgreSQL database backup task.
    """

    name = "app.tasks.db_backup_task.backup"
    abstract = True

    def execute_task(self, config: dict) -> str:

        from app.core.config import get_settings

        settings = get_settings()

        database_url = config.get(
            "database_url",
            settings.DATABASE_URL,
        )

        output_dir = config.get(
            "output_path",
            "/app/backups",
        )

        compress = config.get(
            "compress",
            True,
        )

        os.makedirs(
            output_dir,
            exist_ok=True,
        )

        timestamp = datetime.datetime.now().strftime(
            "%Y%m%d_%H%M%S"
        )

        sql_file = os.path.join(
            output_dir,
            f"backup_{timestamp}.sql",
        )

        sync_url = (
            database_url
            .replace(
                "postgresql+asyncpg://",
                "postgresql://",
            )
        )

        if shutil.which("pg_dump") is None:
            raise RuntimeError(
                "pg_dump executable not found. "
                "Install PostgreSQL client tools."
            )

        command = [
            "pg_dump",
            sync_url,
            "-f",
            sql_file,
        ]

        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=600,
        )

        if result.returncode != 0:

            raise RuntimeError(
                f"pg_dump failed:\n{result.stderr}"
            )

        backup_file = sql_file

        if compress:

            gz_file = sql_file + ".gz"

            with open(sql_file, "rb") as src:

                with gzip.open(gz_file, "wb") as dst:

                    shutil.copyfileobj(src, dst)

            os.remove(sql_file)

            backup_file = gz_file

        size_mb = (
            os.path.getsize(backup_file)
            / (1024 * 1024)
        )

        return (
            f"Backup completed successfully.\n\n"
            f"Location : {backup_file}\n"
            f"Size     : {size_mb:.2f} MB"
        )

backup = celery_app.register_task(DBBackupTask())