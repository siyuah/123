# Paperclip × Dark Factory V3.0 Core Spec

状态: normative  
规范版本: 3.0  
protocolReleaseTag: `v3.0-agent-control-r1`

---

## 1. 目标

V3.0 的目标不是继续堆更多功能，而是把 Agent Control Plane 明确拆成三层：

1. 核心规范层: 承载真相对象、状态、不变量、恢复语义
2. 实现包层: 承载路由、记忆、自愈、operator 与测试的参考实现
3. 运行配置层: 承载 provider/model、fallback、阈值与发布门禁

V3.0 解决的是“不同实现团队是否会对同一条真实时间线给出同一协议结论”。

---

## 2. 核心立场

V3.0 坚持以下约束：

- Run 只有一个权威主状态机。
- Journal 是唯一 truth path。
- Route、memory、repair 不得散落在临时日志或不可回放副路径中。
- Park / rehydrate、lineage invalidation、schema write fence、capability broker 都属于硬边界，不得通过运行参数绕过。
- 协议正确与场景正确必须同时进入发布 gate。

---

## 3. 核心对象

V3.0 的核心对象定义由 `paperclip_darkfactory_v3_0_core_objects.schema.json` 承载，至少包括以下对象家族：

### 3.1 Execution capability 与运行边界

- `ExecutionCapabilityLease`
- capability observation 事件
- runtime audit 引用

语义要求：

- 所有执行 attempt 都必须先获得 capability lease，再进入实际执行。
- `observedCapabilitySet` 可以比声明集合更少，但不得无审计地超出 `grantedCapabilitySet`。
- `profileConformanceStatus=unverifiable` 时，不得直接进入高风险写路径。

### 3.2 Artifact / lineage 家族

- `ArtifactCertification`
- `LineageEdge`
- `ConsumptionWaiver`

语义要求：

- Artifact 认证状态是下游消费资格的唯一协议来源。
- 下游依赖状态必须显式表达为 `clean`、`tentative_upstream`、`reopened_upstream`、`revoked_upstream` 或 `manually_waived`。
- `revoked_upstream` 不得放行新的 high-risk primary write。

### 3.3 Manual park / rehydrate 家族

- `ParkRecord`
- `RehydrationToken`

语义要求：

1. `park` 必须产生 `ParkRecord`
2. `park` 必须释放计算资源，但不能抹掉 truth obligation
3. `rehydrate` 必须消费一次性 `RehydrationToken`
4. `rehydrate` 必须产生新的 `attemptId`
5. `rehydrate` 前必须重新 claim、重新 preflight、重新 route decision

### 3.4 Routing / provider failure 家族

- `RouteDecision`
- `ProviderFailureRecord`
- `ShadowCompareRecord`

语义要求：

- 路由决策是可审计对象，不是临时技巧。
- provider 故障必须先归类为 `providerFaultClass`，再映射到唯一 `recoveryLane`。
- cutover 不是运维经验，而是 truth-backed 协议动作。

### 3.5 Memory 家族

- `MemoryArtifact`
- `PromptInjectionReceipt`

语义要求：

- memory 不是 prompt 拼接，而是受治理的 artifact 家族。
- 注入 prompt 的 memory artifact 必须可追溯到 source trace、consent scope 与 retention policy。
- prompt injection receipt 必须记录选中条目、token budget 与 relevance policy。

### 3.6 Repair 家族

- `RepairAttempt`
- antibody pattern 学习事件

语义要求：

- repair lane 是正式恢复车道，不是旁路补丁机制。
- repair 进入条件、修复结果、人工升级条件都必须在 Journal 中有 truth record。
- repair lane 不得绕过 capability broker 与 schema write fence。

---

## 4. 状态机

### 4.1 Run 状态

Run 合法状态由 `core_enums.yaml` 与 `state_transition_matrix.csv` 共同定义：

- `requested`
- `validating`
- `planning`
- `executing`
- `waiting_approval`
- `waiting_input`
- `parked_manual`
- `rehydrating`
- `finalizing`
- `completed`
- `failed`
- `cancelled`

关键语义：

- `parked_manual` 不是成功终态。
- `rehydrating` 表示旧 attempt 已经失效但新 attempt 尚未进入稳定计划态。
- run 主状态必须由单一 orchestrator 或 closure authority 推进，不允许多个写者并发裁决终态。

### 4.2 Attempt 状态

Attempt 合法状态：

- `created`
- `booting`
- `active`
- `frozen`
- `handoff_pending`
- `parked_manual`
- `rehydrate_pending`
- `superseded`
- `finalizer_owned`
- `succeeded`
- `failed`
- `cancelled`

关键语义：

