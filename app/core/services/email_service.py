from __future__ import annotations

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template import loader
from django.template.exceptions import TemplateDoesNotExist

from enum import Enum
from functools import lru_cache
from dataclasses import dataclass
from abc import ABC, abstractmethod
from typing import Any, Protocol, runtime_checkable
from asgiref.sync import async_to_sync, sync_to_async

import asyncio
import logging

logger = logging.getLogger(__name__)


class EmailTemplate(str, Enum):
    LOGIN_CODE = "login_code"
    REGISTRATION_CONFIRMATION = "registration_confirmation"
    PASSWORD_RESET = "password_reset"
    EMAIL_VERIFICATION = "email_verification"
    NOTIFICATION_INFO = "notification_info"
    NOTIFICATION_SUCCESS = "notification_success"
    NOTIFICATION_WARNING = "notification_warning"
    NOTIFICATION_ERROR = "notification_error"
    SYSTEM_UPDATE = "system_update"
    WELCOME = "welcome"
    ADMIN_ALERT = "admin_alert"
    SECURITY_ALERT = "security_alert"


def _email_base_context(extra: dict[str, Any] | None = None) -> dict[str, Any]:
    base: dict[str, Any] = {
        "site_url": str(getattr(settings, "SITE_URL", "") or "").rstrip("/"),
        "site_name": "NotifyHub",
    }
    if extra:
        base.update(extra)
    return base


def _render_html_sync(template: EmailTemplate, context: dict[str, Any]) -> str:
    ctx = _email_base_context(context)
    path = f"email/{template.value}.html"
    try:
        return loader.render_to_string(path, ctx)
    except TemplateDoesNotExist:
        if (
            template.value.startswith("notification_")
            and template != EmailTemplate.NOTIFICATION_INFO
        ):
            return loader.render_to_string("email/notification_info.html", ctx)
        logger.warning("Шаблон %s не найден, используется base.html", path)
        return loader.render_to_string(
            "email/base.html",
            {**ctx, "subject": ctx.get("subject", "Уведомление")},
        )


def _render_text_sync(template: EmailTemplate, context: dict[str, Any]) -> str:
    ctx = _email_base_context(context)
    path = f"email/{template.value}.txt"
    try:
        return loader.render_to_string(path, ctx)
    except TemplateDoesNotExist:
        title = ctx.get("title") or ctx.get("subject") or "Сообщение"
        body = ctx.get("message") or ctx.get("code") or ""
        return f"{title}\n\n{body}\n"


_render_html = sync_to_async(_render_html_sync, thread_sensitive=True)
_render_text = sync_to_async(_render_text_sync, thread_sensitive=True)


@dataclass(frozen=True)
class EmailMessage:
    template_name: EmailTemplate
    to: list[str]
    subject: str
    context: dict[str, Any]
    from_email: str | None = None
    bcc: list[str] | None = None
    cc: list[str] | None = None
    reply_to: list[str] | None = None
    attachments: list[dict[str, Any]] | None = None

    def __post_init__(self) -> None:
        if not self.to:
            raise ValueError("Recipient list cannot be empty")
        if not isinstance(self.template_name, EmailTemplate):
            raise TypeError("template_name must be EmailTemplate")


@runtime_checkable
class EmailSenderProtocol(Protocol):
    async def send(self, message: EmailMessage) -> bool: ...


class AbstractEmailSender(ABC):
    @abstractmethod
    async def send(self, message: EmailMessage) -> bool:
        raise NotImplementedError


class DjangoEmailSender(AbstractEmailSender):
    def __init__(self, connection: Any | None = None) -> None:
        self._connection = connection

    async def send(self, message: EmailMessage) -> bool:
        logger.info(
            "Email send started template=%s to=%r subject=%r",
            message.template_name.value,
            message.to,
            message.subject,
        )
        try:
            html_content = await _render_html(message.template_name, message.context)
            text_content = await _render_text(message.template_name, message.context)
            email = EmailMultiAlternatives(
                subject=message.subject,
                body=text_content,
                from_email=message.from_email or settings.DEFAULT_FROM_EMAIL,
                to=message.to,
                bcc=message.bcc,
                cc=message.cc,
                reply_to=message.reply_to,
                connection=self._connection,
            )
            email.attach_alternative(html_content, "text/html")
            if message.attachments:
                for attachment in message.attachments:
                    email.attach(**attachment)
            await sync_to_async(email.send)(fail_silently=False)
            logger.info(
                "Email send completed template=%s to=%r subject=%r",
                message.template_name.value,
                message.to,
                message.subject,
            )
            return True
        except Exception:
            logger.exception(
                "Ошибка отправки email (template=%s, to=%r)",
                message.template_name.value,
                message.to,
            )
            return False


