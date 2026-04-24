from __future__ import annotations

from django.dispatch import receiver
from django.contrib.auth.signals import user_logged_in

from asgiref.sync import async_to_sync
from datetime import datetime, timezone
from allauth.account.signals import user_signed_up

from app.core.services.email_service import get_email_service

import logging

logger = logging.getLogger(__name__)


def _extract_ip(request) -> str | None:  # type: ignore[no-untyped-def]
    forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


@receiver(user_signed_up)
def send_welcome_email_on_signup(request, user, **kwargs) -> None:  # type: ignore[no-untyped-def]
    if not user or not user.email:
        return
    try:
        async_to_sync(get_email_service().send_welcome_email)(
            email=user.email,
            username=getattr(user, "username", None),
            send_async=False,
        )
    except Exception:
        logger.exception("Не удалось отправить welcome email пользователю %s", user.pk)


@receiver(user_logged_in)
def send_security_alert_on_login(request, user, **kwargs) -> None:  # type: ignore[no-untyped-def]
    if not user or not user.email:
        return
    try:
        async_to_sync(get_email_service().send_security_alert)(
            email=user.email,
            username=getattr(user, "username", None),
            ip_address=_extract_ip(request),
            user_agent=request.META.get("HTTP_USER_AGENT", ""),
            login_time=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
            send_async=False,
        )
    except Exception:
        logger.exception("Не удалось отправить security alert пользователю %s", user.pk)
