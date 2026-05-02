from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

fastapi = pytest.importorskip("fastapi")
from fastapi.testclient import TestClient

from dark_factory_v3.journal import FileBackedJsonlJournal
from server import PROTOCOL_RELEASE_TAG, create_app


def run_payload(index: int) -> dict[str, str]:
    return {
        "protocolReleaseTag": PROTOCOL_RELEASE_TAG,
        "requestedBy": "load-test",
        "workloadClass": "code",
        "inputRef": f"input://load/{index}",
        "traceId": f"trace-load-{index}",
        "runId": f"run-load-{index}",
        "attemptId": f"attempt-load-{index}",
    }


def test_concurrent_external_run_creation_uses_locked_jsonl_journal():
    with TemporaryDirectory() as tmpdir:
        journal_path = Path(tmpdir) / "journal.jsonl"
        app = create_app(journal_path=journal_path, api_key="load-key", auth_enabled=True)

        def create_run(index: int) -> int:
            with TestClient(app) as client:
                response = client.post(
                    "/api/external-runs",
                    headers={
                        "X-API-Key": "load-key",
                        "X-Protocol-Release-Tag": PROTOCOL_RELEASE_TAG,
                    },
                    json=run_payload(index),
                )
            return response.status_code

        with ThreadPoolExecutor(max_workers=8) as executor:
            statuses = list(executor.map(create_run, range(12)))

        assert statuses == [201] * 12
        events = FileBackedJsonlJournal.load(journal_path).read_all()
        assert len(events) == 36
        assert len({event.eventId for event in events}) == 36
