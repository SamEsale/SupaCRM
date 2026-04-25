from __future__ import annotations

import logging
from typing import Any

from fastapi import HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError

logger = logging.getLogger("supacrm.api.error")


def _json_safe(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value

    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}

    if isinstance(value, (list, tuple, set)):
        return [_json_safe(item) for item in value]

    if isinstance(value, BaseException):
        return str(value)

    return str(value)


def build_error_content(
    *,
    code: str,
    message: str,
    details: Any | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "error": {
            "code": code,
            "message": message,
        }
    }
    if details is not None:
        payload["error"]["details"] = _json_safe(details)
    return payload


def build_error_response(
    *,
    status_code: int,
    code: str,
    message: str,
    details: Any | None = None,
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content=build_error_content(code=code, message=message, details=details),
    )


def _http_status_to_error_code(status_code: int) -> str:
    if status_code == status.HTTP_400_BAD_REQUEST:
        return "bad_request"
    if status_code == status.HTTP_401_UNAUTHORIZED:
        return "unauthorized"
    if status_code == status.HTTP_403_FORBIDDEN:
        return "forbidden"
    if status_code == status.HTTP_404_NOT_FOUND:
        return "not_found"
    if status_code == status.HTTP_409_CONFLICT:
        return "conflict"
    if status_code == status.HTTP_422_UNPROCESSABLE_ENTITY:
        return "validation_error"
    if 400 <= status_code < 500:
        return "client_error"
    return "http_error"


def _request_context(request: Request) -> dict[str, Any]:
    return {
        "request_id": getattr(request.state, "request_id", None),
        "tenant_id": getattr(request.state, "tenant_id", None),
        "method": request.method,
        "path": request.url.path,
        "client_ip": request.client.host if request.client else None,
    }


async def handle_http_exception(request: Request, exc: HTTPException) -> JSONResponse:
    message = exc.detail if isinstance(exc.detail, str) else "Request failed."
    details = None if isinstance(exc.detail, str) else exc.detail

    logger.warning(
        "HTTP exception raised.",
        extra={
            **_request_context(request),
            "event_type": "http_exception",
            "scope": "http",
            "reason": _http_status_to_error_code(exc.status_code),
            "status_code": exc.status_code,
            "outcome": "error",
        },
    )

    return build_error_response(
        status_code=exc.status_code,
        code=_http_status_to_error_code(exc.status_code),
        message=message,
        details=details,
    )


async def handle_request_validation_error(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    details = [_json_safe(error) for error in exc.errors()]

    logger.warning(
        "Request validation failed.",
        extra={
            **_request_context(request),
            "event_type": "validation_error",
            "scope": "validation",
            "reason": "validation_error",
            "status_code": status.HTTP_422_UNPROCESSABLE_ENTITY,
            "outcome": "error",
        },
    )

    return build_error_response(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        code="validation_error",
        message="Request validation failed.",
        details=details,
    )


async def handle_integrity_error(request: Request, exc: IntegrityError) -> JSONResponse:
    logger.warning(
        "Integrity constraint violation.",
        extra={
            **_request_context(request),
            "event_type": "integrity_error",
            "scope": "database",
            "reason": "conflict",
            "status_code": status.HTTP_409_CONFLICT,
            "outcome": "error",
        },
    )

    return build_error_response(
        status_code=status.HTTP_409_CONFLICT,
        code="conflict",
        message="The request conflicts with existing data or persistence constraints.",
        details={"error": str(exc.orig) if getattr(exc, "orig", None) else str(exc)},
    )


async def handle_unexpected_exception(request: Request, exc: Exception) -> JSONResponse:
    logger.exception(
        "An unexpected server error occurred.",
        extra={
            **_request_context(request),
            "event_type": "unhandled_exception",
            "reason": "internal_server_error",
            "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
            "outcome": "error",
        },
    )

    return build_error_response(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        code="internal_server_error",
        message="An unexpected server error occurred.",
    )


def install_exception_handlers(app: Any) -> None:
    app.add_exception_handler(HTTPException, handle_http_exception)
    app.add_exception_handler(RequestValidationError, handle_request_validation_error)
    app.add_exception_handler(IntegrityError, handle_integrity_error)
    app.add_exception_handler(Exception, handle_unexpected_exception)
