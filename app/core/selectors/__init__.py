"""Read-side query modules."""

from app.core.selectors.notification_selector import (
    email_code_selector,
    notification_selector,
)

__all__ = ("email_code_selector", "notification_selector")
