# Paperclip × Dark Factory V3.0 control-plane CLI

This document is the operator contract for the minimal V3 control-plane CLI. It lets humans or agents run a complete journal-backed timeline without reading the Python source.

## Entrypoints

Run commands from the repository root:

```bash
python3 tools/v3_control_plane.py version
python3 tools/v3_control_plane.py <command> --journal /path/to/journal.jsonl ...
python3 tools/v3_control_plane_smoke.py --journal /tmp/v3-smoke.jsonl
make smoke-v3-control-plane JOURNAL=/tmp/v3-smoke.jsonl
make verify-v3-journal JOURNAL=/tmp/v3-smoke.jsonl
```

`tools/v3_control_plane.py` writes and replays an append-only JSONL journal. Every write command requires `--journal`, `--correlation-id`, and `--trace-id`. `projection` replays the journal and does not append an event.

## Commands and required arguments

### version

Required arguments: none.

Outputs a stable JSON contract summary containing `protocolReleaseTag`, the supported command list, event version summary, producer, and journal/projection semantics.

### request-run

Required:

- `--journal`
- `--run-id`
- `--correlation-id`
- `--trace-id`

Optional:

- `--event-id`

Appends `run.lifecycle.transitioned` for `requested -> validating` with trigger `request_accepted`.

### transition-run

Required:

- `--journal`
- `--run-id`
- `--old-state`
- `--new-state`
- `--transition-trigger`
- `--correlation-id`
- `--trace-id`

Optional: `--event-id`.

Appends a run lifecycle transition after validating the replayed projection.

### transition-attempt

Required:

- `--journal`
- `--run-id`
- `--attempt-id`
- `--old-state`
- `--new-state`
- `--transition-trigger`
- `--correlation-id`
- `--trace-id`

Optional: `--event-id`.

Appends an attempt lifecycle transition after validating the replayed projection.

### record-route-decision

Required:

- `--journal`
- `--run-id`
- `--attempt-id`
- `--route-decision-id`
- `--workload-class`
- `--route-policy-ref`
- `--selected-executor-class`
- `--fallback-depth`
- `--decision-reason`
- `--correlation-id`
- `--trace-id`

Optional:

- `--route-decision-state` (default `selected_primary`)
- `--recorded-at`
- `--event-id`

Appends `route.decision.recorded`.

### park-manual

Required:

- `--journal`
- `--run-id`
- `--attempt-id`
- `--park-id`
- `--manual-gate-type`
- `--rehydration-token-id`
- `--correlation-id`
- `--trace-id`

Optional:

- `--execution-suspension-state` (default `resources_released_truth_obligation_retained`)
- `--parked-at`
- `--event-id`

Appends `manual_gate.parked`.

### rehydrate-manual

Required:

- `--journal`
- `--run-id`
- `--previous-attempt-id`
- `--new-attempt-id`
- `--rehydration-token-id`
- `--correlation-id`
- `--trace-id`

Optional:

- `--rehydrated-at`
- `--event-id`

Appends `manual_gate.rehydrated`. Current reducer semantics project the run back to `planning`, mark the previous attempt `superseded`, and create the new attempt as `created`.

### verify-journal

Required:

- `--journal`

Optional:

- `--output PATH`: write the complete stable verify JSON report to `PATH`. Stdout still emits the same stable JSON and includes `outputPath`.
- `--run-id RUN_ID`: replay the full journal, then filter only `projectionSummary` to the requested run and related attempts/route decisions. `fullProjectionSummary` remains available so CI can confirm full replay scope.
- `--strict-empty`: explicitly locks the CI contract that an empty journal fails. Empty journals fail by default; this flag is present for agent/CI scripts that want the requirement visible in command logs.

Verifies an append-only JSONL journal before replay/projection consumers trust it. Recommended gate: run `verify-journal` before `projection`, replay, or any downstream projection/materialization job.

Checks are stable objects with this shape:

```json
{"id": "jsonl.valid_json", "status": "pass", "message": "journal contains only non-empty JSON object lines"}
```

Current check ids:

