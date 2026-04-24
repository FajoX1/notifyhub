from django.conf import settings
from django.utils.functional import SimpleLazyObject

import redis


def _build_client() -> redis.Redis:
    return redis.from_url(
        settings.REDIS_URL,
        decode_responses=True,
        socket_connect_timeout=2,
    )


redis_client: redis.Redis = SimpleLazyObject(_build_client)  # type: ignore[assignment]


def get_redis() -> redis.Redis:
    return redis_client
