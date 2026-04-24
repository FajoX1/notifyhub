from __future__ import annotations

from typing import Any

from django.http import JsonResponse


def build_response_payload(
    *,
    outcome: str = "success",
    data: dict[str, Any] | list[Any] | None = None,
    message: str | None = None,
    details: Any = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {"status": outcome, "ok": outcome == "success"}
    if data is not None:
        payload["data"] = data
    if message is not None:
        payload["message"] = message
    if details is not None:
        payload["details"] = details
    return payload


class BaseResponse(JsonResponse):
    def __init__(
        self,
        *,
        outcome: str = "success",
        data: dict[str, Any] | list[Any] | None = None,
        message: str | None = None,
        details: Any = None,
        http_status: int = 200,
    ) -> None:
        self._payload = build_response_payload(
            outcome=outcome,
            data=data,
            message=message,
            details=details,
        )
        super().__init__(
            self._payload,
            status=http_status,
            json_dumps_params={"ensure_ascii": False},
        )

    def to_dict(self) -> dict[str, Any]:
        return dict(self._payload)

    @classmethod
    def success(
        cls,
        *,
        data: dict[str, Any] | list[Any] | None = None,
        message: str | None = None,
        http_status: int = 200,
    ) -> BaseResponse:
        return cls(
            outcome="success",
            data=data,
            message=message,
            http_status=http_status,
        )

    @classmethod
    def error(
        cls,
        message: str,
        *,
        details: Any = None,
        http_status: int = 400,
    ) -> BaseResponse:
        return cls(
            outcome="error",
            message=message,
            details=details,
            http_status=http_status,
        )
