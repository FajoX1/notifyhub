from django.conf import settings
from django.db.models import Max

from typing import Any

from app.core.models import Notification
from app.core.utils.redis_client import get_redis

import json
import logging

logger = logging.getLogger(__name__)

_LEVELS = frozenset({"info", "success", "warning", "error", "debug"})
_KINDS = frozenset({"system", "message", "payment", "security", "support", "marketing"})


def _normalize_feed_record(data: dict[str, Any]) -> dict[str, Any]:
    out = dict(data)
    raw_id = out.get("id")

    if raw_id is not None:
        try:
            out["id"] = int(raw_id)
        except (TypeError, ValueError):
            pass
    ir = out.get("is_read")

    if isinstance(ir, str):
        out["is_read"] = ir.strip().lower() in ("true", "1", "yes")
    else:
        out["is_read"] = bool(ir)

    lev = str(out.get("level") or "info").strip().lower()
    out["level"] = lev if lev in _LEVELS else "info"
    kind = str(out.get("kind") or "system").strip().lower()
    out["kind"] = kind if kind in _KINDS else "system"
    out["title"] = "" if out.get("title") is None else str(out["title"])
    out["message"] = "" if out.get("message") is None else str(out["message"])

    return out


def _feed_key(user_id: int) -> str:
    return f"nhub:feed:{user_id}"


def _item_key(user_id: int, notification_id: int) -> str:
    return f"nhub:item:{user_id}:{notification_id}"


def _ttl() -> int:
    return int(getattr(settings, "NOTIFICATION_REDIS_TTL_SECONDS", 604800))


def store_from_instance(notification: Notification) -> None:
    r = get_redis()
    ttl = _ttl()
    uid = notification.user_id
    nid = notification.id
    data: dict[str, Any] = {
        "id": nid,
        "title": notification.title,
        "message": notification.message,
        "level": notification.level,
        "kind": notification.kind,
        "is_read": notification.is_read,
        "notification_date": notification.notification_date.isoformat(),
        "created_at": notification.created_at.isoformat(),
    }
    key = _item_key(uid, nid)

    try:
        pipe = r.pipeline()
        pipe.set(key, json.dumps(data), ex=ttl)
        pipe.zadd(_feed_key(uid), {str(nid): float(nid)})
        pipe.execute()
    except Exception as exc:  # noqa: BLE001
        logger.exception("Store notification in Redis failed: %s", exc)


def list_notifications(user_id: int, limit: int = 200) -> list[dict[str, Any]]:
    r = get_redis()
    key = _feed_key(user_id)

    try:
        ids = r.zrevrange(key, 0, max(0, limit - 1))
    except Exception as exc:  # noqa: BLE001
        logger.exception("List notifications (Redis) failed: %s", exc)
        return []

    if not ids:
        return []

    keys = [_item_key(user_id, int(x)) for x in ids]
    try:
        values = r.mget(keys)
    except Exception as exc:  # noqa: BLE001
        logger.exception("MGET notification items (Redis) failed: %s", exc)
        return []

    out: list[dict[str, Any]] = []
    to_remove: list[str] = []

    for raw_id, val in zip(ids, values):
        if not val:
            to_remove.append(str(raw_id))
            continue
        out.append(_normalize_feed_record(json.loads(val)))

    if to_remove:
        try:
            r.zrem(key, *to_remove)
        except Exception:  # noqa: BLE001
            logger.debug("ZREM stale ids failed for user %s", user_id, exc_info=True)

    return out


def get_feed_cursor_max_id(user_id: int) -> int:
    v = Notification.objects.filter(user_id=user_id).aggregate(m=Max("id")).get("m")
    return int(v or 0)


def get_unread_count(user_id: int) -> int:
    return Notification.objects.filter(user_id=user_id, is_read=False).count()


def fetch_items_after_id(
    user_id: int, after_id: int, limit: int = 20
) -> list[dict[str, Any]]:
    r = get_redis()
    key = _feed_key(user_id)

    try:
        raw_ids = r.zrangebyscore(key, f"({after_id}", "+inf", start=0, num=limit)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Fetch after_id (Redis) failed: %s", exc)
        return []

    if not raw_ids:
        return _fetch_items_after_id_from_db(user_id, after_id, limit)

    keys = [_item_key(user_id, int(x)) for x in raw_ids]
    try:
        values = r.mget(keys)
    except Exception as exc:  # noqa: BLE001
        logger.exception("MGET in fetch (Redis) failed: %s", exc)
        return []

    out: list[dict[str, Any]] = []
    to_remove: list[str] = []
    for raw_id, val in zip(raw_ids, values):
        if not val:
            to_remove.append(str(raw_id))
            continue
        out.append(_normalize_feed_record(json.loads(val)))

    if to_remove:
        try:
            r.zrem(key, *to_remove)
        except Exception:  # noqa: BLE001
            logger.debug("ZREM stale in fetch for user %s", user_id, exc_info=True)
    if out:
        return out

    return _fetch_items_after_id_from_db(user_id, after_id, limit)


def mark_read_in_redis(user_id: int, notification_id: int) -> bool:
    r = get_redis()
    key = _item_key(user_id, notification_id)

    try:
        raw = r.get(key)
    except Exception as exc:  # noqa: BLE001
        logger.exception("mark_read get (Redis) failed: %s", exc)
        return False

    if not raw:
        return False

    data = _normalize_feed_record(json.loads(raw))

    if data.get("is_read"):
        return True

    data["is_read"] = True

    try:
        ttl = r.ttl(key)
    except Exception:  # noqa: BLE001
        ttl = -1

    if ttl is None or ttl < 0:
        ttl = _ttl()

    try:
        r.set(key, json.dumps(data), ex=ttl)
    except Exception as exc:  # noqa: BLE001
        logger.exception("mark_read set (Redis) failed: %s", exc)
        return False

    return True


def _fetch_items_after_id_from_db(
    user_id: int,
    after_id: int,
    limit: int,
) -> list[dict[str, Any]]:
    rows = list(
        Notification.objects.filter(user_id=user_id, id__gt=after_id)
        .order_by("id")[:limit]
        .values(
            "id",
            "title",
            "message",
            "level",
            "kind",
            "is_read",
            "notification_date",
            "created_at",
        )
    )

    for row in rows:
        notification_date = row.get("notification_date")
        row["notification_date"] = (
            notification_date.isoformat() if notification_date else ""
        )
        created_at = row.get("created_at")
        row["created_at"] = created_at.isoformat() if created_at else ""

    return rows


def mark_all_read_in_redis(user_id: int) -> None:
    for item in list_notifications(user_id, 2000):
        if not item.get("is_read"):
            mark_read_in_redis(user_id, int(item["id"]))
