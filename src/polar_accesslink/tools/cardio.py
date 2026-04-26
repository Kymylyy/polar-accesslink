from __future__ import annotations

from typing import Any

from ..config import DEFAULT_CARDIO_LOAD_DAYS
from ..service import PolarService


def cardio_load_recent(
    service: PolarService,
    days: int = DEFAULT_CARDIO_LOAD_DAYS,
) -> dict[str, Any]:
    query = {"days": days}
    return service.execute(
        "cardio_load_recent",
        query,
        lambda: service.fetch_cardio_load_recent(days),
    )


def cardio_load_by_date(service: PolarService, date: str) -> dict[str, Any]:
    query = {"date": date}
    return service.execute(
        "cardio_load_by_date",
        query,
        lambda: service.fetch_cardio_load_by_date(date),
    )
