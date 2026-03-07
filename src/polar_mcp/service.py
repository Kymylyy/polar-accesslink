from __future__ import annotations

from collections.abc import Callable
from typing import Any, Protocol

from .client import ApiResponse, RateLimitInfo
from .config import DEFAULT_CARDIO_LOAD_DAYS
from .errors import PolarMcpError, UpstreamServerError
from .response import build_error_response, build_response
from .tcx import parse_tcx_metadata
from .validation import (
    parse_iso_date,
    validate_activity_range,
    validate_cardio_load_days,
    validate_lookback,
    validate_non_empty_string,
)


class PolarClientProtocol(Protocol):
    def request_json(
        self,
        path: str,
        params: dict[str, Any] | None = None,
        treat_404_as_no_data: bool = False,
    ) -> ApiResponse: ...

    def request_text(
        self,
        path: str,
        params: dict[str, Any] | None = None,
        treat_404_as_no_data: bool = False,
    ) -> ApiResponse: ...


class PolarService:
    def __init__(self, client: PolarClientProtocol) -> None:
        self.client = client

    def execute(
        self,
        tool_name: str,
        query: dict[str, Any],
        fn: Callable[[], tuple[str, Any, RateLimitInfo | None]],
    ) -> dict[str, Any]:
        try:
            status, data, rate_limit = fn()
            return build_response(
                status=status,
                tool_name=tool_name,
                query=query,
                data=data,
                rate_limit=rate_limit,
            )
        except PolarMcpError as exc:
            return build_error_response(tool_name=tool_name, query=query, error=exc)
        except Exception:
            error = UpstreamServerError(
                "Unexpected tool failure.",
                "Retry. If this repeats, inspect server logs for stack traces.",
            )
            return build_error_response(tool_name=tool_name, query=query, error=error)

    def fetch_activities_range(
        self,
        from_date: str,
        to_date: str,
        include_samples: bool = False,
    ) -> tuple[str, Any, RateLimitInfo | None]:
        validate_activity_range(from_date, to_date)

        params: dict[str, Any] = {"from": from_date, "to": to_date}
        if include_samples:
            params.update(_samples_params())
        response = self.client.request_json("/users/activities/", params=params)
        status = "no_data" if _is_no_data_payload(response.payload) else "ok"
        return status, response.payload, response.rate_limit

    def fetch_activity_by_date(
        self,
        activity_date: str,
        include_samples: bool = False,
    ) -> tuple[str, Any, RateLimitInfo | None]:
        parsed = parse_iso_date(activity_date, field_name="date")
        validate_lookback(parsed, field_name="date")

        params = _samples_params() if include_samples else None
        response = self.client.request_json(
            f"/users/activities/{activity_date}",
            params=params,
            treat_404_as_no_data=True,
        )
        status = "no_data" if _is_no_data_payload(response.payload) else "ok"
        return status, response.payload, response.rate_limit

    def fetch_cardio_load_recent(
        self,
        days: int = DEFAULT_CARDIO_LOAD_DAYS,
    ) -> tuple[str, Any, RateLimitInfo | None]:
        validate_cardio_load_days(days)

        response = self.client.request_json(f"/users/cardio-load/period/days/{days}")
        status = "no_data" if _is_no_data_payload(response.payload) else "ok"
        return status, response.payload, response.rate_limit

    def fetch_cardio_load_by_date(
        self,
        cardio_date: str,
    ) -> tuple[str, Any, RateLimitInfo | None]:
        parse_iso_date(cardio_date, field_name="date")
        response = self.client.request_json(
            f"/users/cardio-load/{cardio_date}",
            treat_404_as_no_data=True,
        )
        status = "no_data" if _is_no_data_payload(response.payload) else "ok"
        return status, response.payload, response.rate_limit

    def fetch_exercises_recent(
        self,
        include_samples: bool = False,
        include_zones: bool = False,
        include_route: bool = False,
        include_tcx_metadata: bool = False,
    ) -> tuple[str, Any, RateLimitInfo | None]:
        response = self.client.request_json(
            "/exercises",
            params=_exercise_params(include_samples, include_zones, include_route),
        )
        payload = response.payload
        if _is_no_data_payload(payload):
            return "no_data", payload, response.rate_limit
        if include_tcx_metadata and isinstance(payload, list):
            payload = [self._enrich_exercise(item) for item in payload]
        return "ok", payload, response.rate_limit

    def fetch_exercise_by_id(
        self,
        exercise_id: str,
        include_samples: bool = False,
        include_zones: bool = False,
        include_route: bool = False,
        include_tcx_metadata: bool = False,
    ) -> tuple[str, Any, RateLimitInfo | None]:
        validated_id = validate_non_empty_string(exercise_id, field_name="exercise_id")
        response = self.client.request_json(
            f"/exercises/{validated_id}",
            params=_exercise_params(include_samples, include_zones, include_route),
            treat_404_as_no_data=True,
        )
        payload = response.payload
        if _is_no_data_payload(payload):
            return "no_data", payload, response.rate_limit
        if include_tcx_metadata and isinstance(payload, dict):
            payload = self._enrich_exercise(payload)
        return "ok", payload, response.rate_limit

    def _enrich_exercise(self, exercise: dict[str, Any]) -> dict[str, Any]:
        exercise_id = exercise.get("id")
        if not isinstance(exercise_id, str) or not exercise_id:
            return {
                "exercise": exercise,
                "tcx_metadata": {"title": None, "notes": None},
            }

        tcx_response = self.client.request_text(
            f"/exercises/{exercise_id}/tcx",
            treat_404_as_no_data=True,
        )
        metadata: dict[str, str | None] = {"title": None, "notes": None}
        if isinstance(tcx_response.payload, str) and tcx_response.payload:
            metadata = parse_tcx_metadata(tcx_response.payload)
        return {
            "exercise": exercise,
            "tcx_metadata": metadata,
        }


def _samples_params() -> dict[str, str]:
    return {
        "steps": "true",
        "activity_zones": "true",
        "inactivity_stamps": "true",
    }


def _exercise_params(
    include_samples: bool,
    include_zones: bool,
    include_route: bool,
) -> dict[str, str] | None:
    params: dict[str, str] = {}
    if include_samples:
        params["samples"] = "true"
    if include_zones:
        params["zones"] = "true"
    if include_route:
        params["route"] = "true"
    return params or None


def _is_no_data_payload(payload: Any) -> bool:
    if payload is None:
        return True
    if isinstance(payload, list):
        return len(payload) == 0
    if isinstance(payload, dict):
        return len(payload) == 0
    return False
