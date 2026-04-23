# Paperclip × Dark Factory V2.9 Test Asset Spec

**绑定版本**：v2.9-companion-bound-r1

## 1. 命名规则

- Case ID：`TC-V29-<domain>-<3digit>`
- Fixture ID：`FX-V29-<domain>-<name>`
- Golden timeline：`GL-V29-<domain>-<name>.jsonl`

## 2. 目录建议

```text
tests/
  fixtures/
    capability/
    lineage/
    capsule/
    schema/
    archive/
    manual/
  golden_timelines/
  property/
  integration/
  fault_injection/
```

## 3. Golden Timeline 格式

每行一个 JSON 事件，至少包含：

- `seq`
- `eventName`
- `eventVersion`
- `protocolReleaseTag`
- `traceId`
- `runId`
- `attemptId`
- `artifactId`（若相关）
- `expectedProjectionDelta`
- `expectedManualGate`
- `expectedExecutionSuspensionState`
- `expectedBlockNewHighRiskWrites`

Golden timeline 中的 `eventName` 必须使用 canonical dotted.case，且与 `paperclip_darkfactory_v2_9_event_contracts.yaml` 完全一致。
历史 snake_case 事件名只能作为 legacy alias fixture 出现，不能作为新的 golden baseline。

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

## 5. 最小验收用例集合

### capability / opaque executor

- `TC-V29-capability-001`：声明只读，但 observed 出现 brokered network write，状态应变为 `exceeded_declared`
- `TC-V29-capability-002`：直接公网出站尝试，状态应变为 `broker_bypass_attempted`
- `TC-V29-capability-003`：runtime audit coverage 缺失，高风险写必须被阻断并落到 `unverifiable`

### lineage / certification

- `TC-V29-lineage-001`：artifact `tentative -> certified`
- `TC-V29-lineage-002`：artifact `certified -> reopened` 后，下游 `certified_only` run 阻断新的 high-risk write
- `TC-V29-lineage-003`：valid `consumptionWaiverRef` 只能改变指定 consumer 的 gate，不改上游认证态
- `TC-V29-lineage-004`：`revoked_upstream` 时 waiver 不得放行新的 high-risk primary write
- `TC-V29-lineage-005`：`tentative_upstream` consumer 在 artifact 转为 `certified` 后可回到 `clean`

### capsule / provider hard limit

- `TC-V29-capsule-001`：preflight 失败必须进入 `preflight_red`
- `TC-V29-capsule-002`：相同 `capsuleHash` 的 poisoned retry 被阻断
- `TC-V29-capsule-003`：chars/token_estimate 低估导致 provider 400 时，必须进入 poisoned breaker，而不是 blind retry

### schema / mixed deployment

- `TC-V29-schema-001`：旧 writer 尝试写入 `minWriterSchemaVersion=2.9.0` 对象时被 write fence 拒绝
- `TC-V29-schema-002`：unknown field round-trip = 100%
- `TC-V29-schema-003`：旧 reader 只允许保守解释，不得默认成功
- `TC-V29-schema-004`：`ParkRecord`、`RehydrationToken`、`ManualGateDefinition` 都必须回写 `protocolReleaseTag`

### archive / restore

- `TC-V29-archive-001`：mailbox TTL 到期只可归档，不得 silent delete
- `TC-V29-archive-002`：restore path 在目标 SLA 内可检索指定 evidence
- `TC-V29-archive-003`：hold record 存在时归档对象不可被清除

### manual / parked mode

- `TC-V29-manual-001`：operator SLA 超时后 run 可 park，compute 资源释放但 truth obligation 保留
- `TC-V29-manual-002`：rehydrate 后新 attempt 与旧 attempt 的 lineage/trace 可串联
- `TC-V29-manual-003`：parked 状态下不得静默完成 high-risk run
- `TC-V29-manual-004`：`manualGateType=manual_evidence_access_required` 在 OpenAPI、schema、golden timeline 字面量必须完全一致
- `TC-V29-manual-005`：同一个 `rehydrateTokenRef` 最多只允许一次成功消费

### contract consistency

- `TC-V29-contract-001`：`core_enums.yaml` 与主文档中的 `manualGateType` 枚举完全一致
- `TC-V29-contract-002`：主文档、`event_contracts.yaml`、golden timeline 的 canonical event name 完全一致
- `TC-V29-contract-003`：OpenAPI 所有 mutation operation 都声明 `X-Protocol-Release-Tag`
- `TC-V29-contract-004`：所有 view/error 响应都能回写 `protocolReleaseTag`
- `TC-V29-contract-005`：所有 golden timeline 事件的 `protocolReleaseTag` 必须等于 `v2.9-companion-bound-r1`
- `TC-V29-contract-006`：所有 golden timeline 事件的 `eventVersion` 必须与 `paperclip_darkfactory_v2_9_event_contracts.yaml` 中声明完全一致

### measurement / release gate

- `TC-V29-shadow-001`：protected flow 上 `deadlineCrossed=true` 时，shadow 不能算 pass
- `TC-V29-shadow-002`：`weightedHighRiskDecisionDivergence` 计算与 appendix 一致
- `TC-V29-shadow-003`：timing-only shift 仅产生 0.25 penalty，不可伪装为 decision divergence

## 6. Property / Model-based Testing 最低要求

至少对以下域做 property-based 或 model-based test：

- claim/fencing 单 writer 不变量
- artifact reopen/revoke 不回退历史
- lineage invalidation 不允许新 high-risk write 漏放
- same capsule hash poisoned breaker 不出现无限重试
- unknown-field preservation 不丢字段
- parked_manual -> rehydrate -> new attempt 的 trace/linkage 闭合

## 7. Contract Consistency Tests

以下测试必须作为 release-blocking CI 项执行：

1. literal consistency：`manualGateType`、`artifactCertificationState`、`inputDependencyState`、`profileConformanceStatus`、`capsuleHealth`
2. event canonical naming consistency：主文档 / event contracts / golden timelines
3. protocol release propagation：OpenAPI request / response / error / event envelope / schema object
4. state coverage：`parked_manual`、`tentative_upstream`、`manually_waived`
5. park / rehydrate closure：truth obligation、resource release evidence、single-use token

## 8. 合并主干前置条件

- 上述最小用例全部通过
- 任何新增状态、枚举、reason code 都已同步更新到 machine-readable bundle
- Golden timeline 与 state transition matrix 已更新
- contract consistency tests 全部为绿
