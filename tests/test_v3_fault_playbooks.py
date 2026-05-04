import json
from pathlib import Path

import yaml

from dark_factory_v3.fault_playbooks import (
    default_fault_playbooks,
    recommend_playbooks,
    validate_fault_playbook_registry,
)

ROOT = Path(__file__).resolve().parents[1]


def test_fault_playbook_registry_has_eight_common_fault_playbooks():
    playbooks = default_fault_playbooks()
    payload = [playbook.to_dict() for playbook in playbooks]

    assert len(playbooks) == 8
    assert validate_fault_playbook_registry(playbooks) == []
    assert all(item["authoritative"] is False for item in payload)
    assert all(item["truthSource"] == "dark-factory-journal" for item in payload)
    assert {fault for item in payload for fault in item["triggerFaultClasses"]} == {
        "transient_timeout",
        "transient_5xx",
        "rate_limited",
        "quota_exhausted",
        "auth_invalid",
        "capability_unsupported",
        "context_length_exceeded",
        "response_contract_invalid",
        "provider_unreachable",
    }


def test_fault_playbook_schema_and_event_contract_are_declared():
    enums = yaml.safe_load((ROOT / "paperclip_darkfactory_v3_0_core_enums.yaml").read_text(encoding="utf-8"))["enums"]
    schema = json.loads((ROOT / "paperclip_darkfactory_v3_0_core_objects.schema.json").read_text(encoding="utf-8"))
    events = yaml.safe_load((ROOT / "paperclip_darkfactory_v3_0_event_contracts.yaml").read_text(encoding="utf-8"))["events"]

    assert "FaultPlaybook" in schema["$defs"]
    assert schema["$defs"]["FaultPlaybook"]["properties"]["authoritative"]["const"] is False
    assert schema["$defs"]["FaultPlaybook"]["properties"]["truthSource"]["const"] == "dark-factory-journal"
    assert "fault.playbook.registered" in enums["eventCanonicalName"]
    assert "fault.playbook.registered" in {event["canonicalName"] for event in events}


def test_recommend_playbooks_maps_fault_class_to_recovery_lane():
    recommendations = recommend_playbooks("response_contract_invalid")

    assert [playbook.playbookId for playbook in recommendations] == ["response-contract-repair"]
    assert recommendations[0].recoveryLane == "enter_repair_lane"
    assert recommendations[0].autoRecoveryAllowed is False


def test_auto_recovery_is_low_risk_only():
    auto = [playbook for playbook in default_fault_playbooks() if playbook.autoRecoveryAllowed]

    assert [playbook.playbookId for playbook in auto] == ["transient-retry"]
    assert auto[0].riskLevel == "low"
    assert auto[0].approvalLevel == "P2_auto"
