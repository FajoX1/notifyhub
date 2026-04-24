from __future__ import annotations

from django.conf import settings

from typing import Any

from app.core.services import user_notifications


def oauth_providers(_request) -> dict[str, Any]:
    app = (getattr(settings, "SOCIALACCOUNT_PROVIDERS", {}) or {}).get(
        "google", {}
    ).get("APP") or {}
    client_id = (app.get("client_id") or "").strip()
    secret = (app.get("secret") or "").strip()

    return {"google_oauth_enabled": bool(client_id and secret)}


def notification_state(request) -> dict[str, int]:
    if not request.user.is_authenticated:
        return {
            "notify_feed_cursor": 0,
            "unread_count": 0,
        }
    uid = int(request.user.pk)

    return {
        "notify_feed_cursor": user_notifications.get_feed_cursor_max_id(uid),
        "unread_count": user_notifications.get_unread_count(uid),
    }
