#!/usr/bin/env python3
"""Offline operations verifier for the LinghuCall provider shim."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SERVICE_PATH = ROOT / "ops/linghucall-provider-shim/linghucall-provider-shim.service"
ENV_EXAMPLE_PATH = ROOT / "ops/linghucall-provider-shim/linghucall-provider-shim.env.example"
OPS_README_PATH = ROOT / "ops/linghucall-provider-shim/README.md"
RUNBOOK_PATH = ROOT / "docs/linghucall_provider_shim_runbook.md"
HEALTHCHECK_PATH = ROOT / "tools/check_linghucall_provider_shim_health.py"
GATE_SCRIPT_PATH = ROOT / "tools/run_linghucall_provider_shim_gate.sh"


def utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def check(check_id: str, ok: bool, message: str, **details: Any) -> dict[str, Any]:
    item: dict[str, Any] = {
        "id": check_id,
        "ok": ok,
        "status": "pass" if ok else "fail",
        "message": message,
    }
    if details:
        item["details"] = details
    return item


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def build_report(root: Path = ROOT, *, live_endpoint: str | None = None) -> dict[str, Any]:
    service = read_text(SERVICE_PATH) if SERVICE_PATH.exists() else ""
    env_example = read_text(ENV_EXAMPLE_PATH) if ENV_EXAMPLE_PATH.exists() else ""
    ops_readme = read_text(OPS_README_PATH) if OPS_README_PATH.exists() else ""
    runbook = read_text(RUNBOOK_PATH) if RUNBOOK_PATH.exists() else ""
    gitignore = read_text(root / ".gitignore") if (root / ".gitignore").exists() else ""

    checks = [
        check("service_template_exists", SERVICE_PATH.exists(), "systemd user service template exists"),
        check("env_example_exists", ENV_EXAMPLE_PATH.exists(), "environment example exists"),
        check("ops_readme_exists", OPS_README_PATH.exists(), "operations README exists"),
        check("healthcheck_exists", HEALTHCHECK_PATH.exists(), "healthcheck helper exists"),
        check("gate_script_exists", GATE_SCRIPT_PATH.exists(), "operator gated test script exists"),
        check("service_uses_environment_file", "EnvironmentFile=%h/.config/dark-factory/linghucall-provider-shim.env" in service, "service reads operator-managed env file"),
        check("service_restarts_on_failure", "Restart=on-failure" in service, "service restarts on failure"),
        check("service_has_basic_hardening", all(token in service for token in ["NoNewPrivileges=true", "PrivateTmp=true", "ProtectSystem=strict"]), "service includes basic systemd hardening"),
        check("service_limits_write_path", "ReadWritePaths=/home/siyuah/workspace/123/.dark_factory_http" in service, "service write access is limited to shim journal directory"),
        check("env_example_uses_placeholder", "LINGHUCALL_API_KEY=__SET_IN_OPERATOR_SECRET_STORE__" in env_example, "provider credential in env example is a placeholder"),
        check("env_example_has_bridge_key_file", "DF_API_KEY_FILE=" in env_example, "bridge-facing key is file based"),
        check("env_example_has_no_resolved_secret", not contains_resolved_secret(env_example), "env example does not contain resolved credential values"),
        check("runtime_artifacts_ignored", ".dark_factory_http/" in gitignore, "runtime journal/log directory is gitignored"),
        check("runbook_has_start_health_gate_rollback", all(token in ops_readme for token in ["systemctl --user enable --now", "check_linghucall_provider_shim_health.py", "pnpm test -- tests/remote-gated-integration.spec.ts", "Rollback"]), "operations README covers start, healthcheck, gate, and rollback"),
        check("operator_runbook_links_ops", "Operationalized User Service" in runbook and "verify_linghucall_provider_shim_ops.py" in runbook, "provider shim runbook links operations workflow"),
    ]

    if live_endpoint:
        checks.append(run_live_healthcheck(live_endpoint))

    ok = all(item["ok"] for item in checks)
    return {
        "schemaVersion": 1,
        "reportType": "linghucall-provider-shim-operationalization",
        "checkedAt": utc_now(),
        "ok": ok,
        "status": "pass" if ok else "fail",
        "root": str(root),
        "checks": checks,
        "artifacts": {
            "serviceTemplate": str(SERVICE_PATH.relative_to(root)),
            "envExample": str(ENV_EXAMPLE_PATH.relative_to(root)),
            "opsReadme": str(OPS_README_PATH.relative_to(root)),
            "healthcheck": str(HEALTHCHECK_PATH.relative_to(root)),
            "gateScript": str(GATE_SCRIPT_PATH.relative_to(root)),
        },
        "boundary": {
            "truthSource": "dark-factory-journal",
            "authoritative": False,
            "terminalStateAdvanced": False,
            "noResolvedCredentialValues": True,
            "doesInstallService": False,
            "doesContactProvider": live_endpoint is not None,
        },
    }


def contains_resolved_secret(text: str) -> bool:
    forbidden = [
        "sk-",
        "Bearer ",
        "Authorization:",
        "password=",
        "connection_string=",
    ]
    return any(item.lower() in text.lower() for item in forbidden)


def run_live_healthcheck(endpoint: str) -> dict[str, Any]:
    result = subprocess.run(
        [sys.executable, str(HEALTHCHECK_PATH), "--endpoint", endpoint],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    try:
        health = json.loads(result.stdout)
    except json.JSONDecodeError:
        health = {"ok": False, "status": "invalid_healthcheck_output"}
    return check(
        "live_healthcheck",
        result.returncode == 0 and health.get("ok") is True,
        "optional live healthcheck passes",
        endpointHost=health.get("endpointHost"),
        status=health.get("status"),
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Verify LinghuCall provider shim operationalization assets")
    parser.add_argument("--live-endpoint", default=None, help="Optionally run a live /api/health check against this endpoint.")
    parser.add_argument("--output", default=None, help="Optional JSON report path.")
    parser.add_argument("--require-pass", action="store_true", help="Exit non-zero unless all checks pass.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    report = build_report(live_endpoint=args.live_endpoint)
    text = json.dumps(report, indent=2, sort_keys=True)
    if args.output:
        Path(args.output).write_text(f"{text}\n", encoding="utf-8")
    print(text)
    if args.require_pass and not report["ok"]:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
