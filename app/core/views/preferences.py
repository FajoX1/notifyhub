from django.shortcuts import render
from django.http import HttpRequest, HttpResponse
from django.views.decorators.http import require_http_methods

from asgiref.sync import sync_to_async

from app.core.responses import BaseResponse
from app.core.models import UserNotificationPreference
from app.core.views.common import PREFERENCE_FIELDS, async_login_required

import re

_TIME_HHMM = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")


@async_login_required
async def settings_view(request: HttpRequest) -> HttpResponse:
    user = await request.auser()
    preferences, _ = await UserNotificationPreference.objects.aget_or_create(user=user)

    return await sync_to_async(render)(
        request,
        "settings.html",
        {
            "preferences": preferences,
            "user": user,
        },
    )


@async_login_required
@require_http_methods(["POST"])
async def update_dnd(request: HttpRequest) -> BaseResponse:
    user = await request.auser()
    preferences, _ = await UserNotificationPreference.objects.aget_or_create(user=user)

    start = request.POST.get("dnd_start", "").strip()
    end = request.POST.get("dnd_end", "").strip()

    if start and not _TIME_HHMM.match(start):
        return BaseResponse.error(
            "Некорректное время начала. Используйте формат ЧЧ:ММ.",
            http_status=400,
        )
    if end and not _TIME_HHMM.match(end):
        return BaseResponse.error(
            "Некорректное время окончания. Используйте формат ЧЧ:ММ.",
            http_status=400,
        )

    preferences.dnd_start = start or None
    preferences.dnd_end = end or None
    await preferences.asave(update_fields=["dnd_start", "dnd_end", "updated_at"])

    return BaseResponse.success()


@async_login_required
@require_http_methods(["POST"])
async def toggle_preference(request: HttpRequest) -> BaseResponse:
    user = await request.auser()
    key = request.POST.get("key", "").strip()
    value = request.POST.get("value", "").strip().lower()
    if not key or key not in PREFERENCE_FIELDS:
        return BaseResponse.error(
            "Неизвестный параметр настроек.",
            http_status=400,
        )

    preferences, _ = await UserNotificationPreference.objects.aget_or_create(user=user)
    parsed_value = value in {"true", "1", "yes", "on"}
    setattr(preferences, key, parsed_value)
    await preferences.asave(update_fields=[key, "updated_at"])

    return BaseResponse.success(data={"key": key, "value": parsed_value})