class EmailService:
    def __init__(self, sender: EmailSenderProtocol | None = None) -> None:
        self._sender = sender or DjangoEmailSender()
        self._background_tasks: set[asyncio.Task[Any]] = set()

    async def send_email(
        self,
        template_name: EmailTemplate | str,
        context: dict[str, Any],
        recipient_list: list[str],
        subject: str,
        *,
        from_email: str | None = None,
        bcc: list[str] | None = None,
        cc: list[str] | None = None,
        reply_to: list[str] | None = None,
        attachments: list[dict[str, Any]] | None = None,
        send_async: bool = True,
    ) -> bool:
        if isinstance(template_name, str):
            try:
                template_name = EmailTemplate(template_name)
            except ValueError:
                logger.error("Неизвестный тип шаблона: %s", template_name)
                return False

        logger.info(
            "Email request received template=%s recipients=%d send_async=%s",
            template_name.value,
            len(recipient_list),
            send_async,
        )

        message = EmailMessage(
            template_name=template_name,
            to=recipient_list,
            subject=subject,
            context=context,
            from_email=from_email,
            bcc=bcc,
            cc=cc,
            reply_to=reply_to,
            attachments=attachments,
        )

        if send_async:
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                logger.info(
                    "Email send executing synchronously template=%s (no running loop)",
                    template_name.value,
                )
                return await self._sender.send(message)
            task = loop.create_task(self._send_background(message))
            task.add_done_callback(self._background_tasks.discard)
            self._background_tasks.add(task)
            logger.info(
                "Email send scheduled in background template=%s to=%r",
                template_name.value,
                recipient_list,
            )
            return True

        logger.info(
            "Email send executing synchronously template=%s to=%r",
            template_name.value,
            recipient_list,
        )
        return await self._sender.send(message)

    async def _send_background(self, message: EmailMessage) -> None:
        try:
            await self._sender.send(message)
        except Exception:
            logger.exception("Фоновая отправка: %s", message.template_name)

    async def send_login_code(
        self,
        email: str,
        code: str,
        *,
        send_async: bool = True,
    ) -> bool:
        context = {"email": email, "code": code, "valid_minutes": 10}
        return await self.send_email(
            EmailTemplate.LOGIN_CODE,
            context,
            [email],
            "NotifyHub: код для входа",
            send_async=send_async,
        )

    async def send_notification(
        self,
        user_email: str,
        title: str,
        body: str,
        level: str = "info",
        *,
        send_async: bool = True,
    ) -> bool:
        context = {
            "title": title,
            "message": body,
            "level": level,
            "user_email": user_email,
        }
        template_map = {
            "info": EmailTemplate.NOTIFICATION_INFO,
            "success": EmailTemplate.NOTIFICATION_SUCCESS,
            "warning": EmailTemplate.NOTIFICATION_WARNING,
            "error": EmailTemplate.NOTIFICATION_ERROR,
        }
        template_name = template_map.get(level, EmailTemplate.NOTIFICATION_INFO)
        return await self.send_email(
            template_name,
            context,
            [user_email],
            f"NotifyHub: {title}",
            send_async=send_async,
        )

    async def send_welcome_email(
        self,
        email: str,
        username: str | None = None,
        *,
        send_async: bool = True,
    ) -> bool:
        site = str(getattr(settings, "SITE_URL", "") or "").rstrip("/")
        context = {
            "email": email,
            "username": username or email.split("@", maxsplit=1)[0],
            "login_url": f"{site}/accounts/login/" if site else "/accounts/login/",
        }
        return await self.send_email(
            EmailTemplate.WELCOME,
            context,
            [email],
            "Добро пожаловать в NotifyHub!",
            send_async=send_async,
        )

    async def send_security_alert(
        self,
        email: str,
        *,
        username: str | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        login_time: str | None = None,
        send_async: bool = True,
    ) -> bool:
        site = str(getattr(settings, "SITE_URL", "") or "").rstrip("/")
        context = {
            "email": email,
            "username": username or email.split("@", maxsplit=1)[0],
            "ip_address": ip_address or "Не удалось определить",
            "user_agent": user_agent or "Не удалось определить",
            "login_time": login_time or "Только что",
            "security_url": f"{site}/settings/" if site else "/settings/",
        }
        return await self.send_email(
            EmailTemplate.SECURITY_ALERT,
            context,
            [email],
            "Security Alert: вход в ваш аккаунт NotifyHub",
            send_async=send_async,
        )


@lru_cache(maxsize=1)
def get_email_service() -> EmailService:
    return EmailService()


def send_email_sync(
    template_name: EmailTemplate | str,
    context: dict[str, Any],
    recipient_list: list[str],
    subject: str,
    **kwargs: Any,
) -> bool:
    return async_to_sync(get_email_service().send_email)(
        template_name,
        context,
        recipient_list,
        subject,
        send_async=False,
        **kwargs,
    )
