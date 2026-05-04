import json
from pathlib import Path

import pytest
import yaml

fastapi = pytest.importorskip("fastapi")
from fastapi.testclient import TestClient

from server import PROTOCOL_RELEASE_TAG, create_app

ROOT = Path(__file__).resolve().parents[1]


def load_enums() -> dict:
    return yaml.safe_load((ROOT / "paperclip_darkfactory_v3_0_core_enums.yaml").read_text(encoding="utf-8"))["enums"]


def load_schema() -> dict:
    return json.loads((ROOT / "paperclip_darkfactory_v3_0_core_objects.schema.json").read_text(encoding="utf-8"))


def test_provider_health_protocol_enums_and_schema_are_declared():
    enums = load_enums()
    schema = load_schema()

    assert enums["providerHealthState"] == [
        "healthy",
        "degraded",
        "exhausted",
        "unreachable",
        "rate_limited",
        "unknown",
    ]
    assert "ProviderHealthRecord" in schema["$defs"]
    provider_health = schema["$defs"]["ProviderHealthRecord"]
    assert provider_health["properties"]["status"]["$ref"] == "#/$defs/ProviderHealthState"
    assert provider_health["properties"]["fallbackEligible"]["type"] == "boolean"


def test_provider_health_projection_is_derived_from_journal_route_decisions(tmp_path):
    client = TestClient(create_app(journal_path=tmp_path / "journal.jsonl", api_key="test-api-key", auth_enabled=True))
    headers = {
        "X-API-Key": "test-api-key",
        "X-Protocol-Release-Tag": PROTOCOL_RELEASE_TAG,
    }

    create_response = client.post(
        "/api/external-runs",
        headers=headers,
        json={
            "protocolReleaseTag": PROTOCOL_RELEASE_TAG,
            "requestedBy": "provider-health-test",
            "workloadClass": "code",
            "inputRef": "input://provider-health",
            "traceId": "trace-provider-health",
            "runId": "run-provider-health",
            "attemptId": "attempt-provider-health",
            "selectedExecutorClass": "provider-code-primary",
        },
    )
    health_response = client.get("/api/provider-health", headers={"X-API-Key": "test-api-key"})

    assert create_response.status_code == 201
    assert health_response.status_code == 200
    payload = health_response.json()
    assert payload == [
        {
            "protocolReleaseTag": PROTOCOL_RELEASE_TAG,
            "providerId": "provider-code-primary",
            "status": "healthy",
            "faultClass": None,
            "lastFailureAt": None,
            "recoveryLane": "retry_same_route",
            "fallbackEligible": False,
            "authoritative": False,
            "truthSource": "dark-factory-journal",
        }
    ]
