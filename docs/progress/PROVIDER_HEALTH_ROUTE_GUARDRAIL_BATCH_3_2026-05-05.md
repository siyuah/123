# Batch 3 Archive — Provider Health, Route Reasons, and Guardrails

Date: 2026-05-05
Repository: `siyuah/123`
Branch: `main`
Protocol release tag: `v3.0-agent-control-r1`

## Summary

Batch 3 implemented the Phoenix V4.8-inspired runtime operations layer for Dark Factory V3:

- Provider health projection from existing journal-backed route decisions.
- Explainable route decision reasons with standard reason codes.
- Guardrail decision model with P0/P1/P2 approval levels.
- Journal delete guardrail precheck that returns a blocked decision without mutating the append-only journal.
- Release gate reporting fix so ignored generated Python caches remain visible in audit output without becoming releasable changes.

All runtime projections remain non-authoritative. Dark Factory Journal remains truth source.

## Commits

1. `d974c9e` — `feat: add provider health route reasons and guardrail decisions`
2. `7090a0b` — `fix: report ignored generated caches in release gates`
3. `10375ee` — `chore: refresh V3 manifest after release gate cache reporting fix`

## Protocol Extensions

### Enums

Added to `paperclip_darkfactory_v3_0_core_enums.yaml`:

- `providerHealthState`: `healthy`, `degraded`, `exhausted`, `unreachable`, `rate_limited`, `unknown`
- `routeDecisionReasonCode`: workload, provider, guardrail, memory, repair, and fallback reason codes
- `riskLevel`: `low`, `medium`, `high`, `critical`
- `costLevel`: `low_cost`, `standard`, `expensive`, `operator_confirmed`
- `approvalLevel`: `P0_dual_confirm`, `P1_single_confirm`, `P2_auto`
- `guardrailDecision`: `allowed`, `review_required`, `blocked`

Added event canonical names:

- `provider.health.observed`
- `provider.fallback.activated`
- `provider.recovered`
- `guardrail.decision.recorded`

### Objects

Added to `paperclip_darkfactory_v3_0_core_objects.schema.json`:

- `ProviderHealthRecord`
- `RouteDecisionReason`
- `GuardrailDecision`

`RouteDecision.routeDecisionReasons` was added as an optional field to preserve compatibility with existing golden timelines and journal events.

### Event Contracts

Added event contracts for provider health observation, fallback activation, provider recovery, and guardrail decision recording in `paperclip_darkfactory_v3_0_event_contracts.yaml`.

### Runtime Config

Added config registry entries for:

- Provider health timeout
- Provider health rate-limit threshold
- Provider fallback enablement
- Default high-risk write approval level
- Journal delete approval level

## Server Implementation

Added to `server.py`:

- `ProviderHealthRecordView`
- `GuardrailDecisionView`
- `route_decision_reasons_for(...)`
- `provider_health_records(...)`
- `guardrail_decision_for(...)`
- `GET /provider-health`
- `GET /api/provider-health`
- `DELETE /journal`
- `DELETE /api/journal`

`/api/provider-health` is a derived projection from existing Journal-backed route decisions.

`DELETE /api/journal` returns HTTP 403 with a `GuardrailDecisionView` and does not delete, truncate, or mutate the journal.

## Tests

Added:

- `tests/test_v3_provider_health.py`
- `tests/test_v3_route_decision_reason.py`
- `tests/test_v3_guardrail.py`

Coverage:

- Provider health enum/schema declaration
- Provider health projection from created run and route decision
- Route decision reason enum/schema declaration
- Primary and fallback route reason projection
- Guardrail enum/schema/event declaration
- Blocked journal delete without journal mutation
- Low-risk guardrail projection returning allowed

## Additional Release Gate Fix

During full-suite validation, three release gate tests exposed an audit-reporting gap:

- Ignored Python cache artifacts were ignored by `.gitignore`.
- `git status --porcelain` did not show them.
- Tests expected release gates to show those generated artifacts in `ignoredStatusPorcelain`.

Fixed:

- `tools/v3_release_readiness.py`
- `tools/v3_release_dry_run.py`
- `tools/v3_release_evidence.py`

The tools now use `git status --porcelain --ignored=matching` and only surface ignored generated cache paths. This keeps clean release gating intact while making ignored generated artifacts auditable.

## Validation

Final validation after commits:

```text
.venv/bin/python tools/validate_v3_bundle.py
status: pass
checks: 12
errors: 0
warnings: 0
```

```text
.venv/bin/python -m pytest tests/ -v
105 passed
24 subtests passed
```

```text
.venv/bin/python tools/df_review_readiness.py --json
status: CONDITIONAL_READY
passed: 6
warned: 2
failed: 0
warnedChecks: smoke-evidence, bridge-evidence
```

The remaining readiness warnings are evidence-input warnings only; they indicate that smoke and bridge evidence files were not provided to the dashboard command in this run.

## Boundaries Preserved

- No secrets were read, printed, stored, or committed.
- Journal delete remains blocked in the preview API.
- Journal remains append-only.
- Provider health is a non-authoritative projection.
- `truthSource` remains `dark-factory-journal`.
- No standalone Dark Factory UI was claimed or introduced.

## Next Batch

Proceed to Batch 4:

- Fault playbooks
- Structured journal facts
- Contract drift detection

Batch 4 should continue using `paperclip_darkfactory_v3_0_bundle_manifest.yaml` classification and must keep generated outputs separate from source-of-truth binding artifacts.
