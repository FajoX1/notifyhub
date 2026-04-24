from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import models
from django.utils import timezone

from celery import shared_task
from asgiref.sync import async_to_sync

from app.core.models import Notification, UserNotificationPreference, EmailLoginCode
from app.core.services.email_service import get_email_service
from app.core.services.notification_service import (
    NotificationData,
    NotificationChannel,
    get_notification_service,
    should_deliver_notification,
)
from app.core.utils.redis_client import get_redis

import time
import logging

User = get_user_model()
logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 3},
    name="app.core.tasks.send_login_code_email",
)
def send_login_code_email(self, email: str, code: str) -> bool:
    """
    Отправка кода для входа по email (Celery worker; SMTP вне event loop ASGI).
    """
    try:
        return async_to_sync(get_email_service().send_login_code)(
            email, code, send_async=False
        )
    except Exception as exc:
        logger.exception("send_login_code_email failed for %s", email)
        raise self.retry(exc=exc)


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 3},
    name="app.core.tasks.send_notification_task",
)
def send_notification_task(
    self,
    user_id: int,
    title: str,
    message: str,
    level: str = "info",
    channels: list[str] = None,
    data: dict = None,
) -> dict:
    try:
        notification_channels = []
        if channels:
            for channel_str in channels:
                try:
                    channel = NotificationChannel(channel_str)
                    notification_channels.append(channel)
                except ValueError:
                    logger.warning(f"Неизвестный канал уведомления: {channel_str}")

        if not notification_channels:
            notification_channels = [NotificationChannel.IN_APP]

        notification_data = NotificationData(
            user_id=user_id,
            title=title,
            message=message,
            level=level,
            kind=(data or {}).get("kind", Notification.Kind.SYSTEM),
            channels=notification_channels,
            data=data or {},
        )

        notification_service = get_notification_service()
        response = notification_service.send_notification_sync(notification_data)

        if response.success:
            logger.info(f"Уведомление отправлено пользователю {user_id}: {title}")
        else:
            logger.warning(
                f"Ошибка отправки уведомления пользователю {user_id}: {response.message}"
            )

        return {
            "success": response.success,
            "message": response.message,
            "data": response.data,
        }

    except Exception as exc:
        logger.exception(
            f"Ошибка в задаче send_notification_task для пользователя {user_id}: {exc}"
        )
        raise self.retry(exc=exc)


@shared_task(
    name="app.core.tasks.create_notification_task",
)
def create_notification_task(
    user_id: int,
    title: str,
    message: str,
    level: str = "info",
    kind: str = Notification.Kind.SYSTEM,
) -> int:
    try:
        prefs, _ = UserNotificationPreference.objects.get_or_create(user_id=user_id)
        if not should_deliver_notification(prefs, kind):
            logger.info(
                "Уведомление пропущено настройками пользователя user_id=%s kind=%s",
                user_id,
                kind,
            )
            return 0

        notification = Notification.objects.create(
            user_id=user_id,
            title=title,
            message=message,
            level=level,
            kind=kind,
            notification_date=timezone.now(),
        )
        logger.debug(
            f"Создано уведомление {notification.id} для пользователя {user_id}"
        )
        return notification.id

    except Exception as e:
        logger.exception(f"Ошибка создания уведомления для пользователя {user_id}: {e}")
        return 0


def _enqueue_batch_notification_for_user(
    i: int,
    user_data: dict,
    title_template: str,
    message_template: str,
    level: str,
    channels: list[str] | None,
) -> str | None:
    user_id = user_data.get("user_id")
    if not user_id:
        return f"User {i}: Missing user_id"
    title = title_template.format(**user_data)
    message = message_template.format(**user_data)
    send_notification_task.delay(
        user_id=user_id,
        title=title,
        message=message,
        level=level,
        channels=channels,
        data=user_data,
    )
    return None


@shared_task(
    name="app.core.tasks.dispatch_periodic_system_notifications",
)
def dispatch_periodic_system_notifications() -> dict:
    stats = {
        "total_users": 0,
        "sent_notifications": 0,
        "skipped_users": 0,
        "errors": 0,
    }

    try:
        r = get_redis()
        cooldown = int(
            getattr(settings, "SYSTEM_NOTIFICATION_USER_COOLDOWN_SECONDS", 86400)
        )

        users = User.objects.filter(is_active=True).only("id").iterator()

        for user in users:
            stats["total_users"] += 1

            try:
                prefs, _ = UserNotificationPreference.objects.get_or_create(user=user)
                if not (prefs.system_enabled and prefs.browser_enabled):
                    stats["skipped_users"] += 1
                    continue

                lock_key = f"nhub:sys24h:{user.id}"
                try:
                    if r.set(lock_key, "1", ex=cooldown, nx=True) is not True:
                        stats["skipped_users"] += 1
                        continue
                except Exception:
                    logger.exception(
                        f"System notification lock (Redis) failed for user {user.id}"
                    )
                    stats["errors"] += 1
                    continue

                send_notification_task.delay(
                    user.id,
                    "Системное обновление",
                    "NotifyHub работает стабильно. Все каналы связи активны.",
                    "info",
                    channels=[NotificationChannel.IN_APP.value],
                    data={"kind": Notification.Kind.SYSTEM},
                )
                stats["sent_notifications"] += 1

            except Exception:
                logger.exception(f"Ошибка обработки пользователя {user.id}")
                stats["errors"] += 1

        logger.info(f"Периодические уведомления отправлены: {stats}")
        return stats

    except Exception as e:
        logger.exception(f"Ошибка в периодических системных уведомлениях: {e}")
        stats["errors"] += 1
        return stats


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 3},
    name="app.core.tasks.send_batch_notifications",
)
def send_batch_notifications(
    self,
    users_data: list[dict],
    title_template: str,
    message_template: str,
    level: str = "info",
    channels: list[str] = None,
) -> dict:
    stats = {
        "total": len(users_data),
        "success": 0,
        "failed": 0,
        "errors": [],
    }

    try:
        for i, user_data in enumerate(users_data):
            try:
                err = _enqueue_batch_notification_for_user(
                    i,
                    user_data,
                    title_template,
                    message_template,
                    level,
                    channels,
                )
                if err:
                    stats["failed"] += 1
                    stats["errors"].append(err)
                    continue
                stats["success"] += 1
                if i % 10 == 0:
                    time.sleep(0.1)
            except Exception as e:
                stats["failed"] += 1
                stats["errors"].append(f"User {i}: {str(e)}")
                logger.error(
                    f"Ошибка отправки пакетного уведомления пользователю {i}: {e}"
                )

        logger.info(
            f"Пакетные уведомления отправлены: {stats['success']}/{stats['total']}"
        )
        return stats

    except Exception as exc:
        logger.exception(f"Критическая ошибка в пакетной отправке уведомлений: {exc}")
        raise self.retry(exc=exc)


@shared_task(
    name="app.core.tasks.cleanup_expired_tokens",
)
def cleanup_expired_tokens() -> int:
    try:
        deleted_count, _ = EmailLoginCode.objects.filter(
            models.Q(expires_at__lt=timezone.now()) | models.Q(used_at__isnull=False)
        ).delete()

        logger.info(f"Удалено {deleted_count} просроченных токенов")
        return deleted_count

    except Exception as e:
        logger.exception(f"Ошибка очистки просроченных токенов: {e}")
        return 0
