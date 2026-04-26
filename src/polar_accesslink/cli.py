from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any, cast

from .bootstrap import build_service, close_service
from .service import PolarService
from .tools import (
    activities_range,
    activity_by_date,
    cardio_load_by_date,
    cardio_load_recent,
    exercise_by_id,
    exercises_recent,
)

Handler = Callable[[PolarService, argparse.Namespace], dict[str, Any]]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="polar-cli",
        description="Export Polar AccessLink data through a shared core used by both CLI and MCP.",
    )
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--output", choices=("json", "jsonl"), default="json")
    common.add_argument("--out", type=Path, help="Write output to a file instead of stdout.")
    common.add_argument("--pretty", action="store_true", help="Pretty-print JSON output.")
    common.add_argument(
        "--fail-on-no-data",
        action="store_true",
        help="Exit non-zero when the command returns status=no_data.",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    activities_parser = subparsers.add_parser(
        "activities-range",
        parents=[common],
        help="Fetch day-level activities for a date range.",
    )
    activities_parser.add_argument("--from-date", required=True)
    activities_parser.add_argument("--to-date", required=True)
    activities_parser.add_argument("--include-samples", action="store_true")
    activities_parser.set_defaults(handler=_handle_activities_range)

    activity_parser = subparsers.add_parser(
        "activity-by-date",
        parents=[common],
        help="Fetch a single activity summary by date.",
    )
    activity_parser.add_argument("--date", required=True)
    activity_parser.add_argument("--include-samples", action="store_true")
    activity_parser.set_defaults(handler=_handle_activity_by_date)

    cardio_recent_parser = subparsers.add_parser(
        "cardio-load-recent",
        parents=[common],
        help="Fetch recent cardio load history.",
    )
    cardio_recent_parser.add_argument("--days", type=int, default=30)
    cardio_recent_parser.set_defaults(handler=_handle_cardio_load_recent)

    cardio_date_parser = subparsers.add_parser(
        "cardio-load-by-date",
        parents=[common],
        help="Fetch cardio load for a specific date.",
    )
    cardio_date_parser.add_argument("--date", required=True)
    cardio_date_parser.set_defaults(handler=_handle_cardio_load_by_date)

    exercises_recent_parser = subparsers.add_parser(
        "exercises-recent",
        parents=[common],
        help="Fetch recent exercises.",
    )
    exercises_recent_parser.add_argument("--include-samples", action="store_true")
    exercises_recent_parser.add_argument("--include-zones", action="store_true")
    exercises_recent_parser.add_argument("--include-route", action="store_true")
    exercises_recent_parser.add_argument("--include-tcx-metadata", action="store_true")
    exercises_recent_parser.set_defaults(handler=_handle_exercises_recent)

    exercise_id_parser = subparsers.add_parser(
        "exercise-by-id",
        parents=[common],
        help="Fetch one exercise by its Polar identifier.",
    )
    exercise_id_parser.add_argument("--exercise-id", required=True)
    exercise_id_parser.add_argument("--include-samples", action="store_true")
    exercise_id_parser.add_argument("--include-zones", action="store_true")
    exercise_id_parser.add_argument("--include-route", action="store_true")
    exercise_id_parser.add_argument("--include-tcx-metadata", action="store_true")
    exercise_id_parser.set_defaults(handler=_handle_exercise_by_id)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        service = build_service()
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 1

    try:
        handler = cast(Handler, args.handler)
        result = handler(service, args)
        rendered = _render_output(result, output_format=args.output, pretty=args.pretty)
        _write_output(rendered, destination=args.out)
        return _exit_code(result, fail_on_no_data=args.fail_on_no_data)
    except OSError as exc:
        print(f"Failed to write output: {exc}", file=sys.stderr)
        return 1
    finally:
        close_service(service)


def _handle_activities_range(service: PolarService, args: argparse.Namespace) -> dict[str, Any]:
    return activities_range(
        service,
        from_date=args.from_date,
        to_date=args.to_date,
        include_samples=args.include_samples,
    )


def _handle_activity_by_date(service: PolarService, args: argparse.Namespace) -> dict[str, Any]:
    return activity_by_date(service, date=args.date, include_samples=args.include_samples)


def _handle_cardio_load_recent(service: PolarService, args: argparse.Namespace) -> dict[str, Any]:
    return cardio_load_recent(service, days=args.days)


def _handle_cardio_load_by_date(service: PolarService, args: argparse.Namespace) -> dict[str, Any]:
    return cardio_load_by_date(service, date=args.date)


def _handle_exercises_recent(service: PolarService, args: argparse.Namespace) -> dict[str, Any]:
    return exercises_recent(
        service,
        include_samples=args.include_samples,
        include_zones=args.include_zones,
        include_route=args.include_route,
        include_tcx_metadata=args.include_tcx_metadata,
    )


def _handle_exercise_by_id(service: PolarService, args: argparse.Namespace) -> dict[str, Any]:
    return exercise_by_id(
        service,
        exercise_id=args.exercise_id,
        include_samples=args.include_samples,
        include_zones=args.include_zones,
        include_route=args.include_route,
        include_tcx_metadata=args.include_tcx_metadata,
    )


def _render_output(result: dict[str, Any], *, output_format: str, pretty: bool) -> str:
    if output_format == "json":
        return _to_json(result, pretty=pretty)

    if output_format == "jsonl":
        return _to_jsonl(result)

    raise ValueError(f"Unsupported output format: {output_format}")


def _to_json(result: dict[str, Any], *, pretty: bool) -> str:
    indent = 2 if pretty else None
    separators = None if pretty else (",", ":")
    return json.dumps(result, indent=indent, separators=separators) + "\n"


def _to_jsonl(result: dict[str, Any]) -> str:
    if result["status"] == "ok":
        data = result.get("data")
        if isinstance(data, list):
            return "".join(json.dumps(item, separators=(",", ":")) + "\n" for item in data)
        return json.dumps(data, separators=(",", ":")) + "\n"

    if result["status"] == "no_data":
        return ""

    return json.dumps(result, separators=(",", ":")) + "\n"


def _write_output(rendered: str, *, destination: Path | None) -> None:
    if destination is None:
        sys.stdout.write(rendered)
        return
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(rendered, encoding="utf-8")


def _exit_code(result: dict[str, Any], *, fail_on_no_data: bool) -> int:
    status = result.get("status")
    if status == "error":
        return 1
    if status == "no_data" and fail_on_no_data:
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
