from __future__ import annotations

import json

from polar_accesslink.cli import main
from polar_accesslink.client import ApiResponse
from polar_accesslink.service import PolarService


class FakeClient:
    def __init__(
        self,
        responses: list[ApiResponse] | None = None,
        text_responses: list[ApiResponse] | None = None,
    ) -> None:
        self.responses = responses or []
        self.text_responses = text_responses or []
        self.closed = False

    def request_json(
        self,
        path: str,
        params: dict[str, str] | None = None,
        treat_404_as_no_data: bool = False,
    ) -> ApiResponse:
        if self.responses:
            return self.responses.pop(0)
        return ApiResponse(payload=[], rate_limit=None, status_code=200)

    def request_text(
        self,
        path: str,
        params: dict[str, str] | None = None,
        treat_404_as_no_data: bool = False,
    ) -> ApiResponse:
        if self.text_responses:
            return self.text_responses.pop(0)
        return ApiResponse(payload=None, rate_limit=None, status_code=404)

    def close(self) -> None:
        self.closed = True


def test_cli_prints_json_envelope(
    monkeypatch,
    capsys,
) -> None:
    client = FakeClient(
        responses=[ApiResponse(payload=[{"date": "2026-03-06"}], rate_limit=None, status_code=200)]
    )
    service = PolarService(client)
    monkeypatch.setattr("polar_accesslink.cli.build_service", lambda: service)

    exit_code = main(["activities-range", "--from-date", "2026-03-05", "--to-date", "2026-03-06"])

    captured = capsys.readouterr()
    assert exit_code == 0
    payload = json.loads(captured.out)
    assert payload["status"] == "ok"
    assert payload["data"][0]["date"] == "2026-03-06"
    assert client.closed is True


def test_cli_writes_jsonl_to_file(
    monkeypatch,
    tmp_path,
) -> None:
    client = FakeClient(
        responses=[
            ApiResponse(payload=[{"id": "a"}, {"id": "b"}], rate_limit=None, status_code=200)
        ]
    )
    service = PolarService(client)
    monkeypatch.setattr("polar_accesslink.cli.build_service", lambda: service)
    destination = tmp_path / "exercises.jsonl"

    exit_code = main(["exercises-recent", "--output", "jsonl", "--out", str(destination)])

    assert exit_code == 0
    assert destination.read_text(encoding="utf-8").splitlines() == ['{"id":"a"}', '{"id":"b"}']


def test_cli_fail_on_no_data_returns_non_zero(
    monkeypatch,
    capsys,
) -> None:
    client = FakeClient(responses=[ApiResponse(payload=[], rate_limit=None, status_code=200)])
    service = PolarService(client)
    monkeypatch.setattr("polar_accesslink.cli.build_service", lambda: service)

    exit_code = main(
        [
            "activities-range",
            "--from-date",
            "2026-03-05",
            "--to-date",
            "2026-03-06",
            "--fail-on-no-data",
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 3
    payload = json.loads(captured.out)
    assert payload["status"] == "no_data"
