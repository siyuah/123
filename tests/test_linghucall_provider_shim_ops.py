from tools.verify_linghucall_provider_shim_ops import build_report


def test_linghucall_provider_shim_ops_assets_pass_offline_verification():
    report = build_report()

    assert report["ok"] is True
    assert report["status"] == "pass"
    statuses = {item["id"]: item["status"] for item in report["checks"]}
    assert statuses["service_template_exists"] == "pass"
    assert statuses["env_example_uses_placeholder"] == "pass"
    assert statuses["service_has_basic_hardening"] == "pass"
    assert statuses["runtime_artifacts_ignored"] == "pass"
    assert statuses["operator_runbook_links_ops"] == "pass"
    assert report["boundary"] == {
        "truthSource": "dark-factory-journal",
        "authoritative": False,
        "terminalStateAdvanced": False,
        "noResolvedCredentialValues": True,
        "doesInstallService": False,
        "doesContactProvider": False,
    }


def test_linghucall_provider_shim_ops_report_does_not_embed_resolved_credentials():
    report_text = str(build_report())

    assert "sk-" not in report_text
    assert "Bearer " not in report_text
    assert "Authorization:" not in report_text
    assert "password=" not in report_text.lower()
