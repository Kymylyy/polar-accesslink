from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from .client import RateLimitInfo
from .errors import PolarAccessLinkError


def build_response(
    *,
    status: str,
    tool_name: str,
    query: dict[str, Any],
    data: Any,
    rate_limit: RateLimitInfo | None,
) -> dict[str, Any]:
    return {
        "status": status,
        "query": query,
        "data": data,
        "meta": {
            "tool": tool_name,
            "generated_at": _generated_at(),
            "source": "polar_accesslink",
            "rate_limit": rate_limit,
        },
    }


def build_error_response(
    *,
    tool_name: str,
    query: dict[str, Any],
    error: PolarAccessLinkError,
) -> dict[str, Any]:
    return {
        "status": "error",
        "query": query,
        "data": None,
        "error": {
            "type": error.__class__.__name__,
            "message": error.message,
            "hint": error.hint,
        },
        "meta": {
            "tool": tool_name,
            "generated_at": _generated_at(),
            "source": "polar_accesslink",
            "rate_limit": None,
        },
    }


def _generated_at() -> str:
    return (
        datetime.now(UTC)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )
