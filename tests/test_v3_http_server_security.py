import multiprocessing
import tempfile
import time
from pathlib import Path

import pytest

fastapi = pytest.importorskip("fastapi")
fcntl = pytest.importorskip("fcntl")
from fastapi.testclient import TestClient

from dark_factory_v3.journal import JournalLockTimeoutError, _acquire_lock
from server import PROTOCOL_RELEASE_TAG, api_key_from_environment, create_app, redact_sensitive


def make_client(tmpdir: str, *, api_key: str = "test-api-key") -> TestClient:
    return TestClient(create_app(journal_path=Path(tmpdir) / "journal.jsonl", api_key=api_key, auth_enabled=True))


def create_run_payload() -> dict[str, str]:
    return {
        "protocolReleaseTag": PROTOCOL_RELEASE_TAG,
        "requestedBy": "security-test",
        "workloadClass": "code",
        "inputRef": "input://security-test",
        "traceId": "trace-security-test",
        "runId": "run-security-test",
        "attemptId": "attempt-security-test",
    }


def test_health_endpoint_is_available_without_api_key():
    with tempfile.TemporaryDirectory() as tmpdir:
        response = make_client(tmpdir).get("/api/health")

    assert response.status_code == 200
    assert response.json()["protocolReleaseTag"] == PROTOCOL_RELEASE_TAG


def test_non_health_requests_require_valid_api_key():
    with tempfile.TemporaryDirectory() as tmpdir:
        client = make_client(tmpdir)
        missing = client.get("/api/projection")
        wrong = client.get("/api/projection", headers={"X-API-Key": "wrong"})

    assert missing.status_code == 401
    assert wrong.status_code == 401
    assert missing.json() == {
        "protocolReleaseTag": PROTOCOL_RELEASE_TAG,
        "error": "unauthorized",
        "message": "Invalid or missing API key",
    }


def test_create_run_succeeds_with_api_key():
    with tempfile.TemporaryDirectory() as tmpdir:
        client = make_client(tmpdir)
        response = client.post(
            "/api/external-runs",
            headers={
                "X-API-Key": "test-api-key",
                "X-Protocol-Release-Tag": PROTOCOL_RELEASE_TAG,
            },
            json=create_run_payload(),
        )

    assert response.status_code == 201
    assert response.json()["runState"] == "planning"


def test_api_key_file_takes_precedence_over_inline_environment():
    with tempfile.TemporaryDirectory() as tmpdir:
        key_file = Path(tmpdir) / "df_api_key.txt"
        key_file.write_text("file-secret\n", encoding="utf-8")

        key, source, generated = api_key_from_environment(
            env={"DF_API_KEY": "inline-secret", "DF_API_KEY_FILE": str(key_file)},
        )

    assert key == "file-secret"
    assert source == "file"
    assert generated is False


def test_redacts_sensitive_fields_recursively():
    redacted = redact_sensitive({
        "traceId": "trace-1",
        "apiKey": "secret-value",
        "nested": {
            "access_token": "token-value",
            "safe": "visible",
        },
    })

    assert redacted["apiKey"] == "***REDACTED***"
    assert redacted["nested"]["access_token"] == "***REDACTED***"
    assert redacted["nested"]["safe"] == "visible"


def test_file_backed_journal_lock_timeout():
    with tempfile.TemporaryDirectory() as tmpdir:
        journal_path = Path(tmpdir) / "journal.jsonl"
        journal_path.write_text("", encoding="utf-8")

        ready = multiprocessing.Event()
        release = multiprocessing.Event()

        def hold_lock(path: str) -> None:
            with Path(path).open("a+", encoding="utf-8") as handle:
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
                ready.set()
                release.wait(2)
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)

        process = multiprocessing.Process(target=hold_lock, args=(str(journal_path),))
        process.start()
        try:
            assert ready.wait(2)
            with journal_path.open("a+", encoding="utf-8") as handle:
                started_at = time.monotonic()
                try:
                    _acquire_lock(handle, fcntl.LOCK_EX, timeout_seconds=0.01)
                except JournalLockTimeoutError as exc:
                    assert "timed out" in str(exc)
                    assert time.monotonic() - started_at < 1
                else:
                    raise AssertionError("expected JournalLockTimeoutError")
        finally:
            release.set()
            process.join(2)
            if process.is_alive():
                process.terminate()
                process.join(2)
