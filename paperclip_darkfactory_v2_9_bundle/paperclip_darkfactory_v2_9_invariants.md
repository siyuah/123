# Paperclip × Dark Factory V2.9 Invariants

绑定版本：`v2.9-companion-bound-r1`

## 1. Literal invariants

以下字面量必须在主文档、OpenAPI、Schema、事件合同、测试资产中保持完全一致：

- `manualGateType`
- `artifactCertificationState`
- `inputDependencyState`
- `profileConformanceStatus`
- `capsuleHealth`
- `executionSuspensionState`
- `errorCode`

## 2. Event naming invariants

- canonical event name 一律使用 dotted.case。
- `paperclip_darkfactory_v2_9_event_contracts.yaml` 是 canonical event name 的唯一 machine-readable 列表。
- 历史 snake_case 事件名只允许作为 `legacyAliases` 出现，不能作为新的 producer output 或 golden baseline。

## 3. Protocol release propagation invariants

以下对象或接口必须显式携带 `protocolReleaseTag=v2.9-companion-bound-r1`：

- OpenAPI 所有 mutation request
- OpenAPI 所有 view / error response
- event envelope
- `ExecutionCapabilityLease`
- `ArtifactCertification`
- `LineageEdge`
- `ConsumptionWaiver`
- `ParkRecord`
- `RehydrationToken`
- `ManualGateDefinition`
- `ShadowCompareRecord`

## 4. Park / rehydrate invariants

- `parked_manual` 只能在 truth obligation 保留的前提下进入。
- 进入 park 时必须产生 `ParkRecord`。
- 每个 `ParkRecord` 必须引用一个 `rehydrateTokenRef`。
- 每个 `rehydrateTokenRef` 最多只允许一次成功消费。
- rehydrate 成功后必须产生新的 `attemptId`，且可追溯到旧 attempt 与原始 run/trace。

## 5. Lineage invariants

- `artifact.certification.changed` 不得被 waiver 抑制。
- `lineage.invalidation.started` 不得被 waiver 抑制。
- `revoked_upstream` 不得被 waiver 放行为新的 high-risk primary write。
- `tentative_upstream` 只能在 policy 显式允许时出现。

## 6. CI release-blocking checks

1. literal consistency check
2. event canonical naming check
3. protocol release propagation check
4. state coverage check
5. park / rehydrate closure check
