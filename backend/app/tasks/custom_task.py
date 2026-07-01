"""Custom Python task — executes user-provided Python code in a sandbox."""
import io, sys, contextlib, textwrap
from app.workers.celery_app import celery_app
from app.tasks.base_task import BaseTaskQ


@celery_app.task(bind=True, base=BaseTaskQ, name="app.tasks.custom_task.run_custom")
def custom_task(self, execution_id: int, task_id: int, config: dict) -> str:
    return self.run(execution_id, task_id, config)


class CustomTask(BaseTaskQ):
    name = "app.tasks.custom_task.run_custom"

    def run_task(self, config: dict) -> str:
        code    = textwrap.dedent(config.get("code", "print('Hello from TaskQ!')"))
        timeout = config.get("timeout", 60)
        stdout  = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            exec(code, {"__builtins__": {"print": print, "range": range, "len": len, "str": str, "int": int, "list": list, "dict": dict}})
        return stdout.getvalue().strip() or "Executed successfully (no output)"
