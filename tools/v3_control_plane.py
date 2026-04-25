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


def _stable_projection_value(value: Any) -> Any:
    if isinstance(value, tuple):
        return [_stable_projection_value(item) for item in value]
    if isinstance(value, list):
        return [_stable_projection_value(item) for item in value]
    if isinstance(value, dict):
        return {key: _stable_projection_value(value[key]) for key in sorted(value)}
    return value


def projection_to_dict(projection: ProjectionState) -> dict[str, Any]:
    return {
        "runs": {
            key: _stable_projection_value(asdict(value))
            for key, value in sorted(projection.runs.items())
        },
        "attempts": {
            key: _stable_projection_value(asdict(value))
            for key, value in sorted(projection.attempts.items())
        },
        "routeDecisions": {
            key: {
                "decision": _stable_projection_value(asdict(value.decision)),
                "eventId": value.eventId,
            }
            for key, value in sorted(projection.route_decisions.items())
        },
        "unknownEvents": [event.to_dict() for event in sorted(projection.unknown_events, key=lambda event: event.eventId)],
    }


def emit(payload: dict[str, Any], *, stream: Any = None) -> int:
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2), file=stream or sys.stdout)
    return 0


def emit_event(event: Any) -> int:
    return emit({"ok": True, "event": event.to_dict()})


def emit_control_plane_error(exc: ControlPlaneError) -> int:
    emit({"ok": False, "error": {"type": "ControlPlaneError", "message": str(exc)}}, stream=sys.stderr)
    return 2


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
    return emit_event(event)


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
    return emit_event(event)


def cmd_transition_attempt(args: argparse.Namespace) -> int:
    plane = load_plane(args)
    event = plane.transition_attempt(
        run_id=args.run_id,
        attempt_id=args.attempt_id,
        old_state=args.old_state,
        new_state=args.new_state,
        transition_trigger=args.transition_trigger,
        correlation_id=args.correlation_id,
        trace_id=args.trace_id,
        event_id=args.event_id,
    )
    return emit_event(event)


def cmd_record_route_decision(args: argparse.Namespace) -> int:
    plane = load_plane(args)
    event = plane.record_route_decision(
        run_id=args.run_id,
        attempt_id=args.attempt_id,
        route_decision_id=args.route_decision_id,
        workload_class=args.workload_class,
        route_policy_ref=args.route_policy_ref,
        selected_executor_class=args.selected_executor_class,
        fallback_depth=args.fallback_depth,
        decision_reason=args.decision_reason,
        route_decision_state=args.route_decision_state,
        recorded_at=args.recorded_at,
        correlation_id=args.correlation_id,
        trace_id=args.trace_id,
        event_id=args.event_id,
    )
    return emit_event(event)


def cmd_park_manual(args: argparse.Namespace) -> int:
    plane = load_plane(args)
    event = plane.park_manual(
        run_id=args.run_id,
        attempt_id=args.attempt_id,
        park_id=args.park_id,
        manual_gate_type=args.manual_gate_type,
        execution_suspension_state=args.execution_suspension_state,
        parked_at=args.parked_at,
        rehydration_token_id=args.rehydration_token_id,
        correlation_id=args.correlation_id,
        trace_id=args.trace_id,
        event_id=args.event_id,
    )
    return emit_event(event)


def cmd_rehydrate_manual(args: argparse.Namespace) -> int:
    plane = load_plane(args)
    event = plane.rehydrate_manual(
        run_id=args.run_id,
        previous_attempt_id=args.previous_attempt_id,
        new_attempt_id=args.new_attempt_id,
        rehydration_token_id=args.rehydration_token_id,
        rehydrated_at=args.rehydrated_at,
        correlation_id=args.correlation_id,
        trace_id=args.trace_id,
        event_id=args.event_id,
    )
    return emit_event(event)


def cmd_projection(args: argparse.Namespace) -> int:
    plane = load_plane(args)
    return emit({"ok": True, "projection": projection_to_dict(plane.projection())})


def add_common_write_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--journal", required=True, help="Path to the append-only JSONL journal")
    parser.add_argument("--correlation-id", required=True)
    parser.add_argument("--trace-id", required=True)
    parser.add_argument("--event-id")


def add_transition_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--old-state", required=True)
    parser.add_argument("--new-state", required=True)
    parser.add_argument("--transition-trigger", required=True)


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
    add_transition_args(transition_run)
    transition_run.set_defaults(func=cmd_transition_run)

    transition_attempt = subparsers.add_parser("transition-attempt", help="Append an attempt lifecycle transition event")
    add_common_write_args(transition_attempt)
    transition_attempt.add_argument("--run-id", required=True)
    transition_attempt.add_argument("--attempt-id", required=True)
    add_transition_args(transition_attempt)
    transition_attempt.set_defaults(func=cmd_transition_attempt)

    record_route = subparsers.add_parser("record-route-decision", help="Append a route.decision.recorded event")
    add_common_write_args(record_route)
    record_route.add_argument("--run-id", required=True)
    record_route.add_argument("--attempt-id", required=True)
    record_route.add_argument("--route-decision-id", required=True)
    record_route.add_argument("--workload-class", required=True)
    record_route.add_argument("--route-policy-ref", required=True)
    record_route.add_argument("--selected-executor-class", required=True)
    record_route.add_argument("--fallback-depth", required=True, type=int)
    record_route.add_argument("--decision-reason", required=True)
    record_route.add_argument("--route-decision-state", default="selected_primary")
    record_route.add_argument("--recorded-at")
    record_route.set_defaults(func=cmd_record_route_decision)

    park_manual = subparsers.add_parser("park-manual", help="Append a manual_gate.parked event")
    add_common_write_args(park_manual)
    park_manual.add_argument("--run-id", required=True)
    park_manual.add_argument("--attempt-id", required=True)
    park_manual.add_argument("--park-id", required=True)
    park_manual.add_argument("--manual-gate-type", required=True)
    park_manual.add_argument("--rehydration-token-id", required=True)
    park_manual.add_argument(
        "--execution-suspension-state",
        default="resources_released_truth_obligation_retained",
    )
    park_manual.add_argument("--parked-at")
    park_manual.set_defaults(func=cmd_park_manual)

    rehydrate_manual = subparsers.add_parser("rehydrate-manual", help="Append a manual_gate.rehydrated event")
    add_common_write_args(rehydrate_manual)
    rehydrate_manual.add_argument("--run-id", required=True)
    rehydrate_manual.add_argument("--previous-attempt-id", required=True)
    rehydrate_manual.add_argument("--new-attempt-id", required=True)
    rehydrate_manual.add_argument("--rehydration-token-id", required=True)
    rehydrate_manual.add_argument("--rehydrated-at")
    rehydrate_manual.set_defaults(func=cmd_rehydrate_manual)

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
        return emit_control_plane_error(exc)


if __name__ == "__main__":
    raise SystemExit(main())
