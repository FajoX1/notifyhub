from app.core.views.landing import home
from app.core.views.auth import email_login_view
from app.core.views.register import RegisterView
from app.core.views.dashboard import dashboard_view
from app.core.views.notification_pages import (
    mark_all_read,
    notifications_feed,
    notifications_view,
    mark_notification_read,
)
from app.core.views.preferences import (
    update_dnd,
    settings_view,
    toggle_preference,
)

__all__ = [
    "RegisterView",
    "dashboard_view",
    "email_login_view",
    "home",
    "mark_all_read",
    "mark_notification_read",
    "notifications_feed",
    "notifications_view",
    "settings_view",
    "toggle_preference",
    "update_dnd",
]
