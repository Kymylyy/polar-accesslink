from __future__ import annotations

from typing import Any

from polar_mcp.client import ApiResponse
from polar_mcp.config import MAX_LOOKBACK_DAYS
from polar_mcp.errors import ValidationError
from polar_mcp.service import PolarService
from polar_mcp.tools import (
    activities_range,
    activity_by_date,
    cardio_load_by_date,
    cardio_load_recent,
)


class FakeClient:
    def __init__(self, responses: list[ApiResponse] | None = None) -> None:
        self.responses = responses or []
        self.calls: list[tuple[str, dict[str, Any] | None, bool]] = []

    def request_json(
        self,
        path: str,
        params: dict[str, Any] | None = None,
        treat_404_as_no_data: bool = False,
    ) -> ApiResponse:
        self.calls.append((path, params, treat_404_as_no_data))
        if self.responses:
            return self.responses.pop(0)
        return ApiResponse(payload=[], rate_limit=None, status_code=200)


def test_activities_range_ok() -> None:
    client = FakeClient(
        responses=[ApiResponse(payload=[{"date": "2026-03-06"}], rate_limit=None, status_code=200)]
    )
    service = PolarService(client)
    result = activities_range(service, from_date="2026-03-05", to_date="2026-03-06")
    assert result["status"] == "ok"
    assert isinstance(result["data"], list)
    assert client.calls[0][0] == "/users/activities/"


def test_activities_range_no_data_empty_list() -> None:
    client = FakeClient(responses=[ApiResponse(payload=[], rate_limit=None, status_code=200)])
    service = PolarService(client)
    result = activities_range(service, from_date="2026-03-05", to_date="2026-03-06")
    assert result["status"] == "no_data"


def test_activity_by_date_include_samples_sets_params() -> None:
    client = FakeClient(
        responses=[
            ApiResponse(payload={"date": "2026-03-06"}, rate_limit=None, status_code=200),
        ],
    )
    service = PolarService(client)
    result = activity_by_date(service, date="2026-03-06", include_samples=True)
    assert result["status"] == "ok"
    _, params, _ = client.calls[0]
    assert params is not None
    assert params["steps"] == "true"
    assert params["activity_zones"] == "true"
    assert params["inactivity_stamps"] == "true"


def test_activity_by_date_no_data_on_404_style_payload() -> None:
    client = FakeClient(responses=[ApiResponse(payload=None, rate_limit=None, status_code=404)])
    service = PolarService(client)
    result = activity_by_date(service, date="2026-03-06")
    assert result["status"] == "no_data"


def test_cardio_load_recent_ok() -> None:
    payload = [{"date": "2026-03-06", "cardio_load": 100.0}]
    client = FakeClient(responses=[ApiResponse(payload=payload, rate_limit=None, status_code=200)])
    service = PolarService(client)
    result = cardio_load_recent(service, days=30)
    assert result["status"] == "ok"
    assert result["data"] == payload
    assert client.calls[0][0] == "/users/cardio-load/period/days/30"


def test_cardio_load_by_date_no_data_on_empty_list() -> None:
    client = FakeClient(responses=[ApiResponse(payload=[], rate_limit=None, status_code=200)])
    service = PolarService(client)
    result = cardio_load_by_date(service, date="2026-03-06")
    assert result["status"] == "no_data"


def test_validation_error_returns_error_envelope() -> None:
    client = FakeClient()
    service = PolarService(client)
    result = activities_range(service, from_date="2026-03-07", to_date="2026-03-06")
    assert result["status"] == "error"
    assert result["error"]["type"] == ValidationError.__name__


def test_lookback_validation_blocks_old_date() -> None:
    old_year = 2026 - 2
    old_date = f"{old_year}-01-01"
    client = FakeClient()
    service = PolarService(client)
    result = activity_by_date(service, date=old_date)
    assert result["status"] == "error"
    assert f"{MAX_LOOKBACK_DAYS}" in result["error"]["message"]
