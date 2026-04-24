from __future__ import annotations

from django.contrib.auth import get_user_model
from django.core.mail import EmailMultiAlternatives

from allauth.account.adapter import DefaultAccountAdapter
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter

from typing import Any

import logging

logger = logging.getLogger(__name__)


class NotifyHubAccountAdapter(DefaultAccountAdapter):
    """allauth emails (password reset и т.д.) не рвут HTTP при сбое SMTP."""

    def send_mail(
        self, template_prefix: str, email: str, context: dict[str, Any]
    ) -> None:
        logger.info(
            "allauth email send started template_prefix=%r email=%r",
            template_prefix,
            email,
        )
        try:
            message = self.render_mail(template_prefix, email, context)
            html_template = f"{template_prefix}_message.html"
            try:
                rendered_html = self.render_template(html_template, context)
                if isinstance(message, EmailMultiAlternatives) and rendered_html:
                    message.attach_alternative(rendered_html, "text/html")
            except Exception:
                logger.debug(
                    "HTML-шаблон %s не найден или не отрендерен", html_template
                )
            message.send()
            logger.info(
                "allauth email send completed template_prefix=%r email=%r",
                template_prefix,
                email,
            )
        except Exception:
            logger.exception(
                "Не удалось отправить письмо allauth (template_prefix=%r, email=%r)",
                template_prefix,
                email,
            )


class NotifyHubSocialAccountAdapter(DefaultSocialAccountAdapter):
    """
    После callback Google: если пользователь с таким email уже есть — связываем аккаунт.
    Иначе allauth создаёт пользователя (SOCIALACCOUNT_AUTO_SIGNUP).
    """

    def pre_social_login(self, request, sociallogin) -> None:  # type: ignore[no-untyped-def]
        if sociallogin.is_existing:
            return
        email = self._email_from_sociallogin(sociallogin)
        if not email:
            return
        User = get_user_model()
        try:
            user = User.objects.get(email__iexact=email)
        except User.DoesNotExist:
            return

        sociallogin.connect(request, user)

    @staticmethod
    def _email_from_sociallogin(sociallogin) -> str | None:  # type: ignore[no-untyped-def]
        data = sociallogin.account.extra_data or {}
        raw = data.get("email")
        if not raw:
            return None
        return str(raw).strip().lower()
