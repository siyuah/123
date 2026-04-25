#!/usr/bin/env python3
"""Offline V3 release readiness gate.

Aggregates local git, bundle, runtime contract, smoke, journal verification, and CI
workflow presence checks into one stable JSON report. The script intentionally does
not require GitHub credentials or network access.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Sequence

ROOT = Path(__file__).resolve().parents[1]
TOOLS_DIR = ROOT / "tools"
for import_path in (ROOT, TOOLS_DIR):
    if str(import_path) not in sys.path:
        sys.path.insert(0, str(import_path))

REQUIRED_WORKFLOW_STRINGS = [
    "workflow_dispatch",
    "actions/setup-python",
    "make test-v3-contracts",
    "make validate-v3",
    "make smoke-v3-control-plane",
    "make verify-v3-journal",
    "actions/upload-artifact",
]


def stable_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def run_command(args: Sequence[str], *, cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        list(args),
        cwd=cwd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def make_check(
    check_id: str,
    status: str,
    message: str,
    *,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {"id": check_id, "status": status, "message": message}
    if details:
        payload["details"] = details
    return payload


def command_preview(result: subprocess.CompletedProcess[str]) -> dict[str, Any]:
    return {
        "returncode": result.returncode,
        "stdoutTail": result.stdout[-4000:],
        "stderrTail": result.stderr[-4000:],
    }


def git_info(root: Path) -> dict[str, Any]:
    branch_result = run_command(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=root)
    head_result = run_command(["git", "rev-parse", "--short", "HEAD"], cwd=root)
    porcelain = run_command(["git", "status", "--porcelain"], cwd=root)
    clean = porcelain.returncode == 0 and porcelain.stdout == ""
    info: dict[str, Any] = {
        "branch": branch_result.stdout.strip() if branch_result.returncode == 0 else None,
        "headCommit": head_result.stdout.strip() if head_result.returncode == 0 else None,
        "clean": clean,
    }
    if porcelain.returncode == 0:
        info["statusPorcelain"] = porcelain.stdout.splitlines()
    else:
        info["error"] = command_preview(porcelain)
    return info


def check_git_clean(root: Path, *, require_clean: bool) -> tuple[dict[str, Any], dict[str, Any]]:
    info = git_info(root)
    if require_clean and not info.get("clean"):
        return info, make_check(
            "git.clean",
            "fail",
            "git working tree must be clean for release readiness",
            details={"statusPorcelain": info.get("statusPorcelain", [])},
        )
    return info, make_check(
        "git.clean",
        "pass" if info.get("clean") else "warn",
        "git working tree is clean" if info.get("clean") else "git working tree has local changes",
        details={"statusPorcelain": info.get("statusPorcelain", [])},
    )


def check_bundle(root: Path) -> dict[str, Any]:
    try:
        from validate_v3_bundle import validate_bundle

        report = validate_bundle(root)
    except Exception as exc:  # stable JSON; no traceback for normal users
        return make_check("bundle.validate", "fail", str(exc), details={"errorType": type(exc).__name__})
    errors = int(report.get("summary", {}).get("errors", 0))
    warnings = int(report.get("summary", {}).get("warnings", 0))
    status = "pass" if errors == 0 else "fail"
    return make_check(
        "bundle.validate",
        status,
        "V3 manifest and bundle validation passed" if status == "pass" else "V3 manifest and bundle validation failed",
        details={
            "bundleStatus": report.get("status"),
            "errors": errors,
            "warnings": warnings,
            "checks": int(report.get("summary", {}).get("checks", 0)),
        },
    )


def check_unit_contracts(root: Path, *, skip_slow: bool) -> dict[str, Any]:
    if skip_slow:
        return make_check("unit.contracts", "skipped", "skipped because --skip-slow was provided")
    result = run_command([sys.executable, "-m", "unittest", "discover", "-s", "tests", "-p", "test_v3_*.py"], cwd=root)
    return make_check(
        "unit.contracts",
        "pass" if result.returncode == 0 else "fail",
        "V3 contract unit tests passed" if result.returncode == 0 else "V3 contract unit tests failed",
        details=command_preview(result),
    )


def check_smoke_and_verify(root: Path, *, skip_slow: bool) -> tuple[dict[str, Any], dict[str, Any]]:
    if skip_slow:
        skipped_smoke = make_check("control_plane.smoke", "skipped", "skipped because --skip-slow was provided")
        skipped_verify = make_check("journal.verify", "skipped", "skipped because --skip-slow was provided")
        return skipped_smoke, skipped_verify

    with tempfile.TemporaryDirectory(prefix="v3-release-readiness-") as tmpdir:
        journal = Path(tmpdir) / "smoke.jsonl"
        smoke_result = run_command([sys.executable, str(root / "tools/v3_control_plane_smoke.py"), "--journal", str(journal)], cwd=root)
        smoke_details = command_preview(smoke_result)
        try:
            smoke_payload = json.loads(smoke_result.stdout) if smoke_result.stdout.strip() else {}
        except json.JSONDecodeError as exc:
            smoke_payload = {"jsonError": str(exc)}
        smoke_details["payload"] = smoke_payload
        smoke_ok = smoke_result.returncode == 0 and smoke_payload.get("ok") is True and journal.exists()
        smoke_check = make_check(
            "control_plane.smoke",
            "pass" if smoke_ok else "fail",
            "control-plane smoke produced a valid journal" if smoke_ok else "control-plane smoke failed",
            details=smoke_details,
        )
        if not smoke_ok:
            return smoke_check, make_check("journal.verify", "skipped", "skipped because control-plane smoke did not pass")

        try:
            from v3_control_plane import JournalVerificationError, verify_journal_payload

            verify_payload = verify_journal_payload(journal)
            verify_ok = verify_payload.get("ok") is True and all(check.get("status") == "pass" for check in verify_payload.get("checks", []))
            verify_check = make_check(
                "journal.verify",
                "pass" if verify_ok else "fail",
                "smoke journal verification passed" if verify_ok else "smoke journal verification failed",
                details={
                    "events": verify_payload.get("events"),
                    "checkIds": verify_payload.get("checkIds", []),
                    "projectionSummary": verify_payload.get("projectionSummary", {}),
                },
            )
        except JournalVerificationError as exc:
            verify_check = make_check("journal.verify", "fail", exc.message, details={"error": exc.to_dict()})
        except Exception as exc:
            verify_check = make_check("journal.verify", "fail", str(exc), details={"errorType": type(exc).__name__})
        return smoke_check, verify_check


def check_ci_workflow(root: Path, workflow: str) -> dict[str, Any]:
    workflow_path = (root / workflow).resolve()
    try:
        workflow_path.relative_to(root.resolve())
    except ValueError:
        return make_check("ci.workflow_presence", "fail", "CI workflow path must stay inside the repository", details={"path": str(workflow_path)})
    if not workflow_path.exists():
        return make_check("ci.workflow_presence", "fail", f"CI workflow is missing: {workflow}", details={"path": workflow})
    content = workflow_path.read_text(encoding="utf-8")
    missing = [needle for needle in REQUIRED_WORKFLOW_STRINGS if needle not in content]
    return make_check(
        "ci.workflow_presence",
        "pass" if not missing else "fail",
        "V3 contracts CI workflow contains required gates" if not missing else "V3 contracts CI workflow is missing required gates",
        details={"path": workflow, "requiredStrings": REQUIRED_WORKFLOW_STRINGS, "missingStrings": missing},
    )


def summarize(checks: list[dict[str, Any]]) -> dict[str, Any]:
    failed = [check["id"] for check in checks if check["status"] == "fail"]
    skipped = [check["id"] for check in checks if check["status"] == "skipped"]
    passed = [check["id"] for check in checks if check["status"] == "pass"]
    warned = [check["id"] for check in checks if check["status"] == "warn"]
    return {
        "checks": len(checks),
        "passed": len(passed),
        "failed": len(failed),
        "skipped": len(skipped),
        "warnings": len(warned),
        "failedChecks": failed,
        "skippedChecks": skipped,
        "warningChecks": warned,
    }


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    root = Path(args.root).resolve()
    checks: list[dict[str, Any]] = []
    git, git_check = check_git_clean(root, require_clean=args.require_clean_git)
    checks.append(git_check)
    checks.append(check_bundle(root))
    checks.append(check_unit_contracts(root, skip_slow=args.skip_slow))
    smoke_check, verify_check = check_smoke_and_verify(root, skip_slow=args.skip_slow)
    checks.extend([smoke_check, verify_check])
    checks.append(check_ci_workflow(root, args.ci_workflow))
    summary = summarize(checks)
    ok = summary["failed"] == 0
    return {
        "ok": ok,
        "status": "pass" if ok else "fail",
        "git": git,
        "checks": checks,
        "summary": summary,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=str(ROOT), help="repository root directory")
    parser.add_argument("--json", action="store_true", help="emit JSON output (default)")
    parser.add_argument("--output", help="write the full report to PATH while also printing JSON to stdout")
    parser.add_argument("--skip-slow", action="store_true", help="skip slower unit/smoke/journal checks and mark them skipped")
    parser.add_argument("--require-clean-git", action="store_true", help="fail if git status --porcelain is not clean")
    parser.add_argument("--ci-workflow", default=".github/workflows/v3-contracts.yml", help="path to the V3 contracts CI workflow")
    args = parser.parse_args(argv)

    try:
        report = build_report(args)
    except Exception as exc:  # final guardrail: stable JSON, no traceback
        report = {
            "ok": False,
            "status": "fail",
            "git": {},
            "checks": [],
            "summary": {"checks": 0, "passed": 0, "failed": 1, "skipped": 0, "warnings": 0, "failedChecks": ["release_readiness.unhandled_error"], "skippedChecks": [], "warningChecks": []},
            "error": {"type": type(exc).__name__, "message": str(exc)},
        }

    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        report["outputPath"] = str(output_path)
        output_path.write_text(stable_json(report), encoding="utf-8")

    sys.stdout.write(stable_json(report))
    return 0 if report.get("ok") is True else 1


if __name__ == "__main__":
    raise SystemExit(main())
