"""
File Cleanup Task

Deletes files older than a specified number of days.
"""

import glob
import os
import time

from app.tasks.base_task import BaseTaskQ
from app.workers.celery_app import celery_app


class FileCleanupTask(BaseTaskQ):
    """
    Deletes old files matching a pattern.
    """
    name = "app.tasks.file_cleanup_task.cleanup"
    abstract = True

    def execute_task(self, config: dict) -> str:

        directory = config.get("directory")

        if not directory:
            raise ValueError("directory is required")

        if not os.path.exists(directory):
            raise FileNotFoundError(
                f"Directory does not exist: {directory}"
            )

        pattern = config.get("pattern", "*")

        older_than_days = int(
            config.get("older_than_days", 30)
        )

        cutoff = time.time() - (older_than_days * 86400)

        files = glob.glob(
            os.path.join(directory, pattern)
        )

        deleted_files = []

        for file_path in files:

            try:

                if (
                    os.path.isfile(file_path)
                    and os.path.getmtime(file_path) < cutoff
                ):

                    os.remove(file_path)

                    deleted_files.append(file_path)

            except Exception:
                # Skip files we cannot delete
                continue

        return (
            f"Deleted {len(deleted_files)} file(s).\n\n"
            + "\n".join(deleted_files[:100])
        )

cleanup = celery_app.register_task(
    FileCleanupTask()
)
