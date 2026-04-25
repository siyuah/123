import importlib.util
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CLI_PATH = ROOT / "tools" / "v3_control_plane.py"
spec = importlib.util.spec_from_file_location("repo_v3_control_plane", CLI_PATH)
assert spec is not None and spec.loader is not None
v3_control_plane = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = v3_control_plane
spec.loader.exec_module(v3_control_plane)

from dark_factory_v3.projection import ProjectionState, RunProjection


class V3JournalVerificationInternalsTests(unittest.TestCase):
    def test_verify_projection_event_ids_fails_when_projection_id_not_in_journal(self):
        projection = ProjectionState(
            runs={
                "run-missing-001": RunProjection(
                    runId="run-missing-001",
                    currentState="planning",
                    eventIds=("evt-missing-from-journal",),
                )
            }
        )

        with self.assertRaises(v3_control_plane.JournalVerificationError) as ctx:
            v3_control_plane._verify_projection_event_ids(projection, {"evt-present-001"})

        self.assertEqual(ctx.exception.to_dict(), {
            "type": "JournalVerificationError",
            "checkId": "projection.event_ids_resolvable",
            "message": "runs run-missing-001 references eventId not found in journal",
            "eventId": "evt-missing-from-journal",
            "entityId": "run-missing-001",
            "collection": "runs",
        })


if __name__ == "__main__":
    unittest.main()
