from dotenv import load_dotenv

from app.config.celery import celery_app

import os

load_dotenv()

# Символ $ в дефолтном SECRET_KEY ломал docker compose: в .env подстрока $name…
# интерпретировалась как подстановка переменной. Держим ключ без $.
SECRET_KEY = os.getenv(
    "SECRET_KEY",
    "django-insecure-dev-only-replace-abcdef0123456789-CHANGE-IN-PRODUCTION",
)
DEBUG = os.getenv("DEBUG", "True").lower() == "true"

POSTGRES_NAME = os.getenv("POSTGRES_NAME", "oauthproject")
POSTGRES_USER = os.getenv("POSTGRES_USER", "oauthdjango")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "")
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "127.0.0.1")
POSTGRES_PORT = int(os.getenv("POSTGRES_PORT", "5432"))

EMAIL_HOST = os.getenv("EMAIL_HOST", "localhost")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", "1025"))
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = os.getenv("EMAIL_USE_TLS", "False").lower() in ("true", "1", "yes")
EMAIL_USE_SSL = os.getenv("EMAIL_USE_SSL", "False").lower() in ("true", "1", "yes")
DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL", "noreply@localhost")

SITE_URL = os.getenv("SITE_URL", "http://127.0.0.1:8000")

# Для OAuth redirect_uri: на проде с HTTPS задайте "https" (должно совпадать с Google Console).
ACCOUNT_DEFAULT_HTTP_PROTOCOL = os.getenv(
    "ACCOUNT_DEFAULT_HTTP_PROTOCOL", "http"
).lower()

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")

REDIS_HOST = os.getenv("REDIS_HOST", "127.0.0.1")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_DB = int(os.getenv("REDIS_DB", "0"))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", "")
REDIS_URL = os.getenv(
    "REDIS_URL",
    f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}",
)

__all__ = ("celery_app",)
