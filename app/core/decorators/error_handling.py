from __future__ import annotations

from django.conf import settings
from django.shortcuts import redirect
from django.views.decorators.http import require_http_methods
from django.http import HttpRequest, HttpResponse, HttpResponseNotAllowed

from functools import wraps
from typing import Any, ParamSpec, TypeVar
from collections.abc import Awaitable, Callable

from app.core.responses import BaseResponse

import logging

logger = logging.getLogger(__name__)

P = ParamSpec("P")
R = TypeVar("R")


def validate_request(
    *, allowed_methods: list[str]
) -> Callable[
    [Callable[P, Awaitable[HttpResponse]]], Callable[P, Awaitable[HttpResponse]]
]:
    def decorator(
        view: Callable[P, Awaitable[HttpResponse]],
    ) -> Callable[P, Awaitable[HttpResponse]]:
        @wraps(view)
        async def wrapped(
            request: HttpRequest, *args: P.args, **kwargs: P.kwargs
        ) -> HttpResponse:
            if request.method not in allowed_methods:
                return HttpResponseNotAllowed(allowed_methods)
            return await view(request, *args, **kwargs)

        return wrapped

    return decorator


def async_exception_handler(
    *, return_json: bool = False
) -> Callable[
    [Callable[P, Awaitable[HttpResponse]]], Callable[P, Awaitable[HttpResponse]]
]:
    def decorator(
        view: Callable[P, Awaitable[HttpResponse]],
    ) -> Callable[P, Awaitable[HttpResponse]]:
        @wraps(view)
        async def wrapped(
            request: HttpRequest, *args: P.args, **kwargs: P.kwargs
        ) -> HttpResponse:
            try:
                return await view(request, *args, **kwargs)
            except Exception:
                logger.exception("View error: %s", getattr(view, "__name__", view))
                if return_json:
                    return BaseResponse.error(
                        "Внутренняя ошибка сервера",
                        http_status=500,
                    )
                return redirect(f"{settings.LOGIN_URL}?login_error=3")

        return wrapped

    return decorator


def async_login_required_custom(
    *,
    login_url: str | None = None,
) -> Callable[
    [Callable[P, Awaitable[HttpResponse]]], Callable[P, Awaitable[HttpResponse]]
]:
    url = login_url or settings.LOGIN_URL

    def decorator(
        view: Callable[P, Awaitable[HttpResponse]],
    ) -> Callable[P, Awaitable[HttpResponse]]:
        @wraps(view)
        async def wrapped(
            request: HttpRequest, *args: P.args, **kwargs: P.kwargs
        ) -> HttpResponse:
            user = await request.auser()
            if not user.is_authenticated:
                return redirect(f"{url}?next={request.path}")
            request._cached_user = user  # noqa: SLF001
            return await view(request, *args, **kwargs)

        return wrapped

    return decorator


def async_api_view(
    *,
    methods: list[str] | None = None,
    require_auth: bool = False,
    validate_params: list[str] | None = None,
) -> Callable[
    [Callable[P, Awaitable[HttpResponse]]], Callable[P, Awaitable[HttpResponse]]
]:
    methods = methods or ["GET"]
    param_keys = validate_params or []

    def decorator(
        view: Callable[P, Awaitable[HttpResponse]],
    ) -> Callable[P, Awaitable[HttpResponse]]:
        @require_http_methods(methods)
        @wraps(view)
        async def wrapped(
            request: HttpRequest, *args: P.args, **kwargs: P.kwargs
        ) -> HttpResponse:
            if require_auth:
                user = await request.auser()
                if not user.is_authenticated:
                    return BaseResponse.error(
                        "Требуется авторизация",
                        details={"code": "auth_required"},
                        http_status=401,
                    )
            for key in param_keys:
                if not request.POST.get(key):
                    return BaseResponse.error(
                        f"Отсутствует поле: {key}",
                        details={"code": "validation_error", "field": key},
                        http_status=400,
                    )
            return await view(request, *args, **kwargs)

        return wrapped

    return decorator
