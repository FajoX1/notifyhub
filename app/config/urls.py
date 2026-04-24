"""
URL configuration for oauthproject project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.urls import include, path

from app.core.views import (
    RegisterView,
    dashboard_view,
    email_login_view,
    home,
    update_dnd,
    notifications_feed,
    mark_all_read,
    mark_notification_read,
    notifications_view,
    settings_view,
    toggle_preference,
)

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("allauth.urls")),
    path("auth/register/", RegisterView.as_view(), name="register"),
    path("", home, name="home"),
    path("login/email/", email_login_view, name="email-login"),
    path("dashboard/", dashboard_view, name="dashboard"),
    path("notifications/", notifications_view, name="notifications"),
    path("settings/", settings_view, name="settings"),
    path("api/notifications/read-all/", mark_all_read, name="read-all"),
    path(
        "api/notifications/<int:notification_id>/read/",
        mark_notification_read,
        name="read-notification",
    ),
    path("api/preferences/toggle/", toggle_preference, name="toggle-preference"),
    path("api/preferences/dnd/", update_dnd, name="update-dnd"),
    path("api/notifications/feed/", notifications_feed, name="notifications-feed"),
]
