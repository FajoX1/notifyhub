from __future__ import annotations

from django import template
from django.contrib import messages
from django.utils.html import json_script

register = template.Library()

_LEVEL_SLUGS = frozenset({"info", "success", "warning", "error", "debug"})
_KIND_LABELS = {
    "system": "Системное",
    "message": "Сообщения",
    "payment": "Платежи",
    "marketing": "Маркетинг",
    "security": "Безопасность",
    "support": "Поддержка",
}


@register.filter
def nh_level_slug(value: object) -> str:
    s = str(value or "").strip().lower()
    return s if s in _LEVEL_SLUGS else "info"


@register.filter
def nh_kind_label(value: object) -> str:
    s = str(value or "").strip().lower()
    return _KIND_LABELS.get(s, _KIND_LABELS["system"])


@register.simple_tag(takes_context=True)
def django_messages_json(context) -> str:
    request = context["request"]
    storage = messages.get_messages(request)

    payload = [{"tags": m.tags, "body": str(m)} for m in storage]
    if not payload:
        return ""

    return json_script(payload, "django-messages-data")
