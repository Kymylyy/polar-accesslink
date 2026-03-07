from __future__ import annotations

from datetime import date

from .config import (
    MAX_ACTIVITY_RANGE_DAYS,
    MAX_CARDIO_LOAD_DAYS,
    MAX_LOOKBACK_DAYS,
)
from .errors import ValidationError


def validate_activity_range(from_date: str, to_date: str) -> tuple[date, date]:
    start = parse_iso_date(from_date, field_name="from_date")
    end = parse_iso_date(to_date, field_name="to_date")
    if start > end:
        raise ValidationError("from_date must be before or equal to to_date.")
    if (end - start).days + 1 > MAX_ACTIVITY_RANGE_DAYS:
        raise ValidationError(
            f"Activity range cannot exceed {MAX_ACTIVITY_RANGE_DAYS} days.",
        )
    validate_lookback(start, field_name="from_date")
    return start, end


def validate_cardio_load_days(days: int) -> None:
    if not isinstance(days, int):
        raise ValidationError("days must be an integer.")
    if days < 1 or days > MAX_CARDIO_LOAD_DAYS:
        raise ValidationError(f"days must be between 1 and {MAX_CARDIO_LOAD_DAYS}.")


def parse_iso_date(raw: str, field_name: str) -> date:
    try:
        parsed = date.fromisoformat(raw)
    except ValueError as exc:
        raise ValidationError(f"{field_name} must use YYYY-MM-DD format.") from exc
    if parsed.isoformat() != raw:
        raise ValidationError(f"{field_name} must use YYYY-MM-DD format.")
    return parsed


def validate_lookback(value: date, field_name: str) -> None:
    today = date.today()
    age = (today - value).days
    if age > MAX_LOOKBACK_DAYS:
        raise ValidationError(f"{field_name} cannot be older than {MAX_LOOKBACK_DAYS} days.")


def validate_non_empty_string(value: str, field_name: str) -> str:
    if not isinstance(value, str):
        raise ValidationError(f"{field_name} must be a string.")
    trimmed = value.strip()
    if not trimmed:
        raise ValidationError(f"{field_name} cannot be empty.")
    return trimmed
