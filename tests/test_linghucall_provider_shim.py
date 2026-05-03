import tempfile
from pathlib import Path

import pytest

fastapi = pytest.importorskip("fastapi")
from fastapi.testclient import TestClient

from linghucall_provider_shim import LinghuCallResult, create_app
from server import PROTOCOL_RELEASE_TAG


class FakeLinghuCallClient:
    def __init__(self) -> None:
        self.calls = []

    def chat_completion(self, *, run_id: str, trace_id: str, workload_class: str, input_ref: str) -> LinghuCallResult:
        self.calls.append({
            "run_id": run_id,
            "trace_id": trace_id,
            "workload_class": workload_class,
            "input_ref": input_ref,
        })
        return LinghuCallResult(
            responseId=f"resp-{run_id}",
            model="gpt-5.5",
            finishReason="stop",
            contentPreview="pong",
            usage={"prompt_tokens": 18, "completion_tokens": 5, "total_tokens": 23},
        )


def make_client(tmpdir: str, fake: FakeLinghuCallClient | None = None) -> TestClient:
    return TestClient(
        create_app(
            journal_path=Path(tmpdir) / "linghucall-shim.jsonl",
            bridge_api_key="bridge-key",
            auth_enabled=True,
            provider_client=fake or FakeLinghuCallClient(),
        ),
    )


def create_run_payload(run_id: str = "run-linghucall-shim") -> dict[str, str]:
    return {
        "protocolReleaseTag": PROTOCOL_RELEASE_TAG,
        "requestedBy": "shim-test",
        "workloadClass": "code",
        "inputRef": "paperclip://runs/shim-test",
        "traceId": "trace-linghucall-shim",
        "runId": run_id,
        "attemptId": f"attempt-{run_id}",
    }


def auth_headers() -> dict[str, str]:
    return {
        "X-API-Key": "bridge-key",
        "X-Protocol-Release-Tag": PROTOCOL_RELEASE_TAG,
    }


def test_health_is_open_and_redacts_provider_credential_state():
    with tempfile.TemporaryDirectory() as tmpdir:
        response = make_client(tmpdir).get("/api/health")

    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["protocolReleaseTag"] == PROTOCOL_RELEASE_TAG
    assert body["provider"]["kind"] == "linghucall_openai_compatible"
    assert body["provider"]["credentialValueRedacted"] is True


def test_non_health_requests_require_bridge_api_key():
    with tempfile.TemporaryDirectory() as tmpdir:
        client = make_client(tmpdir)
        missing = client.get("/api/external-runs/run-missing")
        wrong = client.get("/api/external-runs/run-missing", headers={"X-API-Key": "wrong"})

    assert missing.status_code == 401
    assert wrong.status_code == 401
    assert missing.json() == {
        "protocolReleaseTag": PROTOCOL_RELEASE_TAG,
        "error": "unauthorized",
        "message": "Invalid or missing API key",
    }


def test_create_external_run_invokes_linghucall_and_returns_dark_factory_contract():
    fake = FakeLinghuCallClient()
    with tempfile.TemporaryDirectory() as tmpdir:
        client = make_client(tmpdir, fake)
        response = client.post("/api/external-runs", headers=auth_headers(), json=create_run_payload())
        route_response = client.get("/api/external-runs/run-linghucall-shim/route-decisions", headers=auth_headers())
        journal_text = (Path(tmpdir) / "linghucall-shim.jsonl").read_text(encoding="utf-8")

    assert response.status_code == 201
    assert response.json() == {
        "protocolReleaseTag": PROTOCOL_RELEASE_TAG,
        "runId": "run-linghucall-shim",
        "runState": "planning",
        "traceId": "trace-linghucall-shim",
        "activeAttemptId": "attempt-run-linghucall-shim",
        "blockedBy": [],
        "currentManualGateType": None,
        "currentExecutionSuspensionState": None,
        "routeDecisionId": "rd-run-linghucall-shim",
        "journalCursor": "dark-factory://linghucall-shim/linghucall-shim.jsonl/run-linghucall-shim#1",
        "lastSequenceNo": 1,
        "sourceJournalRef": f"file://{Path(tmpdir) / 'linghucall-shim.jsonl'}",
    }
    assert fake.calls == [{
        "run_id": "run-linghucall-shim",
        "trace_id": "trace-linghucall-shim",
        "workload_class": "code",
        "input_ref": "paperclip://runs/shim-test",
    }]
    assert route_response.status_code == 200
    assert route_response.json()[0] | {
        "providerResponseId": "resp-run-linghucall-shim",
        "providerModel": "gpt-5.5",
        "providerFinishReason": "stop",
    } == route_response.json()[0]
    assert "resp-run-linghucall-shim" in journal_text
    assert "api_key" not in journal_text.lower()
    assert "authorization" not in journal_text.lower()


def test_duplicate_create_is_idempotent_and_does_not_reinvoke_provider():
    fake = FakeLinghuCallClient()
    with tempfile.TemporaryDirectory() as tmpdir:
        client = make_client(tmpdir, fake)
        first = client.post("/api/external-runs", headers=auth_headers(), json=create_run_payload())
        second = client.post("/api/external-runs", headers=auth_headers(), json=create_run_payload())

    assert first.status_code == 201
    assert second.status_code == 201
    assert second.json() == first.json()
    assert len(fake.calls) == 1


def test_park_and_rehydrate_preserve_non_terminal_contract():
    fake = FakeLinghuCallClient()
    with tempfile.TemporaryDirectory() as tmpdir:
        client = make_client(tmpdir, fake)
        client.post("/api/external-runs", headers=auth_headers(), json=create_run_payload())
        parked = client.post(
            "/api/external-runs/run-linghucall-shim:park",
            headers=auth_headers(),
            json={
                "protocolReleaseTag": PROTOCOL_RELEASE_TAG,
                "manualGateType": "manual_approval_required",
                "parkReasonCode": "operator_review",
                "rehydrationTokenId": "rt-linghucall-shim",
            },
        )
        rehydrated = client.post(
            "/api/external-runs/run-linghucall-shim:rehydrate",
            headers=auth_headers(),
            json={
                "protocolReleaseTag": PROTOCOL_RELEASE_TAG,
                "rehydrationTokenId": "rt-linghucall-shim",
            },
        )

    assert parked.status_code == 200
    assert parked.json()["runState"] == "parked_manual"
    assert parked.json()["blockedBy"] == ["parked_manual"]
    assert parked.json()["lastSequenceNo"] == 2
    assert rehydrated.status_code == 200
    assert rehydrated.json()["runState"] == "planning"
    assert rehydrated.json()["blockedBy"] == []
    assert rehydrated.json()["lastSequenceNo"] == 3
