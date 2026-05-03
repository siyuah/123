import os
from pathlib import Path

from tools.verify_linghucall_provider_shim_supervised import CommandResult, build_report


def make_private_file(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("not-read-by-verifier\n", encoding="utf-8")
    path.chmod(0o600)


def active_runner(args, cwd, env, timeout):
    if args[:3] == ["systemctl", "--user", "is-active"]:
        return CommandResult(0, "active\n", "")
    if args[:2] == ["pnpm", "gate:provider-status"]:
        assert env["DARK_FACTORY_REMOTE_ENDPOINT"] == "http://127.0.0.1:9791"
        return CommandResult(0, '{"ok":true}\n', "")
    if args[:2] == ["pnpm", "test"]:
        return CommandResult(0, "1 passed\n", "")
    return CommandResult(1, "", "unexpected command")


def inactive_runner(args, cwd, env, timeout):
    if args[:3] == ["systemctl", "--user", "is-active"]:
        return CommandResult(3, "inactive\n", "")
    return CommandResult(1, "", "unexpected command")


def healthy(endpoint, timeout):
    return {
        "ok": True,
        "status": "ready",
        "endpointHost": "127.0.0.1:9791",
        "protocolReleaseTag": "v3.0-agent-control-r1",
        "providerKind": "linghucall_openai_compatible",
        "providerCredentialValueRedacted": True,
    }


def unhealthy(endpoint, timeout):
    return {
        "ok": False,
        "status": "unreachable",
        "endpointHost": "127.0.0.1:9791",
    }


def test_supervised_report_passes_with_active_service_private_files_and_gate(monkeypatch, tmp_path):
    env_file = tmp_path / "linghucall-provider-shim.env"
    bridge_key_file = tmp_path / "linghucall-shim-bridge.key"
    make_private_file(env_file)
    make_private_file(bridge_key_file)
    monkeypatch.setenv("DARK_FACTORY_LINGHUCALL_SHIM_BRIDGE_KEY", "bridge-key-not-reported")

    report = build_report(
        env_file=env_file,
        bridge_key_file=bridge_key_file,
        include_paperclip_gate=True,
        command_runner=active_runner,
        health_checker=healthy,
    )

    assert report["ok"] is True
    assert report["status"] == "pass"
    statuses = {item["id"]: item["status"] for item in report["checks"]}
    assert statuses["systemd_user_service_active"] == "pass"
    assert statuses["operator_env_file_private"] == "pass"
    assert statuses["bridge_key_file_private"] == "pass"
    assert statuses["shim_health_ready"] == "pass"
    assert statuses["paperclip_provider_status_gate_passed"] == "pass"
    assert statuses["paperclip_remote_gated_test_passed"] == "pass"
    assert report["boundary"] == {
        "truthSource": "dark-factory-journal",
        "authoritative": False,
        "terminalStateAdvanced": False,
        "noCredentialValuesRead": True,
        "noCredentialValuesPrinted": True,
        "doesInstallService": False,
        "contactsProviderViaShimOnly": True,
    }


def test_supervised_report_fails_closed_when_service_inactive(tmp_path):
    env_file = tmp_path / "linghucall-provider-shim.env"
    bridge_key_file = tmp_path / "linghucall-shim-bridge.key"
    make_private_file(env_file)
    make_private_file(bridge_key_file)

    report = build_report(
        env_file=env_file,
        bridge_key_file=bridge_key_file,
        command_runner=inactive_runner,
        health_checker=healthy,
    )

    assert report["ok"] is False
    statuses = {item["id"]: item["status"] for item in report["checks"]}
    assert statuses["systemd_user_service_active"] == "fail"
    assert statuses["shim_health_ready"] == "pass"


def test_supervised_report_fails_closed_when_health_is_not_ready(tmp_path):
    env_file = tmp_path / "linghucall-provider-shim.env"
    bridge_key_file = tmp_path / "linghucall-shim-bridge.key"
    make_private_file(env_file)
    make_private_file(bridge_key_file)

    report = build_report(
        env_file=env_file,
        bridge_key_file=bridge_key_file,
        command_runner=active_runner,
        health_checker=unhealthy,
    )

    assert report["ok"] is False
    statuses = {item["id"]: item["status"] for item in report["checks"]}
    assert statuses["systemd_user_service_active"] == "pass"
    assert statuses["shim_health_ready"] == "fail"


def test_supervised_report_does_not_embed_secret_values(monkeypatch, tmp_path):
    env_file = tmp_path / "linghucall-provider-shim.env"
    bridge_key_file = tmp_path / "linghucall-shim-bridge.key"
    make_private_file(env_file)
    make_private_file(bridge_key_file)
    monkeypatch.setenv("DARK_FACTORY_LINGHUCALL_SHIM_BRIDGE_KEY", "bridge-key-not-reported")
    monkeypatch.setenv("LINGHUCALL_API_KEY", "provider-key-not-reported")

    report_text = str(
        build_report(
            env_file=env_file,
            bridge_key_file=bridge_key_file,
            include_paperclip_gate=True,
            command_runner=active_runner,
            health_checker=healthy,
        )
    )

    assert "bridge-key-not-reported" not in report_text
    assert "provider-key-not-reported" not in report_text
    assert "Bearer " not in report_text
    assert "Authorization:" not in report_text
    assert "password=" not in report_text.lower()
    assert os.environ["LINGHUCALL_API_KEY"] == "provider-key-not-reported"
