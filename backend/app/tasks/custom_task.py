"""
Custom Python Task

Executes user-provided Python code in a restricted environment.
"""

from __future__ import annotations

import contextlib
import io
import textwrap
import traceback

from app.tasks.base_task import BaseTaskQ
from app.workers.celery_app import celery_app


class CustomTask(BaseTaskQ):
    """
    Executes restricted Python code.
    """
    name = "app.tasks.custom_task.run_custom"
    abstract = True

    def execute_task(self, config: dict) -> str:

        code = config.get("code")

        if not code:
            raise ValueError("code is required")

        code = textwrap.dedent(code)

        output = io.StringIO()

        safe_builtins = {
            "print": print,
            "range": range,
            "len": len,
            "str": str,
            "int": int,
            "float": float,
            "bool": bool,
            "list": list,
            "dict": dict,
            "set": set,
            "tuple": tuple,
            "min": min,
            "max": max,
            "sum": sum,
            "enumerate": enumerate,
            "zip": zip,
            "abs": abs,
            "round": round,
            "sorted": sorted,
        }

        globals_dict = {
            "__builtins__": safe_builtins,
        }

        locals_dict = {}

        try:

            with contextlib.redirect_stdout(output):

                exec(
                    code,
                    globals_dict,
                    locals_dict,
                )

        except Exception:

            raise RuntimeError(
                traceback.format_exc()
            )

        result = output.getvalue().strip()

        if not result:
            result = "Execution completed successfully."

        return result

run_custom = celery_app.register_task(
    CustomTask()
)
