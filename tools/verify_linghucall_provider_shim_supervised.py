#!/usr/bin/env python3
"""Supervised service verifier for the LinghuCall provider shim.

The verifier is intentionally credential-blind: it checks file presence,
permissions, systemd state, and `/api/health`, but it never reads the content of
the operator env file or bridge key file.
"""
from __future__ import annotations

import argparse
import json
import os
import stat
import subprocess
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable, Sequence

ROOT = Path(__file__).resolve().parents[1]
PAPERCLIP_PLUGIN_ROOT = (
    Path(os.environ.get("PAPERCLIP_ROOT", "/home/siyuah/workspace/paperclip_upstream"))
    / "packages/plugins/integrations/dark-factory-bridge"
)
DEFAULT_SERVICE_NAME = "linghucall-provider-shim.service"
DEFAULT_ENV_FILE = Path.home() / ".config/dark-factory/linghucall-provider-shim.env"
DEFAULT_BRIDGE_KEY_FILE = Path.home() / ".config/dark-factory/linghucall-shim-bridge.key"
DEFAULT_ENDPOINT = "http://127.0.0.1:9791"

CommandRunner = Callable[[Sequence[str], Path | None, dict[str, str] | None, float | None], "CommandResult"]
HealthChecker = Callable[[str, float], dict[str, Any]]


@dataclass(frozen=True)
class CommandResult:
    returncode: int
    stdout: str = ""
    stderr: str = ""


def utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def run_command(
    args: Sequence[str],
    cwd: Path | None = None,
    env: dict[str, str] | None = None,
    timeout: float | None = None,
) -> CommandResult:
    completed = subprocess.run(
        list(args),
        cwd=str(cwd) if cwd else None,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout,
        check=False,
    )
    return CommandResult(completed.returncode, completed.stdout, completed.stderr)


def check(check_id: str, ok: bool, message: str, **details: Any) -> dict[str, Any]:
    item: dict[str, Any] = {
        "id": check_id,
        "ok": ok,
        "status": "pass" if ok else "fail",
        "message": message,
    }
    if details:
        item["details"] = sanitize_details(details)
    return item


def sanitize_details(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: sanitize_details(item) for key, item in value.items()}
    if isinstance(value, list):
        return [sanitize_details(item) for item in value]
    if isinstance(value, str):
        return redact_sensitive_text(value)
    return value


def redact_sensitive_text(text: str) -> str:
    if not text:
        return text
    lowered = text.lower()
    sensitive_markers = ("api_key", "apikey", "authorization", "bearer ", "token", "secret", "password")
    if any(marker in lowered for marker in sensitive_markers):
        return "[redacted]"
    return text[:500]


def file_permission_check(path: Path, check_id: str, label: str) -> dict[str, Any]:
    if not path.exists():
        return check(check_id, False, f"{label} exists", path=str(path), exists=False)
    mode = stat.S_IMODE(path.stat().st_mode)
    private = mode & 0o077 == 0
    return check(
        check_id,
        private,
        f"{label} exists and is not group/world readable",
        path=str(path),
        exists=True,
        mode=oct(mode),
    )


def load_health_checker() -> HealthChecker:
    sys.path.insert(0, str(ROOT / "tools"))
    from check_linghucall_provider_shim_health import check_health

    return check_health


def systemd_active_check(
    service_name: str,
    command_runner: CommandRunner,
) -> dict[str, Any]:
    result = command_runner(["systemctl", "--user", "is-active", service_name], None, None, 5.0)
    stdout = result.stdout.strip()
    return check(
        "systemd_user_service_active",
        result.returncode == 0 and stdout == "active",
        "systemd user service is active",
        serviceName=service_name,
        systemctlStatus=stdout or "unknown",
        returnCode=result.returncode,
    )


def healthcheck_check(endpoint: str, timeout: float, health_checker: HealthChecker) -> dict[str, Any]:
    report = health_checker(endpoint, timeout)
    return check(
        "shim_health_ready",
        report.get("ok") is True,
        "supervised shim /api/health reports ready",
        endpointHost=report.get("endpointHost"),
        status=report.get("status"),
        protocolReleaseTag=report.get("protocolReleaseTag"),
        providerKind=report.get("providerKind"),
        providerCredentialValueRedacted=report.get("providerCredentialValueRedacted"),
    )


