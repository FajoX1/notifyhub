from django.shortcuts import render
from django.core.paginator import Paginator
from django.http import HttpRequest, HttpResponse
from django.views.decorators.http import require_http_methods

from asgiref.sync import sync_to_async

from app.core.models import Notification
from app.core.responses import BaseResponse
from app.core.services import user_notifications
from app.core.views.common import async_login_required


@async_login_required
async def notifications_view(request: HttpRequest) -> HttpResponse:

    user = await request.auser()
    await Notification.objects.filter(user=user, is_read=False).aupdate(is_read=True)
    await sync_to_async(user_notifications.mark_all_read_in_redis)(int(user.pk))

    page_number = request.GET.get("page", 1)
    queryset = Notification.objects.filter(user=user).order_by(
        "-notification_date", "-id"
    )
    paginator = Paginator(queryset, 20)
    page_obj = await sync_to_async(paginator.get_page)(page_number)

    return await sync_to_async(render)(
        request,
        "notifications.html",
        {
            "notifications": page_obj.object_list,
            "page_obj": page_obj,
            "is_paginated": page_obj.paginator.num_pages > 1,
            "user": user,
        },
    )


@async_login_required
@require_http_methods(["POST"])
async def mark_notification_read(
    request: HttpRequest, notification_id: int
) -> BaseResponse:
    user = await request.auser()
    uid = int(user.pk)
    n = await Notification.objects.filter(id=notification_id, user=user).afirst()

    if not n:
        return BaseResponse.error(
            "Уведомление не найдено или уже удалено.",
            http_status=404,
        )
    if not n.is_read:
        n.is_read = True
        await n.asave(update_fields=["is_read"])
    await sync_to_async(user_notifications.mark_read_in_redis)(uid, notification_id)

    return BaseResponse.success()


@async_login_required
@require_http_methods(["POST"])
async def mark_all_read(request: HttpRequest) -> BaseResponse:
    user = await request.auser()
    await Notification.objects.filter(user=user, is_read=False).aupdate(is_read=True)
    await sync_to_async(user_notifications.mark_all_read_in_redis)(int(user.pk))

    return BaseResponse.success()


@async_login_required
async def notifications_feed(request: HttpRequest) -> BaseResponse:
    user = await request.auser()
    after_id_raw = request.GET.get("after_id", "0")

    try:
        after_id = int(after_id_raw)
    except ValueError:
        after_id = 0

    items = await sync_to_async(user_notifications.fetch_items_after_id)(
        int(user.pk), after_id, 20
    )

    return BaseResponse.success(data={"items": items})
