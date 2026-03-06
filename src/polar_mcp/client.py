from __future__ import annotations

import random
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any

import httpx

from .config import HTTP_TIMEOUT_SECONDS, MAX_RETRIES, RETRY_DELAYS
from .errors import (
    NotFoundError,
    UpstreamAuthError,
    UpstreamRateLimitError,
    UpstreamServerError,
    UpstreamValidationError,
)

RateLimitWindow = dict[str, int | None]
RateLimitInfo = dict[str, RateLimitWindow]


@dataclass
class ApiResponse:
    payload: Any | None
    rate_limit: RateLimitInfo | None
    status_code: int


class PolarApiClient:
    def __init__(
        self,
        access_token: str,
        base_url: str,
        transport: httpx.BaseTransport | None = None,
        sleep_fn: Callable[[float], None] = time.sleep,
    ) -> None:
        self._sleep_fn = sleep_fn
        self._client = httpx.Client(
            base_url=base_url,
            headers={
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/json",
            },
            timeout=httpx.Timeout(HTTP_TIMEOUT_SECONDS),
            transport=transport,
        )

    def close(self) -> None:
        self._client.close()

    def request_json(
        self,
        path: str,
        params: Mapping[str, Any] | None = None,
        treat_404_as_no_data: bool = False,
    ) -> ApiResponse:
        for attempt in range(MAX_RETRIES + 1):
            try:
                response = self._client.get(path, params=params)
            except (httpx.TimeoutException, httpx.NetworkError) as exc:
                if attempt < MAX_RETRIES:
                    self._backoff(attempt)
                    continue
                raise UpstreamServerError(
                    "Polar API request failed after retries.",
                    "Retry in a moment. If this repeats, check network availability.",
                ) from exc

            rate_limit = _parse_rate_limit(response.headers)
            status = response.status_code
            if status in {401, 403}:
                raise UpstreamAuthError(
                    "Polar API authentication failed or consent is missing.",
                    "Verify POLAR_ACCESS_TOKEN and required user consents in Polar.",
                )

            if status == 404:
                if treat_404_as_no_data:
                    return ApiResponse(None, rate_limit, status)
                raise NotFoundError(
                    "Requested Polar resource was not found.",
                    "Check identifiers and endpoint path.",
                )

            if status == 429:
                if attempt < MAX_RETRIES:
                    self._backoff(attempt)
                    continue
                reset_hint = _format_rate_limit_hint(rate_limit)
                raise UpstreamRateLimitError(
                    "Polar API rate limit reached.",
                    f"Retry later.{reset_hint}",
                )

            if status >= 500:
                if attempt < MAX_RETRIES:
                    self._backoff(attempt)
                    continue
                raise UpstreamServerError(
                    f"Polar API returned HTTP {status} after retries.",
                    "Retry later. If this persists, upstream may be degraded.",
                )

            if status == 204:
                return ApiResponse(None, rate_limit, status)

            if status == 400:
                detail = response.text.strip() or "Bad request."
                raise UpstreamValidationError(
                    f"Polar API rejected the request: {detail}",
                    "Validate date ranges and parameters.",
                )

            if status >= 400:
                raise UpstreamServerError(
                    f"Unexpected Polar API error: HTTP {status}.",
                    "Retry with a smaller request or validate the input.",
                )

            try:
                payload = response.json()
            except ValueError as exc:
                raise UpstreamServerError(
                    "Polar API returned non-JSON payload.",
                    "Retry the request. If this repeats, inspect upstream behavior.",
                ) from exc
            return ApiResponse(payload, rate_limit, status)

        raise UpstreamServerError("Polar API request failed after retries.", "Retry later.")

    def _backoff(self, attempt: int) -> None:
        delay = RETRY_DELAYS[min(attempt, len(RETRY_DELAYS) - 1)] + random.uniform(0.0, 0.2)
        self._sleep_fn(delay)


def _parse_rate_limit(headers: httpx.Headers) -> RateLimitInfo | None:
    usage = _parse_two_ints(headers.get("ratelimit-usage", ""))
    limit = _parse_two_ints(headers.get("ratelimit-limit", ""))
    reset = _parse_two_ints(headers.get("ratelimit-reset", ""))
    if usage is None and limit is None and reset is None:
        return None

    return {
        "short": {
            "usage": usage[0] if usage else None,
            "limit": limit[0] if limit else None,
            "reset_seconds": reset[0] if reset else None,
        },
        "long": {
            "usage": usage[1] if usage else None,
            "limit": limit[1] if limit else None,
            "reset_seconds": reset[1] if reset else None,
        },
    }


def _parse_two_ints(raw: str) -> tuple[int, int] | None:
    values = [part.strip() for part in raw.split(",") if part.strip()]
    if len(values) != 2:
        return None
    try:
        return int(values[0]), int(values[1])
    except ValueError:
        return None


def _format_rate_limit_hint(rate_limit: RateLimitInfo | None) -> str:
    if not rate_limit:
        return ""
    short = rate_limit.get("short", {})
    long = rate_limit.get("long", {})
    short_reset = short.get("reset_seconds")
    long_reset = long.get("reset_seconds")
    if short_reset is None and long_reset is None:
        return ""
    return f" Short reset in {short_reset}s, long reset in {long_reset}s."
