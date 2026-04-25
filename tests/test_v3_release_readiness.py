import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
READINESS = ROOT / "tools/v3_release_readiness.py"
REPORT_JSON = ROOT / "paperclip_darkfactory_v3_0_consistency_report.json"
REPORT_MD = ROOT / "paperclip_darkfactory_v3_0_consistency_report.md"


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

    def test_require_clean_git_reports_expected_generated_artifacts_as_ignored(self):
        (ROOT / "tests/__pycache__").mkdir(exist_ok=True)
        (ROOT / "tests/__pycache__" / "release_readiness_noise.pyc").write_bytes(b"generated")

        result = self.run_readiness("--skip-slow", "--require-clean-git")

        payload = json.loads(result.stdout)
        by_id = {check["id"]: check for check in payload["checks"]}
        self.assertEqual(result.stderr, "")
        self.assertNotIn("tests/__pycache__/", "\n".join(by_id["git.clean"]["details"]["releasableStatusPorcelain"]))
        self.assertIn("tests/__pycache__/", "\n".join(by_id["git.clean"]["details"]["ignoredStatusPorcelain"]))

    def test_release_readiness_does_not_modify_consistency_report_checked_at(self):
        before_json = REPORT_JSON.read_text(encoding="utf-8")
        before_md = REPORT_MD.read_text(encoding="utf-8")

        result = self.run_readiness("--skip-slow", check=True)

        self.assertEqual(result.stderr, "")
        self.assertEqual(REPORT_JSON.read_text(encoding="utf-8"), before_json)
        self.assertEqual(REPORT_MD.read_text(encoding="utf-8"), before_md)


if __name__ == "__main__":
    unittest.main()
