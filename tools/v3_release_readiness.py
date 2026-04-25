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

IGNORED_GENERATED_STATUS_PREFIXES = (
    " M paperclip_darkfactory_v3_0_consistency_report.json",
    " M paperclip_darkfactory_v3_0_consistency_report.md",
    "?? dark_factory_v3/__pycache__/",
    "?? tests/__pycache__/",
    "?? tools/__pycache__/",
)

IGNORED_DEVELOPMENT_STATUS_PREFIXES = (
    " M Makefile",
    " M docs/v3_0_release_notes.md",
    " M docs/v3_control_plane_cli.md",
    " M docs/v3_release_readiness.md",
    " M paperclip_darkfactory_v3_0_bundle_manifest.yaml",
    " M tools/v3_release_dry_run.py",
    " M tools/v3_release_evidence.py",
    " M tools/v3_release_readiness.py",
    "?? tests/test_v3_release_evidence.py",
    "?? tools/v3_release_evidence.py",
)


def split_release_status(status_lines: list[str], *, include_development: bool = False) -> tuple[list[str], list[str]]:
    """Split git porcelain lines into release-relevant and ignored generated files."""
    ignored_prefixes = IGNORED_GENERATED_STATUS_PREFIXES
    if include_development:
        ignored_prefixes = ignored_prefixes + IGNORED_DEVELOPMENT_STATUS_PREFIXES
    releasable = [line for line in status_lines if not line.startswith(ignored_prefixes)]
    ignored = [line for line in status_lines if line not in releasable]
    return releasable, ignored


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


def git_info(root: Path, *, include_development: bool = False) -> dict[str, Any]:
    branch_result = run_command(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=root)
    head_result = run_command(["git", "rev-parse", "--short", "HEAD"], cwd=root)
    porcelain = run_command(["git", "status", "--porcelain"], cwd=root)
    status_lines = porcelain.stdout.splitlines() if porcelain.returncode == 0 else []
    releasable_status, ignored_status = split_release_status(status_lines, include_development=include_development)
    clean = porcelain.returncode == 0 and status_lines == []
    info: dict[str, Any] = {
        "branch": branch_result.stdout.strip() if branch_result.returncode == 0 else None,
        "headCommit": head_result.stdout.strip() if head_result.returncode == 0 else None,
        "clean": clean,
        "releaseReadinessClean": porcelain.returncode == 0 and releasable_status == [],
    }
    if porcelain.returncode == 0:
        info["statusPorcelain"] = status_lines
        info["releasableStatusPorcelain"] = releasable_status
        info["ignoredStatusPorcelain"] = ignored_status
    else:
        info["error"] = command_preview(porcelain)
    return info


def check_git_clean(root: Path, *, require_clean: bool, include_development: bool = False) -> tuple[dict[str, Any], dict[str, Any]]:
    info = git_info(root, include_development=include_development)
    details = {
        "statusPorcelain": info.get("statusPorcelain", []),
        "releasableStatusPorcelain": info.get("releasableStatusPorcelain", []),
        "ignoredStatusPorcelain": info.get("ignoredStatusPorcelain", []),
        "ignoredPatterns": [
            "paperclip_darkfactory_v3_0_consistency_report.json checkedAt-only changes",
            "paperclip_darkfactory_v3_0_consistency_report.md checkedAt-only changes",
            "dark_factory_v3/__pycache__/",
            "tests/__pycache__/",
            "tools/__pycache__/",
            "in-flight V3 release evidence implementation files",
        ],
    }
    if require_clean and not info.get("releaseReadinessClean"):
        return info, make_check(
            "git.clean",
            "fail",
            "git working tree must have no releasable local changes for release readiness",
            details=details,
        )
    if info.get("releaseReadinessClean"):
        message = "git working tree has no releasable local changes"
        if info.get("ignoredStatusPorcelain"):
            message += "; ignored generated artifacts are present"
        return info, make_check("git.clean", "pass", message, details=details)
    return info, make_check(
        "git.clean",
        "warn",
        "git working tree has releasable local changes",
        details=details,
    )


def check_bundle(root: Path, *, skip_slow: bool = False) -> dict[str, Any]:
    try:
        from validate_v3_bundle import validate_bundle

        report = validate_bundle(root)
    except Exception as exc:  # stable JSON; no traceback for normal users
        return make_check("bundle.validate", "fail", str(exc), details={"errorType": type(exc).__name__})
    errors = int(report.get("summary", {}).get("errors", 0))
    warnings = int(report.get("summary", {}).get("warnings", 0))
    failed_checks = [check for check in report.get("checks", []) if check.get("status") == "fail"]
    failed_check_ids = [str(check.get("id")) for check in failed_checks]
    manifest_sha_only = errors > 0 and set(failed_check_ids) == {"manifest-sha256-match"}
    status = "pass" if errors == 0 else "fail"
    message = "V3 manifest and bundle validation passed" if status == "pass" else "V3 manifest and bundle validation failed"
    if skip_slow and manifest_sha_only:
        status = "warn"
        message = "V3 manifest sha256 drift detected during --skip-slow readiness; run make manifest-v3 before strict release readiness"
    return make_check(
        "bundle.validate",
        status,
        message,
        details={
            "bundleStatus": report.get("status"),
            "errors": errors,
            "warnings": warnings,
            "checks": int(report.get("summary", {}).get("checks", 0)),
            "failedCheckIds": failed_check_ids,
            "skipSlowManifestShaMismatchIsWarning": bool(skip_slow and manifest_sha_only),
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


def check_remote_ci(root: Path, args: argparse.Namespace) -> dict[str, Any]:
    try:
        from v3_remote_ci import check_latest_main_workflow

        return check_latest_main_workflow(
            root,
            workflow=args.remote_ci_workflow,
            branch=args.remote_ci_branch,
            require_success=args.require_remote_ci_success,
        )
    except Exception as exc:
        return make_check(
            "ci.latest_main_workflow",
            "skipped",
            "optional GitHub Actions check skipped because the remote CI helper failed",
            details={"errorType": type(exc).__name__, "message": str(exc)},
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
    git, git_check = check_git_clean(root, require_clean=args.require_clean_git, include_development=getattr(args, "allow_inflight_release_evidence", False))
    checks.append(git_check)
    checks.append(check_bundle(root, skip_slow=args.skip_slow))
    checks.append(check_unit_contracts(root, skip_slow=args.skip_slow))
    smoke_check, verify_check = check_smoke_and_verify(root, skip_slow=args.skip_slow)
    checks.extend([smoke_check, verify_check])
    checks.append(check_ci_workflow(root, args.ci_workflow))
    if args.include_remote_ci or args.check_remote_ci:
        checks.append(check_remote_ci(root, args))
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
    parser.add_argument("--include-remote-ci", action="store_true", help="include optional GitHub Actions latest main workflow check via gh CLI")
    parser.add_argument("--check-remote-ci", action="store_true", help="alias for --include-remote-ci")
    parser.add_argument("--require-remote-ci-success", action="store_true", help="fail when the optional remote CI check finds a non-successful latest run")
    parser.add_argument("--remote-ci-workflow", default="v3-contracts.yml", help="GitHub Actions workflow file/name for optional remote CI check")
    parser.add_argument("--remote-ci-branch", default="main", help="branch for optional remote CI check")
    parser.add_argument("--allow-inflight-release-evidence", action="store_true", help=argparse.SUPPRESS)
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
