import json
from pathlib import Path

import yaml

from tools.generate_v3_contract_summary import render_summary
from tools.v3_contract_drift_report import build_report

ROOT = Path(__file__).resolve().parents[1]


def test_contract_drift_report_passes_current_contracts():
    report = build_report(ROOT, summary_path="docs/generated/V3_CONTRACT_SUMMARY.md")

    assert report["ok"] is True
    assert report["status"] == "in_sync"
    assert report["summary"]["failed"] == 0
    assert {check["id"] for check in report["checks"]} >= {
        "protocol-tags",
        "event-parity",
        "schema-enum-parity",
        "batch4-definitions",
        "bundle-validation",
        "generated-summary",
    }


def test_contract_drift_report_detects_stale_generated_summary(tmp_path):
    summary = tmp_path / "stale.md"
    summary.write_text("stale\n", encoding="utf-8")

    report = build_report(ROOT, summary_path=str(summary))
    check = {item["id"]: item for item in report["checks"]}["generated-summary"]

    assert report["ok"] is False
    assert report["status"] == "drift_detected"
    assert check["status"] == "fail"


def test_contract_summary_contains_batch4_surfaces():
    summary = render_summary(ROOT)

    assert "FaultPlaybook" in summary
    assert "StructuredJournalFact" in summary
    assert "ContractDriftReport" in summary
    assert "`structuredJournalFactType` enum: 8 values" in summary
    assert "`contractDriftStatus` enum: 2 values" in summary


def test_contract_drift_schema_and_event_contract_are_declared():
    enums = yaml.safe_load((ROOT / "paperclip_darkfactory_v3_0_core_enums.yaml").read_text(encoding="utf-8"))["enums"]
    schema = json.loads((ROOT / "paperclip_darkfactory_v3_0_core_objects.schema.json").read_text(encoding="utf-8"))
    events = yaml.safe_load((ROOT / "paperclip_darkfactory_v3_0_event_contracts.yaml").read_text(encoding="utf-8"))["events"]

    assert enums["contractDriftStatus"] == ["in_sync", "drift_detected"]
    assert "ContractDriftReport" in schema["$defs"]
    assert schema["$defs"]["ContractDriftReport"]["properties"]["status"]["$ref"] == "#/$defs/ContractDriftStatus"
    assert "contract.drift.reported" in {event["canonicalName"] for event in events}