- 同一 run 任一时刻只能存在一个 active attempt。
- `parked_manual` 表示资源已释放、truth obligation 未消失。
- `superseded` 表示旧 attempt 被 rehydrate 后的新 attempt 取代。

### 4.3 Artifact 与 dependency 状态

Artifact 状态：

- `tentative`
- `certified`
- `reopened`
- `revoked`
- `quarantined`
- `superseded`

Dependency 状态：

- `clean`
- `tentative_upstream`
- `reopened_upstream`
- `revoked_upstream`
- `manually_waived`

关键语义：

- `tentative_upstream` 是一等状态，不是注释或临时标签。
- reopened / revoked 的上游变化必须向 consumer run 传播，而不是只停留在源 artifact 上。

---

## 5. 事件合同

事件 envelope 与目录由 `paperclip_darkfactory_v3_0_event_contracts.yaml` 约束。

### 5.1 envelope 最小字段

每个事件必须包含：

- `eventName`
- `eventVersion`
- `eventId`
- `emittedAt`
- `protocolReleaseTag`
- `traceId`
- `producer`
- `causationId`
- `correlationId`
- `sequenceNo`
- `isReplay`

### 5.2 命名规则

- 事件 canonical name 统一采用 dotted.case
- full name 统一采用 `canonicalName.version`
- 不再允许使用与 canonical name 冲突的旧别名作为主字段
- 如保留历史别名，只能通过 `legacyAliases[]` 这类兼容字段承载

### 5.3 V3.0 新增事件域

V3.0 重点扩展以下事件域：

- `manual_gate.parked`
- `manual_gate.rehydrated`
- `route.decision.recorded`
- `provider.failure.recorded`
- `route.cutover.performed`
- `memory.artifact.created`
- `memory.artifact.corrected`
- `memory.injection.recorded`
- `repair.attempt.started`
- `repair.attempt.completed`
- `antibody.pattern.learned`

---

## 6. protocolReleaseTag 传播闭环

V3.0 要求以下对象显式携带 `protocolReleaseTag`：

- create request
- park request
- rehydrate request
- waiver request
- memory create / correct request
- run view
- artifact view
- lineage view
- memory view
- error response
- event envelope
- bundle manifest

任何一处缺失都视为协议传播不闭合。

---

## 7. 恢复语义

### 7.1 Recovery lane

`recoveryLane` 只能从以下集合中取值：

- `retry_same_route`
- `cutover_fallback_route`
- `degrade_low_risk_only`
- `enter_repair_lane`
- `park_manual`
- `fail_terminal`

### 7.2 唯一映射要求

- 先做 provider fault 分类
- 再做 recovery lane 映射
- 不允许用 `A or B` 形式保留歧义分支

### 7.3 Repair lane

- repair 适用于 provider 故障、响应合同失配、有限范围内的自动补救
- repair 若需要 operator 审批，必须进入明确 manual gate
- repair 成功也必须经过验证与 journal append，不能只看执行器自报

---

## 8. Runtime config 的边界

`paperclip_darkfactory_v3_0_runtime_config_registry.yaml` 只承载运行参数，不承载协议不变量。

以下内容不得进入 registry 作为可调项：

1. 是否允许绕过 capability broker
2. 是否允许旧 schema 覆盖新对象
3. 是否允许 `revoked_upstream` 继续放行高风险写
4. 是否允许 out-of-scope memory artifact 注入 prompt
5. 是否允许 repair lane 绕过 schema write fence

---

## 9. 发布要求

一个实现只有在同时满足以下条件时，才能宣称符合 V3.0：

1. 采用本 bundle 的唯一枚举与对象名
2. 能按 `state_transition_matrix.csv` 回放状态推进
3. 能记录 route、memory、repair 的 truth object 与事件
4. 不变量未被运行参数削弱
5. 场景验收与协议验收都进入 CI gate

---

## 10. Reference key mapping

本节用于给 machine-readable 资产中的 `source` / `source_section` 提供可解析映射。

- `core-spec-4.1`: 本文第 3.1 节与第 7 节共同定义的 execution capability、preflight、poisoned retry 与高风险降级边界
- `core-spec-6`: 本文第 4 节定义的 Run / Attempt / Artifact 主状态机与 closure 语义
- `core-spec-8.2`: 本文第 6 节定义的 `protocolReleaseTag` 传播闭环
- `core-spec-8.3`: 本文第 3.3 节与第 4 节定义的 park / rehydrate 语义与状态推进
- `core-spec-8.4`: 本文第 3.2 节与第 4.3 节定义的 dependency / lineage / tentative_upstream 传播语义
- `core-spec-8.5`: 本文第 8 节定义的 runtime config 边界与不可配置硬约束
