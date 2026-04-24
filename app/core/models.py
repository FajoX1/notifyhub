from django.db import models
from django.utils import timezone
from django.contrib.auth import get_user_model

User = get_user_model()


class EmailLoginCode(models.Model):
    email = models.EmailField(db_index=True)
    code = models.CharField(max_length=6)
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)

    @property
    def is_expired(self) -> bool:
        return timezone.now() > self.expires_at

    @property
    def is_active(self) -> bool:
        return self.used_at is None and not self.is_expired


class Notification(models.Model):
    class Level(models.TextChoices):
        INFO = "info", "Info"
        SUCCESS = "success", "Success"
        WARNING = "warning", "Warning"
        ERROR = "error", "Error"

    class Kind(models.TextChoices):
        SYSTEM = "system", "Системное"
        MESSAGE = "message", "Сообщение"
        PAYMENT = "payment", "Платежи"
        SECURITY = "security", "Безопасность"
        SUPPORT = "support", "Поддержка"
        MARKETING = "marketing", "Маркетинг"

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="notifications",
    )
    title = models.CharField(max_length=120)
    message = models.TextField()
    level = models.CharField(
        max_length=16,
        choices=Level.choices,
        default=Level.INFO,
    )
    kind = models.CharField(
        max_length=24,
        choices=Kind.choices,
        default=Kind.SYSTEM,
        db_index=True,
    )
    is_read = models.BooleanField(default=False, db_index=True)
    notification_date = models.DateTimeField(
        default=timezone.now,
        db_index=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-notification_date", "-id")


class UserNotificationPreference(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="notification_preferences",
    )
    payments_enabled = models.BooleanField(default=True)
    messages_enabled = models.BooleanField(default=True)
    system_enabled = models.BooleanField(default=True)
    marketing_enabled = models.BooleanField(default=False)
    security_enabled = models.BooleanField(default=True)
    support_enabled = models.BooleanField(default=True)
    email_enabled = models.BooleanField(default=True)
    browser_enabled = models.BooleanField(default=True)
    mute_all_enabled = models.BooleanField(default=False)
    dnd_enabled = models.BooleanField(default=False)
    dnd_start = models.TimeField(null=True, blank=True)
    dnd_end = models.TimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
