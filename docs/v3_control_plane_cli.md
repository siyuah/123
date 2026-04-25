# Paperclip × Dark Factory V3.0 control-plane CLI

This document is the operator contract for the minimal V3 control-plane CLI. It lets humans or agents run a complete journal-backed timeline without reading the Python source.

## Entrypoints

Run commands from the repository root:

```bash
python3 tools/v3_control_plane.py version
python3 tools/v3_control_plane.py <command> --journal /path/to/journal.jsonl ...
python3 tools/v3_control_plane_smoke.py --journal /tmp/v3-smoke.jsonl
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

Keep the journal at a known path:

```bash
python3 tools/v3_control_plane_smoke.py --journal /tmp/v3-control-plane-smoke.jsonl
```

The smoke script invokes `tools/v3_control_plane.py` through subprocess, appends this timeline, then replays projection:

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
  "projection": {"runs": {}, "attempts": {}, "routeDecisions": {}, "unknownEvents": []}
}
```

The script asserts that the run ends in `planning`, the original attempt is `superseded`, the new attempt is `created`, route decision `rd-smoke-001` exists, and event `sequenceNo` values are contiguous from 1.

## Append-only journal and replay semantics

- The journal is JSONL: one event envelope per line.
- Write commands load the whole journal, create a candidate event, replay the candidate timeline, and append only after projection validation passes.
- Duplicate `eventId` values are rejected.
- `sequenceNo` must strictly increase within each `correlationId`.
- Projection is derived state, not source of truth. Re-run `projection --journal ...` to rebuild it from the journal.

Do not hand-edit JSONL journals. Manual edits can break sequence invariants, duplicate detection, idempotency keys, or replay semantics. Create a new journal by replaying valid CLI commands instead.
