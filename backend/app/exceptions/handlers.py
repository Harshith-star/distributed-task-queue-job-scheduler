"""
app/exceptions/handlers.py

Global FastAPI exception handler.

Converts every AppError subclass into a consistent JSON response:
  { "detail": "<message>", "error_code": "<ClassName>", "status": <int> }

Why centralise here instead of try/except in every router?
  - DRY: one place to change the error response shape.
  - Consistent: every error looks identical to the client.
  - Separation of concerns: services throw domain errors, HTTP layer handles them.
"""
import traceback

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.logging import get_logger
from app.exceptions.domain import AppError

logger = get_logger(__name__)


def register_exception_handlers(app: FastAPI) -> None:
    """Register all exception handlers on the FastAPI app instance."""

    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
        # Log at WARNING — these are expected domain errors, not bugs.
        logger.warning(
            "AppError %s: %s | path=%s | internal=%s",
            exc.__class__.__name__,
            exc.detail,
            request.url.path,
            exc.internal,
        )
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "detail": exc.detail,
                "error_code": exc.__class__.__name__,
                "status": exc.status_code,
            },
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_error_handler(
        request: Request, exc: StarletteHTTPException
    ) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "detail": exc.detail,
                "error_code": "HTTPException",
                "status": exc.status_code,
            },
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        # Flatten Pydantic errors into a readable list.
        errors = [
            {"field": ".".join(str(l) for l in e["loc"]), "msg": e["msg"]}
            for e in exc.errors()
        ]
        logger.warning("Validation failed path=%s errors=%s", request.url.path, errors)
        return JSONResponse(
            status_code=422,
            content={
                "detail": "Request validation failed",
                "errors": errors,
                "error_code": "RequestValidationError",
                "status": 422,
            },
        )

    @app.exception_handler(Exception)
    async def unhandled_error_handler(
        request: Request, exc: Exception
    ) -> JSONResponse:
        # Log at ERROR with traceback — unexpected bug.
        logger.error(
            "Unhandled exception path=%s: %s\n%s",
            request.url.path,
            exc,
            traceback.format_exc(),
        )
        return JSONResponse(
            status_code=500,
            content={
                "detail": "Internal server error",
                "error_code": "InternalServerError",
                "status": 500,
            },
        )
