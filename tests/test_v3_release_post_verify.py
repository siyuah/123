import json
import unittest
import urllib.error
from pathlib import Path
from unittest import mock

import sys

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import v3_release_post_verify as post_verify  # noqa: E402


TAG = "v3.0.0-rc1"
EXPECTED_TARGET = "cafad42e70bc2d431e902bc5f2d659cb00cb0df6"
TAG_OBJECT = "1ac0b980148cadf4c3172b564773a625c2cc1777"


class V3ReleasePostVerifyTests(unittest.TestCase):
    def fake_github_json(self, url, *, timeout):
        if url.endswith(f"/git/ref/tags/{TAG}"):
            return {
                "ref": f"refs/tags/{TAG}",
                "object": {
                    "sha": TAG_OBJECT,
                    "type": "tag",
                    "url": f"https://api.github.com/repos/siyuah/123/git/tags/{TAG_OBJECT}",
                },
            }
        if url.endswith(f"/git/tags/{TAG_OBJECT}"):
            return {"object": {"sha": EXPECTED_TARGET, "type": "commit"}}
        if url.endswith(f"/releases/tags/{TAG}"):
            return {
                "tag_name": TAG,
                "target_commitish": EXPECTED_TARGET,
                "draft": False,
                "prerelease": True,
                "html_url": f"https://github.com/siyuah/123/releases/tag/{TAG}",
            }
        raise AssertionError(f"unexpected URL: {url}")

    def test_build_report_passes_with_public_release_state(self):
        args = type(
            "Args",
            (),
            {"root": str(ROOT), "tag": TAG, "expected_target": EXPECTED_TARGET, "timeout": 1, "require_clean_git": True},
        )()
        with mock.patch.object(post_verify, "github_json", side_effect=self.fake_github_json), mock.patch.object(
            post_verify,
            "check_git_clean",
            return_value=(
                {"branch": "main", "headSha": EXPECTED_TARGET, "clean": True, "requireCleanGit": True, "statusPorcelain": []},
                post_verify.make_check("git.clean", "pass", "git working tree is clean"),
            ),
        ):
            report = post_verify.build_report(args)

        self.assertEqual(report["ok"], True, json.dumps(report, indent=2))
        self.assertEqual(report["status"], "pass")
        self.assertEqual(report["tag"], TAG)
        self.assertEqual(report["expectedTargetSha"], EXPECTED_TARGET)
        self.assertTrue(report["postReleaseVerifyOnly"])
        self.assertEqual(report["repo"], "siyuah/123")
        by_id = {check["id"]: check for check in report["checks"]}
        self.assertEqual(by_id["git.local_tag_exists"]["status"], "pass")
        self.assertEqual(by_id["git.local_tag_target"]["details"]["peeledTargetSha"], EXPECTED_TARGET)
        self.assertEqual(by_id["github.tag_ref"]["status"], "pass")
        self.assertEqual(by_id["github.release"]["status"], "pass")
        self.assertTrue(any("does not read or print tokens" in item for item in report["nonDestructiveGuarantees"]))

    def test_github_release_mismatch_fails_stable_check(self):
        def fake_json(url, *, timeout):
            if url.endswith(f"/git/ref/tags/{TAG}"):
                return {"ref": f"refs/tags/{TAG}", "object": {"sha": EXPECTED_TARGET, "type": "commit"}}
            if url.endswith(f"/releases/tags/{TAG}"):
                return {"tag_name": TAG, "target_commitish": "deadbeef", "draft": True, "prerelease": False}
            raise AssertionError(url)

        args = type("Args", (), {"root": str(ROOT), "tag": TAG, "expected_target": EXPECTED_TARGET, "timeout": 1, "require_clean_git": False})()
        with mock.patch.object(post_verify, "github_json", side_effect=fake_json):
            report = post_verify.build_report(args)

        self.assertEqual(report["ok"], False)
        self.assertIn("github.release", report["summary"]["failedChecks"])
        by_id = {check["id"]: check for check in report["checks"]}
        self.assertEqual(by_id["github.release"]["status"], "fail")
        self.assertEqual(by_id["github.release"]["details"]["targetCommitish"], "deadbeef")

    def test_network_unavailable_fails_without_token_or_traceback(self):
        def raise_url_error(url, *, timeout):
            raise urllib.error.URLError("network unavailable")

        args = type("Args", (), {"root": str(ROOT), "tag": TAG, "expected_target": EXPECTED_TARGET, "timeout": 1, "require_clean_git": False})()
        with mock.patch.object(post_verify, "github_json", side_effect=raise_url_error):
            report = post_verify.build_report(args)

        rendered = json.dumps(report)
        self.assertEqual(report["ok"], False)
        self.assertIn("github.tag_ref", report["summary"]["failedChecks"])
        self.assertIn("github.release", report["summary"]["failedChecks"])
        self.assertNotIn("Traceback", rendered)
        self.assertNotIn("ghp_", rendered)
        self.assertNotIn("github_pat_", rendered)

    def test_make_post_release_verify_target_invokes_read_only_tool(self):
        import subprocess

        result = subprocess.run(
            ["make", "-n", "post-release-verify-v3", f"TAG={TAG}", f"EXPECTED_TARGET={EXPECTED_TARGET}"],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
        )
        self.assertIn("tools/v3_release_post_verify.py", result.stdout)
        self.assertIn(f"--tag {TAG}", result.stdout)
        self.assertIn(f"--expected-target {EXPECTED_TARGET}", result.stdout)
        self.assertTrue(result.stdout.rstrip().endswith(f"--expected-target {EXPECTED_TARGET}"))
        self.assertNotIn("git tag -a", result.stdout)
        self.assertNotIn("git push", result.stdout)


if __name__ == "__main__":
    unittest.main()
