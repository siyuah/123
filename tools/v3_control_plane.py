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
from dark_factory_v3.projection import ProjectionReplayError, ProjectionState, RunLifecycleReducer  # noqa: E402
from dark_factory_v3.protocol import EventEnvelope, PROTOCOL_RELEASE_TAG, load_event_contracts  # noqa: E402

SUPPORTED_COMMANDS = [
    "request-run",
    "transition-run",
    "transition-attempt",
    "record-route-decision",
    "park-manual",
    "rehydrate-manual",
    "projection",
    "verify-journal",
    "version",
]
DEFAULT_PRODUCER = "dark-factory-control-plane"


VERIFY_JOURNAL_CHECK_MESSAGES = {
    "jsonl.valid_json": "journal contains only non-empty JSON object lines",
    "journal.not_empty": "journal contains at least one event",
    "journal.sequence_contiguous": "sequenceNo starts at 1 and increments by one per journal line",
    "journal.event_id_unique": "eventId values are unique across the journal",
    "envelope.required_fields": "required EventEnvelope fields are present",
    "envelope.protocol_release_tag": f"protocolReleaseTag is {PROTOCOL_RELEASE_TAG}",
    "envelope.event_version_compatible": "eventVersion matches the known event contract",
    "projection.replay": "RunLifecycleReducer can replay the full journal",
    "projection.event_ids_unique": "projected run and attempt eventIds are unique",
    "projection.event_ids_resolvable": "projected run and attempt eventIds resolve to journal envelopes",
}
VERIFY_JOURNAL_CHECKS = list(VERIFY_JOURNAL_CHECK_MESSAGES)
REQUIRED_ENVELOPE_FIELDS = ("correlationId", "traceId", "eventName", "emittedAt", "eventId", "eventVersion")


class JournalVerificationError(ValueError):
    def __init__(
        self,
        check: str,
        message: str,
        *,
        line_number: int | None = None,
        line: int | None = None,
        event_id: str | None = None,
        entity_id: str | None = None,
        collection: str | None = None,
    ) -> None:
        super().__init__(message)
        self.check = check
        self.message = message
        self.line_number = line_number if line_number is not None else line
        self.event_id = event_id
        self.entity_id = entity_id
        self.collection = collection

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "type": "JournalVerificationError",
            "checkId": self.check,
            "message": self.message,
        }
        if self.line_number is not None:
            payload["lineNumber"] = self.line_number
        if self.event_id is not None:
            payload["eventId"] = self.event_id
        if self.entity_id is not None:
            payload["entityId"] = self.entity_id
        if self.collection is not None:
            payload["collection"] = self.collection
        return payload


def emit_journal_verification_error(exc: JournalVerificationError) -> int:
    emit({"ok": False, "error": exc.to_dict()}, stream=sys.stderr)
    return 2