def paperclip_gate_checks(
    endpoint: str,
    bridge_key_env: str,
    command_runner: CommandRunner,
) -> list[dict[str, Any]]:
    if not os.environ.get(bridge_key_env):
        return [
            check(
                "paperclip_bridge_key_env_present",
                False,
                "bridge-facing API key env var is exported for gated Paperclip test",
                envVar=bridge_key_env,
            )
        ]

    env = os.environ.copy()
    env.update(
        {
            "DARK_FACTORY_REMOTE_INTEGRATION": "1",
            "DARK_FACTORY_REMOTE_ENDPOINT": endpoint,
            "DARK_FACTORY_REMOTE_API_KEY_ENV": bridge_key_env,
        }
    )
    gate = command_runner(["pnpm", "gate:provider-status", "--", "--require-ready"], PAPERCLIP_PLUGIN_ROOT, env, 60.0)
    test = command_runner(["pnpm", "test", "--", "tests/remote-gated-integration.spec.ts"], PAPERCLIP_PLUGIN_ROOT, env, 180.0)
    return [
        check(
            "paperclip_provider_status_gate_passed",
            gate.returncode == 0,
            "Paperclip provider status gate passes against supervised shim",
            returnCode=gate.returncode,
        ),
        check(
            "paperclip_remote_gated_test_passed",
            test.returncode == 0,
            "Paperclip remote gated integration test passes against supervised shim",
            returnCode=test.returncode,
        ),
    ]


def build_report(
    *,
    endpoint: str = DEFAULT_ENDPOINT,
    service_name: str = DEFAULT_SERVICE_NAME,
    env_file: Path = DEFAULT_ENV_FILE,
    bridge_key_file: Path = DEFAULT_BRIDGE_KEY_FILE,
    bridge_key_env: str = "DARK_FACTORY_LINGHUCALL_SHIM_BRIDGE_KEY",
    timeout: float = 3.0,
    include_paperclip_gate: bool = False,
    command_runner: CommandRunner = run_command,
    health_checker: HealthChecker | None = None,
) -> dict[str, Any]:
    health_checker = health_checker or load_health_checker()
    checks = [
        systemd_active_check(service_name, command_runner),
        file_permission_check(env_file, "operator_env_file_private", "operator env file"),
        file_permission_check(bridge_key_file, "bridge_key_file_private", "bridge key file"),
        healthcheck_check(endpoint, timeout, health_checker),
    ]
    if include_paperclip_gate:
        checks.extend(paperclip_gate_checks(endpoint, bridge_key_env, command_runner))

    ok = all(item["ok"] for item in checks)
    return {
        "schemaVersion": 1,
        "reportType": "linghucall-provider-shim-supervised-attempt",
        "checkedAt": utc_now(),
        "ok": ok,
        "status": "pass" if ok else "fail",
        "endpoint": endpoint,
        "serviceName": service_name,
        "paperclipGateAttempted": include_paperclip_gate,
        "checks": checks,
        "boundary": {
            "truthSource": "dark-factory-journal",
            "authoritative": False,
            "terminalStateAdvanced": False,
            "noCredentialValuesRead": True,
            "noCredentialValuesPrinted": True,
            "doesInstallService": False,
            "contactsProviderViaShimOnly": True,
        },
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Verify a supervised LinghuCall provider shim service")
    parser.add_argument("--endpoint", default=DEFAULT_ENDPOINT, help="Shim base endpoint.")
    parser.add_argument("--service-name", default=DEFAULT_SERVICE_NAME, help="systemd user service name.")
    parser.add_argument("--env-file", default=str(DEFAULT_ENV_FILE), help="Operator env file path. Contents are not read.")
    parser.add_argument("--bridge-key-file", default=str(DEFAULT_BRIDGE_KEY_FILE), help="Bridge key file path. Contents are not read.")
    parser.add_argument("--bridge-key-env", default="DARK_FACTORY_LINGHUCALL_SHIM_BRIDGE_KEY", help="Env var containing bridge-facing key for optional Paperclip gate.")
    parser.add_argument("--timeout", default=3.0, type=float, help="Healthcheck timeout.")
    parser.add_argument("--include-paperclip-gate", action="store_true", help="Run Paperclip provider gate and gated integration test.")
    parser.add_argument("--output", default=None, help="Optional JSON report path.")
    parser.add_argument("--require-pass", action="store_true", help="Exit non-zero unless all selected checks pass.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    report = build_report(
        endpoint=args.endpoint,
        service_name=args.service_name,
        env_file=Path(args.env_file).expanduser(),
        bridge_key_file=Path(args.bridge_key_file).expanduser(),
        bridge_key_env=args.bridge_key_env,
        timeout=args.timeout,
        include_paperclip_gate=args.include_paperclip_gate,
    )
    text = json.dumps(report, indent=2, sort_keys=True)
    if args.output:
        Path(args.output).write_text(f"{text}\n", encoding="utf-8")
    print(text)
    if args.require_pass and not report["ok"]:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
