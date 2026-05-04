import importlib.util
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "df_handoff_packet.py"
SECURITY_DOC = ROOT / "docs" / "security_boundaries.md"


def load_tool():
    spec = importlib.util.spec_from_file_location("df_handoff_packet", TOOL)
    module = importlib.util.module_from_spec(spec)
    sys.modules["df_handoff_packet"] = module
    spec.loader.exec_module(module)
    return module


def test_handoff_packet_summarizes_current_contracts_without_paperclip_dependency():
    tool = load_tool()

    packet = tool.build_packet(ROOT, include_paperclip_status=False)

    assert packet["reportType"] == "dark-factory-handoff-packet"
    assert packet["protocolReleaseTag"] == "v3.0-agent-control-r1"
    assert packet["boundary"]["authoritative"] is False
    assert packet["boundary"]["terminalStateAdvanced"] is False
    assert packet["boundary"]["truthSource"] == "dark-factory-journal"
    assert packet["boundary"]["noCredentialValuesRead"] is True
    assert packet["validation"]["bundle"]["ok"] is True
    assert packet["validation"]["contractDrift"]["status"] == "in_sync"
    assert packet["paperclipRepository"] == {"skipped": True}
    assert any("FAULT_PLAYBOOK_FACTS_DRIFT_BATCH_4" in item["path"] for item in packet["progressArchives"])


def test_cli_json_output_and_file_output_are_stable(tmp_path):
    output = tmp_path / "handoff.json"

    result = subprocess.run(
        [sys.executable, str(TOOL), "--json", "--no-paperclip-status", "--output", str(output)],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
    )

    stdout_payload = json.loads(result.stdout)
    file_payload = json.loads(output.read_text(encoding="utf-8"))
    assert result.stderr == ""
    assert stdout_payload == file_payload
    assert stdout_payload["status"] in {"ready", "conditional_ready", "blocked"}
    assert stdout_payload["securityBoundaries"]["document"] == "docs/security_boundaries.md"


def test_markdown_render_contains_operator_handoff_sections():
    tool = load_tool()
    packet = tool.build_packet(ROOT, include_paperclip_status=False)

    markdown = tool.render_markdown(packet)

    assert "# Dark Factory Handoff Packet" in markdown
    assert "## Validation Summary" in markdown
    assert "## Security Boundary" in markdown
    assert "Dark Factory Journal remains truth source" in markdown
    assert "No credential values are read" in markdown


def test_sensitive_text_is_redacted_before_packet_output():
    tool = load_tool()

    assert tool.redact_sensitive_text("Authorization: Bearer abc123") == "[redacted]"
    assert tool.redact_sensitive_text("scoped token design preview only") == "scoped token design preview only"
    assert tool.redact_payload({"apiKey": "abc123", "safe": "visible"}) == {
        "apiKey": "[redacted]",
        "safe": "visible",
    }


def test_security_boundaries_doc_records_three_layers_and_scoped_token_preview():
    text = SECURITY_DOC.read_text(encoding="utf-8")

    required_terms = [
        "Three API Layers",
        "Public health/readiness",
        "Bridge/provider shim",
        "Operator-only local control",
        "Scoped Token Design Preview",
        "design preview only",
        "Dark Factory Journal remains truth source",
        "journal:read",
        "provider:gate",
        "handoff:read",
    ]
    for term in required_terms:
        assert term in text

    forbidden_examples = ["Bearer abc123", "sk-live", "password=secret", "LINGHUCALL_API_KEY="]
    for example in forbidden_examples:
        assert example not in text