def _read_verified_journal_events(journal_path: Path) -> list[tuple[int, EventEnvelope]]:
    contracts = load_event_contracts(ROOT)
    events: list[tuple[int, EventEnvelope]] = []
    seen_event_ids: dict[str, int] = {}
    if not journal_path.exists():
        raise JournalVerificationError("jsonl.valid_json", f"journal does not exist: {journal_path}")
    for line_number, line in enumerate(journal_path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            raw = json.loads(line)
        except json.JSONDecodeError as exc:
            raise JournalVerificationError("jsonl.valid_json", f"line {line_number} is not valid JSON: {exc.msg}", line=line_number) from exc
        if not isinstance(raw, dict):
            raise JournalVerificationError("jsonl.valid_json", f"line {line_number} must be a JSON object", line=line_number)
        event_id = raw.get("eventId") if isinstance(raw.get("eventId"), str) else None
        expected_sequence = len(events) + 1
        if raw.get("sequenceNo") != expected_sequence:
            raise JournalVerificationError(
                "journal.sequence_contiguous",
                f"expected sequenceNo {expected_sequence}, got {raw.get('sequenceNo')!r}",
                line=line_number,
                event_id=event_id,
            )
        if event_id in seen_event_ids:
            raise JournalVerificationError(
                "journal.event_id_unique",
                f"duplicate eventId {event_id!r}; first seen on line {seen_event_ids[event_id]}",
                line=line_number,
                event_id=event_id,
            )
        if event_id is not None:
            seen_event_ids[event_id] = line_number
        for field_name in REQUIRED_ENVELOPE_FIELDS:
            if not raw.get(field_name):
                raise JournalVerificationError(
                    "envelope.required_fields",
                    f"missing required envelope field {field_name!r}",
                    line=line_number,
                    event_id=event_id,
                )
        if raw.get("protocolReleaseTag") != PROTOCOL_RELEASE_TAG:
            raise JournalVerificationError(
                "envelope.protocol_release_tag",
                f"protocolReleaseTag must be {PROTOCOL_RELEASE_TAG!r}, got {raw.get('protocolReleaseTag')!r}",
                line=line_number,
                event_id=event_id,
            )
        event_name = raw.get("eventName")
        legacy_runtime_versions = {"run.lifecycle.transitioned": "v1", "attempt.lifecycle.transitioned": "v1"}
        if event_name in contracts:
            expected_version = str(contracts[event_name]["version"])
        elif event_name in legacy_runtime_versions:
            expected_version = legacy_runtime_versions[event_name]
        else:
            raise JournalVerificationError(
                "envelope.event_version_compatible",
                f"unknown eventName {event_name!r}",
                line=line_number,
                event_id=event_id,
            )
        if str(raw.get("eventVersion")) != expected_version:
            raise JournalVerificationError(
                "envelope.event_version_compatible",
                f"eventVersion for {event_name!r} must be {expected_version!r}, got {raw.get('eventVersion')!r}",
                line=line_number,
                event_id=event_id,
            )
        try:
            event = EventEnvelope.from_dict(raw, isReplay=True)
        except (TypeError, ValueError) as exc:
            raise JournalVerificationError("envelope.required_fields", str(exc), line=line_number, event_id=event_id) from exc
        if event.eventId != event_id:
            raise JournalVerificationError(
                "projection.event_ids_resolvable",
                f"raw journal eventId {event_id!r} does not match replay envelope eventId {event.eventId!r}",
                line=line_number,
                event_id=event.eventId,
                entity_id=event.runId or event.attemptId,
            )
        events.append((line_number, event))
    return events


def _projection_summary(projection: ProjectionState, *, run_id: str | None = None) -> dict[str, int]:
    if run_id is None:
        return {
            "attempts": len(projection.attempts),
            "routeDecisions": len(projection.route_decisions),
            "runs": len(projection.runs),
            "unknownEvents": len(projection.unknown_events),
        }
    attempts = {
        attempt_id: attempt
        for attempt_id, attempt in projection.attempts.items()
        if attempt.runId == run_id
    }
    route_decisions = {
        decision_id: decision
        for decision_id, decision in projection.route_decisions.items()
        if decision.decision.runId == run_id
    }
    return {
        "attempts": len(attempts),
        "routeDecisions": len(route_decisions),
        "runs": 1 if run_id in projection.runs else 0,
        "unknownEvents": len(projection.unknown_events),
    }


def _passed_checks() -> list[dict[str, str]]:
    return [
        {"id": check_id, "status": "pass", "message": VERIFY_JOURNAL_CHECK_MESSAGES[check_id]}
        for check_id in VERIFY_JOURNAL_CHECKS
    ]


def _verify_projection_event_ids(projection: ProjectionState, journal_event_ids: set[str]) -> None:
    collections = (
        ("runs", projection.runs),
        ("attempts", projection.attempts),
    )
    for collection_name, entities in collections:
        for entity_id in sorted(entities):
            event_ids = list(entities[entity_id].eventIds)
            if event_ids != list(dict.fromkeys(event_ids)):
                raise JournalVerificationError(
                    "projection.event_ids_unique",
                    f"{collection_name} {entity_id} has duplicate eventIds",
                    entity_id=entity_id,
                    collection=collection_name,
                )
            for event_id in event_ids:
                if event_id not in journal_event_ids:
                    raise JournalVerificationError(
                        "projection.event_ids_resolvable",
                        f"{collection_name} {entity_id} references eventId not found in journal",
                        event_id=event_id,
                        entity_id=entity_id,
                        collection=collection_name,
                    )


def verify_journal_payload(journal_path: Path, *, run_id: str | None = None) -> dict[str, Any]:
    line_events = _read_verified_journal_events(journal_path)
    events = [event for _, event in line_events]
    if not events:
        raise JournalVerificationError("journal.not_empty", "journal must contain at least one event")
    try:
        projection = RunLifecycleReducer(root=ROOT).replay(events)
    except ProjectionReplayError as exc:
        raise JournalVerificationError("projection.replay", str(exc)) from exc
    _verify_projection_event_ids(projection, {event.eventId for event in events})
    full_summary = _projection_summary(projection)
    payload: dict[str, Any] = {
        "ok": True,
        "journal": str(journal_path),
        "events": len(events),
        "checks": _passed_checks(),
        "checkIds": VERIFY_JOURNAL_CHECKS,
        "projectionSummary": _projection_summary(projection, run_id=run_id),
    }
    if run_id is not None:
        payload["runId"] = run_id
        payload["fullProjectionSummary"] = full_summary
    return payload


def cmd_verify_journal(args: argparse.Namespace) -> int:
    try:
        payload = verify_journal_payload(Path(args.journal), run_id=args.run_id)
        if args.output:
            output_path = Path(args.output)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            payload["outputPath"] = str(output_path)
            output_path.write_text(json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
        return emit(payload)
    except JournalVerificationError as exc:
        return emit_journal_verification_error(exc)


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


def cmd_version(args: argparse.Namespace) -> int:
    contracts = load_event_contracts(ROOT)
    supported_event_names = [
        "run.lifecycle.transitioned",
        "attempt.lifecycle.transitioned",
        "route.decision.recorded",
        "manual_gate.parked",
        "manual_gate.rehydrated",
    ]
    event_versions = {
        name: str(contracts[name]["version"]) if name in contracts else "v1"
        for name in supported_event_names
    }
    return emit({
        "ok": True,
        "protocolReleaseTag": PROTOCOL_RELEASE_TAG,
        "commands": SUPPORTED_COMMANDS,
        "eventContract": {
            "eventVersion": "v1",
            "producer": DEFAULT_PRODUCER,
            "supportedEvents": supported_event_names,
            "eventVersions": event_versions,
            "journal": "append-only-jsonl",
            "projection": "replay-current-journal",
        },
    })


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

    verify_journal = subparsers.add_parser("verify-journal", help="Verify an append-only JSONL journal before replay/projection")
    verify_journal.add_argument("--journal", required=True, help="Path to the append-only JSONL journal")
    verify_journal.add_argument("--output", help="Write the complete stable verify JSON report to this path")
    verify_journal.add_argument("--run-id", help="Filter projectionSummary to one run after replaying the full journal")
    verify_journal.add_argument(
        "--strict-empty",
        action="store_true",
        help="Require at least one event in the journal. Empty journals fail by default; this flag locks that contract for CI.",
    )
    verify_journal.set_defaults(func=cmd_verify_journal)

    version = subparsers.add_parser("version", help="Print stable V3 CLI contract summary")
    version.set_defaults(func=cmd_version)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except ControlPlaneError as exc:
        return emit_control_plane_error(exc)
    except JournalVerificationError as exc:
        return emit_journal_verification_error(exc)


if __name__ == "__main__":
    raise SystemExit(main())