- `jsonl.valid_json`: every non-empty line is a JSON object.
- `journal.not_empty`: the journal contains at least one event. Empty journals fail by default and with `--strict-empty`.
- `journal.sequence_contiguous`: `sequenceNo` starts at 1 and increments by exactly 1 for every journal line.
- `journal.event_id_unique`: every `eventId` is unique.
- `envelope.required_fields`: `correlationId`, `traceId`, `eventName`, `emittedAt`, `eventId`, and `eventVersion` are present.
- `envelope.protocol_release_tag`: `protocolReleaseTag` is exactly `v3.0-agent-control-r1`.
- `envelope.event_version_compatible`: `eventVersion` is compatible with the current known event contract for `eventName`.
- `projection.replay`: the full journal can be replayed by `RunLifecycleReducer`.
- `projection.event_ids_unique`: every projected run/attempt has unique `eventIds`.
- `projection.event_ids_resolvable`: every projected run/attempt `eventId` exists in the journal.

Success output is stable JSON:

```json
{
  "ok": true,
  "journal": "/tmp/v3-control-plane-smoke.jsonl",
  "events": 8,
  "checks": [{"id": "jsonl.valid_json", "status": "pass", "message": "..."}],
  "checkIds": ["jsonl.valid_json", "journal.not_empty", "..."],
  "projectionSummary": {"runs": 1, "attempts": 2, "routeDecisions": 1, "unknownEvents": 0},
  "outputPath": "/tmp/v3-control-plane-smoke.verify.json"
}
```

With `--run-id run-smoke-001`, `projectionSummary` is filtered after full replay and `fullProjectionSummary` records the unfiltered totals:

```json
{
  "ok": true,
  "runId": "run-smoke-001",
  "events": 9,
  "projectionSummary": {"runs": 1, "attempts": 2, "routeDecisions": 1, "unknownEvents": 0},
  "fullProjectionSummary": {"runs": 2, "attempts": 2, "routeDecisions": 1, "unknownEvents": 0}
}
```

Failure output is stable JSON on stderr and exits non-zero without a Python traceback. `error.type` is `JournalVerificationError`; `error.checkId` is the failed check id. Location fields are included when available: `lineNumber`, `eventId`, `entityId`, and `collection`.

```json
{
  "ok": false,
  "error": {
    "type": "JournalVerificationError",
    "checkId": "journal.sequence_contiguous",
    "message": "expected sequenceNo 2, got 3",
    "lineNumber": 2,
    "eventId": "evt-corr-smoke-001-0002"
  }
}
```

### projection

Required:

- `--journal`

Replays the current JSONL journal and prints stable JSON projection state: `runs`, `attempts`, `routeDecisions`, and `unknownEvents`.

## Success and failure JSON

Write command success:

```json
{
  "ok": true,
  "event": {"eventName": "...", "sequenceNo": 1}
}
```

Projection success:

```json
{
  "ok": true,
  "projection": {"runs": {}, "attempts": {}, "routeDecisions": {}, "unknownEvents": []}
}
```

Control-plane validation failure writes stable JSON to stderr and exits non-zero:

```json
{
  "ok": false,
  "error": {
    "type": "ControlPlaneError",
    "message": "illegal run transition ..."
  }
}
```

Argparse usage errors use argparse's default stderr format.

## End-to-end smoke script

Run a complete timeline with a temporary journal:

```bash
python3 tools/v3_control_plane_smoke.py
```

Keep the journal at a known path and optionally keep the verify report:

```bash
python3 tools/v3_control_plane_smoke.py --journal /tmp/v3-control-plane-smoke.jsonl --verify-report /tmp/v3-control-plane-smoke.verify.json
make smoke-v3-control-plane JOURNAL=/tmp/v3-control-plane-smoke.jsonl
make verify-v3-journal JOURNAL=/tmp/v3-control-plane-smoke.jsonl
```

The smoke script invokes `tools/v3_control_plane.py` through subprocess, appends this timeline, replays projection, then runs `verify-journal` against the generated journal:

1. `request-run`
2. `record-route-decision`
3. `transition-attempt created -> booting`
4. `transition-attempt booting -> active`
5. `transition-run validating -> planning`
6. `transition-run planning -> executing`
7. `park-manual`
8. `rehydrate-manual`
9. `projection`

Success output is stable JSON:

```json
{
  "ok": true,
  "journal": "/tmp/v3-control-plane-smoke.jsonl",
  "events": 8,
  "sequenceNos": [1, 2, 3, 4, 5, 6, 7, 8],
  "projection": {"runs": {}, "attempts": {}, "routeDecisions": {}, "unknownEvents": []},
  "verifyJournal": {"ok": true, "events": 8, "checks": [{"id": "jsonl.valid_json", "status": "pass", "message": "..."}], "projectionSummary": {}}
}
```

