#!/usr/bin/env python3
"""Generate a Dark Factory handoff packet.

The packet is intentionally read-only. It collects repository status, local
contract validation summaries, progress archive pointers, and next-step
commands without reading operator credential files, provider key files, or
runtime journals.
"""
from __future__ import annotations

import argparse
import json
import re
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

PROTOCOL_RELEASE_TAG = "v3.0-agent-control-r1"
DEFAULT_PROGRESS_DIR = "docs/progress"
DEFAULT_PAPERCLIP_ROOT = ROOT.parent / "paperclip_upstream"
SENSITIVE_MARKERS = (
    "api_key",
    "apikey",
    "authorization",
    "bearer ",
    "connection_string",
    "credential",
    "df_api_key",
    "linghucall_api_key",
    "password",
    "secret",
    "token",
    "x-api-key",
)
SENSITIVE_KEY_RE = re.compile(
    r"(api[_-]?key|apikey|authorization|connection[_-]?string|credential|password|secret|token|x-api-key)",
    re.IGNORECASE,
)
SENSITIVE_VALUE_RE = re.compile(
    r"(bearer\s+[A-Za-z0-9._~+/=-]+|sk-[A-Za-z0-9]{8,}|"
    r"(api[_-]?key|apikey|authorization|connection[_-]?string|password|secret|token|x-api-key)\s*[:=]\s*\S+)",
    re.IGNORECASE,
)
SENSITIVE_KEY_EXACT = {
    "accesstoken",
    "apikey",
    "authorization",
    "bearer",
    "connectionstring",
    "credential",
    "credentials",
    "dfapikey",
    "linghucallapikey",
    "password",
    "secret",
    "token",
    "xapikey",
}


def stable_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def redact_sensitive_text(value: str) -> str:
    if SENSITIVE_VALUE_RE.search(value):
        return "[redacted]"
    return value


def redact_payload(value: Any) -> Any:
    if isinstance(value, str):
        return redact_sensitive_text(value)
    if isinstance(value, list):
        return [redact_payload(item) for item in value]
    if isinstance(value, dict):
        redacted: dict[str, Any] = {}
        for key, item in value.items():
            normalized_key = re.sub(r"[^a-z0-9]", "", str(key).lower())
            key_holds_credential = (
                normalized_key in SENSITIVE_KEY_EXACT
                or normalized_key.endswith("apikey")
                or normalized_key.endswith("password")
                or normalized_key.endswith("secret")
            )
            if key_holds_credential and isinstance(item, str) and item:
                redacted[key] = "[redacted]"
            else:
                redacted[key] = redact_payload(item)
        return redacted
    return value


def run_command(args: Sequence[str], *, cwd: Path, timeout: int = 30) -> subprocess.CompletedProcess[str]:
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


def safe_lines(text: str, *, limit: int = 20) -> list[str]:
    lines = [redact_sensitive_text(line) for line in text.splitlines()]
    if len(lines) <= limit:
        return lines
    return lines[-limit:]


def command_summary(result: subprocess.CompletedProcess[str]) -> dict[str, Any]:
    return {
        "returnCode": result.returncode,
        "stdoutTail": safe_lines(result.stdout, limit=30),
        "stderrTail": safe_lines(result.stderr, limit=30),
    }


def git_status(root: Path, *, max_commits: int) -> dict[str, Any]:
    if not (root / ".git").exists():
        return {"exists": False, "path": str(root)}

    branch = run_command(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=root)
    head_short = run_command(["git", "rev-parse", "--short", "HEAD"], cwd=root)
    head_full = run_command(["git", "rev-parse", "HEAD"], cwd=root)
    status = run_command(["git", "status", "--short"], cwd=root)
    log = run_command(["git", "log", "--oneline", "--decorate", f"--max-count={max_commits}"], cwd=root)

    status_lines = status.stdout.splitlines() if status.returncode == 0 else []
    return {
        "exists": True,
        "path": str(root),
        "branch": branch.stdout.strip() if branch.returncode == 0 else None,
        "headCommit": head_short.stdout.strip() if head_short.returncode == 0 else None,
        "headCommitFull": head_full.stdout.strip() if head_full.returncode == 0 else None,
        "clean": status.returncode == 0 and status_lines == [],
        "statusShort": [redact_sensitive_text(line) for line in status_lines],
        "recentCommits": safe_lines(log.stdout, limit=max_commits),
        "errors": {
            "branch": command_summary(branch) if branch.returncode != 0 else None,
            "head": command_summary(head_short) if head_short.returncode != 0 else None,
            "status": command_summary(status) if status.returncode != 0 else None,
            "log": command_summary(log) if log.returncode != 0 else None,
        },
    }


