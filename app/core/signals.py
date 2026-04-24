from django.db import transaction
from django.dispatch import receiver
from django.db.models.signals import post_save

from app.core.models import Notification
from app.core.services import user_notifications
from app.core.services.messaging import broadcast_notification


@receiver(post_save, sender=Notification)
def on_notification_post_save(
    sender, instance: Notification, created: bool, **kwargs
) -> None:
    if not created:
        return

    def _after_commit() -> None:
        user_notifications.store_from_instance(instance)
        broadcast_notification(
            user_id=instance.user_id,
            payload={
                "id": instance.id,
                "title": instance.title,
                "message": instance.message,
                "level": instance.level,
                "kind": instance.kind,
                "is_read": instance.is_read,
                "notification_date": instance.notification_date.isoformat(),
                "created_at": instance.created_at.isoformat(),
            },
        )

    transaction.on_commit(_after_commit)
