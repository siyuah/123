#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "tools" / "v3_control_plane.py"


class SmokeAssertionError(AssertionError):
    """Raised when the subprocess-driven V3 CLI smoke timeline fails validation."""


def emit(payload: dict[str, Any], *, stream: Any = None) -> int:
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2), file=stream or sys.stdout)
    return 0


def emit_error(exc: BaseException) -> int:
    emit({"ok": False, "error": {"type": type(exc).__name__, "message": str(exc)}}, stream=sys.stderr)
    return 2


def run_cli(*args: str) -> dict[str, Any]:
    result = subprocess.run(
        [sys.executable, str(CLI), *args],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if result.returncode != 0:
        message = result.stderr.strip() or result.stdout.strip() or f"CLI exited {result.returncode}"
        try:
            parsed = json.loads(message)
            if isinstance(parsed, dict) and "error" in parsed:
                message = parsed["error"].get("message", message)
        except json.JSONDecodeError:
            pass
        raise SmokeAssertionError(message)
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise SmokeAssertionError(f"CLI emitted non-JSON stdout for {' '.join(args)}: {result.stdout!r}") from exc


def timeline_commands(journal: Path, *, inject_illegal_transition: bool) -> list[list[str]]:
    common = ["--journal", str(journal), "--correlation-id", "corr-smoke-001", "--trace-id", "trace-smoke-001"]
    run_id = "run-smoke-001"
    attempt_id = "attempt-smoke-001"
    commands = [
        ["request-run", "--journal", str(journal), "--run-id", run_id, "--correlation-id", "corr-smoke-001", "--trace-id", "trace-smoke-001"],
        [
            "record-route-decision", *common,
            "--run-id", run_id,
            "--attempt-id", attempt_id,
            "--route-decision-id", "rd-smoke-001",
            "--workload-class", "code",
            "--route-policy-ref", "policy://routing/v3/default",
            "--selected-executor-class", "code_executor",
            "--fallback-depth", "0",
            "--decision-reason", "primary_policy_match",
        ],
        ["transition-attempt", *common, "--run-id", run_id, "--attempt-id", attempt_id, "--old-state", "created", "--new-state", "booting", "--transition-trigger", "sandbox_allocated"],
        ["transition-attempt", *common, "--run-id", run_id, "--attempt-id", attempt_id, "--old-state", "booting", "--new-state", "active", "--transition-trigger", "first_checkpoint"],
    ]
    if inject_illegal_transition:
        commands.append(["transition-run", *common, "--run-id", run_id, "--old-state", "validating", "--new-state", "completed", "--transition-trigger", "closure_success"])
        return commands
    commands.extend([
        ["transition-run", *common, "--run-id", run_id, "--old-state", "validating", "--new-state", "planning", "--transition-trigger", "validation_passed"],
        ["transition-run", *common, "--run-id", run_id, "--old-state", "planning", "--new-state", "executing", "--transition-trigger", "execution_starts"],
        ["park-manual", *common, "--run-id", run_id, "--attempt-id", attempt_id, "--park-id", "park-smoke-001", "--manual-gate-type", "operator_review", "--rehydration-token-id", "rt-smoke-001"],
        ["rehydrate-manual", *common, "--run-id", run_id, "--previous-attempt-id", attempt_id, "--new-attempt-id", "attempt-smoke-002", "--rehydration-token-id", "rt-smoke-001"],
    ])
    return commands


def load_journal_events(journal: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in journal.read_text(encoding="utf-8").splitlines() if line.strip()]


def _assert_unique_event_ids(collection_name: str, entities: dict[str, Any]) -> None:
    for entity_id, entity in entities.items():
        event_ids = entity.get("eventIds", [])
        if event_ids != list(dict.fromkeys(event_ids)):
            raise SmokeAssertionError(f"{collection_name} {entity_id} has duplicate eventIds: {event_ids}")


def validate_projection(journal: Path, projection: dict[str, Any]) -> list[int]:
    events = load_journal_events(journal)
    sequence_nos = [event["sequenceNo"] for event in events]
    if sequence_nos != list(range(1, len(events) + 1)):
        raise SmokeAssertionError(f"sequenceNo values are not contiguous from 1: {sequence_nos}")
    if len(events) != 8:
        raise SmokeAssertionError(f"expected 8 events, found {len(events)}")
    if projection["runs"]["run-smoke-001"]["currentState"] != "planning":
        raise SmokeAssertionError("run-smoke-001 did not project to planning")
    if projection["attempts"]["attempt-smoke-001"]["currentState"] != "superseded":
        raise SmokeAssertionError("attempt-smoke-001 did not project to superseded")
    if projection["attempts"]["attempt-smoke-002"]["currentState"] != "created":
        raise SmokeAssertionError("attempt-smoke-002 did not project to created")
    if "rd-smoke-001" not in projection["routeDecisions"]:
        raise SmokeAssertionError("rd-smoke-001 routeDecision missing from projection")
    _assert_unique_event_ids("run", projection["runs"])
    _assert_unique_event_ids("attempt", projection["attempts"])
    rehydrated_event_id = "evt-corr-smoke-001-0008"
    if projection["runs"]["run-smoke-001"]["eventIds"].count(rehydrated_event_id) > 1:
        raise SmokeAssertionError("run-smoke-001 repeats the rehydrated eventId")
    if projection["attempts"]["attempt-smoke-001"]["eventIds"].count(rehydrated_event_id) > 1:
        raise SmokeAssertionError("attempt-smoke-001 repeats the rehydrated eventId")
    return sequence_nos


def run_smoke(journal: Path, *, inject_illegal_transition: bool) -> dict[str, Any]:
    journal.parent.mkdir(parents=True, exist_ok=True)
    if journal.exists():
        journal.unlink()
    for command in timeline_commands(journal, inject_illegal_transition=inject_illegal_transition):
        run_cli(*command)
    projection_payload = run_cli("projection", "--journal", str(journal))
    projection = projection_payload["projection"]
    sequence_nos = validate_projection(journal, projection)
    verify_payload = run_cli("verify-journal", "--journal", str(journal))
    if verify_payload.get("ok") is not True:
        raise SmokeAssertionError("verify-journal did not return ok")
    return {
        "ok": True,
        "journal": str(journal),
        "events": 8,
        "sequenceNos": sequence_nos,
        "projection": projection,
        "verifyJournal": {
            "ok": verify_payload["ok"],
            "events": verify_payload["events"],
            "checks": verify_payload["checks"],
            "projectionSummary": verify_payload["projectionSummary"],
        },
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run an end-to-end V3 control-plane CLI smoke timeline")
    parser.add_argument("--journal", help="Path to keep the append-only JSONL journal. Defaults to a temporary smoke directory.")
    parser.add_argument(
        "--inject-illegal-transition",
        action="store_true",
        help=argparse.SUPPRESS,
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.journal:
            payload = run_smoke(Path(args.journal), inject_illegal_transition=args.inject_illegal_transition)
            return emit(payload)
        with tempfile.TemporaryDirectory(prefix="v3-control-plane-smoke-") as tmpdir:
            journal = Path(tmpdir) / "v3_control_plane_smoke.jsonl"
            payload = run_smoke(journal, inject_illegal_transition=args.inject_illegal_transition)
            return emit(payload)
    except SmokeAssertionError as exc:
        return emit_error(exc)


if __name__ == "__main__":
    raise SystemExit(main())
