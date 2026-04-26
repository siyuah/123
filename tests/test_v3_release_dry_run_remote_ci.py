import json
import os
import stat
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DRY_RUN = ROOT / "tools/v3_release_dry_run.py"
TAG = "v3.0.0-rc1-test-dry-run-remote-ci"


class V3ReleaseDryRunRemoteCITests(unittest.TestCase):
    def run_dry_run(self, *args, env=None):
        run_env = os.environ.copy()
        if env:
            run_env.update(env)
        return subprocess.run(
            [sys.executable, str(DRY_RUN), *args],
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

    def remote_ci_check(self, payload):
        by_id = {check["id"]: check for check in payload["checks"]}
        return by_id["ci.latest_main_workflow"]

    def test_include_remote_ci_skips_when_gh_is_missing_and_ok_remains_true(self):
        with tempfile.TemporaryDirectory() as tmp:
            env = {"V3_REMOTE_CI_GH_BIN": str(Path(tmp) / "gh")}
            result = self.run_dry_run("--tag", TAG, "--include-remote-ci", "--skip-remote-tag-check", env=env)

        payload = json.loads(result.stdout)
        check = self.remote_ci_check(payload)
        self.assertEqual(result.stderr, "")
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertEqual(payload["ok"], True)
        self.assertEqual(check["status"], "skipped")
        self.assertIn("gh CLI", check["message"])
        self.assertEqual(check["details"]["workflow"], "v3-contracts.yml")
        self.assertEqual(check["details"]["branch"], "main")

    def test_include_remote_ci_auth_failure_warns_and_ok_remains_true(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmpdir = Path(tmp)
            self.make_fake_gh(
                tmpdir,
                "#!/usr/bin/env python3\n"
                "import sys\n"
                "if sys.argv[1:3] == ['auth', 'status']:\n"
                "    print('not logged in', file=sys.stderr)\n"
                "    raise SystemExit(1)\n"
                "raise SystemExit(2)\n",
            )
            result = self.run_dry_run(
                "--tag", TAG, "--include-remote-ci", "--skip-remote-tag-check", env=self.env_with_fake_gh(tmpdir)
            )

        payload = json.loads(result.stdout)
        check = self.remote_ci_check(payload)
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertEqual(payload["ok"], True)
        self.assertEqual(check["status"], "skipped")
        self.assertIn("auth", check["message"])
        self.assertNotIn("Traceback", result.stdout)

    def test_include_remote_ci_passes_for_completed_success_and_exposes_url_and_head_sha(self):
        run_payload = [
            {
                "status": "completed",
                "conclusion": "success",
                "headSha": "0123456789abcdef",
                "url": "https://github.com/siyuah/123/actions/runs/1",
                "displayTitle": "V3 contracts",
                "createdAt": "2026-04-25T00:00:00Z",
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
                f"    print({json.dumps(json.dumps(run_payload))})\n"
                "    raise SystemExit(0)\n"
                "raise SystemExit(2)\n",
            )
            result = self.run_dry_run(
                "--tag", TAG, "--include-remote-ci", "--skip-remote-tag-check", env=self.env_with_fake_gh(tmpdir)
            )

        payload = json.loads(result.stdout)
        check = self.remote_ci_check(payload)
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertEqual(payload["ok"], True)
        self.assertEqual(check["status"], "pass")
        self.assertEqual(check["details"]["status"], "completed")
        self.assertEqual(check["details"]["conclusion"], "success")
        self.assertEqual(check["details"]["headSha"], "0123456789abcdef")
        self.assertEqual(check["details"]["url"], "https://github.com/siyuah/123/actions/runs/1")

    def test_include_remote_ci_failure_warns_by_default_but_strict_mode_fails(self):
        run_payload = [
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
                f"    print({json.dumps(json.dumps(run_payload))})\n"
                "    raise SystemExit(0)\n"
                "raise SystemExit(2)\n",
            )
            env = self.env_with_fake_gh(tmpdir)
            default_result = self.run_dry_run("--tag", TAG, "--include-remote-ci", "--skip-remote-tag-check", env=env)
            strict_result = self.run_dry_run(
                "--tag",
                TAG,
                "--include-remote-ci",
                "--require-remote-ci-success",
                "--skip-remote-tag-check",
                env=env,
            )

        default_payload = json.loads(default_result.stdout)
        default_check = self.remote_ci_check(default_payload)
        self.assertEqual(default_result.returncode, 0, default_result.stdout)
        self.assertEqual(default_payload["ok"], True)
        self.assertEqual(default_check["status"], "warn")
        self.assertEqual(default_check["details"]["conclusion"], "failure")

        strict_payload = json.loads(strict_result.stdout)
        strict_check = self.remote_ci_check(strict_payload)
        self.assertNotEqual(strict_result.returncode, 0)
        self.assertEqual(strict_payload["ok"], False)
        self.assertEqual(strict_check["status"], "fail")
        self.assertIn("ci.latest_main_workflow", strict_payload["summary"]["failedChecks"])

    def test_default_release_dry_run_does_not_call_gh(self):
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
            result = self.run_dry_run("--tag", TAG, "--skip-remote-tag-check", env=self.env_with_fake_gh(tmpdir))

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertEqual(payload["ok"], True)
        self.assertNotIn("ci.latest_main_workflow", {check["id"] for check in payload["checks"]})
        self.assertFalse(marker.exists())

    def test_make_remote_ci_targets_invoke_expected_flags(self):
        result = subprocess.run(
            ["make", "-n", "release-dry-run-v3-remote-ci", f"TAG={TAG}"],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
        )
        self.assertIn("--include-remote-ci", result.stdout)
        self.assertIn("--require-clean-git", result.stdout)
        self.assertNotIn("--require-remote-ci-success", result.stdout)

        strict_result = subprocess.run(
            ["make", "-n", "release-dry-run-v3-remote-ci-strict", f"TAG={TAG}"],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
        )
        self.assertIn("--include-remote-ci", strict_result.stdout)
        self.assertIn("--require-remote-ci-success", strict_result.stdout)


if __name__ == "__main__":
    unittest.main()
