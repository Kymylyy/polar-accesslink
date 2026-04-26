from __future__ import annotations

from typing import Any

from ..service import PolarService


def exercises_recent(
    service: PolarService,
    include_samples: bool = False,
    include_zones: bool = False,
    include_route: bool = False,
    include_tcx_metadata: bool = False,
) -> dict[str, Any]:
    query = {
        "include_samples": include_samples,
        "include_zones": include_zones,
        "include_route": include_route,
        "include_tcx_metadata": include_tcx_metadata,
    }
    return service.execute(
        "exercises_recent",
        query,
        lambda: service.fetch_exercises_recent(
            include_samples=include_samples,
            include_zones=include_zones,
            include_route=include_route,
            include_tcx_metadata=include_tcx_metadata,
        ),
    )


def exercise_by_id(
    service: PolarService,
    exercise_id: str,
    include_samples: bool = False,
    include_zones: bool = False,
    include_route: bool = False,
    include_tcx_metadata: bool = False,
) -> dict[str, Any]:
    query = {
        "exercise_id": exercise_id,
        "include_samples": include_samples,
        "include_zones": include_zones,
        "include_route": include_route,
        "include_tcx_metadata": include_tcx_metadata,
    }
    return service.execute(
        "exercise_by_id",
        query,
        lambda: service.fetch_exercise_by_id(
            exercise_id=exercise_id,
            include_samples=include_samples,
            include_zones=include_zones,
            include_route=include_route,
            include_tcx_metadata=include_tcx_metadata,
        ),
    )
