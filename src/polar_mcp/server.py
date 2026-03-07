from __future__ import annotations

import os
from typing import Any

from .client import PolarApiClient
from .config import BASE_URL
from .errors import ValidationError
from .service import PolarService
from .tools import (
    activities_range,
    activity_by_date,
    cardio_load_by_date,
    cardio_load_recent,
    exercise_by_id,
    exercises_recent,
)

try:
    from fastmcp import FastMCP as _FastMCP
except ModuleNotFoundError:  # pragma: no cover
    FastMCP: Any = None
else:
    FastMCP = _FastMCP


_SERVICE: PolarService | None = None


def build_service() -> PolarService:
    access_token = os.getenv("POLAR_ACCESS_TOKEN", "").strip()
    if not access_token:
        raise ValidationError(
            "POLAR_ACCESS_TOKEN is missing.",
            "Set POLAR_ACCESS_TOKEN in MCP server environment before startup.",
        )
    client = PolarApiClient(access_token=access_token, base_url=BASE_URL)
    return PolarService(client)


def get_service() -> PolarService:
    global _SERVICE
    if _SERVICE is None:
        _SERVICE = build_service()
    return _SERVICE


def create_mcp_server() -> Any:
    if FastMCP is None:
        raise RuntimeError("fastmcp is not installed. Install dependencies before running server.")

    mcp = FastMCP("polar")

    @mcp.tool()
    def tool_activities_range(
        from_date: str,
        to_date: str,
        include_samples: bool = False,
    ) -> dict[str, Any]:
        service = get_service()
        return activities_range(
            service,
            from_date=from_date,
            to_date=to_date,
            include_samples=include_samples,
        )

    @mcp.tool()
    def tool_activity_by_date(date: str, include_samples: bool = False) -> dict[str, Any]:
        service = get_service()
        return activity_by_date(service, date=date, include_samples=include_samples)

    @mcp.tool()
    def tool_cardio_load_recent(days: int = 30) -> dict[str, Any]:
        service = get_service()
        return cardio_load_recent(service, days=days)

    @mcp.tool()
    def tool_cardio_load_by_date(date: str) -> dict[str, Any]:
        service = get_service()
        return cardio_load_by_date(service, date=date)

    @mcp.tool()
    def tool_exercises_recent(
        include_samples: bool = False,
        include_zones: bool = False,
        include_route: bool = False,
        include_tcx_metadata: bool = False,
    ) -> dict[str, Any]:
        service = get_service()
        return exercises_recent(
            service,
            include_samples=include_samples,
            include_zones=include_zones,
            include_route=include_route,
            include_tcx_metadata=include_tcx_metadata,
        )

    @mcp.tool()
    def tool_exercise_by_id(
        exercise_id: str,
        include_samples: bool = False,
        include_zones: bool = False,
        include_route: bool = False,
        include_tcx_metadata: bool = False,
    ) -> dict[str, Any]:
        service = get_service()
        return exercise_by_id(
            service,
            exercise_id=exercise_id,
            include_samples=include_samples,
            include_zones=include_zones,
            include_route=include_route,
            include_tcx_metadata=include_tcx_metadata,
        )

    return mcp


def main() -> None:
    server = create_mcp_server()
    server.run()


if __name__ == "__main__":
    main()
