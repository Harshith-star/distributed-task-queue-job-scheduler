"""Request logging middleware — structured per-request log lines."""
import time
import uuid
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from app.core.logging import get_logger

logger = get_logger("taskq.request")


class RequestLoggerMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        req_id  = str(uuid.uuid4())[:8]
        start   = time.perf_counter()
        response = await call_next(request)
        duration = round((time.perf_counter() - start) * 1000, 1)

        # Skip health probes to keep logs clean
        if request.url.path not in ("/health", "/ready"):
            logger.info(
                "method=%s path=%s status=%s duration_ms=%s req_id=%s",
                request.method,
                request.url.path,
                response.status_code,
                duration,
                req_id,
            )
        return response
