import json
import os
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "tools/v3_release_evidence.py"
TAG = "v3.0.0-rc1"


class V3ReleaseEvidenceTests(unittest.TestCase):
    def run_evidence(self, *args, env=None):
        run_env = os.environ.copy()
        if env:
            run_env.update(env)
        return subprocess.run(
            [sys.executable, str(EVIDENCE), *args],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            env=run_env,
        )

    def make_fake_gh(self, tmpdir: Path, script: str) -> Path:
        gh = tmpdir / "gh"
        gh.write_text(script, encoding="utf-8")
        gh.chmod(gh.stat().st_mode | stat.S_IXUSR)
        return gh

    def env_with_fake_gh(self, tmpdir: Path):
        return {"PATH": f"{tmpdir}{os.pathsep}{os.environ.get('PATH', '')}"}

    def by_id(self, payload):
        return {check["id"]: check for check in payload["checks"]}

    def test_default_evidence_outputs_json_and_does_not_call_gh(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmpdir = Path(tmp)
            marker = tmpdir / "gh-called"
            self.make_fake_gh(
                tmpdir,
                "#!/usr/bin/env python3\n"
                "from pathlib import Path\n"
                f"Path({str(marker)!r}).write_text('called', encoding='utf-8')\n"
                "raise SystemExit(99)\n",
            )
            result = self.run_evidence("--tag", TAG, env=self.env_with_fake_gh(tmpdir))

        payload = json.loads(result.stdout)
        self.assertEqual(result.stderr, "")
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertEqual(payload["ok"], True)
        self.assertEqual(payload["status"], "pass")
        self.assertEqual(payload["tag"], TAG)
        self.assertRegex(payload["headSha"], r"^[0-9a-f]{40}$")
        self.assertIn("branch", payload)
        self.assertIn("checkedAt", payload)
        self.assertIn("releaseNotesPath", payload)
        self.assertIn("bundleManifestPath", payload)
        self.assertIn("consistencyReportPath", payload)
        self.assertIn("readiness", payload)
        self.assertIn("dryRun", payload)
        self.assertIn("summary", payload["readiness"])
        self.assertIn("summary", payload["dryRun"])
        self.assertGreaterEqual(len(payload["artifacts"]), 5)
        roles = {artifact["role"] for artifact in payload["artifacts"]}
        self.assertIn("release_notes", roles)
        self.assertIn("bundle_manifest", roles)
        self.assertIn("consistency_report_json", roles)
        self.assertNotIn("ci.latest_main_workflow", self.by_id(payload))
        self.assertFalse(marker.exists())

    def test_output_writes_same_json_and_stdout_contains_output_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "v3-release-evidence.json"
            result = self.run_evidence("--tag", TAG, "--output", str(output))
            stdout_payload = json.loads(result.stdout)
            file_payload = json.loads(output.read_text(encoding="utf-8"))

        self.assertEqual(result.stderr, "")
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertEqual(stdout_payload, file_payload)
        self.assertEqual(stdout_payload["outputPath"], str(output))

    def test_require_clean_git_fails_for_functional_uncommitted_change(self):
        path = ROOT / "v3_release_evidence_functional_change.tmp"
        try:
            path.write_text("functional change", encoding="utf-8")
            result = self.run_evidence("--tag", TAG, "--require-clean-git")
        finally:
            path.unlink(missing_ok=True)

        payload = json.loads(result.stdout)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(payload["ok"], False)
        self.assertIn("git.clean", payload["summary"]["failedChecks"])
        git_check = self.by_id(payload)["git.clean"]
        self.assertTrue(any("v3_release_evidence_functional_change.tmp" in line for line in git_check["details"]["releasableStatusPorcelain"]))

    def test_require_clean_git_allows_generated_pycache_noise(self):
        pycache = ROOT / "tools/__pycache__"
        pycache.mkdir(exist_ok=True)
        (pycache / "evidence_noise.pyc").write_bytes(b"generated")

        result = self.run_evidence("--tag", TAG, "--require-clean-git")

        payload = json.loads(result.stdout)
        git_check = self.by_id(payload)["git.clean"]
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertEqual(payload["ok"], True)
        self.assertNotIn("tools/__pycache__/", "\n".join(git_check["details"]["releasableStatusPorcelain"]))
        self.assertIn("tools/__pycache__/", "\n".join(git_check["details"]["ignoredStatusPorcelain"]))

    def test_include_remote_ci_skips_when_gh_missing_and_ok_remains_true(self):
        with tempfile.TemporaryDirectory() as tmp:
            env = {"V3_REMOTE_CI_GH_BIN": str(Path(tmp) / "gh")}
            result = self.run_evidence("--tag", TAG, "--include-remote-ci", env=env)

        payload = json.loads(result.stdout)
        check = self.by_id(payload)["ci.latest_main_workflow"]
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertEqual(payload["ok"], True)
        self.assertEqual(check["status"], "skipped")

    def test_include_remote_ci_pass_warn_and_fail_behaviors(self):
        failed_run = [
            {
                "status": "completed",
                "conclusion": "failure",
                "headSha": "deadbeefdeadbeef",
                "url": "https://github.com/siyuah/123/actions/runs/2",
                "displayTitle": "V3 contracts failed",
                "createdAt": "2026-04-25T01:00:00Z",
            }
        ]
        with tempfile.TemporaryDirectory() as tmp:
            tmpdir = Path(tmp)
            self.make_fake_gh(
                tmpdir,
                "#!/usr/bin/env python3\n"
                "import json, sys\n"
                "if sys.argv[1:3] == ['auth', 'status']:\n"
                "    raise SystemExit(0)\n"
                "if sys.argv[1:3] == ['run', 'list']:\n"
                f"    print({json.dumps(json.dumps(failed_run))})\n"
                "    raise SystemExit(0)\n"
                "raise SystemExit(2)\n",
            )
            env = self.env_with_fake_gh(tmpdir)
            default_result = self.run_evidence("--tag", TAG, "--include-remote-ci", env=env)
            strict_result = self.run_evidence("--tag", TAG, "--include-remote-ci", "--require-remote-ci-success", env=env)

        default_payload = json.loads(default_result.stdout)
        default_check = self.by_id(default_payload)["ci.latest_main_workflow"]
        self.assertEqual(default_result.returncode, 0, default_result.stdout)
        self.assertEqual(default_payload["ok"], True)
        self.assertEqual(default_check["status"], "warn")

        strict_payload = json.loads(strict_result.stdout)
        strict_check = self.by_id(strict_payload)["ci.latest_main_workflow"]
        self.assertNotEqual(strict_result.returncode, 0)
        self.assertEqual(strict_payload["ok"], False)
        self.assertEqual(strict_check["status"], "fail")
        self.assertIn("ci.latest_main_workflow", strict_payload["summary"]["failedChecks"])

    def test_make_release_evidence_v3_stdout_is_pure_json(self):
        result = subprocess.run(
            ["make", "release-evidence-v3", f"TAG={TAG}"],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )

        payload = json.loads(result.stdout)
        self.assertEqual(result.stderr, "")
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertEqual(payload["tag"], TAG)
        self.assertTrue(result.stdout.lstrip().startswith("{"))
        self.assertFalse(result.stdout.lstrip().startswith("python3"))


if __name__ == "__main__":
    unittest.main()
