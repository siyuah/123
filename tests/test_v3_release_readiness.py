import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
READINESS = ROOT / "tools/v3_release_readiness.py"


class V3ReleaseReadinessTests(unittest.TestCase):
    def run_readiness(self, *args, check=False):
        return subprocess.run(
            [sys.executable, str(READINESS), *args],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=check,
        )

    def test_skip_slow_outputs_ok_and_ci_workflow_presence_check(self):
        result = self.run_readiness("--skip-slow", check=True)

        payload = json.loads(result.stdout)
        by_id = {check["id"]: check for check in payload["checks"]}
        self.assertEqual(payload["ok"], True)
        self.assertEqual(payload["status"], "pass")
        self.assertIn("ci.workflow_presence", by_id)
        self.assertEqual(by_id["ci.workflow_presence"]["status"], "pass")
        self.assertEqual(by_id["unit.contracts"]["status"], "skipped")
        self.assertEqual(by_id["control_plane.smoke"]["status"], "skipped")
        self.assertEqual(by_id["journal.verify"]["status"], "skipped")
        self.assertIn("unit.contracts", payload["summary"]["skippedChecks"])
        self.assertEqual(result.stderr, "")

    def test_output_writes_report_and_stdout_includes_output_path(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            output = Path(tmpdir) / "release-readiness.json"

            result = self.run_readiness("--skip-slow", "--output", str(output), check=True)

            stdout_payload = json.loads(result.stdout)
            file_payload = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(stdout_payload["ok"], True)
            self.assertEqual(stdout_payload["outputPath"], str(output))
            self.assertEqual(file_payload, stdout_payload)

    def test_missing_ci_workflow_path_fails_with_stable_json(self):
        result = self.run_readiness("--skip-slow", "--ci-workflow", ".github/workflows/missing-v3-contracts.yml")

        payload = json.loads(result.stdout)
        by_id = {check["id"]: check for check in payload["checks"]}
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(payload["ok"], False)
        self.assertEqual(payload["status"], "fail")
        self.assertIn("ci.workflow_presence", payload["summary"]["failedChecks"])
        self.assertEqual(by_id["ci.workflow_presence"]["status"], "fail")
        self.assertIn("missing", by_id["ci.workflow_presence"]["message"])
        self.assertNotIn("Traceback", result.stdout)
        self.assertEqual(result.stderr, "")

    def test_make_release_readiness_v3_target_is_non_destructive_to_dry_run(self):
        result = subprocess.run(
            ["make", "-n", "release-readiness-v3"],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
        )

        self.assertIn("tools/v3_release_readiness.py", result.stdout)
        self.assertIn("--require-clean-git", result.stdout)


if __name__ == "__main__":
    unittest.main()
