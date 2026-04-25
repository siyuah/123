# Paperclip × Dark Factory V3.0 Agent Control Runtime

protocolReleaseTag: v3.0-agent-control-r1

## Release title

Paperclip × Dark Factory V3.0 Agent Control Runtime

## Release scope

This dry-run release candidate covers the local V3.0 agent-control runtime bundle at the current repository HEAD. It is intended to make the publish decision inspectable by humans and agents before any tag, push, GitHub Release, or production deployment is created.

Included scope:

- schema/contracts: core enums, object schema, event contracts, state transition matrix, runtime config registry, OpenAPI surfaces, storage mapping, responsibility matrix, and traceability assets.
- golden timelines: V3.0 JSONL golden timelines under tests/golden_timelines/v3_0 for routing, lineage, manual park/rehydrate, memory denial, and repair success scenarios.
- runtime reducer/projection: minimal runtime protocol objects, append-only event replay, reducer, projection, and state/event lineage coverage.
- file-backed journal CLI: local JSONL journal commands and projection output through tools/v3_control_plane.py.
- control-plane CLI: request-run, transition-run, transition-attempt, route-decision, manual park/rehydrate, projection, version, and verify-journal operator contracts.
- smoke contract: tools/v3_control_plane_smoke.py and make smoke-v3-control-plane generate a representative journal timeline.
- journal verification: make verify-v3-journal JOURNAL=... and verify-journal stable JSON diagnostics validate JSONL shape, envelope fields, sequence integrity, protocol tag, event versions, replay, and event-id resolvability.
- Makefile gates: make test-v3-contracts, make validate-v3, make smoke-v3-control-plane, make verify-v3-journal, make release-readiness-v3, make release-dry-run-v3, and optional remote-CI dry-run targets.
- GitHub Actions CI: .github/workflows/v3-contracts.yml and .github/workflows/v3-bundle-validate.yml provide repository-side validation coverage; optional remote-CI checks can inspect the latest main workflow through the gh CLI without requiring local release validation to be online.
- release readiness gate: tools/v3_release_readiness.py aggregates local bundle validation, runtime contracts, control-plane smoke, journal verification, CI workflow presence, optional remote CI status, and git cleanliness into stable JSON.
- release dry-run gate: tools/v3_release_dry_run.py checks this release notes document, release readiness, candidate tag availability, optional remote CI status, and suggested manual publication commands without creating any tag or release.

## Local pre-release verification commands

Run from the repository root before promoting a V3.0 release candidate:

```bash
make test-v3-contracts
make validate-v3
make smoke-v3-control-plane JOURNAL=/tmp/v3-control-plane-smoke.jsonl
make verify-v3-journal JOURNAL=/tmp/v3-control-plane-smoke.jsonl
make release-readiness-v3
make release-dry-run-v3 TAG=v3.0.0-rc1
make release-dry-run-v3-remote-ci TAG=v3.0.0-rc1
make release-evidence-v3 TAG=v3.0.0-rc1
make release-evidence-v3-remote-ci TAG=v3.0.0-rc1
```

`make release-dry-run-v3-remote-ci` is optional and best-effort: it uses the GitHub CLI to inspect the latest `main` run for `.github/workflows/v3-contracts.yml`, skips when `gh`, auth, network, or run history is unavailable, and does not create tags or releases. Use `make release-dry-run-v3-remote-ci-strict TAG=v3.0.0-rc1` only when a human wants latest remote CI success to be a blocking pre-release condition.

`make release-evidence-v3` emits a stable JSON RC evidence package that records this release notes file, bundle manifest, consistency report, readiness summary, dry-run summary, git cleanliness, and artifact hashes. It is offline by default. `make release-evidence-v3-remote-ci` adds the optional latest-`main` GitHub Actions observation and treats unavailable `gh`, auth, network, or workflow history as `skipped`; neither evidence target creates a tag, pushes, or calls the GitHub Release API.

For machine-readable artifacts:

```bash
python3 tools/v3_release_readiness.py --output /tmp/v3-release-readiness.json
python3 tools/v3_release_dry_run.py --tag v3.0.0-rc1 --output /tmp/v3-release-dry-run.json
python3 tools/v3_release_evidence.py --tag v3.0.0-rc1 --output /tmp/v3-release-evidence.json
```

