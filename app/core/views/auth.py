from __future__ import annotations

from django.conf import settings
from django.shortcuts import redirect
from asgiref.sync import sync_to_async
from django.core.validators import validate_email
from django.http import HttpRequest, HttpResponse
from django.core.exceptions import ValidationError
from django.contrib.auth import authenticate, login

from app.core.decorators.error_handling import (
    validate_request,
    async_exception_handler,
)

import logging

logger = logging.getLogger(__name__)


@async_exception_handler(return_json=False)
@validate_request(allowed_methods=["POST"])
async def email_login_view(request: HttpRequest) -> HttpResponse:
    email = request.POST.get("email", "").strip().lower()
    password = request.POST.get("password", "").strip()

    if not email or not password:
        logger.warning("Попытка входа с пустым email или паролем")
        return redirect(f"{settings.LOGIN_URL}?login_error=1")

    try:
        validate_email(email)
    except ValidationError:
        logger.warning("Некорректный email: %s", email)
        return redirect(f"{settings.LOGIN_URL}?login_error=1")

    try:
        user = await sync_to_async(authenticate)(
            request, email=email, password=password
        )
        if user is None:
            user = await sync_to_async(authenticate)(
                request, username=email, password=password
            )

        if user is None:
            logger.warning("Неудачная попытка входа для email: %s", email)
            return redirect(f"{settings.LOGIN_URL}?login_error=1")

        if not user.is_active:
            logger.warning("Попытка входа неактивного пользователя: %s", email)
            return redirect(f"{settings.LOGIN_URL}?login_error=2")

        await sync_to_async(login)(request, user)
        logger.info("Успешный вход пользователя: %s", email)

        return redirect("dashboard")

    except Exception:
        logger.exception("Ошибка при аутентификации email %s", email)

        return redirect(f"{settings.LOGIN_URL}?login_error=3")
