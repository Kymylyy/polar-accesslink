from __future__ import annotations

import os

from .client import PolarApiClient
from .config import BASE_URL
from .errors import ValidationError
from .service import PolarService

_SERVICE: PolarService | None = None


def build_service() -> PolarService:
    access_token = os.getenv("POLAR_ACCESS_TOKEN", "").strip()
    if not access_token:
        raise ValidationError(
            "POLAR_ACCESS_TOKEN is missing.",
            "Set POLAR_ACCESS_TOKEN in the environment before startup.",
        )
    client = PolarApiClient(access_token=access_token, base_url=BASE_URL)
    return PolarService(client)


def get_service() -> PolarService:
    global _SERVICE
    if _SERVICE is None:
        _SERVICE = build_service()
    return _SERVICE


def close_service(service: PolarService) -> None:
    close = getattr(service.client, "close", None)
    if callable(close):
        close()


def reset_service() -> None:
    global _SERVICE
    if _SERVICE is None:
        return
    close_service(_SERVICE)
    _SERVICE = None
