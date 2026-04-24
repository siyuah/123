#!/usr/bin/env python3
"""Validate the Paperclip Dark Factory V3.0 documentation bundle.

The checker is intentionally dependency-light: it only uses Python stdlib plus
PyYAML when available. It verifies the bundle-level invariants that can be
checked without a running implementation.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

try:
    import yaml  # type: ignore
except Exception:  # pragma: no cover - handled at runtime
    yaml = None

PROTOCOL_RELEASE_TAG = "v3.0-agent-control-r1"
MANIFEST_PATH = "paperclip_darkfactory_v3_0_bundle_manifest.yaml"
REPORT_JSON_PATH = "paperclip_darkfactory_v3_0_consistency_report.json"
REPORT_MD_PATH = "paperclip_darkfactory_v3_0_consistency_report.md"


def _load_yaml(path: Path) -> Any:
    if yaml is None:
        raise RuntimeError("PyYAML is required to parse YAML files")
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _check(check_id: str, status: str, message: str, **details: Any) -> Dict[str, Any]:
    item: Dict[str, Any] = {"id": check_id, "status": status, "message": message}
    if details:
        item["details"] = details
    return item


def _csv_rows(path: Path) -> List[Dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def _iter_manifest_files(manifest: Dict[str, Any]) -> Iterable[Dict[str, Any]]:
    return manifest.get("files", []) or []


def validate_bundle(root: Path | str) -> Dict[str, Any]:
    root = Path(root)
    checks: List[Dict[str, Any]] = []

    manifest = _load_yaml(root / MANIFEST_PATH)
    manifest_files = list(_iter_manifest_files(manifest))
    manifest_paths = [entry.get("path") for entry in manifest_files]

    missing = [p for p in manifest_paths if not p or not (root / p).exists()]
    checks.append(
        _check(
            "manifest-path-exists",
            "fail" if missing else "pass",
            "all manifest paths exist" if not missing else "manifest references missing files",
            missingPaths=missing,
            checkedFiles=len(manifest_files),
        )
    )

    duplicate_paths = sorted({p for p in manifest_paths if manifest_paths.count(p) > 1})
    checks.append(
        _check(
            "manifest-unique-paths",
            "fail" if duplicate_paths else "pass",
            "manifest paths are unique" if not duplicate_paths else "manifest contains duplicate paths",
            duplicatePaths=duplicate_paths,
        )
    )

    hash_mismatches: List[Dict[str, str]] = []
    skipped_hash_paths = set(manifest.get("excludedFromDigest", []) or [])
    if manifest.get("selfHashMode") == "excluded-from-own-digest":
        skipped_hash_paths.add(MANIFEST_PATH)
        skipped_hash_paths.add(REPORT_JSON_PATH)
        skipped_hash_paths.add(REPORT_MD_PATH)
    for entry in manifest_files:
        rel = entry.get("path")
        if not rel or rel in skipped_hash_paths:
            continue
        path = root / rel
        if not path.exists():
            continue
        expected = entry.get("sha256")
        actual = _sha256(path)
        if expected != actual:
            hash_mismatches.append({"path": rel, "expected": str(expected), "actual": actual})
    checks.append(
        _check(
            "manifest-sha256-match",
            "fail" if hash_mismatches else "pass",
            "manifest sha256 values match disk" if not hash_mismatches else "manifest sha256 mismatch",
            mismatches=hash_mismatches,
        )
    )

    tracked = [
        p
        for p in ((root / ".git").exists() and _git_ls_files(root) or [])
        if "__pycache__/" not in p and not p.endswith((".pyc", ".pyo"))
    ]
    excluded = set(manifest.get("excludedFromDigest", []) or []) | set(manifest.get("informativeOutOfBundle", []) or [])
    unclassified = [p for p in tracked if p not in manifest_paths and p not in excluded]
    checks.append(
        _check(
            "tracked-files-classified-by-manifest",
            "fail" if unclassified else "pass",
            "tracked files are listed or explicitly excluded" if not unclassified else "tracked files lack manifest classification",
            unclassifiedPaths=unclassified,
        )
    )

    core_enums = _load_yaml(root / "paperclip_darkfactory_v3_0_core_enums.yaml")
    event_contracts = _load_yaml(root / "paperclip_darkfactory_v3_0_event_contracts.yaml")
    enum_events = set(core_enums["enums"].get("eventCanonicalName", []))
    contract_events = {event["canonicalName"] for event in event_contracts.get("events", [])}
    event_diff = {
        "enumOnly": sorted(enum_events - contract_events),
        "contractOnly": sorted(contract_events - enum_events),
    }
    checks.append(
        _check(
            "event-enum-contract-parity",
            "fail" if event_diff["enumOnly"] or event_diff["contractOnly"] else "pass",
            "event canonical names match between enum and event contracts"
            if not event_diff["enumOnly"] and not event_diff["contractOnly"]
            else "event canonical name drift detected",
            **event_diff,
        )
    )

    state_rows = _csv_rows(root / "paperclip_darkfactory_v3_0_state_transition_matrix.csv")
    state_enums = {
        "run": set(core_enums["enums"].get("runState", [])),
        "attempt": set(core_enums["enums"].get("attemptState", [])),
        "artifact": set(core_enums["enums"].get("artifactCertificationState", [])),
        "dependency": set(core_enums["enums"].get("inputDependencyState", [])),
    }
    undeclared_states = []
    for row in state_rows:
        domain = row.get("domain", "")
        for column in ("current_state", "next_state"):
            value = row.get(column, "")
            if value not in state_enums.get(domain, set()):
                undeclared_states.append({"domain": domain, "column": column, "value": value})
    checks.append(
        _check(
            "state-matrix-enum-parity",
            "fail" if undeclared_states else "pass",
            "state transition matrix values are declared in core enums"
            if not undeclared_states
            else "state transition matrix contains undeclared values",
            undeclaredStates=undeclared_states,
        )
    )

    scenario_rows = _csv_rows(root / "paperclip_darkfactory_v3_0_scenario_acceptance_matrix.csv")
    trace_rows = _csv_rows(root / "paperclip_darkfactory_v3_0_test_traceability.csv")
    traced_scenarios = {r.get("scenario_id", "") for r in trace_rows if r.get("scenario_id")}
    release_blockers = [r.get("scenario_id", "") for r in scenario_rows if r.get("release_blocker", "").lower() == "true"]
    missing_scenario_trace = sorted([sid for sid in release_blockers if sid and sid not in traced_scenarios])
    checks.append(
        _check(
            "release-blocker-scenario-traceability",
            "fail" if missing_scenario_trace else "pass",
            "every release-blocker scenario is mapped in traceability"
            if not missing_scenario_trace
            else "release-blocker scenarios missing traceability rows",
            missingScenarioIds=missing_scenario_trace,
        )
    )

    golden_refs = sorted({r.get("golden_timeline", "") for r in trace_rows if r.get("golden_timeline")})
    missing_golden = [ref for ref in golden_refs if not (root / ref).exists()]
    checks.append(
        _check(
            "golden-timeline-exists",
            "fail" if missing_golden else "pass",
            "all referenced golden timelines exist" if not missing_golden else "referenced golden timelines are missing",
            goldenTimelineRefs=golden_refs,
            missingGoldenTimelineRefs=missing_golden,
        )
    )

    golden_errors = _validate_golden_timelines(root, golden_refs, event_contracts)
    checks.append(
        _check(
            "golden-timeline-event-contract-parity",
            "fail" if golden_errors else "pass",
            "golden timelines use canonical event names, event versions, and protocol tags"
            if not golden_errors
            else "golden timeline event drift detected",
            errors=golden_errors,
        )
    )

    for openapi_path in ["paperclip_darkfactory_v3_0_external_runs.openapi.yaml", "paperclip_darkfactory_v3_0_memory.openapi.yaml"]:
        api = _load_yaml(root / openapi_path)
        tag_count = json.dumps(api, sort_keys=True).count(PROTOCOL_RELEASE_TAG)
        checks.append(
            _check(
                f"openapi-parse-and-protocol-tag:{openapi_path}",
                "pass" if tag_count > 0 else "fail",
                "OpenAPI parses and contains protocol release tag"
                if tag_count > 0
                else "OpenAPI missing protocol release tag",
                protocolReleaseTagOccurrences=tag_count,
            )
        )

    json.loads((root / "paperclip_darkfactory_v3_0_core_objects.schema.json").read_text(encoding="utf-8"))
    checks.append(_check("json-schema-parse", "pass", "core object JSON Schema parses"))

    errors = sum(1 for c in checks if c["status"] == "fail")
    warnings = sum(1 for c in checks if c["status"] == "warn")
    status = "pass" if errors == 0 and warnings == 0 else "fail" if errors else "warn"
    return {
        "protocolReleaseTag": PROTOCOL_RELEASE_TAG,
        "status": status,
        "checkedAt": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "summary": {"errors": errors, "warnings": warnings, "checks": len(checks)},
        "checks": checks,
    }


def _git_ls_files(root: Path) -> List[str]:
    import subprocess

    # Use NUL-delimited output so non-ASCII filenames round-trip correctly.
    # Only validate files that are tracked/staged for the bundle; unrelated
    # local scratch files from document review should not affect release gates.
    result = subprocess.run(
        ["git", "ls-files", "-z", "--cached"],
        cwd=root,
        check=True,
        stdout=subprocess.PIPE,
    )
    raw_paths = result.stdout.split(b"\0")
    return [p.decode("utf-8", errors="surrogateescape") for p in raw_paths if p]


def _validate_golden_timelines(root: Path, refs: Iterable[str], event_contracts: Dict[str, Any]) -> List[Dict[str, Any]]:
    by_name = {event["canonicalName"]: event for event in event_contracts.get("events", [])}
    errors: List[Dict[str, Any]] = []
    for ref in refs:
        path = root / ref
        if not path.exists():
            continue
        for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            if not line.strip():
                continue
            try:
                item = json.loads(line)
            except json.JSONDecodeError as exc:
                errors.append({"path": ref, "line": line_no, "error": f"invalid JSONL: {exc}"})
                continue
            event_name = item.get("eventName")
            event = by_name.get(event_name)
            if event is None:
                errors.append({"path": ref, "line": line_no, "error": "unknown eventName", "eventName": event_name})
                continue
            if item.get("eventVersion") != event.get("version"):
                errors.append(
                    {
                        "path": ref,
                        "line": line_no,
                        "error": "eventVersion mismatch",
                        "eventName": event_name,
                        "expected": event.get("version"),
                        "actual": item.get("eventVersion"),
                    }
                )
            if item.get("protocolReleaseTag") != PROTOCOL_RELEASE_TAG:
                errors.append(
                    {
                        "path": ref,
                        "line": line_no,
                        "error": "protocolReleaseTag mismatch",
                        "expected": PROTOCOL_RELEASE_TAG,
                        "actual": item.get("protocolReleaseTag"),
                    }
                )
    return errors


def render_markdown(report: Dict[str, Any]) -> str:
    lines = [
        "# V3.0 Bundle Consistency Check",
        "",
        f"protocolReleaseTag: `{report['protocolReleaseTag']}`",
        f"checkedAt: `{report['checkedAt']}`",
        f"status: `{report['status']}`",
        "",
        f"errors: {report['summary']['errors']}",
        f"warnings: {report['summary']['warnings']}",
        f"checks: {report['summary']['checks']}",
        "",
        "## Checks",
        "",
    ]
    for check in report["checks"]:
        lines.append(f"- `{check['id']}`: **{check['status']}** — {check['message']}")
        details = check.get("details") or {}
        non_empty = {k: v for k, v in details.items() if v not in ([], {}, None, "")}
        if non_empty:
            lines.append("  - details: `" + json.dumps(non_empty, ensure_ascii=False, sort_keys=True) + "`")
    lines.append("")
    if report["summary"]["errors"] == 0 and report["summary"]["warnings"] == 0:
        lines.append("No blocking consistency issues detected by the automated lightweight checker.")
    else:
        lines.append("Consistency issues detected. Do not promote this bundle until all failures are resolved.")
    lines.append("")
    return "\n".join(lines)


def write_reports(root: Path | str, report: Dict[str, Any]) -> None:
    root = Path(root)
    (root / REPORT_JSON_PATH).write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (root / REPORT_MD_PATH).write_text(render_markdown(report), encoding="utf-8")


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=".", help="bundle root directory")
    parser.add_argument("--write-report", action="store_true", help="write markdown and JSON consistency reports")
    args = parser.parse_args(argv)

    root = Path(args.root).resolve()
    report = validate_bundle(root)
    if args.write_report:
        write_reports(root, report)
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 1 if report["summary"]["errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
