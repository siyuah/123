#!/usr/bin/env python3
"""Dark Factory review readiness dashboard.

This tool aggregates low-cost review gates into one stable report. It is
read-only: it does not update manifests, consistency reports, journals, or
runtime state.
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

try:
    import yaml  # type: ignore
except Exception:  # pragma: no cover - handled at runtime
    yaml = None

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL_RELEASE_TAG = "v3.0-agent-control-r1"

BUNDLE_MANIFEST = "paperclip_darkfactory_v3_0_bundle_manifest.yaml"
CORE_ENUMS = "paperclip_darkfactory_v3_0_core_enums.yaml"
CORE_OBJECTS_SCHEMA = "paperclip_darkfactory_v3_0_core_objects.schema.json"
EVENT_CONTRACTS = "paperclip_darkfactory_v3_0_event_contracts.yaml"
STATE_MATRIX = "paperclip_darkfactory_v3_0_state_transition_matrix.csv"
SCENARIO_MATRIX = "paperclip_darkfactory_v3_0_scenario_acceptance_matrix.csv"
TEST_TRACEABILITY = "paperclip_darkfactory_v3_0_test_traceability.csv"

PROTOCOL_TAG_FILES = [
    CORE_OBJECTS_SCHEMA,
    EVENT_CONTRACTS,
    "paperclip_darkfactory_v3_0_external_runs.openapi.yaml",
    "paperclip_darkfactory_v3_0_memory.openapi.yaml",
    BUNDLE_MANIFEST,
]

STATE_ENUM_BY_DOMAIN = {
    "run": "runState",
    "attempt": "attemptState",
    "artifact": "artifactCertificationState",
    "dependency": "inputDependencyState",
}

VALID_STATUSES = {"PASS", "WARN", "FAIL", "SKIP"}


@dataclass(frozen=True)
class CheckResult:
    id: str
    status: str
    summary: str
    details: str = ""
    evidence: str = ""

    def __post_init__(self) -> None:
        if self.status not in VALID_STATUSES:
            raise ValueError(f"invalid check status: {self.status}")

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


def load_yaml(path: Path) -> Any:
    if yaml is None:
        raise RuntimeError("PyYAML is required to parse YAML files")
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def stable_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def is_binding_manifest_entry(entry: dict[str, Any]) -> bool:
    normativity = str(entry.get("normativity", "")).lower()
    return "binding" in normativity or normativity == "normative"


def check_bundle_files(root: Path) -> CheckResult:
    try:
        manifest = load_yaml(root / BUNDLE_MANIFEST)
    except Exception as exc:
        return CheckResult("bundle-files", "FAIL", "bundle manifest cannot be parsed", type(exc).__name__, str(exc))

    files = [entry for entry in manifest.get("files", []) if is_binding_manifest_entry(entry)]
    missing = [str(entry.get("path")) for entry in files if not entry.get("path") or not (root / str(entry.get("path"))).exists()]
    if missing:
        return CheckResult(
            "bundle-files",
            "FAIL",
            f"{len(files) - len(missing)}/{len(files)} binding files present",
            "missing: " + ", ".join(missing),
            BUNDLE_MANIFEST,
        )
    return CheckResult(
        "bundle-files",
        "PASS",
        f"{len(files)}/{len(files)} binding files present",
        "binding/normative manifest entries all exist",
        BUNDLE_MANIFEST,
    )


def check_protocol_tag(root: Path) -> CheckResult:
    missing_files: list[str] = []
    missing_tag: list[str] = []
    occurrences: dict[str, int] = {}
    for rel_path in PROTOCOL_TAG_FILES:
        path = root / rel_path
        if not path.exists():
            missing_files.append(rel_path)
            continue
        count = path.read_text(encoding="utf-8").count(PROTOCOL_RELEASE_TAG)
        occurrences[rel_path] = count
        if count == 0:
            missing_tag.append(rel_path)

    if missing_files or missing_tag:
        details = []
        if missing_files:
            details.append("missing files: " + ", ".join(missing_files))
        if missing_tag:
            details.append("missing protocolReleaseTag: " + ", ".join(missing_tag))
        return CheckResult(
            "protocol-tag",
            "FAIL",
            f"{PROTOCOL_RELEASE_TAG} propagated in {len(occurrences) - len(missing_tag)}/{len(PROTOCOL_TAG_FILES)} files",
            "; ".join(details),
            stable_json({"occurrences": occurrences}).strip(),
        )

    return CheckResult(
        "protocol-tag",
        "PASS",
        f"{PROTOCOL_RELEASE_TAG} propagated in {len(PROTOCOL_TAG_FILES)}/{len(PROTOCOL_TAG_FILES)} files",
        "schema, OpenAPI, event contracts, and manifest contain the protocol release tag",
        stable_json({"occurrences": occurrences}).strip(),
    )


def check_contract_parity(root: Path) -> CheckResult:
    try:
        core_enums = load_yaml(root / CORE_ENUMS)
        event_contracts = load_yaml(root / EVENT_CONTRACTS)
        state_rows = csv_rows(root / STATE_MATRIX)
    except Exception as exc:
        return CheckResult("contract-parity", "FAIL", "contract sources cannot be parsed", type(exc).__name__, str(exc))

    enum_map = core_enums.get("enums", {})
    enum_events = set(enum_map.get("eventCanonicalName", []))
    contract_events = {event.get("canonicalName", "") for event in event_contracts.get("events", []) if event.get("canonicalName")}

    event_enum_only = sorted(enum_events - contract_events)
    event_contract_only = sorted(contract_events - enum_events)

    undeclared_states: list[str] = []
    matched_state_values = 0
    for row in state_rows:
        domain = row.get("domain", "")
        enum_key = STATE_ENUM_BY_DOMAIN.get(domain)
        allowed = set(enum_map.get(enum_key, [])) if enum_key else set()
        for column in ("current_state", "next_state"):
            value = row.get(column, "")
            if value in allowed:
                matched_state_values += 1
            else:
                undeclared_states.append(f"{domain}.{column}={value}")

    drift = event_enum_only or event_contract_only or undeclared_states
    matched_values = len(enum_events & contract_events) + matched_state_values
    if drift:
        return CheckResult(
            "contract-parity",
            "FAIL",
            "enum/state/event contract drift detected",
            stable_json(
                {
                    "eventEnumOnly": event_enum_only,
                    "eventContractOnly": event_contract_only,
                    "undeclaredStates": undeclared_states,
                }
            ).strip(),
            f"{matched_values} enum/state/event values matched before drift",
        )

    return CheckResult(
        "contract-parity",
        "PASS",
        f"{matched_values} enum/state/event values matched",
        "event canonical names and state matrix values match core enums",
        f"{CORE_ENUMS}; {EVENT_CONTRACTS}; {STATE_MATRIX}",
    )


def check_release_blockers(root: Path) -> CheckResult:
    try:
        scenarios = csv_rows(root / SCENARIO_MATRIX)
        traceability = csv_rows(root / TEST_TRACEABILITY)
    except Exception as exc:
        return CheckResult("release-blockers", "FAIL", "release blocker sources cannot be parsed", type(exc).__name__, str(exc))

    release_blockers = [row.get("scenario_id", "") for row in scenarios if row.get("release_blocker", "").lower() == "true"]
    traced_scenarios = {row.get("scenario_id", "") for row in traceability if row.get("scenario_id")}
    covered = [scenario_id for scenario_id in release_blockers if scenario_id in traced_scenarios]
    missing = [scenario_id for scenario_id in release_blockers if scenario_id and scenario_id not in traced_scenarios]

    if missing:
        return CheckResult(
            "release-blockers",
            "WARN",
            f"{len(covered)}/{len(release_blockers)} release-blocker scenarios have traceability evidence",
            "missing evidence: " + ", ".join(sorted(missing)),
            f"{SCENARIO_MATRIX}; {TEST_TRACEABILITY}",
        )

    return CheckResult(
        "release-blockers",
        "PASS",
        f"{len(covered)}/{len(release_blockers)} release-blocker scenarios have traceability evidence",
        "all release-blocker scenarios are represented in test traceability",
        f"{SCENARIO_MATRIX}; {TEST_TRACEABILITY}",
    )


def check_journal_admin(root: Path) -> CheckResult:
    path = root / "tools" / "journal_admin.py"
    if not path.exists():
        return CheckResult("journal-admin", "FAIL", "journal_admin.py is missing", "", str(path))
    source = path.read_text(encoding="utf-8")
    capabilities = {
        "backup": "subcommands.add_parser(\"backup\"" in source and "def backup(" in source,
        "retain": "subcommands.add_parser(\"retain\"" in source and "def retain(" in source,
        "verify": "def validate_jsonl(" in source,
    }
    missing = [name for name, present in capabilities.items() if not present]
    if missing:
        return CheckResult(
            "journal-admin",
            "WARN",
            f"{len(capabilities) - len(missing)}/{len(capabilities)} journal admin capabilities available",
            "missing: " + ", ".join(missing),
            str(path),
        )
    return CheckResult(
        "journal-admin",
        "PASS",
        "backup/retain/verify capabilities available",
        "verify is provided by validate_jsonl before backup/restore",
        str(path),
    )


def check_agents_md(root: Path) -> CheckResult:
    path = root / "AGENTS.md"
    if not path.exists():
        return CheckResult("agents-md", "FAIL", "AGENTS.md missing", "", str(path))
    source = path.read_text(encoding="utf-8")
    required_terms = ["Coordinator", "Researcher", "Builder", "Writer", "df-contract-check", "Dark Factory Journal remains truth source"]
    missing = [term for term in required_terms if term not in source]
    if missing:
        return CheckResult("agents-md", "WARN", "AGENTS.md exists but is missing expected workflow terms", ", ".join(missing), str(path))
    return CheckResult("agents-md", "PASS", "AGENTS.md present with role and workflow terms", "", str(path))


def evidence_status(payload: Any) -> tuple[bool, str]:
    if not isinstance(payload, dict):
        return False, "evidence root is not an object"
    if payload.get("ok") is True:
        return True, "ok=true"
    if str(payload.get("status", "")).lower() in {"pass", "passed", "ready"}:
        return True, f"status={payload.get('status')}"
    return False, f"ok={payload.get('ok')} status={payload.get('status')}"


def check_evidence(check_id: str, label: str, path_value: str | None) -> CheckResult:
    if not path_value:
        return CheckResult(check_id, "WARN", f"{label} evidence not provided")
    path = Path(path_value)
    if not path.exists():
        return CheckResult(check_id, "WARN", f"{label} evidence path does not exist", "", str(path))
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return CheckResult(check_id, "WARN", f"{label} evidence cannot be parsed", type(exc).__name__, str(path))
    ok, detail = evidence_status(payload)
    return CheckResult(
        check_id,
        "PASS" if ok else "WARN",
        f"{label} evidence {'passes' if ok else 'does not pass'}",
        detail,
        str(path),
    )


def build_checks(root: Path, *, smoke_evidence: str | None = None, bridge_evidence: str | None = None) -> list[CheckResult]:
    return [
        check_bundle_files(root),
        check_protocol_tag(root),
        check_contract_parity(root),
        check_release_blockers(root),
        check_journal_admin(root),
        check_agents_md(root),
        check_evidence("smoke-evidence", "smoke", smoke_evidence),
        check_evidence("bridge-evidence", "bridge", bridge_evidence),
    ]


def select_checks(checks: Iterable[CheckResult], only: list[str] | None) -> list[CheckResult]:
    checks = list(checks)
    if not only:
        return checks
    wanted = set(only)
    selected = [check for check in checks if check.id in wanted]
    missing = sorted(wanted - {check.id for check in selected})
    selected.extend(CheckResult(name, "FAIL", f"unknown check id: {name}") for name in missing)
    return selected


def overall_status(checks: Iterable[CheckResult]) -> str:
    statuses = [check.status for check in checks]
    if any(status == "FAIL" for status in statuses):
        return "NOT_READY"
    if any(status == "WARN" for status in statuses):
        return "CONDITIONAL_READY"
    return "READY"


def summarize(checks: list[CheckResult]) -> dict[str, Any]:
    return {
        "total": len(checks),
        "passed": sum(1 for check in checks if check.status == "PASS"),
        "warned": sum(1 for check in checks if check.status == "WARN"),
        "failed": sum(1 for check in checks if check.status == "FAIL"),
        "skipped": sum(1 for check in checks if check.status == "SKIP"),
        "failedChecks": [check.id for check in checks if check.status == "FAIL"],
        "warnedChecks": [check.id for check in checks if check.status == "WARN"],
        "skippedChecks": [check.id for check in checks if check.status == "SKIP"],
    }


def build_report(root: Path, *, only: list[str] | None = None, smoke_evidence: str | None = None, bridge_evidence: str | None = None) -> dict[str, Any]:
    checks = select_checks(build_checks(root, smoke_evidence=smoke_evidence, bridge_evidence=bridge_evidence), only)
    status = overall_status(checks)
    return {
        "checkedAt": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "ok": status != "NOT_READY",
        "protocolReleaseTag": PROTOCOL_RELEASE_TAG,
        "reportType": "dark-factory-review-readiness",
        "root": str(root),
        "status": status,
        "summary": summarize(checks),
        "checks": [check.to_dict() for check in checks],
    }


def render_text(report: dict[str, Any]) -> str:
    lines = [f"Dark Factory Review Readiness — {report['checkedAt']}", ""]
    for check in report["checks"]:
        lines.append(f"[{check['status']}] {check['id']}: {check['summary']}")
        if check.get("details"):
            lines.append(f"  details: {check['details']}")
        if check.get("evidence"):
            lines.append(f"  evidence: {check['evidence']}")
    lines.append("")
    lines.append(f"Overall: {report['status']}")
    return "\n".join(lines) + "\n"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Aggregate Dark Factory review readiness checks")
    parser.add_argument("--json", action="store_true", help="output stable JSON")
    parser.add_argument("--only", action="append", help="run only the named check id; may be repeated")
    parser.add_argument("--fail-on-blocker", action="store_true", help="return non-zero when any check fails")
    parser.add_argument("--smoke-evidence", help="read optional smoke result JSON")
    parser.add_argument("--bridge-evidence", help="read optional bridge readiness JSON")
    parser.add_argument("--root", default=str(ROOT), help=argparse.SUPPRESS)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    root = Path(args.root).resolve()
    report = build_report(root, only=args.only, smoke_evidence=args.smoke_evidence, bridge_evidence=args.bridge_evidence)
    sys.stdout.write(stable_json(report) if args.json else render_text(report))
    if args.fail_on_blocker and report["status"] == "NOT_READY":
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
