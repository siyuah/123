import json
from pathlib import Path

import pytest
import yaml

fastapi = pytest.importorskip("fastapi")
from fastapi.testclient import TestClient

from server import PROTOCOL_RELEASE_TAG, create_app, guardrail_decision_for

ROOT = Path(__file__).resolve().parents[1]


def test_guardrail_decision_protocol_enums_schema_and_event_are_declared():
    enums = yaml.safe_load((ROOT / "paperclip_darkfactory_v3_0_core_enums.yaml").read_text(encoding="utf-8"))["enums"]
    schema = json.loads((ROOT / "paperclip_darkfactory_v3_0_core_objects.schema.json").read_text(encoding="utf-8"))
    events = yaml.safe_load((ROOT / "paperclip_darkfactory_v3_0_event_contracts.yaml").read_text(encoding="utf-8"))["events"]

    assert enums["approvalLevel"] == ["P0_dual_confirm", "P1_single_confirm", "P2_auto"]
    assert enums["guardrailDecision"] == ["allowed", "review_required", "blocked"]
    assert "GuardrailDecision" in schema["$defs"]
    assert "guardrail.decision.recorded" in {event["canonicalName"] for event in events}


def test_journal_delete_guardrail_blocks_without_mutating_journal(tmp_path):
    journal = tmp_path / "journal.jsonl"
    client = TestClient(create_app(journal_path=journal, api_key="test-api-key", auth_enabled=True))
    headers = {
        "X-API-Key": "test-api-key",
        "X-Protocol-Release-Tag": PROTOCOL_RELEASE_TAG,
    }
    create_response = client.post(
        "/api/external-runs",
        headers=headers,
        json={
            "protocolReleaseTag": PROTOCOL_RELEASE_TAG,
            "requestedBy": "guardrail-test",
            "workloadClass": "code",
            "inputRef": "input://guardrail",
            "traceId": "trace-guardrail",
            "runId": "run-guardrail",
            "attemptId": "attempt-guardrail",
        },
    )
    before = journal.read_text(encoding="utf-8")

    delete_response = client.delete("/api/journal", headers={"X-API-Key": "test-api-key"})

    assert create_response.status_code == 201
    assert delete_response.status_code == 403
    assert delete_response.json()["decision"] == "blocked"
    assert delete_response.json()["level"] == "P0_dual_confirm"
    assert delete_response.json()["truthSource"] == "dark-factory-journal"
    assert journal.read_text(encoding="utf-8") == before


def test_low_risk_guardrail_decision_is_allowed_projection():
    decision = guardrail_decision_for("projection.read", trace_id="trace-low-risk")

    assert decision.decision == "allowed"
    assert decision.level == "P2_auto"
    assert decision.confirmationRequired is False
    assert decision.authoritative is False
