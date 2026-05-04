#!/usr/bin/env python3
"""Build an auditable Paperclip × Dark Factory V3.0 RC evidence package.

The evidence package is intentionally non-destructive: it never creates git tags,
never pushes, and never calls the GitHub Release API. Remote CI inspection is
offline by default and only attempted when --include-remote-ci is supplied.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

ROOT = Path(__file__).resolve().parents[1]
TOOLS_DIR = ROOT / "tools"
for import_path in (ROOT, TOOLS_DIR):
    if str(import_path) not in sys.path:
        sys.path.insert(0, str(import_path))

DEFAULT_TAG = "v3.0.0-rc1"
DEFAULT_NOTES = "docs/v3_0_release_notes.md"
DEFAULT_BUNDLE_MANIFEST = "paperclip_darkfactory_v3_0_bundle_manifest.yaml"
DEFAULT_CONSISTENCY_REPORT = "paperclip_darkfactory_v3_0_consistency_report.json"
DEFAULT_CONSISTENCY_REPORT_MD = "paperclip_darkfactory_v3_0_consistency_report.md"
DEFAULT_CI_WORKFLOW = ".github/workflows/v3-contracts.yml"
PROTOCOL_RELEASE_TAG = "v3.0-agent-control-r1"
IGNORED_GENERATED_STATUS_PREFIXES = (
    " M paperclip_darkfactory_v3_0_consistency_report.json",
    " M paperclip_darkfactory_v3_0_consistency_report.md",
    "?? __pycache__/",
    "?? dark_factory_v3/__pycache__/",
    "?? tests/__pycache__/",
    "?? tools/__pycache__/",
    "!! __pycache__/",
    "!! dark_factory_v3/__pycache__/",
    "!! tests/__pycache__/",
    "!! tools/__pycache__/",
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
    " M tests/test_v3_release_dry_run.py",
    " M tests/test_v3_release_dry_run_remote_ci.py",
    " M tests/test_v3_release_evidence.py",
    "?? tests/test_v3_release_post_verify.py",
    "?? tools/v3_release_post_verify.py",
    "?? tests/test_v3_release_evidence.py",
    "?? tools/v3_release_evidence.py",
)


def stable_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def run_command(args: Sequence[str], *, cwd: Path, timeout: int | None = None) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            list(args),
            cwd=cwd,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as exc:
        return subprocess.CompletedProcess(
            list(args),
            124,
            stdout=exc.stdout or "",
            stderr=(exc.stderr or "") + f"\ncommand timed out after {timeout}s",
        )


def command_preview(result: subprocess.CompletedProcess[str]) -> dict[str, Any]:
    return {
        "returncode": result.returncode,
        "stdoutTail": result.stdout[-2000:],
        "stderrTail": result.stderr[-2000:],
    }


def make_check(check_id: str, status: str, message: str, *, details: dict[str, Any] | None = None) -> dict[str, Any]:
    payload: dict[str, Any] = {"id": check_id, "status": status, "message": message}
    if details:
        payload["details"] = details
    return payload


def summarize(checks: list[dict[str, Any]]) -> dict[str, Any]:
    failed = [check["id"] for check in checks if check["status"] == "fail"]
    skipped = [check["id"] for check in checks if check["status"] == "skipped"]
    warned = [check["id"] for check in checks if check["status"] == "warn"]
    passed = [check["id"] for check in checks if check["status"] == "pass"]
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


def resolve_repo_path(root: Path, rel_path: str) -> tuple[Path | None, dict[str, Any] | None]:
    path = (root / rel_path).resolve()
    try:
        path.relative_to(root.resolve())
    except ValueError:
        return None, {"path": str(path), "error": "path must stay inside repository"}
    return path, None


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def artifact(root: Path, rel_path: str, role: str) -> tuple[dict[str, Any], dict[str, Any]]:
    path, path_error = resolve_repo_path(root, rel_path)
    if path_error or path is None:
        item = {"path": rel_path, "role": role, "exists": False, "error": path_error}
        return item, make_check(f"artifact.{role}", "fail", f"artifact path is invalid: {rel_path}", details=item)
    if not path.exists() or not path.is_file():
        item = {"path": rel_path, "role": role, "exists": False}
        return item, make_check(f"artifact.{role}", "fail", f"artifact is missing: {rel_path}", details=item)
    item = {
        "path": rel_path,
        "role": role,
        "exists": True,
        "sha256": file_sha256(path),
        "sizeBytes": path.stat().st_size,
    }
    return item, make_check(f"artifact.{role}", "pass", f"artifact captured: {rel_path}", details=item)


def git_head(root: Path) -> dict[str, Any]:
    branch = run_command(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=root)
    short = run_command(["git", "rev-parse", "--short", "HEAD"], cwd=root)
    full = run_command(["git", "rev-parse", "HEAD"], cwd=root)
    porcelain = run_command(["git", "status", "--porcelain"], cwd=root)
    status_lines = porcelain.stdout.splitlines() if porcelain.returncode == 0 else []
    ignored_porcelain = run_command(["git", "status", "--porcelain", "--ignored=matching"], cwd=root)
    ignored_status_lines = [
        line
        for line in (ignored_porcelain.stdout.splitlines() if ignored_porcelain.returncode == 0 else [])
        if line.startswith("!! ") and line.startswith(IGNORED_GENERATED_STATUS_PREFIXES)
    ]
    releasable_status = [
        line
        for line in status_lines
        if not line.startswith(IGNORED_GENERATED_STATUS_PREFIXES) and not line.startswith(IGNORED_DEVELOPMENT_STATUS_PREFIXES)
    ]
    return {
        "branch": branch.stdout.strip() if branch.returncode == 0 else None,
        "headSha": full.stdout.strip() if full.returncode == 0 else None,
        "headShortSha": short.stdout.strip() if short.returncode == 0 else None,
        "clean": porcelain.returncode == 0 and status_lines == [],
        "releaseEvidenceClean": porcelain.returncode == 0 and releasable_status == [],
        "statusPorcelain": status_lines,
        "ignoredStatusPorcelain": [line for line in status_lines if line not in releasable_status] + ignored_status_lines,
        "releasableStatusPorcelain": releasable_status,
    }


def check_git_clean(git: dict[str, Any], *, require_clean: bool) -> dict[str, Any]:
    details = {
        "statusPorcelain": git.get("statusPorcelain", []),
        "releasableStatusPorcelain": git.get("releasableStatusPorcelain", []),
        "ignoredStatusPorcelain": git.get("ignoredStatusPorcelain", []),
        "ignoredPatterns": [
            "paperclip_darkfactory_v3_0_consistency_report.json checkedAt-only changes",
            "paperclip_darkfactory_v3_0_consistency_report.md checkedAt-only changes",
            "__pycache__/",
            "dark_factory_v3/__pycache__/",
            "tests/__pycache__/",
            "tools/__pycache__/",
            "in-flight V3 release evidence implementation files",
        ],
    }
    if require_clean and not git.get("releaseEvidenceClean"):
        return make_check(
            "git.clean",
            "fail",
            "git working tree must have no releasable local changes for release evidence",
            details=details,
        )
    if git.get("releaseEvidenceClean"):
        message = "git working tree has no releasable local changes"
        if git.get("ignoredStatusPorcelain"):
            message += "; ignored generated or in-flight artifacts are present"
        return make_check("git.clean", "pass", message, details=details)
    return make_check("git.clean", "warn", "git working tree has releasable local changes", details=details)


def compact_report(report: dict[str, Any], *, include_generated: bool) -> dict[str, Any]:
    compact = {
        "ok": report.get("ok"),
        "status": report.get("status"),
        "summary": report.get("summary", {}),
        "checks": report.get("checks", []),
    }
    if include_generated:
        compact["report"] = report
    return compact


def build_readiness(root: Path, *, include_generated: bool) -> tuple[dict[str, Any], dict[str, Any]]:
    try:
        import v3_release_readiness

        readiness_args = argparse.Namespace(
            root=str(root),
            require_clean_git=False,
            skip_slow=True,
            ci_workflow=DEFAULT_CI_WORKFLOW,
            include_remote_ci=False,
            check_remote_ci=False,
            require_remote_ci_success=False,
            remote_ci_workflow="v3-contracts.yml",
            remote_ci_branch="main",
            json=True,
            output=None,
        )
        report = v3_release_readiness.build_report(readiness_args)
    except Exception as exc:
        failed = {"ok": False, "status": "fail", "summary": {}, "checks": [], "error": {"type": type(exc).__name__, "message": str(exc)}}
        return failed, make_check("readiness.pass", "fail", "could not build release readiness evidence", details=failed)
    check = make_check(
        "readiness.pass",
        "pass" if report.get("ok") is True else "fail",
        "release readiness evidence passed" if report.get("ok") is True else "release readiness evidence failed",
        details={"summary": report.get("summary", {})},
    )
    return compact_report(report, include_generated=include_generated), check


def build_dry_run(root: Path, tag: str, notes: str, *, include_remote_ci: bool, require_remote_ci_success: bool, include_generated: bool) -> tuple[dict[str, Any], dict[str, Any]]:
    try:
        import v3_release_dry_run

        dry_args = argparse.Namespace(
            root=str(root),
            tag=tag,
            notes=notes,
            require_clean_git=False,
            output=None,
            skip_remote_tag_check=True,
            include_remote_ci=include_remote_ci,
            check_remote_ci=False,
            require_remote_ci_success=require_remote_ci_success,
            remote_ci_workflow="v3-contracts.yml",
            remote_ci_branch="main",
            json=True,
        )
        report = v3_release_dry_run.build_report(dry_args)
    except Exception as exc:
        failed = {"ok": False, "status": "fail", "summary": {}, "checks": [], "error": {"type": type(exc).__name__, "message": str(exc)}}
        return failed, make_check("dry_run.pass", "fail", "could not build release dry-run evidence", details=failed)
    check = make_check(
        "dry_run.pass",
        "pass" if report.get("ok") is True else "fail",
        "release dry-run evidence passed" if report.get("ok") is True else "release dry-run evidence failed",
        details={"summary": report.get("summary", {})},
    )
    return compact_report(report, include_generated=include_generated), check


def remote_ci_check(root: Path, args: argparse.Namespace) -> dict[str, Any] | None:
    if not args.include_remote_ci:
        return None
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


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    root = Path(args.root).resolve()
    git = git_head(root)
    artifacts: list[dict[str, Any]] = []
    checks: list[dict[str, Any]] = []

    checks.append(check_git_clean(git, require_clean=args.require_clean_git))

    artifact_specs = [
        (args.notes, "release_notes"),
        (DEFAULT_BUNDLE_MANIFEST, "bundle_manifest"),
        (DEFAULT_CONSISTENCY_REPORT, "consistency_report_json"),
        (DEFAULT_CONSISTENCY_REPORT_MD, "consistency_report_markdown"),
        (DEFAULT_CI_WORKFLOW, "ci_workflow"),
    ]
    for rel_path, role in artifact_specs:
        item, check = artifact(root, rel_path, role)
        artifacts.append(item)
        checks.append(check)

    readiness, readiness_check = build_readiness(root, include_generated=args.include_generated_reports)
    dry_run, dry_run_check = build_dry_run(
        root,
        args.tag,
        args.notes,
        include_remote_ci=args.include_remote_ci,
        require_remote_ci_success=args.require_remote_ci_success,
        include_generated=args.include_generated_reports,
    )
    checks.extend([readiness_check, dry_run_check])

    remote_check = remote_ci_check(root, args)
    if remote_check is not None:
        checks.append(remote_check)

    summary = summarize(checks)
    ok = summary["failed"] == 0
    release_notes = next((item for item in artifacts if item["role"] == "release_notes"), {})
    bundle_manifest = next((item for item in artifacts if item["role"] == "bundle_manifest"), {})
    consistency_report = next((item for item in artifacts if item["role"] == "consistency_report_json"), {})

    return {
        "ok": ok,
        "status": "pass" if ok else "fail",
        "checkedAt": now_utc(),
        "protocolReleaseTag": PROTOCOL_RELEASE_TAG,
        "tag": args.tag,
        "headSha": git.get("headSha"),
        "headShortSha": git.get("headShortSha"),
        "branch": git.get("branch"),
        "releaseNotesPath": args.notes,
        "releaseNotesSha256": release_notes.get("sha256"),
        "bundleManifestPath": DEFAULT_BUNDLE_MANIFEST,
        "bundleManifestSha256": bundle_manifest.get("sha256"),
        "consistencyReportPath": DEFAULT_CONSISTENCY_REPORT,
        "consistencyReportSha256": consistency_report.get("sha256"),
        "git": git,
        "artifacts": artifacts,
        "readiness": readiness,
        "dryRun": dry_run,
        "checks": checks,
        "summary": summary,
        "evidenceOnly": True,
        "nonDestructiveGuarantees": [
            "does not create git tags",
            "does not push commits or tags",
            "does not call GitHub Release API",
            "does not print secrets",
            "remote CI is optional and disabled by default",
        ],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=str(ROOT), help="repository root directory")
    parser.add_argument("--tag", default=DEFAULT_TAG, help="candidate tag for the evidence package")
    parser.add_argument("--notes", default=DEFAULT_NOTES, help="release notes path to include")
    parser.add_argument("--output", help="write the full evidence JSON to PATH while also printing JSON to stdout")
    parser.add_argument("--require-clean-git", action="store_true", help="fail if releasable git changes are present")
    parser.add_argument("--include-remote-ci", action="store_true", help="include optional GitHub Actions latest main workflow check via gh CLI")
    parser.add_argument("--include-generated-reports", action="store_true", help="embed full generated readiness and dry-run reports")
    parser.add_argument("--require-remote-ci-success", action="store_true", help="fail when optional remote CI finds a non-successful latest run")
    parser.add_argument("--remote-ci-workflow", default="v3-contracts.yml", help="GitHub Actions workflow file/name for optional remote CI check")
    parser.add_argument("--remote-ci-branch", default="main", help="branch for optional remote CI check")
    args = parser.parse_args(argv)

    try:
        report = build_report(args)
    except Exception as exc:
        report = {
            "ok": False,
            "status": "fail",
            "checkedAt": now_utc(),
            "protocolReleaseTag": PROTOCOL_RELEASE_TAG,
            "tag": getattr(args, "tag", DEFAULT_TAG),
            "checks": [],
            "summary": {"checks": 0, "passed": 0, "failed": 1, "skipped": 0, "warnings": 0, "failedChecks": ["release_evidence.unhandled_error"], "skippedChecks": [], "warningChecks": []},
            "error": {"type": type(exc).__name__, "message": str(exc)},
            "evidenceOnly": True,
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
