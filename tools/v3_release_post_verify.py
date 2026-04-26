#!/usr/bin/env python3
"""Read-only Paperclip × Dark Factory V3.0 post-release verifier.

This verifier is for after an RC tag/release already exists. It never creates,
deletes, or pushes git tags and never calls a mutating GitHub API. GitHub checks
use only the public unauthenticated API and intentionally do not read or print
secrets or tokens.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Sequence

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TAG = "v3.0.0-rc1"
DEFAULT_REPO = "siyuah/123"
USER_AGENT = "paperclip-dark-factory-v3-post-release-verify"


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
    return {"returncode": result.returncode, "stdoutTail": result.stdout[-2000:], "stderrTail": result.stderr[-2000:]}


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


def parse_github_repo(remote_url: str) -> str | None:
    remote_url = remote_url.strip()
    patterns = [
        r"github\.com[:/](?P<owner>[^/]+)/(?P<repo>[^/.]+)(?:\.git)?$",
        r"https://github\.com/(?P<owner>[^/]+)/(?P<repo>[^/.]+)(?:\.git)?$",
    ]
    for pattern in patterns:
        match = re.search(pattern, remote_url)
        if match:
            return f"{match.group('owner')}/{match.group('repo')}"
    return None


def repo_from_origin(root: Path) -> tuple[str, dict[str, Any]]:
    result = run_command(["git", "remote", "get-url", "origin"], cwd=root, timeout=10)
    details = command_preview(result)
    if result.returncode == 0:
        repo = parse_github_repo(result.stdout)
        if repo:
            details["repo"] = repo
            return repo, details
    details["fallbackRepo"] = DEFAULT_REPO
    return DEFAULT_REPO, details


def current_head(root: Path) -> str:
    result = run_command(["git", "rev-parse", "HEAD"], cwd=root, timeout=10)
    if result.returncode != 0:
        raise RuntimeError(f"could not determine HEAD: {result.stderr.strip()}")
    return result.stdout.strip()


def check_git_clean(root: Path, *, require_clean_git: bool) -> tuple[dict[str, Any], dict[str, Any]]:
    branch = run_command(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=root, timeout=10)
    head = run_command(["git", "rev-parse", "HEAD"], cwd=root, timeout=10)
    porcelain = run_command(["git", "status", "--porcelain"], cwd=root, timeout=10)
    status_lines = porcelain.stdout.splitlines() if porcelain.returncode == 0 else []
    clean = porcelain.returncode == 0 and status_lines == []
    git = {
        "branch": branch.stdout.strip() if branch.returncode == 0 else None,
        "headSha": head.stdout.strip() if head.returncode == 0 else None,
        "clean": clean,
        "requireCleanGit": require_clean_git,
        "statusPorcelain": status_lines,
    }
    if porcelain.returncode != 0:
        return git, make_check("git.clean", "fail", "could not inspect git working tree", details=command_preview(porcelain))
    if clean:
        return git, make_check("git.clean", "pass", "git working tree is clean", details={"statusPorcelain": status_lines})
    status = "fail" if require_clean_git else "warn"
    message = "git working tree must be clean for strict post-release verification" if require_clean_git else "git working tree is not clean; continuing because --require-clean-git was not set"
    return git, make_check("git.clean", status, message, details={"statusPorcelain": status_lines})


def check_local_tag(root: Path, tag: str, expected_target: str) -> list[dict[str, Any]]:
    listed = run_command(["git", "tag", "--list", tag], cwd=root, timeout=10)
    exists = listed.returncode == 0 and listed.stdout.strip() == tag
    checks = [
        make_check(
            "git.local_tag_exists",
            "pass" if exists else "fail",
            f"local tag exists: {tag}" if exists else f"local tag is missing: {tag}",
            details={"tag": tag, "exists": exists, **({} if listed.returncode == 0 else {"command": command_preview(listed)})},
        )
    ]
    if not exists:
        checks.append(make_check("git.local_tag_target", "skipped", "skipped because local tag is missing", details={"tag": tag}))
        return checks

    tag_object = run_command(["git", "rev-parse", tag], cwd=root, timeout=10)
    peeled = run_command(["git", "rev-parse", f"{tag}^{{}}"], cwd=root, timeout=10)
    target = peeled.stdout.strip() if peeled.returncode == 0 else None
    ok = target == expected_target
    checks.append(
        make_check(
            "git.local_tag_target",
            "pass" if ok else "fail",
            f"local tag {tag} points to expected target" if ok else f"local tag {tag} points to unexpected target",
            details={
                "tag": tag,
                "tagObjectSha": tag_object.stdout.strip() if tag_object.returncode == 0 else None,
                "peeledTargetSha": target,
                "expectedTargetSha": expected_target,
            },
        )
    )
    return checks


def github_json(url: str, *, timeout: int) -> dict[str, Any]:
    request = urllib.request.Request(url, headers={"Accept": "application/vnd.github+json", "User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def fetch_github_json(url: str, *, timeout: int) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    try:
        return github_json(url, timeout=timeout), None
    except urllib.error.HTTPError as exc:
        return None, {"type": "HTTPError", "status": exc.code, "reason": exc.reason, "url": url}
    except urllib.error.URLError as exc:
        return None, {"type": "URLError", "reason": str(exc.reason), "url": url}
    except TimeoutError as exc:
        return None, {"type": "TimeoutError", "message": str(exc), "url": url}
    except Exception as exc:
        return None, {"type": type(exc).__name__, "message": str(exc), "url": url}


def check_github_tag_ref(repo: str, tag: str, expected_target: str, *, timeout: int) -> dict[str, Any]:
    ref_url = f"https://api.github.com/repos/{repo}/git/ref/tags/{tag}"
    ref_payload, ref_error = fetch_github_json(ref_url, timeout=timeout)
    if ref_error or ref_payload is None:
        return make_check("github.tag_ref", "fail", "GitHub public tag ref could not be read", details=ref_error)

    obj = ref_payload.get("object", {})
    target_sha = obj.get("sha")
    target_type = obj.get("type")
    tag_object_url = obj.get("url")
    annotated_target: str | None = None
    if target_type == "tag" and tag_object_url:
        tag_payload, tag_error = fetch_github_json(tag_object_url, timeout=timeout)
        if tag_error or tag_payload is None:
            return make_check("github.tag_ref", "fail", "GitHub annotated tag object could not be read", details=tag_error)
        annotated_target = tag_payload.get("object", {}).get("sha")
    effective_target = annotated_target or target_sha
    ok = ref_payload.get("ref") == f"refs/tags/{tag}" and effective_target == expected_target
    return make_check(
        "github.tag_ref",
        "pass" if ok else "fail",
        "GitHub public tag ref points to expected target" if ok else "GitHub public tag ref points to unexpected target",
        details={
            "repo": repo,
            "tag": tag,
            "ref": ref_payload.get("ref"),
            "objectType": target_type,
            "objectSha": target_sha,
            "peeledTargetSha": effective_target,
            "expectedTargetSha": expected_target,
        },
    )


def check_github_release(repo: str, tag: str, expected_target: str, *, timeout: int) -> dict[str, Any]:
    release_url = f"https://api.github.com/repos/{repo}/releases/tags/{tag}"
    payload, error = fetch_github_json(release_url, timeout=timeout)
    if error or payload is None:
        return make_check("github.release", "fail", "GitHub public release could not be read", details=error)
    ok = (
        payload.get("tag_name") == tag
        and payload.get("draft") is False
        and payload.get("prerelease") is True
        and payload.get("target_commitish") == expected_target
    )
    return make_check(
        "github.release",
        "pass" if ok else "fail",
        "GitHub public release matches expected RC1 state" if ok else "GitHub public release does not match expected RC1 state",
        details={
            "repo": repo,
            "tagName": payload.get("tag_name"),
            "targetCommitish": payload.get("target_commitish"),
            "expectedTargetSha": expected_target,
            "draft": payload.get("draft"),
            "prerelease": payload.get("prerelease"),
            "htmlUrl": payload.get("html_url"),
        },
    )


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    root = Path(args.root).resolve()
    expected_target = args.expected_target or current_head(root)
    repo, remote_details = repo_from_origin(root)
    git, git_check = check_git_clean(root, require_clean_git=args.require_clean_git)
    checks: list[dict[str, Any]] = [git_check]
    checks.extend(check_local_tag(root, args.tag, expected_target))
    checks.append(check_github_tag_ref(repo, args.tag, expected_target, timeout=args.timeout))
    checks.append(check_github_release(repo, args.tag, expected_target, timeout=args.timeout))
    summary = summarize(checks)
    ok = summary["failed"] == 0
    return {
        "ok": ok,
        "status": "pass" if ok else "fail",
        "postReleaseVerifyOnly": True,
        "tag": args.tag,
        "expectedTargetSha": expected_target,
        "repo": repo,
        "git": git,
        "origin": remote_details,
        "checks": checks,
        "summary": summary,
        "nonDestructiveGuarantees": [
            "does not create, delete, or move git tags",
            "does not push commits or tags",
            "does not create or modify GitHub Releases",
            "does not read or print tokens, secrets, or credentials",
            "uses GitHub public read-only API endpoints only",
        ],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=str(ROOT), help="repository root directory")
    parser.add_argument("--tag", default=DEFAULT_TAG, help="existing release tag to verify")
    parser.add_argument("--expected-target", help="expected peeled commit SHA for the release tag; defaults to current HEAD")
    parser.add_argument("--require-clean-git", action="store_true", help="fail when local working tree has uncommitted changes")
    parser.add_argument("--timeout", type=int, default=20, help="public GitHub API timeout in seconds")
    parser.add_argument("--output", help="write the full report to PATH while also printing JSON to stdout")
    parser.add_argument("--json", action="store_true", help="emit JSON output (default)")
    args = parser.parse_args(argv)

    try:
        report = build_report(args)
    except Exception as exc:
        report = {
            "ok": False,
            "status": "fail",
            "postReleaseVerifyOnly": True,
            "tag": getattr(args, "tag", DEFAULT_TAG),
            "expectedTargetSha": getattr(args, "expected_target", None),
            "checks": [],
            "summary": {"checks": 0, "passed": 0, "failed": 1, "skipped": 0, "warnings": 0, "failedChecks": ["post_release_verify.unhandled_error"], "skippedChecks": [], "warningChecks": []},
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
