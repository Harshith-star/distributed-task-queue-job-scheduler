"""File cleanup task — deletes old files matching a pattern."""
import glob, os, time
from app.workers.celery_app import celery_app
from app.tasks.base_task import BaseTaskQ


@celery_app.task(bind=True, base=BaseTaskQ, name="app.tasks.file_cleanup_task.cleanup")
def file_cleanup_task(self, execution_id: int, task_id: int, config: dict) -> str:
    return self.run(execution_id, task_id, config)


class FileCleanupTask(BaseTaskQ):
    name = "app.tasks.file_cleanup_task.cleanup"

    def run_task(self, config: dict) -> str:
        directory      = config.get("directory", "/tmp")
        pattern        = config.get("pattern", "*")
        older_than_days = config.get("older_than_days", 30)
        cutoff         = time.time() - (older_than_days * 86400)
        path_pattern   = os.path.join(directory, pattern)
        files          = glob.glob(path_pattern)
        deleted        = 0
        for f in files:
            try:
                if os.path.isfile(f) and os.path.getmtime(f) < cutoff:
                    os.remove(f)
                    deleted += 1
            except Exception:
                pass
        return f"Deleted {deleted} files from {directory} matching '{pattern}'"
