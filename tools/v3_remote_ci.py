#!/usr/bin/env python3
"""Optional GitHub Actions status checks for V3 release gates.

This helper is intentionally optional and best-effort: it uses the gh CLI when
available, never requires secrets, and never turns local/offline release checks
into network-dependent gates unless strict mode is requested by the caller.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any, Sequence

CHECK_ID = "ci.latest_main_workflow"
DEFAULT_BRANCH = "main"
DEFAULT_WORKFLOW = "v3-contracts.yml"
TERMINAL_UNSUCCESSFUL_CONCLUSIONS = {
    "action_required",
    "cancelled",
    "failure",
    "neutral",
    "skipped",
    "stale",
    "startup_failure",
    "timed_out",
}


def make_check(check_id: str, status: str, message: str, *, details: dict[str, Any] | None = None) -> dict[str, Any]:
    payload: dict[str, Any] = {"id": check_id, "status": status, "message": message}
    if details:
        payload["details"] = details
    return payload


def run_command(args: Sequence[str], *, cwd: Path, timeout: int = 15) -> subprocess.CompletedProcess[str]:
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


def base_details(workflow: str, branch: str) -> dict[str, Any]:
    return {"workflow": workflow, "branch": branch}


def check_latest_main_workflow(
    root: Path,
    *,
    workflow: str = DEFAULT_WORKFLOW,
    branch: str = DEFAULT_BRANCH,
    require_success: bool = False,
    timeout: int = 15,
) -> dict[str, Any]:
    """Return a stable release-gate check for the latest GitHub Actions run.

    The check is skipped when gh is missing, gh auth is unavailable, the command
    times out, network access fails, or no run exists. A completed non-successful
    run is a warning by default and a failure only in strict mode.
    """
    details = base_details(workflow, branch)
    gh_bin = os.environ.get("V3_REMOTE_CI_GH_BIN") or shutil.which("gh")
    if gh_bin is None or not Path(gh_bin).exists():
        return make_check(
            CHECK_ID,
            "skipped",
            "optional GitHub Actions check skipped because gh CLI is not available",
            details=details,
        )

    auth = run_command([gh_bin, "auth", "status"], cwd=root, timeout=timeout)
    if auth.returncode != 0:
        auth_details = dict(details)
        auth_details["auth"] = command_preview(auth)
        return make_check(
            CHECK_ID,
            "skipped",
            "optional GitHub Actions check skipped because gh auth status failed",
            details=auth_details,
        )

    result = run_command(
        [
            gh_bin,
            "run",
            "list",
            "--branch",
            branch,
            "--workflow",
            workflow,
            "--limit",
            "1",
            "--json",
            "status,conclusion,headSha,url,displayTitle,createdAt",
        ],
        cwd=root,
        timeout=timeout,
    )
    if result.returncode != 0:
        run_details = dict(details)
        run_details["runList"] = command_preview(result)
        return make_check(
            CHECK_ID,
            "skipped",
            "optional GitHub Actions check skipped because gh run list failed or network was unavailable",
            details=run_details,
        )

    try:
        runs = json.loads(result.stdout or "[]")
    except json.JSONDecodeError as exc:
        parse_details = dict(details)
        parse_details["jsonError"] = str(exc)
        parse_details["stdoutTail"] = result.stdout[-2000:]
        return make_check(
            CHECK_ID,
            "skipped",
            "optional GitHub Actions check skipped because gh run list returned invalid JSON",
            details=parse_details,
        )

    if not runs:
        return make_check(
            CHECK_ID,
            "skipped",
            "optional GitHub Actions check skipped because no workflow run was found for main",
            details=details,
        )

    run = runs[0]
    run_details = {
        "workflow": workflow,
        "branch": branch,
        "status": run.get("status"),
        "conclusion": run.get("conclusion"),
        "headSha": run.get("headSha"),
        "url": run.get("url"),
        "displayTitle": run.get("displayTitle"),
        "createdAt": run.get("createdAt"),
    }
    status = run.get("status")
    conclusion = run.get("conclusion")
    if status == "completed" and conclusion == "success":
        return make_check(
            CHECK_ID,
            "pass",
            "latest main GitHub Actions V3 workflow completed successfully",
            details=run_details,
        )

    blocking = require_success and (status != "completed" or conclusion != "success")
    check_status = "fail" if blocking else "warn"
    if status == "completed" and conclusion in TERMINAL_UNSUCCESSFUL_CONCLUSIONS:
        message = "latest main GitHub Actions V3 workflow completed without success"
    else:
        message = "latest main GitHub Actions V3 workflow is not completed successfully"
    if not require_success:
        message += "; warning only because remote CI strict mode is off"
    return make_check(CHECK_ID, check_status, message, details=run_details)
