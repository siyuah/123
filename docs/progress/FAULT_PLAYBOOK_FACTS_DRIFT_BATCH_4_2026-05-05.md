# Batch 4 Archive — Fault Playbooks, Structured Facts, and Contract Drift

Date: 2026-05-05
Repository: `siyuah/123`
Branch: `main`
Protocol release tag: `v3.0-agent-control-r1`

## Summary

Batch 4 implemented the Phoenix/GStack-inspired operational support layer:

- `FaultPlaybook` registry with 8 common provider failure playbooks.
- `StructuredJournalFact` extractor for journal-derived facts.
- `ContractDriftReport` tool for enum/schema/event/summary drift.
- Deterministic generated contract summary in `docs/generated/V3_CONTRACT_SUMMARY.md`.

Facts are derived projections. They do not replace Journal truth events. Dark Factory Journal remains truth source.

## Commit

- `2968e3c` — `feat: add fault playbooks structured facts and contract drift tools`

## Protocol Extensions

Added enums in `paperclip_darkfactory_v3_0_core_enums.yaml`:

- `structuredJournalFactType`
- `contractDriftStatus`

Added event canonical names:

- `fault.playbook.registered`
- `journal.fact.extracted`
- `contract.drift.reported`

Added core object definitions in `paperclip_darkfactory_v3_0_core_objects.schema.json`:

- `FaultPlaybook`
- `StructuredJournalFact`
- `ContractDriftReport`

Added event contracts in `paperclip_darkfactory_v3_0_event_contracts.yaml`:

- `fault.playbook.registered.v1`
- `journal.fact.extracted.v1`
- `contract.drift.reported.v1`

## Runtime Modules

Added `dark_factory_v3/fault_playbooks.py`:

- Provides a deterministic 8-playbook registry.
- Maps provider fault classes to recovery lanes.
- Enforces non-authoritative projection boundaries.
- Allows automatic recovery only for low-risk `P2_auto` transient retry.

Added `dark_factory_v3/structured_facts.py`:

- Extracts facts from selected journal event families.
- Covers route decisions, provider failures, provider health, guardrails, memory artifacts, repair attempts, run state, and attempt state.
- Emits `authoritative: false` and `truthSource: dark-factory-journal`.
- Ignores unknown events instead of inventing facts.

## Tools

Added `tools/v3_contract_drift_report.py`:

- Checks protocol tag parity.
- Checks event enum and event contract parity.
- Checks schema enum definitions against `core_enums.yaml`.
- Checks Batch 4 schema definitions.
- Reuses V3 bundle validation.
- Checks generated summary freshness.

Added `tools/generate_v3_contract_summary.py`:

- Generates deterministic markdown summary from source artifacts.
- Includes source digests, counts, object definitions, event contracts, and Batch 4 surfaces.
- Writes `docs/generated/V3_CONTRACT_SUMMARY.md`.

## Tests

Added:

- `tests/test_v3_fault_playbooks.py`
- `tests/test_v3_structured_facts.py`
- `tests/test_v3_contract_drift_report.py`

Coverage:

- 8 common fault playbooks exist and validate.
- Fault-class recommendation maps to expected recovery lane.
- Auto recovery remains low-risk only.
- Structured facts are non-authoritative derived projections.
- Unknown events do not emit facts.
- Batch 4 schema/event/enum definitions are declared.
- Drift report passes current contracts.
- Drift report detects stale generated summary.
- Contract summary includes Batch 4 surfaces.

## Validation

Final clean validation:

```text
.venv/bin/python tools/validate_v3_bundle.py
status: pass
checks: 12
errors: 0
warnings: 0
```

```text
.venv/bin/python tools/v3_contract_drift_report.py --json --fail-on-drift
status: in_sync
failed: 0
warnings: 0
```

```text
.venv/bin/python tools/generate_v3_contract_summary.py --check --output docs/generated/V3_CONTRACT_SUMMARY.md
ok: true
```

```text
.venv/bin/python -m pytest tests/ -v
117 passed
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

The remaining readiness warnings mean smoke and bridge evidence were not supplied to the dashboard command in this run.

## Boundaries Preserved

- No secrets were read, printed, stored, or committed.
- No real provider or external service was contacted.
- No journal mutation is performed by the drift report or summary generator.
- Facts remain derived views and do not replace Journal truth events.
- Generated summary lives under `docs/generated/` and can be regenerated from source artifacts.

## Next Batch

Proceed to Batch 5:

- `tools/df_handoff_packet.py`
- `docs/security_boundaries.md`
- scoped token design preview
- progress archive structure follow-through
