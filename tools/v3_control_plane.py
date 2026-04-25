#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dark_factory_v3.control_plane import ControlPlane, ControlPlaneError  # noqa: E402
from dark_factory_v3.projection import ProjectionState  # noqa: E402


def projection_to_dict(projection: ProjectionState) -> dict[str, Any]:
    return {
        "runs": {key: asdict(value) for key, value in sorted(projection.runs.items())},
        "attempts": {key: asdict(value) for key, value in sorted(projection.attempts.items())},
        "routeDecisions": {key: {"decision": asdict(value.decision), "eventId": value.eventId} for key, value in sorted(projection.route_decisions.items())},
        "unknownEvents": [event.to_dict() for event in projection.unknown_events],
    }


def emit(payload: dict[str, Any]) -> int:
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2))
    return 0


def load_plane(args: argparse.Namespace) -> ControlPlane:
    return ControlPlane.from_jsonl_path(ROOT, args.journal)


def cmd_request_run(args: argparse.Namespace) -> int:
    plane = load_plane(args)
    event = plane.request_run(
        run_id=args.run_id,
        correlation_id=args.correlation_id,
        trace_id=args.trace_id,
        event_id=args.event_id,
    )
    return emit({"ok": True, "event": event.to_dict()})


def cmd_transition_run(args: argparse.Namespace) -> int:
    plane = load_plane(args)
    event = plane.transition_run(
        run_id=args.run_id,
        old_state=args.old_state,
        new_state=args.new_state,
        transition_trigger=args.transition_trigger,
        correlation_id=args.correlation_id,
        trace_id=args.trace_id,
        event_id=args.event_id,
    )
    return emit({"ok": True, "event": event.to_dict()})


def cmd_projection(args: argparse.Namespace) -> int:
    plane = load_plane(args)
    return emit({"ok": True, "projection": projection_to_dict(plane.projection())})


def add_common_write_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--journal", required=True, help="Path to the append-only JSONL journal")
    parser.add_argument("--correlation-id", required=True)
    parser.add_argument("--trace-id", required=True)
    parser.add_argument("--event-id")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Paperclip × Dark Factory V3 minimal control-plane CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    request_run = subparsers.add_parser("request-run", help="Append a requested -> validating run lifecycle event")
    add_common_write_args(request_run)
    request_run.add_argument("--run-id", required=True)
    request_run.set_defaults(func=cmd_request_run)

    transition_run = subparsers.add_parser("transition-run", help="Append a run lifecycle transition event")
    add_common_write_args(transition_run)
    transition_run.add_argument("--run-id", required=True)
    transition_run.add_argument("--old-state", required=True)
    transition_run.add_argument("--new-state", required=True)
    transition_run.add_argument("--transition-trigger", required=True)
    transition_run.set_defaults(func=cmd_transition_run)

    projection = subparsers.add_parser("projection", help="Replay a JSONL journal and print projection state")
    projection.add_argument("--journal", required=True, help="Path to the append-only JSONL journal")
    projection.set_defaults(func=cmd_projection)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except ControlPlaneError as exc:
        print(str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
