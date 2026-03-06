from __future__ import annotations

import httpx
import pytest

from polar_mcp.client import PolarApiClient
from polar_mcp.errors import (
    NotFoundError,
    UpstreamAuthError,
    UpstreamRateLimitError,
    UpstreamServerError,
    UpstreamValidationError,
)


def _client(handler: httpx.MockTransport) -> PolarApiClient:
    return PolarApiClient(
        access_token="token",
        base_url="https://example.test",
        transport=handler,
        sleep_fn=lambda _: None,
    )


def test_request_json_retries_429_then_succeeds() -> None:
    attempts = {"count": 0}

    def handler(_: httpx.Request) -> httpx.Response:
        attempts["count"] += 1
        if attempts["count"] < 3:
            return httpx.Response(429, text="rate limit")
        return httpx.Response(200, json={"ok": True})

    client = _client(httpx.MockTransport(handler))

    response = client.request_json("/resource")
    assert response.payload == {"ok": True}
    assert attempts["count"] == 3


def test_request_json_retries_timeout_then_succeeds() -> None:
    attempts = {"count": 0}

    def handler(_: httpx.Request) -> httpx.Response:
        attempts["count"] += 1
        if attempts["count"] < 2:
            raise httpx.ReadTimeout("timeout")
        return httpx.Response(200, json={"ok": True})

    client = _client(httpx.MockTransport(handler))
    response = client.request_json("/resource")
    assert response.payload == {"ok": True}
    assert attempts["count"] == 2


def test_request_json_401_raises_auth_error() -> None:
    client = _client(httpx.MockTransport(lambda _: httpx.Response(401, text="unauthorized")))
    with pytest.raises(UpstreamAuthError):
        client.request_json("/resource")


def test_request_json_400_raises_validation_error() -> None:
    client = _client(httpx.MockTransport(lambda _: httpx.Response(400, text="bad date range")))
    with pytest.raises(UpstreamValidationError):
        client.request_json("/resource")


def test_request_json_404_not_found_raises() -> None:
    client = _client(httpx.MockTransport(lambda _: httpx.Response(404, text="not found")))
    with pytest.raises(NotFoundError):
        client.request_json("/resource")


def test_request_json_404_no_data_allowed() -> None:
    client = _client(httpx.MockTransport(lambda _: httpx.Response(404, text="not found")))
    response = client.request_json("/resource", treat_404_as_no_data=True)
    assert response.payload is None


def test_request_json_429_after_retries_raises_rate_limit_error() -> None:
    client = _client(httpx.MockTransport(lambda _: httpx.Response(429, text="rate limit")))
    with pytest.raises(UpstreamRateLimitError):
        client.request_json("/resource")


def test_request_json_5xx_after_retries_raises_server_error() -> None:
    client = _client(httpx.MockTransport(lambda _: httpx.Response(503, text="server down")))
    with pytest.raises(UpstreamServerError):
        client.request_json("/resource")


def test_request_json_204_returns_no_payload() -> None:
    client = _client(httpx.MockTransport(lambda _: httpx.Response(204, text="")))
    response = client.request_json("/resource")
    assert response.payload is None


def test_request_json_captures_rate_limit_headers() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json=[],
            headers={
                "ratelimit-usage": "3, 10",
                "ratelimit-limit": "500, 5000",
                "ratelimit-reset": "620, 86000",
            },
        )

    client = _client(httpx.MockTransport(handler))
    response = client.request_json("/resource")
    assert response.rate_limit is not None
    assert response.rate_limit["short"]["usage"] == 3
    assert response.rate_limit["short"]["limit"] == 500
    assert response.rate_limit["short"]["reset_seconds"] == 620