The script asserts that the run ends in `planning`, the original attempt is `superseded`, the new attempt is `created`, route decision `rd-smoke-001` exists, event `sequenceNo` values are contiguous from 1, projection event lineage has no duplicate event ids, and `verify-journal` succeeds with object checks before the smoke output is accepted.

## CI/agent recommended flow

Use the same journal path through the flow so diagnostics can be inspected if a later stage fails:

```bash
make test-v3-contracts
make validate-v3
make smoke-v3-control-plane JOURNAL=/tmp/v3-control-plane-smoke.jsonl
make verify-v3-journal JOURNAL=/tmp/v3-control-plane-smoke.jsonl
python3 tools/v3_control_plane.py projection --journal /tmp/v3-control-plane-smoke.jsonl
```

The GitHub Actions workflow `.github/workflows/v3-contracts.yml` runs on pushes to `main`, pull requests targeting `main`, and manual `workflow_dispatch`. It uses Ubuntu with Python 3.12 and stays offline after standard `actions/checkout` and `actions/setup-python` setup. The CI gate runs `make test-v3-contracts`, `make validate-v3`, validates that `make smoke-v3-control-plane` emits parseable JSON with `ok=true` and `verifyJournal.ok=true`, then creates a temporary smoke journal and runs `make verify-v3-journal JOURNAL="$RUNNER_TEMP/v3_smoke.jsonl"`.

Optional release dry-run remote CI checks are available through `python3 tools/v3_release_dry_run.py --include-remote-ci`, `make release-dry-run-v3-remote-ci TAG=v3.0.0-rc1`, and strict `make release-dry-run-v3-remote-ci-strict TAG=v3.0.0-rc1`. They use the GitHub CLI only to inspect the latest `main` workflow run and never create a tag, never push, and never call the GitHub Release API; missing `gh`, auth, network, or run history is reported as `skipped` unless strict success is explicitly required.

For RC handoff evidence, run `make release-evidence-v3 TAG=v3.0.0-rc1` to emit one stable JSON package containing release notes, bundle manifest, consistency report, readiness, dry-run, git cleanliness, and artifact hashes. It is offline by default. `make release-evidence-v3-remote-ci TAG=v3.0.0-rc1` adds the same optional latest-`main` remote CI observation used by dry-run. Evidence generation is non-destructive: it never creates tags/releases, never pushes, and never calls the GitHub Release API.

Both Makefile control-plane targets are expected to emit stdout that can be passed directly to `json.loads` or `python -m json.tool`; recipe command echoes, `make` directory banners, and shell `echo` prefixes are contract violations. CI uploads the smoke JSON, smoke journal, and verify JSON as the `v3-control-plane-diagnostics` artifact for failure analysis.

For persisted diagnostics, call `verify-journal` directly with `--output /tmp/v3-control-plane-smoke.verify.json`. For scoped dashboards, add `--run-id RUN_ID`; this never weakens validation because the full journal is replayed before the summary is filtered.

### Projection lineage contract

- `RunProjection.eventIds` and `AttemptProjection.eventIds` are unique, ordered envelope lineage.
- The order is the first time each `EventEnvelope.eventId` contributes to that run or attempt projection during replay.
- Compound events such as `manual_gate.rehydrated` may fold multiple internal state transitions into one projection update (for example `parked_manual -> rehydrating -> planning` for the run, and `parked_manual -> rehydrate_pending -> superseded` for the previous attempt), but they still list that envelope's `eventId` only once per affected projection.
- Internal state folding is not duplicate envelope lineage. Use each listed `eventId` to look up exactly one JSONL envelope in the append-only journal.

## Append-only journal and replay semantics

- The journal is JSONL: one event envelope per line.
- Write commands load the whole journal, create a candidate event, replay the candidate timeline, and append only after projection validation passes.
- Duplicate `eventId` values are rejected.
- `sequenceNo` must strictly increase within each `correlationId`.
- Projection is derived state, not source of truth. Re-run `projection --journal ...` to rebuild it from the journal.

Do not hand-edit JSONL journals. Manual edits can break sequence invariants, duplicate detection, idempotency keys, or replay semantics. Create a new journal by replaying valid CLI commands instead.