def bundle_summary(root: Path) -> dict[str, Any]:
    try:
        from validate_v3_bundle import validate_bundle

        report = validate_bundle(root)
        summary = report.get("summary", {})
        return {
            "ok": int(summary.get("errors", 0)) == 0,
            "status": report.get("status"),
            "errors": int(summary.get("errors", 0)),
            "warnings": int(summary.get("warnings", 0)),
            "checks": int(summary.get("checks", 0)),
            "failedChecks": [check.get("id") for check in report.get("checks", []) if check.get("status") == "fail"],
        }
    except Exception as exc:
        return {"ok": False, "status": "error", "errorType": type(exc).__name__, "message": redact_sensitive_text(str(exc))}


def drift_summary(root: Path) -> dict[str, Any]:
    try:
        from v3_contract_drift_report import build_report

        report = build_report(root, summary_path="docs/generated/V3_CONTRACT_SUMMARY.md")
        return {
            "ok": bool(report.get("ok")),
            "status": report.get("status"),
            "failed": int(report.get("summary", {}).get("failed", 0)),
            "warnings": int(report.get("summary", {}).get("warnings", 0)),
            "failedChecks": report.get("summary", {}).get("failedChecks", []),
            "warningChecks": report.get("summary", {}).get("warningChecks", []),
        }
    except Exception as exc:
        return {"ok": False, "status": "error", "errorType": type(exc).__name__, "message": redact_sensitive_text(str(exc))}


def readiness_summary(root: Path, *, smoke_evidence: str | None = None, bridge_evidence: str | None = None) -> dict[str, Any]:
    try:
        from df_review_readiness import build_report

        report = build_report(root, smoke_evidence=smoke_evidence, bridge_evidence=bridge_evidence)
        return {
            "ok": bool(report.get("ok")),
            "status": report.get("status"),
            "passed": int(report.get("summary", {}).get("passed", 0)),
            "warned": int(report.get("summary", {}).get("warned", 0)),
            "failed": int(report.get("summary", {}).get("failed", 0)),
            "warnedChecks": report.get("summary", {}).get("warnedChecks", []),
            "failedChecks": report.get("summary", {}).get("failedChecks", []),
        }
    except Exception as exc:
        return {"ok": False, "status": "error", "errorType": type(exc).__name__, "message": redact_sensitive_text(str(exc))}


def generated_summary_status(root: Path) -> dict[str, Any]:
    path = root / "docs/generated/V3_CONTRACT_SUMMARY.md"
    if not path.exists():
        return {"exists": False, "path": "docs/generated/V3_CONTRACT_SUMMARY.md"}
    return {
        "exists": True,
        "path": "docs/generated/V3_CONTRACT_SUMMARY.md",
        "bytes": path.stat().st_size,
    }


def progress_archives(root: Path, *, limit: int = 12) -> list[dict[str, Any]]:
    progress_dir = root / DEFAULT_PROGRESS_DIR
    if not progress_dir.exists():
        return []
    records: list[dict[str, Any]] = []
    for path in sorted(progress_dir.glob("*.md")):
        if path.name == "README.md":
            continue
        first_heading = ""
        try:
            for line in path.read_text(encoding="utf-8").splitlines():
                if line.startswith("#"):
                    first_heading = redact_sensitive_text(line.strip("# "))
                    break
        except UnicodeDecodeError:
            first_heading = "[unreadable markdown heading]"
        records.append(
            {
                "path": str(path.relative_to(root)),
                "bytes": path.stat().st_size,
                "heading": first_heading,
            }
        )
    return records[-limit:]


