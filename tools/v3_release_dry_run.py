#!/usr/bin/env python3
"""Offline V3 release dry-run checker.

This script validates that the current Paperclip × Dark Factory V3.0 working tree
has enough local release evidence to support a human tag/release decision. It is
intentionally non-destructive: it never creates git tags, never pushes, and never
calls the GitHub Release API.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Sequence

ROOT = Path(__file__).resolve().parents[1]
TOOLS_DIR = ROOT / "tools"
for import_path in (ROOT, TOOLS_DIR):
    if str(import_path) not in sys.path:
        sys.path.insert(0, str(import_path))

DEFAULT_TAG = "v3.0.0-rc1"
DEFAULT_NOTES = "docs/v3_0_release_notes.md"
DEFAULT_CI_WORKFLOW = ".github/workflows/v3-contracts.yml"
PROTOCOL_RELEASE_TAG = "v3.0-agent-control-r1"
REQUIRED_NOTES_STRINGS = [
    "Paperclip × Dark Factory V3.0 Agent Control Runtime",
    "protocolReleaseTag",
    PROTOCOL_RELEASE_TAG,
    "make test-v3-contracts",
    "make validate-v3",
    "make smoke-v3-control-plane",
    "make verify-v3-journal JOURNAL=",
    "make release-readiness-v3",
    "release readiness",
    DEFAULT_CI_WORKFLOW,
]
IGNORED_GENERATED_STATUS_PREFIXES = (
    " M paperclip_darkfactory_v3_0_consistency_report.json",
    " M paperclip_darkfactory_v3_0_consistency_report.md",
    "?? dark_factory_v3/__pycache__/",
    "?? tests/__pycache__/",
    "?? tools/__pycache__/",
)


def stable_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


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
        "stdoutTail": result.stdout[-4000:],
        "stderrTail": result.stderr[-4000:],
    }


def make_check(check_id: str, status: str, message: str, *, details: dict[str, Any] | None = None) -> dict[str, Any]:
    payload: dict[str, Any] = {"id": check_id, "status": status, "message": message}
    if details:
        payload["details"] = details
    return payload


def git_head(root: Path) -> dict[str, Any]:
    branch = run_command(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=root)
    short = run_command(["git", "rev-parse", "--short", "HEAD"], cwd=root)
    full = run_command(["git", "rev-parse", "HEAD"], cwd=root)
    porcelain = run_command(["git", "status", "--porcelain"], cwd=root)
    status_lines = porcelain.stdout.splitlines() if porcelain.returncode == 0 else []
    releasable_status = [line for line in status_lines if not line.startswith(IGNORED_GENERATED_STATUS_PREFIXES)]
    return {
        "branch": branch.stdout.strip() if branch.returncode == 0 else None,
        "headCommit": short.stdout.strip() if short.returncode == 0 else None,
        "headCommitFull": full.stdout.strip() if full.returncode == 0 else None,
        "clean": porcelain.returncode == 0 and status_lines == [],
        "releaseDryRunClean": porcelain.returncode == 0 and releasable_status == [],
        "statusPorcelain": status_lines,
        "ignoredStatusPorcelain": [line for line in status_lines if line not in releasable_status],
        "releasableStatusPorcelain": releasable_status,
    }


def check_git_clean(git: dict[str, Any], *, require_clean: bool) -> dict[str, Any]:
    clean_key = "releaseDryRunClean"
    status_key = "releasableStatusPorcelain"
    ignored = git.get("ignoredStatusPorcelain", [])
    details = {
        "statusPorcelain": git.get("statusPorcelain", []),
        "releasableStatusPorcelain": git.get(status_key, []),
        "ignoredStatusPorcelain": ignored,
        "ignoredPatterns": [
            "paperclip_darkfactory_v3_0_consistency_report.json checkedAt-only changes",
            "paperclip_darkfactory_v3_0_consistency_report.md checkedAt-only changes",
            "dark_factory_v3/__pycache__/",
            "tests/__pycache__/",
            "tools/__pycache__/",
        ],
    }
    if require_clean and not git.get(clean_key):
        return make_check(
            "git.clean",
            "fail",
            "git working tree must have no releasable local changes for release dry-run",
            details=details,
        )
    if git.get(clean_key):
        message = "git working tree has no releasable local changes"
        if ignored:
            message += "; ignored generated artifacts are present"
        return make_check("git.clean", "pass", message, details=details)
    return make_check("git.clean", "warn", "git working tree has releasable local changes", details=details)


def resolve_repo_path(root: Path, rel_path: str) -> tuple[Path | None, dict[str, Any] | None]:
    path = (root / rel_path).resolve()
    try:
        path.relative_to(root.resolve())
    except ValueError:
        return None, {"path": str(path), "error": "path must stay inside repository"}
    return path, None


def check_release_notes(root: Path, notes: str, head_short: str | None) -> list[dict[str, Any]]:
    path, path_error = resolve_repo_path(root, notes)
    if path_error or path is None:
        return [
            make_check("release_notes.exists", "fail", "release notes path must stay inside the repository", details=path_error),
            make_check("release_notes.content", "skipped", "skipped because release notes path is invalid"),
        ]
    if not path.exists():
        return [
            make_check("release_notes.exists", "fail", f"release notes file is missing: {notes}", details={"path": notes}),
            make_check("release_notes.content", "skipped", "skipped because release notes file is missing"),
        ]
    content = path.read_text(encoding="utf-8")
    required = list(REQUIRED_NOTES_STRINGS)
    missing = [needle for needle in required if needle not in content]
    head_evidence = None
    if head_short:
        head_evidence = {
            "headCommit": head_short,
            "exactHeadPresent": head_short in content,
            "currentHeadMarkerPresent": "Current HEAD:" in content,
        }
        if not head_evidence["exactHeadPresent"] and not head_evidence["currentHeadMarkerPresent"]:
            missing.append(f"Current HEAD marker or exact short sha: {head_short}")
    details: dict[str, Any] = {"path": notes, "requiredStrings": required, "missingStrings": missing}
    if head_evidence:
        details["headEvidence"] = head_evidence
    return [
        make_check("release_notes.exists", "pass", "release notes file exists", details={"path": notes}),
        make_check(
            "release_notes.content",
            "pass" if not missing else "fail",
            "release notes contain required V3 release evidence" if not missing else "release notes are missing required V3 release evidence",
            details=details,
        ),
    ]


def check_release_readiness(root: Path, *, require_clean: bool) -> dict[str, Any]:
    try:
        import v3_release_readiness

        readiness_args = argparse.Namespace(
            root=str(root),
            require_clean_git=False,
            skip_slow=True,
            ci_workflow=DEFAULT_CI_WORKFLOW,
            json=True,
            output=None,
        )
        readiness = v3_release_readiness.build_report(readiness_args)
    except Exception as exc:
        return make_check("release_readiness.pass", "fail", str(exc), details={"errorType": type(exc).__name__})

    summary = readiness.get("summary", {})
    readiness_ok = readiness.get("ok") is True
    return make_check(
        "release_readiness.pass",
        "pass" if readiness_ok else "fail",
        "release readiness report passed" if readiness_ok else "release readiness report failed",
        details={
            "ok": readiness.get("ok"),
            "status": readiness.get("status"),
            "summary": summary,
            "git": readiness.get("git", {}),
            "cleanGitEnforcedByDryRun": require_clean,
        },
    )


def check_local_tag(root: Path, tag: str) -> dict[str, Any]:
    result = run_command(["git", "tag", "--list", tag], cwd=root)
    exists = result.returncode == 0 and result.stdout.strip() == tag
    if result.returncode != 0:
        return make_check("git.local_tag_available", "fail", "could not inspect local git tags", details=command_preview(result))
    return make_check(
        "git.local_tag_available",
        "fail" if exists else "pass",
        f"local tag already exists: {tag}" if exists else f"local tag is available: {tag}",
        details={"tag": tag, "exists": exists},
    )


def check_remote_tag(root: Path, tag: str) -> dict[str, Any]:
    result = run_command(["git", "ls-remote", "--tags", "--exit-code", "origin", tag], cwd=root, timeout=10)
    if result.returncode == 2:
        return make_check(
            "git.remote_tag_available",
            "pass",
            f"remote tag appears available: {tag}",
            details={"tag": tag, "exists": False, "stdout": result.stdout.strip()},
        )
    if result.returncode != 0:
        return make_check("git.remote_tag_available", "skipped", "remote tag check skipped because origin was unavailable", details=command_preview(result))
    exists = bool(result.stdout.strip())
    return make_check(
        "git.remote_tag_available",
        "warn" if exists else "pass",
        f"remote tag appears to exist: {tag}" if exists else f"remote tag appears available: {tag}",
        details={"tag": tag, "exists": exists, "stdout": result.stdout.strip()},
    )


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


def recommended_commands(tag: str, notes: str) -> list[str]:
    return [
        "make test-v3-contracts",
        "make validate-v3",
        "make release-readiness-v3",
        f"python3 tools/v3_release_dry_run.py --tag {tag} --notes {notes} --require-clean-git --output /tmp/v3-release-dry-run.json",
        f"git tag -a {tag} -m 'Paperclip × Dark Factory V3.0 Agent Control Runtime {tag}'",
        f"git push origin {tag}",
        "Create a GitHub Release manually from the checked release notes; do not include secrets.",
    ]


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    root = Path(args.root).resolve()
    tag = args.tag
    notes = args.notes
    git = git_head(root)
    checks: list[dict[str, Any]] = []
    checks.append(check_git_clean(git, require_clean=args.require_clean_git))
    checks.extend(check_release_notes(root, notes, git.get("headCommit")))
    checks.append(check_release_readiness(root, require_clean=args.require_clean_git))
    checks.append(check_local_tag(root, tag))
    if not args.skip_remote_tag_check:
        checks.append(check_remote_tag(root, tag))
    else:
        checks.append(make_check("git.remote_tag_available", "skipped", "remote tag check skipped by --skip-remote-tag-check", details={"tag": tag}))
    summary = summarize(checks)
    ok = summary["failed"] == 0
    return {
        "ok": ok,
        "status": "pass" if ok else "fail",
        "tag": tag,
        "notes": notes,
        "protocolReleaseTag": PROTOCOL_RELEASE_TAG,
        "dryRunOnly": True,
        "git": git,
        "checks": checks,
        "summary": summary,
        "recommendedCommands": recommended_commands(tag, notes),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=str(ROOT), help="repository root directory")
    parser.add_argument("--json", action="store_true", help="emit JSON output (default)")
    parser.add_argument("--tag", default=DEFAULT_TAG, help="candidate tag to check without creating it")
    parser.add_argument("--notes", default=DEFAULT_NOTES, help="release notes path to validate")
    parser.add_argument("--require-clean-git", action="store_true", help="fail if git status --porcelain is not clean")
    parser.add_argument("--output", help="write the full report to PATH while also printing JSON to stdout")
    parser.add_argument("--skip-remote-tag-check", action="store_true", help="skip optional remote tag availability check")
    args = parser.parse_args(argv)

    try:
        report = build_report(args)
    except Exception as exc:
        report = {
            "ok": False,
            "status": "fail",
            "tag": getattr(args, "tag", DEFAULT_TAG),
            "notes": getattr(args, "notes", DEFAULT_NOTES),
            "dryRunOnly": True,
            "git": {},
            "checks": [],
            "summary": {"checks": 0, "passed": 0, "failed": 1, "skipped": 0, "warnings": 0, "failedChecks": ["release_dry_run.unhandled_error"], "skippedChecks": [], "warningChecks": []},
            "recommendedCommands": [],
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
