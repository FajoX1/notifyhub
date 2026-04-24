from django import forms
from django.contrib import admin
from django.contrib import messages
from django.urls import path, reverse
from django.contrib.auth import get_user_model
from django.shortcuts import redirect, render

from app.core.models import EmailLoginCode, Notification, UserNotificationPreference
from app.core.services.notification_service import (
    NotificationData,
    get_notification_service,
    should_deliver_notification,
)
from app.core.tasks import create_notification_task

User = get_user_model()


@admin.register(EmailLoginCode)
class EmailLoginCodeAdmin(admin.ModelAdmin):
    list_display = ("email", "code", "expires_at", "used_at", "created_at")
    search_fields = ("email",)
    list_filter = ("used_at", "created_at")


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("title", "user", "kind", "level", "is_read", "created_at")
    search_fields = ("title", "message", "user__email")
    list_filter = ("level", "is_read", "created_at")
    change_list_template = "admin/core/notification/change_list.html"

    class SendNotificationForm(forms.Form):
        user = forms.ModelChoiceField(
            queryset=User.objects.order_by("-id").only("id", "username", "email"),
            label="Пользователь",
        )
        title = forms.CharField(max_length=120, label="Заголовок")
        message = forms.CharField(widget=forms.Textarea, label="Текст")
        level = forms.ChoiceField(
            choices=Notification.Level.choices,
            initial=Notification.Level.INFO,
            label="Уровень",
        )
        kind = forms.ChoiceField(
            choices=Notification.Kind.choices,
            initial=Notification.Kind.SYSTEM,
            label="Тип уведомления",
        )
        send_async = forms.BooleanField(
            required=False,
            initial=True,
            label="Отправить через Celery (нужен запущенный celery-worker)",
        )

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                "send/",
                self.admin_site.admin_view(self.send_notification_view),
                name="core_notification_send",
            )
        ]
        return custom_urls + urls

    def send_notification_view(self, request):
        if request.method == "POST":
            form = self.SendNotificationForm(request.POST)
            if form.is_valid():
                payload = form.cleaned_data
                user_id = payload["user"].id
                preferences, _ = UserNotificationPreference.objects.get_or_create(
                    user_id=user_id
                )
                if not should_deliver_notification(preferences, payload["kind"]):
                    self.message_user(
                        request,
                        "Уведомление заблокировано настройками пользователя: выключен тип, mute или DND.",
                        level=messages.WARNING,
                    )
                    changelist_url = reverse("admin:core_notification_changelist")
                    return redirect(changelist_url)
                if payload["send_async"]:
                    task = create_notification_task.delay(
                        user_id,
                        payload["title"],
                        payload["message"],
                        payload["level"],
                        payload["kind"],
                    )
                    self.message_user(
                        request,
                        f"Уведомление поставлено в очередь. Task ID: {task.id}",
                        level=messages.SUCCESS,
                    )
                else:
                    result = get_notification_service().send_notification_sync(
                        NotificationData(
                            user_id=user_id,
                            title=payload["title"],
                            message=payload["message"],
                            level=payload["level"],
                            kind=payload["kind"],
                        )
                    )
                    if result.message == "skipped_by_preferences":
                        self.message_user(
                            request,
                            "Уведомление не отправлено: у пользователя отключен этот тип или активен mute.",
                            level=messages.WARNING,
                        )
                    else:
                        self.message_user(
                            request,
                            "Уведомление отправлено сразу (sync).",
                            level=messages.SUCCESS,
                        )
                changelist_url = reverse("admin:core_notification_changelist")
                return redirect(changelist_url)
        else:
            form = self.SendNotificationForm()

        context = {
            **self.admin_site.each_context(request),
            "opts": self.model._meta,
            "form": form,
            "title": "Отправка уведомления",
        }
        return render(request, "admin/core/notification/send_form.html", context)


@admin.register(UserNotificationPreference)
class UserNotificationPreferenceAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "payments_enabled",
        "messages_enabled",
        "system_enabled",
        "marketing_enabled",
        "security_enabled",
        "support_enabled",
        "mute_all_enabled",
        "email_enabled",
        "browser_enabled",
    )
    search_fields = ("user__email", "user__username")
