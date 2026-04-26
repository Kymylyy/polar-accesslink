from __future__ import annotations

from typing import Any

from ..service import PolarService


def activities_range(
    service: PolarService,
    from_date: str,
    to_date: str,
    include_samples: bool = False,
) -> dict[str, Any]:
    query = {
        "from_date": from_date,
        "to_date": to_date,
        "include_samples": include_samples,
    }
    return service.execute(
        "activities_range",
        query,
        lambda: service.fetch_activities_range(from_date, to_date, include_samples),
    )


def activity_by_date(
    service: PolarService,
    date: str,
    include_samples: bool = False,
) -> dict[str, Any]:
    query = {"date": date, "include_samples": include_samples}
    return service.execute(
        "activity_by_date",
        query,
        lambda: service.fetch_activity_by_date(date, include_samples),
    )