def derive_status(bundle: dict[str, Any], drift: dict[str, Any], readiness: dict[str, Any], git: dict[str, Any]) -> str:
    if not bundle.get("ok") or not drift.get("ok") or readiness.get("failed", 0):
        return "blocked"
    if readiness.get("status") != "READY" or not git.get("clean", False):
        return "conditional_ready"
    return "ready"


def build_packet(
    root: Path | str = ROOT,
    *,
    include_paperclip_status: bool = True,
    paperclip_root: Path | str = DEFAULT_PAPERCLIP_ROOT,
    max_commits: int = 8,
    smoke_evidence: str | None = None,
    bridge_evidence: str | None = None,
) -> dict[str, Any]:
    root = Path(root)
    paperclip_root = Path(paperclip_root)
    git = git_status(root, max_commits=max_commits)
    bundle = bundle_summary(root)
    drift = drift_summary(root)
    readiness = readiness_summary(root, smoke_evidence=smoke_evidence, bridge_evidence=bridge_evidence)
    status = derive_status(bundle, drift, readiness, git)

    packet: dict[str, Any] = {
        "schemaVersion": 1,
        "reportType": "dark-factory-handoff-packet",
        "generatedAt": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "protocolReleaseTag": PROTOCOL_RELEASE_TAG,
        "status": status,
        "repository": git,
        "paperclipRepository": git_status(paperclip_root, max_commits=max_commits) if include_paperclip_status else {"skipped": True},
        "validation": {
            "bundle": bundle,
            "contractDrift": drift,
            "reviewReadiness": readiness,
            "generatedSummary": generated_summary_status(root),
        },
        "progressArchives": progress_archives(root),
        "securityBoundaries": {
            "document": "docs/security_boundaries.md",
            "currentAuthMode": "single bridge-facing API key for non-health routes",
            "scopedTokenStatus": "design preview only; not implemented",
        },
        "boundary": {
            "authoritative": False,
            "terminalStateAdvanced": False,
            "truthSource": "dark-factory-journal",
            "writesJournal": False,
            "readsRuntimeJournal": False,
            "noCredentialValuesRead": True,
            "noCredentialValuesPrinted": True,
        },
        "nextSteps": [
            "Provide smoke and bridge evidence paths to df_review_readiness.py when recording a release review.",
            "Review docs/security_boundaries.md before implementing scoped token issuance.",
            "Keep Dark Factory Journal as truth source; handoff packet facts are derived and non-authoritative.",
        ],
        "handoffCommandForNextAi": (
            "cd /home/siyuah/workspace/123 && "
            ".venv/bin/python tools/df_handoff_packet.py --json --include-paperclip-status"
        ),
    }
    return redact_payload(packet)


