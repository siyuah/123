# V3 Release Readiness Gate

`tools/v3_release_readiness.py` is the local, offline readiness gate for Paperclip × Dark Factory V3.0. It produces stable JSON so humans, agents, and CI can decide whether the current V3 bundle is ready to promote without needing a GitHub token or network access.

## Quick use

```bash
python3 tools/v3_release_readiness.py
python3 tools/v3_release_readiness.py --skip-slow
python3 tools/v3_release_readiness.py --output /tmp/v3-release-readiness.json
python3 tools/v3_release_dry_run.py --tag v3.0.0-rc1 --output /tmp/v3-release-dry-run.json
make release-readiness-v3
make release-dry-run-v3 TAG=v3.0.0-rc1
```

`make release-dry-run-v3` runs a non-destructive release dry-run against `docs/v3_0_release_notes.md`. It validates release-note evidence, local readiness, and candidate tag availability, then prints recommended manual commands. It does not create a git tag, does not push, and does not call the GitHub Release API.

`make release-readiness-v3` runs:

```bash
python3 tools/v3_release_readiness.py --require-clean-git
```

That target is intended for final local release checks. Because it requires a clean worktree, run it after committing or after temporarily stashing unrelated local changes. The readiness script calls the in-process bundle validator and direct unit-test runner rather than `make test-v3-contracts`, so it should not refresh `checkedAt` or leave manifest/report changes behind.

## CLI options

- `--json`: JSON output mode. JSON is the default; this flag is accepted for explicit agent/CI usage.
- `--output PATH`: write the full report to `PATH`. Stdout still emits the same JSON and includes `outputPath`.
- `--skip-slow`: skip slower checks and mark them as `skipped` in the report. This currently skips `unit.contracts`, `control_plane.smoke`, and `journal.verify`.
- `--require-clean-git`: fail when `git status --porcelain` is non-empty.
- `--ci-workflow PATH`: override the workflow path checked for V3 CI gate presence. Defaults to `.github/workflows/v3-contracts.yml`.

## Report shape

Top-level fields:

- `ok`: boolean; true only when no check has `status: fail`.
- `status`: `pass` or `fail`.
- `git.headCommit`: short current commit hash.
- `git.branch`: current branch.
- `git.clean`: whether `git status --porcelain` is empty.
- `checks`: ordered list of check objects.
- `summary.checks`: total check count.
- `summary.failedChecks`: ids of failed checks.
- `summary.skippedChecks`: ids of skipped checks.
- `summary.warningChecks`: ids of warning checks.
- `outputPath`: present only when `--output PATH` is used.
- `error`: present only for an unexpected top-level failure; Python tracebacks are not printed for normal users.

Each check has:

- `id`: stable machine-readable check id.
- `status`: `pass`, `fail`, `skipped`, or `warn`.
- `message`: human-readable summary.
- `details`: optional structured diagnostics.

## Checks

Current readiness checks:

- `git.clean`: records branch/head/clean state, and fails if `--require-clean-git` is set and the worktree is dirty.
- `bundle.validate`: calls `tools.validate_v3_bundle.validate_bundle()` in-process without `--write-report`, avoiding `checkedAt` churn.
- `unit.contracts`: runs the V3 Python unittest contract suite directly unless `--skip-slow` is set.
- `control_plane.smoke`: runs `tools/v3_control_plane_smoke.py` against a temporary journal unless `--skip-slow` is set.
- `journal.verify`: verifies that temporary smoke journal via `tools.v3_control_plane.verify_journal_payload()` unless `--skip-slow` is set or smoke failed.
- `ci.workflow_presence`: confirms the V3 contracts workflow exists and contains required gates: `workflow_dispatch`, `actions/setup-python`, `make test-v3-contracts`, `make validate-v3`, `make smoke-v3-control-plane`, `make verify-v3-journal`, and `actions/upload-artifact`.

## Recommended local/CI flow

For normal local development:

```bash
make test-v3-contracts
make validate-v3
python3 tools/v3_release_readiness.py --skip-slow
```

Before promoting or tagging a V3 bundle:

```bash
make manifest-v3      # if manifest-covered files changed
make test-v3-contracts
make validate-v3
make release-readiness-v3
make release-dry-run-v3 TAG=v3.0.0-rc1
```

Use `docs/v3_0_release_notes.md` as the human-readable release summary for the dry-run. If `make validate-v3` only refreshes `paperclip_darkfactory_v3_0_consistency_report.json` / `.md` timestamps, revert those timestamp-only changes before committing. If manifest/checksum/report content changes substantively, include those changes in the commit.
