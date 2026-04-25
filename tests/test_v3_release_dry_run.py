import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DRY_RUN = ROOT / "tools/v3_release_dry_run.py"
TAG = "v3.0.0-rc1"


class V3ReleaseDryRunTests(unittest.TestCase):
    def run_dry_run(self, *args):
        return subprocess.run(
            [sys.executable, str(DRY_RUN), *args],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )

    def tag_exists(self, tag=TAG):
        result = subprocess.run(
            ["git", "tag", "--list", tag],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
        )
        return result.stdout.strip() == tag

    def test_dry_run_outputs_ok_writes_output_path_and_does_not_create_tag(self):
        self.assertFalse(self.tag_exists())
        with tempfile.TemporaryDirectory() as tmpdir:
            output = Path(tmpdir) / "v3-release-dry-run.json"

            result = self.run_dry_run("--tag", TAG, "--output", str(output))

            self.assertEqual(result.stderr, "")
            self.assertEqual(result.returncode, 0, result.stdout)
            stdout_payload = json.loads(result.stdout)
            file_payload = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(stdout_payload, file_payload)
            self.assertEqual(stdout_payload["ok"], True)
            self.assertEqual(stdout_payload["status"], "pass")
            self.assertEqual(stdout_payload["tag"], TAG)
            self.assertEqual(stdout_payload["outputPath"], str(output))
            self.assertIn("recommendedCommands", stdout_payload)
            self.assertIn(f"git tag -a {TAG}", "\n".join(stdout_payload["recommendedCommands"]))
            self.assertFalse(self.tag_exists())

    def test_missing_release_notes_fails_with_stable_json(self):
        result = self.run_dry_run("--tag", TAG, "--notes", "docs/missing-v3-release-notes.md")

        payload = json.loads(result.stdout)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(result.stderr, "")
        self.assertEqual(payload["ok"], False)
        self.assertEqual(payload["status"], "fail")
        self.assertIn("release_notes.exists", payload["summary"]["failedChecks"])
        self.assertNotIn("Traceback", result.stdout)

    def test_release_notes_missing_protocol_release_tag_fails_with_stable_json(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as tmpdir:
            rel = Path(tmpdir).relative_to(ROOT) / "notes.md"
            (ROOT / rel).write_text(
                "# Paperclip × Dark Factory V3.0 Agent Control Runtime\n\n"
                "make test-v3-contracts\nmake validate-v3\nmake release-readiness-v3\n"
                ".github/workflows/v3-contracts.yml\n",
                encoding="utf-8",
            )

            result = self.run_dry_run("--tag", TAG, "--notes", str(rel))

        payload = json.loads(result.stdout)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(result.stderr, "")
        self.assertIn("release_notes.content", payload["summary"]["failedChecks"])
        by_id = {check["id"]: check for check in payload["checks"]}
        self.assertIn("protocolReleaseTag", by_id["release_notes.content"]["details"]["missingStrings"])
        self.assertNotIn("Traceback", result.stdout)

    def test_make_release_dry_run_v3_target_invokes_dry_run_without_creating_tag(self):
        self.assertFalse(self.tag_exists())
        result = subprocess.run(
            ["make", "-n", "release-dry-run-v3", f"TAG={TAG}"],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
        )

        self.assertIn("tools/v3_release_dry_run.py", result.stdout)
        self.assertIn(f"--tag {TAG}", result.stdout)
        self.assertIn("--require-clean-git", result.stdout)
        self.assertFalse(self.tag_exists())

    def test_make_release_dry_run_v3_allows_generated_pycache_noise_and_writes_stable_json(self):
        self.assertFalse(self.tag_exists())
        (ROOT / "tools/__pycache__").mkdir(exist_ok=True)
        (ROOT / "tools/__pycache__" / "release_dry_run_noise.pyc").write_bytes(b"generated")

        result = subprocess.run(
            ["make", "release-dry-run-v3", f"TAG={TAG}"],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )

        stderr = result.stderr.replace("make[1]: *** [Makefile:34: release-dry-run-v3] Error 1\n", "")
        payload = json.loads(result.stdout)
        by_id = {check["id"]: check for check in payload["checks"]}
        self.assertEqual(stderr, "")
        self.assertNotIn("tools/__pycache__/", "\n".join(by_id["git.clean"]["details"]["releasableStatusPorcelain"]))
        self.assertIn("tools/__pycache__/", "\n".join(by_id["git.clean"]["details"]["ignoredStatusPorcelain"]))
        self.assertFalse(self.tag_exists())


if __name__ == "__main__":
    unittest.main()