def render_markdown(packet: dict[str, Any]) -> str:
    repo = packet["repository"]
    paperclip = packet["paperclipRepository"]
    validation = packet["validation"]
    readiness = validation["reviewReadiness"]
    drift = validation["contractDrift"]
    bundle = validation["bundle"]

    lines = [
        "# Dark Factory Handoff Packet",
        "",
        f"Generated at: `{packet['generatedAt']}`",
        f"Status: `{packet['status']}`",
        f"Protocol release tag: `{packet['protocolReleaseTag']}`",
        "",
        "## Boundary",
        "",
        "- Dark Factory Journal remains truth source.",
        "- This packet is a derived, non-authoritative review aid.",
        "- `authoritative: false` and `terminalStateAdvanced: false` are preserved.",
        "- No credential values are read, printed, stored, or archived by this tool.",
        "",
        "## Main Repository",
        "",
        f"- Path: `{repo.get('path')}`",
        f"- Branch: `{repo.get('branch')}`",
        f"- HEAD: `{repo.get('headCommit')}`",
        f"- Clean: `{repo.get('clean')}`",
        f"- Status lines: `{len(repo.get('statusShort', []))}`",
        "",
        "Recent commits:",
        "",
    ]
    lines.extend([f"- `{line}`" for line in repo.get("recentCommits", [])] or ["- None"])
    lines.extend(["", "## Paperclip Repository", ""])
    if paperclip.get("skipped"):
        lines.append("- Skipped by CLI option.")
    elif paperclip.get("exists"):
        lines.extend(
            [
                f"- Path: `{paperclip.get('path')}`",
                f"- Branch: `{paperclip.get('branch')}`",
                f"- HEAD: `{paperclip.get('headCommit')}`",
                f"- Clean: `{paperclip.get('clean')}`",
            ]
        )
    else:
        lines.append(f"- Not found at `{paperclip.get('path')}`.")

    lines.extend(
        [
            "",
            "## Validation Summary",
            "",
            f"- V3 bundle: `{bundle.get('status')}`; checks `{bundle.get('checks')}`, errors `{bundle.get('errors')}`, warnings `{bundle.get('warnings')}`.",
            f"- Contract drift: `{drift.get('status')}`; failed `{drift.get('failed')}`, warnings `{drift.get('warnings')}`.",
            f"- Review readiness: `{readiness.get('status')}`; pass `{readiness.get('passed')}`, warn `{readiness.get('warned')}`, fail `{readiness.get('failed')}`.",
            f"- Readiness warnings: `{', '.join(readiness.get('warnedChecks', [])) or 'none'}`.",
            "",
            "## Progress Archives",
            "",
        ]
    )
    for item in packet.get("progressArchives", []):
        heading = item.get("heading") or item.get("path")
        lines.append(f"- `{item.get('path')}` - {heading}")
    if not packet.get("progressArchives"):
        lines.append("- None")

    lines.extend(
        [
            "",
            "## Security Boundary",
            "",
            f"- Document: `{packet['securityBoundaries']['document']}`",
            f"- Current auth mode: `{packet['securityBoundaries']['currentAuthMode']}`",
            f"- Scoped token status: `{packet['securityBoundaries']['scopedTokenStatus']}`",
            "",
            "## Next Steps",
            "",
        ]
    )
    lines.extend([f"- {step}" for step in packet.get("nextSteps", [])])
    lines.extend(["", "## Next AI Command", "", "```bash", packet["handoffCommandForNextAi"], "```", ""])
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate a Dark Factory handoff packet")
    parser.add_argument("--json", action="store_true", help="emit stable JSON instead of Markdown")
    parser.add_argument("--output", help="write the packet to PATH while also printing it")
    parser.add_argument("--include-paperclip-status", dest="include_paperclip_status", action="store_true", default=True)
    parser.add_argument("--no-paperclip-status", dest="include_paperclip_status", action="store_false")
    parser.add_argument("--paperclip-root", default=str(DEFAULT_PAPERCLIP_ROOT))
    parser.add_argument("--max-commits", type=int, default=8)
    parser.add_argument("--smoke-evidence", help="optional smoke evidence JSON path for readiness summary")
    parser.add_argument("--bridge-evidence", help="optional bridge evidence JSON path for readiness summary")
    parser.add_argument("--fail-on-dirty", action="store_true", help="exit non-zero when the main repo has local changes")
    parser.add_argument("--root", default=str(ROOT), help=argparse.SUPPRESS)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    root = Path(args.root).resolve()
    packet = build_packet(
        root,
        include_paperclip_status=args.include_paperclip_status,
        paperclip_root=Path(args.paperclip_root),
        max_commits=args.max_commits,
        smoke_evidence=args.smoke_evidence,
        bridge_evidence=args.bridge_evidence,
    )
    rendered = stable_json(packet) if args.json else render_markdown(packet)
    if args.output:
        output = Path(args.output)
        if not output.is_absolute():
            output = root / output
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(rendered, encoding="utf-8")
    sys.stdout.write(rendered)
    if args.fail_on_dirty and not packet["repository"].get("clean"):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
