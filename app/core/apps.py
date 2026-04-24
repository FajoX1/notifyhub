from django.apps import AppConfig

from importlib import import_module


class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "app.core"

    def ready(self):
        import_module("app.core.signals")
        import_module("app.core.auth_signals")
