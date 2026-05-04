#!/usr/bin/env python3
"""Report drift between Dark Factory V3 contract artifacts."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import yaml  # type: ignore

ROOT = Path(__file__).resolve().parents[1]
TOOLS_DIR = ROOT / "tools"
for import_path in (ROOT, TOOLS_DIR):
    if str(import_path) not in sys.path:
        sys.path.insert(0, str(import_path))

from generate_v3_contract_summary import render_summary  # noqa: E402
from validate_v3_bundle import validate_bundle  # noqa: E402

PROTOCOL_RELEASE_TAG = "v3.0-agent-control-r1"
CORE_ENUMS = "paperclip_darkfactory_v3_0_core_enums.yaml"
CORE_OBJECTS_SCHEMA = "paperclip_darkfactory_v3_0_core_objects.schema.json"
EVENT_CONTRACTS = "paperclip_darkfactory_v3_0_event_contracts.yaml"

ENUM_SCHEMA_MAP = {
    "artifactCertificationState": "ArtifactCertificationState",
    "inputDependencyState": "InputDependencyState",
    "dependencyConsumptionPolicy": "DependencyConsumptionPolicy",
    "profileConformanceStatus": "ProfileConformanceStatus",
    "capsuleHealth": "CapsuleHealth",
    "manualGateType": "ManualGateType",
    "executionSuspensionState": "ExecutionSuspensionState",
    "workloadClass": "WorkloadClass",
    "providerFaultClass": "ProviderFaultClass",
    "providerHealthState": "ProviderHealthState",
    "recoveryLane": "RecoveryLane",
    "routeDecisionReasonCode": "RouteDecisionReasonCode",
    "riskLevel": "RiskLevel",
    "costLevel": "CostLevel",
    "memoryArtifactType": "MemoryArtifactType",
    "memoryArtifactState": "MemoryArtifactState",
    "repairOutcome": "RepairOutcome",
    "routeDecisionState": "RouteDecisionState",
    "blastRadiusClass": "BlastRadiusClass",
    "approvalLevel": "ApprovalLevel",
    "guardrailDecision": "GuardrailDecisionValue",
    "timingBucketShift": "TimingBucketShift",
    "structuredJournalFactType": "StructuredJournalFactType",
    "contractDriftStatus": "ContractDriftStatus",
}


def stable_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def load_yaml(path: Path) -> Any:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def make_check(check_id: str, status: str, message: str, **details: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {"id": check_id, "status": status, "message": message}
    if details:
        payload["details"] = details
    return payload


def check_protocol_tags(root: Path) -> dict[str, Any]:
    sources = {
        CORE_ENUMS: load_yaml(root / CORE_ENUMS).get("protocolReleaseTag"),
        EVENT_CONTRACTS: load_yaml(root / EVENT_CONTRACTS).get("protocolReleaseTag"),
    }
    schema = json.loads((root / CORE_OBJECTS_SCHEMA).read_text(encoding="utf-8"))
    schema_tag_count = json.dumps(schema, sort_keys=True).count(PROTOCOL_RELEASE_TAG)
    drift = {path: value for path, value in sources.items() if value != PROTOCOL_RELEASE_TAG}
    if schema_tag_count == 0:
        drift[CORE_OBJECTS_SCHEMA] = "missing"
    return make_check(
        "protocol-tags",
        "fail" if drift else "pass",
        "protocolReleaseTag values match" if not drift else "protocolReleaseTag drift detected",
        drift=drift,
        schemaTagOccurrences=schema_tag_count,
    )


def check_event_parity(root: Path) -> dict[str, Any]:
    core = load_yaml(root / CORE_ENUMS)
    events = load_yaml(root / EVENT_CONTRACTS)
    enum_events = set(core.get("enums", {}).get("eventCanonicalName", []))
    contract_events = {event["canonicalName"] for event in events.get("events", [])}
    enum_only = sorted(enum_events - contract_events)
    contract_only = sorted(contract_events - enum_events)
    return make_check(
        "event-parity",
        "fail" if enum_only or contract_only else "pass",
        "event enum and event contracts match" if not enum_only and not contract_only else "event parity drift detected",
        enumOnly=enum_only,
        contractOnly=contract_only,
    )


def check_schema_enum_parity(root: Path) -> dict[str, Any]:
    core = load_yaml(root / CORE_ENUMS)
    schema = json.loads((root / CORE_OBJECTS_SCHEMA).read_text(encoding="utf-8"))
    enum_map = core.get("enums", {})
    defs = schema.get("$defs", {})
    drift: list[dict[str, Any]] = []
    for enum_key, schema_key in ENUM_SCHEMA_MAP.items():
        expected = list(enum_map.get(enum_key, []))
        actual = list(defs.get(schema_key, {}).get("enum", []))
        if expected != actual:
            drift.append({"enum": enum_key, "schemaDef": schema_key, "expected": expected, "actual": actual})
    return make_check(
        "schema-enum-parity",
        "fail" if drift else "pass",
        "schema enum definitions match core enums" if not drift else "schema enum drift detected",
        drift=drift,
        checkedEnums=len(ENUM_SCHEMA_MAP),
    )


def check_required_batch4_defs(root: Path) -> dict[str, Any]:
    schema = json.loads((root / CORE_OBJECTS_SCHEMA).read_text(encoding="utf-8"))
    defs = schema.get("$defs", {})
    required = ["FaultPlaybook", "StructuredJournalFact", "ContractDriftReport"]
    missing = [name for name in required if name not in defs]
    return make_check(
        "batch4-definitions",
        "fail" if missing else "pass",
        "Batch 4 schema definitions are present" if not missing else "Batch 4 schema definitions are missing",
        missing=missing,
    )


def check_bundle(root: Path) -> dict[str, Any]:
    report = validate_bundle(root)
    errors = int(report.get("summary", {}).get("errors", 0))
    return make_check(
        "bundle-validation",
        "fail" if errors else "pass",
        "V3 bundle validation passes" if not errors else "V3 bundle validation fails",
        errors=errors,
        failedChecks=[check.get("id") for check in report.get("checks", []) if check.get("status") == "fail"],
    )


def check_generated_summary(root: Path, rel_path: str | None) -> dict[str, Any]:
    if not rel_path:
        return make_check("generated-summary", "skipped", "summary path not provided")
    path = root / rel_path
    expected = render_summary(root)
    if not path.exists():
        return make_check("generated-summary", "warn", "generated summary is missing", path=rel_path)
    actual = path.read_text(encoding="utf-8")
    return make_check(
        "generated-summary",
        "fail" if actual != expected else "pass",
        "generated summary matches current contracts" if actual == expected else "generated summary drift detected",
        path=rel_path,
    )


def build_report(root: Path | str = ROOT, *, summary_path: str | None = None) -> dict[str, Any]:
    root = Path(root)
    checks = [
        check_protocol_tags(root),
        check_event_parity(root),
        check_schema_enum_parity(root),
        check_required_batch4_defs(root),
        check_bundle(root),
        check_generated_summary(root, summary_path),
    ]
    failed = [check["id"] for check in checks if check["status"] == "fail"]
    warned = [check["id"] for check in checks if check["status"] == "warn"]
    status = "drift_detected" if failed else "in_sync"
    return {
        "ok": not failed,
        "protocolReleaseTag": PROTOCOL_RELEASE_TAG,
        "reportType": "dark-factory-v3-contract-drift-report",
        "status": status,
        "checks": checks,
        "summary": {
            "checks": len(checks),
            "failed": len(failed),
            "warnings": len(warned),
            "failedChecks": failed,
            "warningChecks": warned,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=str(ROOT), help="repository root")
    parser.add_argument("--summary-path", default="docs/generated/V3_CONTRACT_SUMMARY.md")
    parser.add_argument("--json", action="store_true", help="emit JSON")
    parser.add_argument("--fail-on-drift", action="store_true", help="exit non-zero when drift is detected")
    args = parser.parse_args()

    report = build_report(Path(args.root), summary_path=args.summary_path)
    if args.json:
        print(stable_json(report), end="")
    else:
        print(f"Dark Factory V3 Contract Drift Report: {report['status']}")
        for check in report["checks"]:
            print(f"[{check['status'].upper()}] {check['id']}: {check['message']}")
    return 1 if args.fail_on_drift and not report["ok"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
