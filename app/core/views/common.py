from django.conf import settings
from django.http import HttpRequest
from django.shortcuts import redirect

PREFERENCE_FIELDS = {
    "payments_enabled",
    "messages_enabled",
    "system_enabled",
    "marketing_enabled",
    "security_enabled",
    "support_enabled",
    "email_enabled",
    "browser_enabled",
    "mute_all_enabled",
    "dnd_enabled",
}


def async_login_required(view_func):
    async def _wrapped(request: HttpRequest, *args, **kwargs):
        user = await request.auser()
        if not user.is_authenticated:
            return redirect(f"{settings.LOGIN_URL}?next={request.path}")
        request._cached_user = user
        return await view_func(request, *args, **kwargs)

    return _wrapped
