from app.config.celery import celery_app
from app.core.models import Notification

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer


def broadcast_notification(user_id: int, payload: dict) -> None:
    layer = get_channel_layer()
    if not layer:
        return

    async_to_sync(layer.group_send)(
        f"notifications_{user_id}",
        {
            "type": "notify.message",
            "payload": payload,
        },
    )


def send_notification(
    user_id: int,
    title: str,
    message: str,
    level: str = "info",
    kind: str = Notification.Kind.SYSTEM,
    *,
    use_celery: bool = True,
) -> str | int:
    if use_celery:
        task = celery_app.send_task(
            "app.core.tasks.create_notification_task",
            args=[user_id, title, message, level, kind],
        )
        return task.id

    notification = Notification.objects.create(
        user_id=user_id,
        title=title,
        message=message,
        level=level,
        kind=kind,
    )
    return notification.id
