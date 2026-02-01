"""Exception handlers for consistent error responses."""

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.exceptions import AppException

logger = logging.getLogger(__name__)


def create_error_response(
    request_id: str | None,
    error_code: str,
    message: str,
    status_code: int,
    details: dict | None = None,
) -> dict:
    """Create a consistent error response structure."""
    response = {
        "error": {
            "code": error_code,
            "message": message,
        }
    }
    if details:
        response["error"]["details"] = details
    if request_id:
        response["request_id"] = request_id
    return response


async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    """Handle custom application exceptions."""
    request_id = getattr(request.state, "request_id", None)

    logger.warning(
        "Application error",
        extra={
            "error_code": exc.error_code,
            "message": exc.message,
            "status_code": exc.status_code,
            "request_id": request_id,
            "path": request.url.path,
        },
    )

    return JSONResponse(
        status_code=exc.status_code,
        content=create_error_response(
            request_id=request_id,
            error_code=exc.error_code,
            message=exc.message,
            status_code=exc.status_code,
            details=exc.details if exc.details else None,
        ),
    )


async def http_exception_handler(
    request: Request, exc: StarletteHTTPException
) -> JSONResponse:
    """Handle standard HTTP exceptions."""
    request_id = getattr(request.state, "request_id", None)

    error_code = "HTTP_ERROR"
    if exc.status_code == 404:
        error_code = "NOT_FOUND"
    elif exc.status_code == 401:
        error_code = "UNAUTHORIZED"
    elif exc.status_code == 403:
        error_code = "FORBIDDEN"
    elif exc.status_code == 405:
        error_code = "METHOD_NOT_ALLOWED"

    return JSONResponse(
        status_code=exc.status_code,
        content=create_error_response(
            request_id=request_id,
            error_code=error_code,
            message=str(exc.detail),
            status_code=exc.status_code,
        ),
    )


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Handle request validation errors."""
    request_id = getattr(request.state, "request_id", None)

    errors = []
    for error in exc.errors():
        errors.append({
            "field": ".".join(str(loc) for loc in error["loc"]),
            "message": error["msg"],
            "type": error["type"],
        })

    return JSONResponse(
        status_code=422,
        content=create_error_response(
            request_id=request_id,
            error_code="VALIDATION_ERROR",
            message="Request validation failed",
            status_code=422,
            details={"errors": errors},
        ),
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle unhandled exceptions."""
    request_id = getattr(request.state, "request_id", None)

    logger.exception(
        "Unhandled exception",
        extra={
            "request_id": request_id,
            "path": request.url.path,
            "method": request.method,
        },
    )

    return JSONResponse(
        status_code=500,
        content=create_error_response(
            request_id=request_id,
            error_code="INTERNAL_ERROR",
            message="An unexpected error occurred",
            status_code=500,
        ),
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Register all exception handlers with the FastAPI app."""
    app.add_exception_handler(AppException, app_exception_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)
