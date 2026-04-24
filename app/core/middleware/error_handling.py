from __future__ import annotations

from django.http import HttpRequest, HttpResponse

from typing import Callable

from app.core.responses import BaseResponse

import time
import logging

logger = logging.getLogger(__name__)


class AsyncMiddleware:
    """
    Placeholder / compatibility shim for ASGI stacks.
    Ensures request timing attributes exist for downstream code.
    """

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        request._nh_request_started = time.monotonic()  # noqa: SLF001
        return self.get_response(request)


class RequestLoggingMiddleware:
    """Structured access log for debugging and operations."""

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        response = self.get_response(request)
        duration_ms = None
        started = getattr(request, "_nh_request_started", None)
        if started is not None:
            duration_ms = round((time.monotonic() - started) * 1000, 2)
        logger.info(
            "%s %s -> %s%s",
            request.method,
            request.path,
            getattr(response, "status_code", "?"),
            f" ({duration_ms} ms)" if duration_ms is not None else "",
        )
        return response


class GlobalExceptionMiddleware:
    """For /api/* routes return BaseResponse JSON instead of an HTML error page."""

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        try:
            return self.get_response(request)
        except Exception as exc:  # noqa: BLE001
            if request.path.startswith("/api/"):
                logger.exception("Unhandled API error: %s", request.path)
                return BaseResponse.error(
                    "Внутренняя ошибка сервера",
                    details={"type": exc.__class__.__name__},
                    http_status=500,
                )
            raise
