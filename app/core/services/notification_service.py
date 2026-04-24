from __future__ import annotations

from django.utils import timezone
from django.contrib.auth import get_user_model

from app.core.services.email_service import get_email_service
from app.core.models import Notification, UserNotificationPreference

from enum import Enum
from typing import Any
from asgiref.sync import async_to_sync
from dataclasses import dataclass, field

import logging

logger = logging.getLogger(__name__)


class NotificationChannel(str, Enum):
    IN_APP = "in_app"
    EMAIL = "email"


@dataclass
class NotificationData:
    user_id: int
    title: str
    message: str
    level: str = "info"
    kind: str = Notification.Kind.SYSTEM
    channels: list[NotificationChannel] = field(default_factory=list)
    data: dict[str, Any] = field(default_factory=dict)
    notification_date: Any | None = None


@dataclass
class NotificationSendResult:
    success: bool
    message: str
    data: dict[str, Any] | None = None


class NotificationService:
    def send_notification_sync(
        self, payload: NotificationData
    ) -> NotificationSendResult:
        channels = payload.channels or [NotificationChannel.IN_APP]
        prefs, _ = UserNotificationPreference.objects.get_or_create(
            user_id=payload.user_id
        )
        if not should_deliver_notification(prefs, payload.kind):
            return NotificationSendResult(
                True, "skipped_by_preferences", {"skipped": True}
            )
        try:
            notification = Notification.objects.create(
                user_id=payload.user_id,
                title=payload.title,
                message=payload.message,
                level=payload.level,
                kind=payload.kind,
                notification_date=payload.notification_date or timezone.now(),
            )
        except Exception:
            logger.exception(
                "Notification DB create failed user_id=%s", payload.user_id
            )
            return NotificationSendResult(False, "create_failed", None)

        extra: dict[str, Any] = {"notification_id": notification.id}

        if NotificationChannel.EMAIL in channels:
            User = get_user_model()
            user = User.objects.filter(pk=payload.user_id).only("id", "email").first()
            if user and user.email:
                logger.info(
                    "Dispatching notification email user_id=%s notification_id=%s level=%s",
                    payload.user_id,
                    notification.id,
                    payload.level,
                )
                try:
                    async_to_sync(get_email_service().send_notification)(
                        user.email,
                        payload.title,
                        payload.message,
                        payload.level,
                        send_async=False,
                    )
                    extra["email_dispatched"] = True
                    logger.info(
                        "Notification email dispatched user_id=%s notification_id=%s",
                        payload.user_id,
                        notification.id,
                    )
                except Exception:
                    logger.exception(
                        "Notification email failed user_id=%s", payload.user_id
                    )
                    extra["email_dispatched"] = False
            else:
                logger.warning(
                    "Notification email skipped user_id=%s reason=no_email",
                    payload.user_id,
                )
                extra["email_dispatched"] = False

        return NotificationSendResult(True, "ok", extra)


_service: NotificationService | None = None


def get_notification_service() -> NotificationService:
    global _service  # noqa: PLW0603
    if _service is None:
        _service = NotificationService()
    return _service


def should_deliver_notification(
    preferences: UserNotificationPreference,
    notification_kind: str,
) -> bool:
    if preferences.mute_all_enabled:
        return False
    if not preferences.browser_enabled:
        return False
    if preferences.dnd_enabled and _is_dnd_active(preferences):
        return False
    pref_field = _kind_to_preference_field(notification_kind)
    return bool(getattr(preferences, pref_field, True))


def _is_dnd_active(preferences: UserNotificationPreference) -> bool:
    start = preferences.dnd_start
    end = preferences.dnd_end
    if start is None or end is None:
        return True
    now = timezone.localtime().time()
    if start <= end:
        return start <= now <= end
    return now >= start or now <= end


def _kind_to_preference_field(notification_kind: str) -> str:
    mapping = {
        Notification.Kind.PAYMENT: "payments_enabled",
        Notification.Kind.MESSAGE: "messages_enabled",
        Notification.Kind.SYSTEM: "system_enabled",
        Notification.Kind.MARKETING: "marketing_enabled",
        Notification.Kind.SECURITY: "security_enabled",
        Notification.Kind.SUPPORT: "support_enabled",
    }
    return mapping.get(notification_kind, "system_enabled")