## Key commit range

Release summary range: `40ef551 docs: add Dark Factory V3.0 documentation bundle` through current HEAD.

Notable commits in this V3.0 agent-control runtime line:

- `40ef551 docs: add Dark Factory V3.0 documentation bundle`
- `cd57f56 chore: add V3 bundle validation gate`
- `9714db9 Add V3 runtime contract skeleton`
- `96995ca Add V3 runtime projection reducer`
- `f081522 Add V3 file-backed journal CLI`
- `fa32a79 Expand V3 control-plane CLI commands`
- `6bf84ef Add V3 control-plane smoke contract`
- `72e8e36 Add V3 journal verification CLI`
- `68a1feb Add V3 contracts CI workflow`
- `2b6a7d9 Add V3 release readiness gate`
- Current HEAD: 2b6a7d9

## Known non-goals and limitations

- Does not include real external agent scheduling or live executor dispatch.
- Does not depend on secrets, GitHub tokens, cloud credentials, or network access for local release validation.
- Does not create production infrastructure, deployment artifacts, Git tags, or GitHub Releases.
- Does not commit `__pycache__/`, `.pyc`, or other interpreter caches produced by test/readiness runs.
- Does not commit timestamp-only `checkedAt` churn in `paperclip_darkfactory_v3_0_consistency_report.json` or `.md`; revert timestamp-only validate output before committing.
- Does not treat optional remote tag checking as a hard blocker when the network or remote is unavailable; local tag existence remains the authoritative offline safety check.
- Does not treat optional remote CI inspection as a local/offline blocker unless `--require-remote-ci-success` or the strict Makefile target is explicitly requested.

## Rollback and troubleshooting

### Bad or suspicious journal

Use `verify-journal` first, before trusting projection output:

```bash
python3 tools/v3_control_plane.py verify-journal --journal /path/to/journal.jsonl --output /tmp/v3-journal-verify.json
make verify-v3-journal JOURNAL=/path/to/journal.jsonl
```

The stable JSON report identifies the failed `checkId` and usually includes `lineNumber`, `eventId`, `entityId`, or collection details. Start with sequence and envelope failures, then replay/projection failures. If a smoke journal is needed for comparison, regenerate one with:

```bash
make smoke-v3-control-plane JOURNAL=/tmp/v3-control-plane-smoke.jsonl
```

### Failed release readiness

Run:

```bash
python3 tools/v3_release_readiness.py --output /tmp/v3-release-readiness.json
```

Inspect `summary.failedChecks`, `summary.warningChecks`, and each check object in `checks`. Typical actions:

- `git.clean`: commit, stash, or revert local changes before final release gating.
- `bundle.validate`: run `make manifest-v3` when manifest-covered files changed, then `make validate-v3`.
- `unit.contracts`: rerun `make test-v3-contracts` and inspect the failing unittest.
- `control_plane.smoke`: run `make smoke-v3-control-plane JOURNAL=/tmp/v3-smoke.jsonl` for direct CLI diagnostics.
- `journal.verify`: run `make verify-v3-journal JOURNAL=/tmp/v3-smoke.jsonl` or the direct verify-journal command above.
- `ci.workflow_presence`: inspect `.github/workflows/v3-contracts.yml` for missing gate commands.
- `ci.latest_main_workflow`: when optional remote CI is enabled, inspect the check `details.url`, `details.status`, `details.conclusion`, and `details.headSha`; skipped means the GitHub CLI, auth, network, or workflow history was unavailable and does not invalidate local release evidence.

### Failed release dry-run

Run:

```bash
python3 tools/v3_release_dry_run.py --tag v3.0.0-rc1 --output /tmp/v3-release-dry-run.json
```

Inspect `summary.failedChecks` and `summary.warningChecks`. A pass means the next manual commands are only recommendations in `recommendedCommands`; the dry-run itself never creates a local tag, never pushes, and never calls the GitHub Release API. When `ci.latest_main_workflow` appears as a warning, use `details.url` and `details.headSha` to compare the latest remote run with the intended release HEAD before deciding whether to rerun CI or use strict mode.
