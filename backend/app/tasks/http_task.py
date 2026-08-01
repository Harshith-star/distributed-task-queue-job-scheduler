"""
HTTP Request Task

Executes HTTP GET/POST/PUT/PATCH/DELETE requests.
"""

import json
import urllib.error
import urllib.request
from wsgiref import headers
from urllib.parse import urlencode
from app.tasks.base_task import BaseTaskQ
from app.workers.celery_app import celery_app


class HTTPTask(BaseTaskQ):
    """
    Executes HTTP requests.
    """
    name = "app.tasks.http_task.http_request"
    abstract = True

    def execute_task(self, config: dict) -> str:

        url = config.get("url")

        if not url:
            raise ValueError("url is required")

        method = config.get("method", "GET").upper()

        headers = config.get("headers", {}).copy()

# Default headers if user doesn't provide them
        headers.setdefault(
    "User-Agent",
    "Mozilla/5.0"
)

        headers.setdefault(
    "Accept",
    "application/json"
)


        payload = config.get("payload", {})

        timeout = config.get("timeout", 30)

        body = None

        if method in ("POST", "PUT", "PATCH", "DELETE") and payload:
            body = json.dumps(payload).encode("utf-8")
        else :
            body = None    
        if method == "GET" and payload:
            url = f"{url}?{urlencode(payload)}"  

        request = urllib.request.Request(
            url=url,
            data=body,
            method=method,
        )

        for key, value in headers.items():
            request.add_header(key, value)

        if body is not None:
            request.add_header(
                "Content-Type",
                "application/json",
            )

        try:

            with urllib.request.urlopen(
                request,
                timeout=timeout,
            ) as response:

                status = response.status

                response_body = (
                    response.read()
                    .decode("utf-8", errors="ignore")
                )

            return (
                f"HTTP {method} {url}\n"
                f"Status : {status}\n\n"
                f"{response_body[:1000]}"
            )

        except urllib.error.HTTPError as e:

            error_body = ""

            try:
                error_body = e.read().decode(
                    "utf-8",
                    errors="ignore",
                )
            except Exception:
                pass

            raise RuntimeError(
                f"HTTP Error {e.code}: {e.reason}\n{error_body}"
            )

        except urllib.error.URLError as e:

            raise RuntimeError(
                f"Connection Error: {e.reason}"
            )

        except Exception as e:

            raise RuntimeError(str(e))


http_request = celery_app.register_task(
    HTTPTask()
)