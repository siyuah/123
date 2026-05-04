import importlib.util
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "df_review_readiness.py"


def load_tool():
    spec = importlib.util.spec_from_file_location("df_review_readiness", TOOL)
    module = importlib.util.module_from_spec(spec)
    sys.modules["df_review_readiness"] = module
    spec.loader.exec_module(module)
    return module


def write_minimal_contract(root: Path, *, include_protocol_tag: bool = True, drift: bool = False) -> None:
    tag = "v3.0-agent-control-r1" if include_protocol_tag else "missing-tag"
    (root / "paperclip_darkfactory_v3_0_bundle_manifest.yaml").write_text(
        "\n".join(
            [
                "files:",
                "  - path: paperclip_darkfactory_v3_0_core_enums.yaml",
                "    normativity: binding",
                "  - path: paperclip_darkfactory_v3_0_event_contracts.yaml",
                "    normativity: binding",
            ]
        ),
        encoding="utf-8",
    )
    (root / "paperclip_darkfactory_v3_0_core_enums.yaml").write_text(
        "\n".join(
            [
                "enums:",
                "  eventCanonicalName:",
                "    - run.created",
                "  runState:",
                "    - requested",
                "    - validating",
                "  attemptState: []",
                "  artifactCertificationState: []",
                "  inputDependencyState: []",
            ]
        ),
        encoding="utf-8",
    )
    event_name = "run.drifted" if drift else "run.created"
    (root / "paperclip_darkfactory_v3_0_event_contracts.yaml").write_text(
        f"protocolReleaseTag: {tag}\nevents:\n  - canonicalName: {event_name}\n",
        encoding="utf-8",
    )
    (root / "paperclip_darkfactory_v3_0_state_transition_matrix.csv").write_text(
        "domain,current_state,trigger,next_state\nrun,requested,accepted,validating\n",
        encoding="utf-8",
    )
    for name in [
        "paperclip_darkfactory_v3_0_core_objects.schema.json",
        "paperclip_darkfactory_v3_0_external_runs.openapi.yaml",
        "paperclip_darkfactory_v3_0_memory.openapi.yaml",
    ]:
        (root / name).write_text(f"protocolReleaseTag: {tag}\n", encoding="utf-8")
    (root / "paperclip_darkfactory_v3_0_scenario_acceptance_matrix.csv").write_text(
        "scenario_id,release_blocker\nSC-1,true\nSC-2,true\n",
        encoding="utf-8",
    )
    (root / "paperclip_darkfactory_v3_0_test_traceability.csv").write_text(
        "scenario_id,test_case_id\nSC-1,TC-1\n",
        encoding="utf-8",
    )
    (root / "AGENTS.md").write_text(
        "Coordinator Researcher Builder Writer df-contract-check Dark Factory Journal remains truth source\n",
        encoding="utf-8",
    )
    tools = root / "tools"
    tools.mkdir()
    (tools / "journal_admin.py").write_text(
        'def backup(): pass\ndef retain(): pass\ndef validate_jsonl(): pass\nsubcommands.add_parser("backup")\nsubcommands.add_parser("retain")\n',
        encoding="utf-8",
    )


def test_overall_status_aggregation():
    tool = load_tool()
    assert tool.overall_status([tool.CheckResult("a", "PASS", "ok"), tool.CheckResult("b", "SKIP", "skip")]) == "READY"
    assert tool.overall_status([tool.CheckResult("a", "PASS", "ok"), tool.CheckResult("b", "WARN", "warn")]) == "CONDITIONAL_READY"
    assert tool.overall_status([tool.CheckResult("a", "FAIL", "fail"), tool.CheckResult("b", "WARN", "warn")]) == "NOT_READY"


def test_bundle_files_check_identifies_missing_binding_file(tmp_path):
    tool = load_tool()
    write_minimal_contract(tmp_path)
    (tmp_path / "paperclip_darkfactory_v3_0_core_enums.yaml").unlink()

    result = tool.check_bundle_files(tmp_path)

    assert result.status == "FAIL"
    assert "paperclip_darkfactory_v3_0_core_enums.yaml" in result.details


def test_protocol_tag_check_identifies_missing_propagation(tmp_path):
    tool = load_tool()
    write_minimal_contract(tmp_path, include_protocol_tag=False)

    result = tool.check_protocol_tag(tmp_path)

    assert result.status == "FAIL"
    assert "missing protocolReleaseTag" in result.details


def test_contract_parity_check_identifies_event_drift(tmp_path):
    tool = load_tool()
    write_minimal_contract(tmp_path, drift=True)

    result = tool.check_contract_parity(tmp_path)

    assert result.status == "FAIL"
    assert "run.drifted" in result.details
    assert "run.created" in result.details


def test_json_output_format_and_only_filter():
    result = subprocess.run(
        [sys.executable, str(TOOL), "--json", "--only", "agents-md"],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
    )

    payload = json.loads(result.stdout)
    assert result.stderr == ""
    assert payload["reportType"] == "dark-factory-review-readiness"
    assert payload["status"] == "READY"
    assert payload["summary"]["total"] == 1
    assert payload["checks"][0]["id"] == "agents-md"
    assert payload["checks"][0]["status"] == "PASS"


def test_missing_evidence_is_warn_not_pass():
    result = subprocess.run(
        [sys.executable, str(TOOL), "--json"],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
    )

    payload = json.loads(result.stdout)
    by_id = {check["id"]: check for check in payload["checks"]}
    assert payload["status"] == "CONDITIONAL_READY"
    assert by_id["smoke-evidence"]["status"] == "WARN"
    assert by_id["bridge-evidence"]["status"] == "WARN"
