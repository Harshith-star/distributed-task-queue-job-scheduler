"""HTTP API task — makes an HTTP request to a URL."""
import json
import urllib.request
import urllib.error
from app.workers.celery_app import celery_app
from app.tasks.base_task import BaseTaskQ


@celery_app.task(bind=True, base=BaseTaskQ, name="app.tasks.http_task.http_request")
def http_request_task(self, execution_id: int, task_id: int, config: dict) -> str:
    return self.run(execution_id, task_id, config)


class HTTPRequestTask(BaseTaskQ):
    name = "app.tasks.http_task.http_request"

    def run_task(self, config: dict) -> str:
        url     = config.get("url", "")
        method  = config.get("method", "GET").upper()
        headers = config.get("headers", {})
        payload = config.get("payload", {})
        timeout = config.get("timeout", 30)

        data = json.dumps(payload).encode("utf-8") if payload else None
        req  = urllib.request.Request(url, data=data, method=method)
        for k, v in headers.items():
            req.add_header(k, v)
        if data:
            req.add_header("Content-Type", "application/json")

        with urllib.request.urlopen(req, timeout=timeout) as response:
            status  = response.getcode()
            body    = response.read().decode("utf-8")[:500]
        return f"HTTP {method} {url} → {status}: {body[:200]}"
