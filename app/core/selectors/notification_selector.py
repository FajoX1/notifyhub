"""Async notification and email-code data access (avoids N+1 in views)."""

from __future__ import annotations

from django.utils import timezone

from datetime import timedelta
from dataclasses import dataclass
from asgiref.sync import sync_to_async

from app.core.models import EmailLoginCode, Notification


@dataclass(frozen=True)
class NotificationSelector:
    @staticmethod
    async def get_user_notifications(
        user_id: int,
        *,
        limit: int = 10,
        unread_only: bool = False,
    ) -> list[Notification]:
        qs = Notification.objects.filter(user_id=user_id).order_by(
            "-notification_date", "-id"
        )
        if unread_only:
            qs = qs.filter(is_read=False)
        return await sync_to_async(list)(qs[:limit])

    @staticmethod
    async def get_unread_count(user_id: int) -> int:
        return await Notification.objects.filter(
            user_id=user_id, is_read=False
        ).acount()

    @staticmethod
    async def mark_as_read(notification_id: int, user_id: int) -> bool:
        notification = await Notification.objects.filter(
            id=notification_id, user_id=user_id
        ).afirst()
        if notification is None:
            return False
        if notification.is_read:
            return True
        notification.is_read = True
        await notification.asave(update_fields=["is_read"])
        return True

    @staticmethod
    async def mark_all_as_read(user_id: int) -> int:
        def _update() -> int:
            return Notification.objects.filter(user_id=user_id, is_read=False).update(
                is_read=True
            )

        return await sync_to_async(_update)()


@dataclass(frozen=True)
class EmailCodeSelector:
    @staticmethod
    async def create_code(
        *,
        email: str,
        code: str,
        expires_minutes: int = 10,
    ) -> EmailLoginCode:
        expires_at = timezone.now() + timedelta(minutes=expires_minutes)
        return await EmailLoginCode.objects.acreate(
            email=email,
            code=code,
            expires_at=expires_at,
        )

    @staticmethod
    async def validate_code(
        email: str,
        code: str,
    ) -> tuple[bool, EmailLoginCode | None]:
        row = (
            await EmailLoginCode.objects.filter(
                email=email,
                code=code,
                used_at__isnull=True,
            )
            .order_by("-notification_date", "-id")
            .afirst()
        )
        if row is None:
            return False, None
        if row.is_expired:
            return False, None
        row.used_at = timezone.now()
        await row.asave(update_fields=["used_at"])
        return True, row


notification_selector = NotificationSelector()
email_code_selector = EmailCodeSelector()
