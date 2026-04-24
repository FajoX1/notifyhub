from __future__ import annotations

from django.template import loader
from django.http import HttpRequest, HttpResponse

from asgiref.sync import sync_to_async

from app.core.selectors.notification_selector import notification_selector
from app.core.decorators.error_handling import async_login_required_custom

import logging

logger = logging.getLogger(__name__)


@async_login_required_custom()
async def dashboard_view(request: HttpRequest) -> HttpResponse:
    user = await request.auser()
    status = 200

    try:
        notifications = await notification_selector.get_user_notifications(
            user_id=user.id,
            limit=10,
            unread_only=False,
        )
        unread_count = await notification_selector.get_unread_count(user.id)
        context = {
            "user": user,
            "notifications": notifications,
            "unread_count": unread_count,
            "total_notifications": len(notifications),
        }
    except Exception:
        logger.exception("dashboard_view failed user_id=%s", user.id)
        context = {
            "user": user,
            "error": "Не удалось загрузить данные. Попробуйте обновить страницу.",
        }
        status = 500

    template = loader.get_template("dashboard.html")
    content = await sync_to_async(template.render)(context, request)

    return HttpResponse(content, status=status)
