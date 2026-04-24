# Paperclip × Dark Factory V3.0 Test Asset Spec

状态: binding-on-covered-obligations  
规范版本: 3.0  
protocolReleaseTag: `v3.0-agent-control-r1`  
scenarioPackVersion: `3.0-scenarios.1`

---

## 1. 命名规则

- Case ID: `TC-V30-<domain>-<3digit>`
- Fixture ID: `FX-V30-<domain>-<name>`
- Golden timeline: `GL-V30-<domain>-<name>.jsonl`
- Scenario ID: `SC-V30-<domain>-<3digit>`

## 2. 目录建议

```text
tests/
  fixtures/
    capability/
    lineage/
    capsule/
    schema/
    routing/
    memory/
    repair/
    manual/
    archive/
  golden_timelines/
  property/
  integration/
  fault_injection/
  scenario_acceptance/
```

## 3. Golden Timeline 格式

每行一个 JSON 事件，至少包含：

- `seq`
- `eventName`
- `eventVersion`
- `protocolReleaseTag`
- `traceId`
- `runId`
- `attemptId`（若相关）
- `artifactId`（若相关）
- `memoryArtifactId`（若相关）
- `repairAttemptId`（若相关）
- `expectedProjectionDelta`
- `expectedManualGate`
- `expectedExecutionSuspensionState`
- `expectedBlockNewHighRiskWrites`

`eventName` 必须使用 `paperclip_darkfactory_v3_0_event_contracts.yaml` 中声明的 canonical dotted.case。不得用 legacy alias 作为新的 golden baseline。

## 4. Failure Injection 钩子

必须预留以下可控注入点：

1. `claim_store_lease_timeout`
2. `broker_receipt_late_delivery`
3. `sidecar_audit_gap`
4. `mailbox_post_scan_high_risk_entry`
5. `artifact_reopen_after_downstream_start`
6. `context_length_exceeded_provider_400`
7. `legacy_writer_unknown_field_drop`
8. `archive_restore_not_found`
9. `trace_context_missing`
10. `operator_sla_timeout_then_park`
11. `provider_transient_timeout`
12. `provider_quota_exhausted`
13. `memory_consent_missing`
14. `repair_verification_failed`

## 5. 最小验收用例集合

### capability / opaque executor

- `TC-V30-capability-001`: declared read-only but observed brokered network write => `exceeded_declared`
- `TC-V30-capability-002`: direct public egress attempt => `broker_bypass_attempted`
- `TC-V30-capability-003`: runtime audit coverage missing blocks high-risk writes and marks `unverifiable`

### lineage / certification

- `TC-V30-lineage-001`: artifact `tentative -> certified`
- `TC-V30-lineage-002`: artifact `certified -> reopened` blocks downstream `certified_only` high-risk writes
- `TC-V30-lineage-003`: valid waiver affects only scoped consumer, not upstream certification history
- `TC-V30-lineage-004`: `revoked_upstream` cannot be waived into new high-risk primary write
- `TC-V30-lineage-005`: `tentative_upstream` returns to `clean` after upstream recertification

### routing / provider recovery

- `TC-V30-routing-001`: classifier records `route.decision.recorded.v1` for every execution attempt
- `TC-V30-routing-002`: `transient_timeout` maps to exactly one `recoveryLane`
- `TC-V30-routing-003`: cutover emits `provider.failure.recorded.v1` and `route.cutover.performed.v1`
- `TC-V30-routing-004`: `unverifiable` route can only degrade to low-risk when policy allows

### memory

- `TC-V30-memory-001`: `MemoryArtifact` creation records subject, confidence, consent, state and source trace
- `TC-V30-memory-002`: revoked/corrected/expired artifact is not injected as active prompt input
- `TC-V30-memory-003`: cross-session injection without required consent is blocked and receipted
- `TC-V30-memory-004`: prompt injection emits `memory.injection.recorded.v1`

### repair

- `TC-V30-repair-001`: provider response contract failure may enter repair lane when policy allows
- `TC-V30-repair-002`: successful repair requires sandbox verification evidence before main state advances
- `TC-V30-repair-003`: high-risk repair without operator approval becomes `repair_needs_manual`
- `TC-V30-repair-004`: repair cannot bypass schema write fence, lineage block or capability broker

### capsule / provider hard limit

- `TC-V30-capsule-001`: preflight failure enters `preflight_red`
- `TC-V30-capsule-002`: same `capsuleHash` poisoned retry is blocked
- `TC-V30-capsule-003`: provider context-length 400 enters poisoned breaker rather than blind retry

### schema / mixed deployment

- `TC-V30-schema-001`: old writer below `schema.minWriterVersion.v3_0_objects` is rejected
- `TC-V30-schema-002`: unknown field round-trip preservation remains 100% where compatibility layer permits
- `TC-V30-schema-003`: all view/error responses include `protocolReleaseTag`

### manual / parked mode

- `TC-V30-manual-001`: operator SLA timeout can park run, release compute and preserve truth obligation
- `TC-V30-manual-002`: rehydrate creates a new attempt and links trace/lineage to prior attempt
- `TC-V30-manual-003`: parked attempt cannot silently complete a high-risk run
- `TC-V30-manual-004`: `RehydrationToken` is single-use

### scenario / release gate

- `TC-V30-scenario-001`: every `release_blocker=true` scenario in scenario matrix is executed in CI
- `TC-V30-scenario-002`: scenario decision divergence above threshold blocks release
- `TC-V30-scenario-003`: memory miss and repair regression thresholds are enforced from runtime registry

## 6. Property / Model-based Testing 最低要求

至少覆盖：

- claim/fencing single writer invariant
- artifact reopen/revoke never rolls back history
- lineage invalidation does not leak new high-risk writes
- same capsule hash poisoned breaker has no infinite retry
- park -> rehydrate -> new attempt trace/linkage closure
- provider fault class -> recovery lane total and unique mapping
- memory scope/consent/retention denies injection when invalid
- repair lane cannot bypass capability/schema/lineage/manual gates

## 7. Contract Consistency Tests

release-blocking CI 必须验证：

1. enum parity: core enums, JSON Schema, OpenAPI, state matrix
2. event parity: `eventCanonicalName`, `event_contracts`, golden timelines
3. protocol release propagation: request, response, error, event envelope, manifest
4. source reference resolvability: registry/matrix/source keys point to defined source keys
5. scenario gate coverage: release blocker scenarios map to traceability rows and executable tests
6. manifest integrity: every listed path exists and SHA-256 matches

## 8. 合并主干前置条件

- 最小用例全部通过
- 新增状态、枚举、reason code、事件、对象字段已同步到 machine-readable bundle
- Golden timeline 与 state transition matrix 已更新
- Contract consistency tests 全部为绿
- Bundle manifest 与磁盘产物一致
