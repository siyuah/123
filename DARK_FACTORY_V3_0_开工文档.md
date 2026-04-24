# Dark Factory V3.0 开工开发文档

## 1. 文档定位

这份文档是 V3.0 的直接开工文档，目标不是重复 V2.9，而是在 V2.9 已经建立的执行真相、风险治理和协议边界之上，吸收 Phoenix V2 中真正值得制度化的能力，形成一套可以持续施工、持续验证、持续发布的 V3.0 开发基线。

V3.0 的核心判断只有一句话：

**V2.9 负责“别出事故”，V3.0 还要负责“系统持续可用、可恢复、可进化、可记忆”。**

因此，V3.0 不是推翻 V2.9，而是做三件事：

1. 继承 V2.9 已经正确的协议骨架
2. 修复 V2.9 companion bundle 中已经暴露的硬冲突和闭环缺口
3. 把 Phoenix V2 的路由、故障切换、记忆闭环、自愈闭环、场景验收，按层次收编进规范、实现包和运行配置面

---

## 2. 输入基线

V3.0 的设计基于以下输入：

### 2.1 V2.9 现有协议与实现材料

- `/home/siyuah/workspace/.inspect_darkfactory_v2_9/paperclip_darkfactory_revised_framework_v2_9_companion_bound.md`
- `/home/siyuah/workspace/.inspect_darkfactory_v2_9/paperclip_darkfactory_v2_9_impl_pack.md`
- `/home/siyuah/workspace/.inspect_darkfactory_v2_9/paperclip_darkfactory_v2_9_event_contracts.yaml`
- `/home/siyuah/workspace/.inspect_darkfactory_v2_9/paperclip_darkfactory_v2_9_external_runs.openapi.yaml`
- `/home/siyuah/workspace/.inspect_darkfactory_v2_9/paperclip_darkfactory_v2_9_core_enums.yaml`
- `/home/siyuah/workspace/.inspect_darkfactory_v2_9/paperclip_darkfactory_v2_9_core_objects.schema.json`
- `/home/siyuah/workspace/.inspect_darkfactory_v2_9/paperclip_darkfactory_v2_9_runtime_config_registry.yaml`
- `/home/siyuah/workspace/.inspect_darkfactory_v2_9/paperclip_darkfactory_v2_9_state_transition_matrix.csv`
- `/home/siyuah/workspace/.inspect_darkfactory_v2_9/paperclip_darkfactory_v2_9_test_asset_spec.md`
- `/home/siyuah/workspace/paperclip_darkfactory_v2_9_bundle_review_notes.md`

### 2.2 当前工程骨架

- `/home/siyuah/workspace/hermes_gpt54_starter/README.md`
- `/home/siyuah/workspace/hermes_gpt54_starter/control-plane/package.json`
- `/home/siyuah/workspace/hermes_gpt54_starter/control-plane/src/`
- `/home/siyuah/workspace/hermes_gpt54_starter/control-plane/tests/`

### 2.3 Phoenix V2 启发输入

- `/home/siyuah/workspace/不死鸟.txt`
- `/home/siyuah/workspace/GPT5.4Pro的回答.txt`
- `/home/siyuah/workspace/GLM5.1的回答.txt`
- `/home/siyuah/workspace/gemini的回答.txt`

这些 Phoenix 输入只作为能力抽象来源，不直接构成协议真相源。

---

## 3. V3.0 的总体目标

V3.0 的目标不是把系统做成“更大的 V2.9”，而是把它升级成一个分层清楚的 Agent Control Plane：

1. **核心规范层**继续定义不可放松的真相、状态、事件、不变量和风险边界
2. **实现包层**定义路由、记忆、自愈、运维、测试、存储与 operator surface 的推荐实现
3. **运行配置层**承载具体模型路由、故障切换、记忆注入、修复阈值和发布门禁配置

这三层必须分开，否则会重复 V2.9 的问题：把不该写进核心宪法的产品参数混进协议层，最后导致规范和部署配置缠在一起。

---

## 4. V2.9 必须继承的内容

V3.0 必须完整继承以下内容，不能退化：

### 4.1 必须原样保留的 V2.9 核心能力

1. Journal 作为 append-only truth source
2. Run 与 Attempt 分离建模
3. 单一主状态机，不允许多处各自推进 run 主状态
4. Capability lease / brokered effect / runtime audit 边界
5. Artifact certification 与 Lineage invalidation 机制
6. Capsule hard-token preflight 与 poisoned breaker 思路
7. Manual park / rehydrate 的 truth obligation 语义
8. Archive / restore / hold 的可检索冷数据路径
9. Schema write fence 与旧写者阻断
10. `protocolReleaseTag` 版本绑定语义
11. 事件 envelope 的稳定字段集合
12. runtime config registry 作为 release gate 真相来源

### 4.2 必须在 V3.0 修复的 V2.9 问题

以下问题在 V3.0 中不能再以“后续再说”的方式保留：

1. `manualGateType` 字面量冲突
2. 事件 canonical naming 风格不统一
3. `protocolReleaseTag` 在 OpenAPI / 对象 / 错误响应中传播不闭合
4. `parked_manual` / `rehydrateTokenRef` 缺少 truth object 闭环
5. `tentative_upstream` 状态迁移矩阵不完整
6. README 对 binding / informative / CI 边界表述不清
7. 错误码仍偏散乱，不足以支撑路由、记忆、自愈和恢复车道
8. runtime config registry 还没有覆盖新的路由、记忆、自愈配置面

---

## 5. V3.0 的分层设计

## 5.1 三层模型

### L1. 核心规范层 Core Normative Spec

这一层只放稳定语义，不放具体模型名单、厂商顺序、成本策略或运营偏好。

必须进入 L1 的内容：

1. 核心对象与状态机
2. 事件 canonical name 与 envelope 规则
3. 错误码与恢复车道语义
4. 路由决策、记忆注入、修复尝试这些行为的最小审计对象
5. 不变量、版本绑定与跨文件一致性要求

### L2. 实现包层 Implementation Pack + Reference Agent Assembly Pack

这一层承载推荐实现，不新增 L1 不存在的协议真义。

必须进入 L2 的内容：

1. Router Engine、Provider Adapter、Fallback Chain 的接口建议
2. Memory Pipeline 的组件拆分与落库建议
3. Repair Lane、Antibody Store、Scenario Acceptance Pack 的工程组织方式
4. API surface、operator surface、storage mapping、测试资产与 fixture 规范

### L3. 运行配置层 Runtime Registry + Deployment Profile

这一层承载部署差异与可调参数。

必须进入 L3 的内容：

1. workload 到 provider/model 的映射
2. 各 workload 的 fallback chain 与 cutover 规则
3. 记忆提取、保留、注入预算与相关性阈值
4. 自动修复是否开启、最多尝试次数、人工升级阈值
5. 场景验收与发布门禁阈值

---

## 6. Phoenix V2 能力的层次归属

这一节是 V3.0 的关键设计结论。

## 6.1 进入核心规范层的 Phoenix 能力

Phoenix V2 的以下能力应该被抽象后纳入核心规范，但必须去掉具体供应商与产品品牌细节：

| Phoenix 能力 | 是否进入核心规范 | V3.0 收口方式 |
|---|---|---|
| 任务路由 | 是 | 抽象成 `workloadClass`、`routeDecision`、`routePolicyRef`、`executionObjective` |
| 故障分类与切换 | 是 | 抽象成 `providerFaultClass`、`recoveryLane`、`cutoverReason` |
| 记忆闭环 | 是，但只进抽象对象 | 抽象成 `memoryFact`、`sessionMemorySnapshot`、`knowledgeEdge`、`diaryEntry`、`promptInjectionReceipt` |
| 自愈闭环 | 是，但只进最小语义 | 抽象成 `repairAttempt`、`repairOutcome`、`antibodyPatternRef` |
| 模型主备链 | 否 | 进入 runtime profile，不进入核心规范 |
| 具体模型名单 | 否 | 进入 deployment profile |
| Telegram/飞书入口 | 否 | 属于产品接入层 |
| 免费/付费成本策略 | 否 | 属于运行配置层 |

### 6.1.1 新增核心枚举

V3.0 核心规范建议新增以下枚举：

- `workloadClass`
  - `chat`
  - `code`
  - `reasoning`
  - `vision`
  - `memory_maintenance`
  - `repair`
  - `operator_adjudication`

- `providerFaultClass`
  - `transient_timeout`
  - `transient_5xx`
  - `rate_limited`
  - `quota_exhausted`
  - `auth_invalid`
  - `capability_unsupported`
  - `context_length_exceeded`
  - `response_contract_invalid`
  - `provider_unreachable`

- `recoveryLane`
  - `retry_same_route`
  - `cutover_fallback_route`
  - `degrade_low_risk_only`
  - `enter_repair_lane`
  - `park_manual`
  - `fail_terminal`

- `memoryArtifactType`
  - `memory_fact`
  - `session_memory_snapshot`
  - `knowledge_edge`
  - `diary_entry`
  - `prompt_injection_receipt`

- `repairOutcome`
  - `repair_succeeded`
  - `repair_failed`
  - `repair_rejected`
  - `repair_needs_manual`

### 6.1.2 新增核心对象

V3.0 建议新增以下核心对象定义，并纳入 schema / OpenAPI / projection 一致性校验：

1. `RouteDecision`
   - `routeDecisionId`
   - `runId`
   - `attemptId`
   - `workloadClass`
   - `routePolicyRef`
   - `selectedExecutorClass`
   - `fallbackDepth`
   - `decisionReason`
   - `protocolReleaseTag`

2. `ProviderFailureRecord`
   - `failureId`
   - `runId`
   - `attemptId`
   - `providerFaultClass`
   - `providerRef`
   - `routeDecisionId`
   - `recoveryLane`
   - `cutoverPerformed`
   - `evidenceRef`

3. `ParkRecord`
   - `parkId`
   - `runId`
   - `attemptId`
   - `manualGateType`
   - `executionSuspensionState`
   - `rehydrationRequirements[]`
   - `resourceReleaseEvidenceRef`
   - `parkedAt`

4. `RehydrationToken`
   - `rehydrationTokenId`
   - `runId`
   - `previousAttemptId`
   - `requirementsDigest`
   - `issuedAt`
   - `expiresAt`
   - `consumedAt`
   - `issuer`

5. `MemoryArtifact`
   - `memoryArtifactId`
   - `memoryArtifactType`
   - `subjectRef`
   - `sourceTraceId`
   - `sourceRunId`
   - `confidence`
   - `consentScope`
   - `retentionPolicyRef`
   - `currentState`

6. `PromptInjectionReceipt`
   - `receiptId`
   - `runId`
   - `attemptId`
   - `selectedMemoryArtifactIds[]`
   - `injectionBudgetTokens`
   - `relevancePolicyRef`
   - `injectedAt`

7. `RepairAttempt`
   - `repairAttemptId`
   - `runId`
   - `attemptId`
   - `triggeredBy`
   - `triggerFaultClass`
   - `repairPlanRef`
   - `outcome`
   - `antibodyPatternRef`
   - `operatorApprovalRequired`

### 6.1.3 新增核心事件

V3.0 建议在事件目录中正式加入：

- `route.decision.recorded.v1`
- `provider.failure.recorded.v1`
- `route.cutover.performed.v1`
- `memory.artifact.created.v1`
- `memory.artifact.corrected.v1`
- `memory.injection.recorded.v1`
- `repair.attempt.started.v1`
- `repair.attempt.completed.v1`
- `antibody.pattern.learned.v1`

这些事件和现有 V2.9 事件并列，继续采用 dotted.case + version suffix 的唯一命名风格。

## 6.2 进入实现包层的 Phoenix 能力

以下能力不应该写成硬协议，但必须进入实现包作为推荐实现：

1. `RouterEngine`
2. `ProviderAdapterRegistry`
3. `FallbackChainResolver`
4. `ProviderFaultClassifier`
5. `MemoryExtractor`
6. `MemorySyncService`
7. `KnowledgeGraphProjector`
8. `DiaryProjectionService`
9. `PromptContextAssembler`
10. `PhoenixRecover` 对应的 `RecoveryBootstrapService`
11. `RepairLaneService`
12. `AntibodyStore`
13. `ScenarioAcceptancePack`

### 6.2.1 实现包要求

V3.0 impl pack 应增加一个 **Reference Agent Assembly Pack**，明确以下内容：

1. workload routing reference profile
2. provider fault matrix
3. memory artifact pack
4. repair loop pack
5. scenario acceptance spec
6. operator runbook

这个 Agent Assembly Pack 的定位是：

- 它是 L2 的参考实现包
- 它不能凌驾于 L1 核心规范之上
- 它可以给出默认链路和推荐配置
- 它不能把具体厂商选择写成协议真义

## 6.3 进入运行配置层的 Phoenix 能力

以下能力明确只进运行配置层，不进核心规范：

1. 各 workload 的首选 provider/model
2. `fallbackChain` 的顺序与层数
3. 哪类错误先重试、哪类错误直接切换
4. 注入多少记忆 token
5. 哪些 memory artifact 允许跨会话注入
6. repair lane 是否自动执行
7. repair 修改是否必须人工批准
8. 场景验收阈值和发布闸门阈值
9. 成本优先、质量优先、延迟优先策略

---

## 7. V3.0 文档结构设计

V3.0 不再沿用“主文档很重、附录和实现包都像补丁”的组织方式，而是改成更清晰的文档树。

## 7.1 建议的 V3.0 文档树

```text
paperclip_darkfactory_v3_0/
  README.md
  paperclip_darkfactory_v3_0_core_spec.md
  paperclip_darkfactory_v3_0_impl_pack.md
  paperclip_darkfactory_v3_0_agent_assembly_pack.md
  paperclip_darkfactory_v3_0_invariants.md
  paperclip_darkfactory_v3_0_test_asset_spec.md
  paperclip_darkfactory_v3_0_core_enums.yaml
  paperclip_darkfactory_v3_0_core_objects.schema.json
  paperclip_darkfactory_v3_0_event_contracts.yaml
  paperclip_darkfactory_v3_0_external_runs.openapi.yaml
  paperclip_darkfactory_v3_0_memory.openapi.yaml
  paperclip_darkfactory_v3_0_runtime_config_registry.yaml
  paperclip_darkfactory_v3_0_state_transition_matrix.csv
  paperclip_darkfactory_v3_0_storage_mapping.csv
  paperclip_darkfactory_v3_0_responsibility_matrix.csv
  paperclip_darkfactory_v3_0_scenario_acceptance_matrix.csv
  paperclip_darkfactory_v3_0_bundle_manifest.yaml
```

## 7.2 每个文档的职责

### `README.md`

负责说明：

- 文件清单
- binding / informative / CI boundary
- 冲突处理优先级
- bundle manifest 与 release tag 的关系

### `paperclip_darkfactory_v3_0_core_spec.md`

负责说明：

- 核心对象
- 状态机
- 路由、记忆、修复的最小语义
- park / rehydrate / lineage / write fence 等硬边界
- 不变量引用位置

### `paperclip_darkfactory_v3_0_impl_pack.md`

负责说明：

- API surface
- storage mapping
- operator surface
- runtime audit
- archive / restore
- testing and observability

### `paperclip_darkfactory_v3_0_agent_assembly_pack.md`

负责说明：

- 路由器
- provider adapter
- fallback strategy
- memory pipeline
- repair lane
- antibody store
- scenario acceptance

### `paperclip_darkfactory_v3_0_invariants.md`

负责承载 JSON Schema 和 OpenAPI 无法表达的约束，例如：

1. 同一 run 任一时刻只能有一个 active attempt
2. `revoked_upstream` 不得放行新的 high-risk primary write
3. `parked_manual` 不是成功终态
4. `RehydrationToken` 一次性消费
5. `PromptInjectionReceipt` 不得引用 revoked 或 out-of-scope memory artifact
6. repair lane 不得绕过 capability broker 和 schema write fence

---

## 8. V3.0 的规范修订要点

## 8.1 统一 literal 与命名风格

V3.0 必须做以下统一：

1. `manualGateType` 统一采用：
   - `manual_approval_required`
   - `manual_evidence_access_required`
   - `manual_adjudication_required`
   - `manual_risk_acceptance_required`
   - `manual_recovery_required`
   - `manual_external_followup_required`

2. 事件 canonical name 统一采用 dotted.case
3. 事件 full name 统一采用 `canonicalName.version`
4. 所有 machine-readable 资产不得再使用与 canonical name 冲突的旧别名作为主字段
5. 若保留旧别名，只能通过 `legacyAliases[]` 承载

## 8.2 补齐 protocolReleaseTag 传播闭环

V3.0 要求以下对象全部显式携带 `protocolReleaseTag`，不再允许只靠“服务端默认回写”作为唯一机制：

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

## 8.3 park / rehydrate 真相闭环

V3.0 必须明确：

1. `park` 产生 `ParkRecord`
2. `park` 必须释放计算资源，但不能抹掉 truth obligation
3. `rehydrate` 必须消费 `RehydrationToken`
4. `rehydrate` 产生新的 `attemptId`
5. `rehydrate` 前必须重新 claim、重新 preflight、重新 route decision

## 8.4 tentative_upstream 状态闭环

V3.0 的状态矩阵至少补齐：

- `clean -> tentative_upstream`
- `tentative_upstream -> clean`
- `tentative_upstream -> manually_waived`
- `tentative_upstream -> reopened_upstream`
- `tentative_upstream -> revoked_upstream`

## 8.5 错误码扩展

V3.0 建议统一错误码目录，新增至少以下错误码：

- `invalid_protocol_release_tag`
- `run_not_found`
- `attempt_not_parkable`
- `rehydration_requirements_not_met`
- `manual_gate_not_satisfied`
- `waiver_scope_invalid`
- `waiver_fanout_exceeded`
- `artifact_not_consumable`
- `provider_fault_cutover_exhausted`
- `route_policy_not_found`
- `memory_injection_scope_invalid`
- `memory_artifact_revoked`
- `memory_retention_expired`
- `repair_attempt_blocked`
- `repair_requires_operator_approval`
- `capsule_poisoned_retry_blocked`
- `profile_conformance_unverifiable`
- `schema_write_fence_rejected`

---

## 9. V3.0 的代码目录规划

基于当前 `hermes_gpt54_starter/control-plane`，V3.0 建议目录如下：

```text
control-plane/
  src/
    api/
      handlers/
      router.ts
      server.ts
    protocol/
      constants.ts
      enums.ts
      events.ts
      errors.ts
      schemas.ts
      invariants.ts
    journal/
      journal-store.ts
      file-journal-store.ts
      journal-service.ts
    projections/
      run-view-projection.ts
      artifact-view-projection.ts
      lineage-view-projection.ts
      memory-view-projection.ts
      route-view-projection.ts
      repair-view-projection.ts
    runs/
      run-types.ts
      run-state-machine.ts
      run-service.ts
      attempt-service.ts
      execution-adapter.ts
    routing/
      workload-types.ts
      route-policy-service.ts
      router-engine.ts
      fallback-chain-resolver.ts
      provider-fault-classifier.ts
    providers/
      provider-adapter.ts
      provider-adapter-registry.ts
    capability/
      capability-types.ts
      capability-broker.ts
      runtime-audit-service.ts
    artifacts/
      artifact-service.ts
      waiver-service.ts
    lineage/
      lineage-service.ts
    capsule/
      capsule-types.ts
      hard-token-preflight.ts
      poisoned-breaker.ts
    manual/
      manual-gate-service.ts
    archive/
      archive-catalog-service.ts
      restore-service.ts
    memory/
      memory-types.ts
      memory-extractor.ts
      memory-sync-service.ts
      knowledge-graph-service.ts
      diary-service.ts
      prompt-context-assembler.ts
      recovery-bootstrap-service.ts
    remediation/
      repair-lane-service.ts
      antibody-store.ts
      repair-policy-service.ts
    config/
      runtime-registry.ts
      routing-profile-loader.ts
      memory-policy-loader.ts
      repair-policy-loader.ts
    orchestration/
      task-runtime-orchestrator.ts
      agent-control-orchestrator.ts
    scenario/
      scenario-acceptance-service.ts
      scenario-gate-service.ts
  tests/
    fixtures/
    golden_timelines/
    integration/
    property/
    fault_injection/
    scenario/
```

### 9.1 当前工程中的保留原则

以下模块继续保留，不重写，只做接入和分层修正：

- `sandbox/`
- `llm/`
- `policies/`
- `image/`
- `orchestration/task-runtime-orchestrator.ts`
- 已有 `protocol/`、`journal/`、`api/` 骨架

### 9.2 当前工程中的改造原则

1. 已有 `protocol/constants.ts`、`enums.ts`、`events.ts`、`errors.ts` 作为 V3.0 起点继续扩展
2. 已有 `journal-service.ts` 继续作为 truth path 核心
3. 现有 `RunService`、`CapabilityBroker` 的占位实现要升级成真实服务，不能再停留在 stub
4. `TaskRuntimeOrchestrator` 不承担路由真相和恢复裁决，只承担执行沙箱协调

---

## 10. V3.0 的运行配置面设计

V3.0 runtime config registry 需要从 V2.9 的治理面扩展到“路由 + 记忆 + 自愈 + 场景门禁”。

## 10.1 建议新增的 registry key

### 路由相关

- `routing.classifier.defaultPolicyRef`
- `routing.workload.chat.fallbackChain`
- `routing.workload.code.fallbackChain`
- `routing.workload.reasoning.fallbackChain`
- `routing.workload.vision.fallbackChain`
- `routing.retry.maxAttempts.transient_timeout`
- `routing.retry.maxAttempts.transient_5xx`
- `routing.cutover.enabled.quota_exhausted`
- `routing.cutover.enabled.auth_invalid`
- `routing.degrade.lowRiskOnlyOnUnverifiable`

### 记忆相关

- `memory.extractor.minConfidence`
- `memory.extractor.maxArtifactsPerTurn`
- `memory.sync.enableDiary`
- `memory.sync.enableKnowledgeGraph`
- `memory.retention.defaultTtlDays`
- `memory.injection.maxTokenBudget`
- `memory.injection.maxArtifactsPerRun`
- `memory.injection.allowedScopes`
- `memory.injection.requireConsentForCrossSession`
- `memory.recover.bootstrapMaxArtifacts`

### 自愈相关

- `repair.auto.enabled`
- `repair.auto.maxAttemptsPerRun`
- `repair.auto.allowCodePatch`
- `repair.auto.requireSandboxVerification`
- `repair.auto.requireOperatorApproval.highRisk`
- `repair.antibody.matchThreshold`
- `repair.antibody.maxReuseAgeDays`

### 场景验收与发布相关

- `scenario.acceptance.requiredPackVersion`
- `scenario.acceptance.maxDecisionDivergence`
- `scenario.acceptance.maxFallbackRate`
- `scenario.acceptance.maxMemoryInjectionMissRate`
- `scenario.acceptance.maxRepairRegressionRate`
- `release.blockOnScenarioGateFailure`

## 10.2 不应进入 registry 的内容

以下内容不要塞进 runtime registry：

1. 破坏协议语义的不变量
2. 是否允许绕过 capability broker
3. 是否允许旧 schema 覆盖新对象
4. 是否允许 `revoked_upstream` 继续放行高风险写
5. 是否允许 out-of-scope memory artifact 注入 prompt

这些都是核心规范约束，不是运行参数。

---

## 11. V3.0 API 面设计

V3.0 在保留 V2.9 最小 API surface 的基础上，新增 memory 和 repair 相关接口，但仍坚持“HTTP 只是 service facade”。

## 11.1 继续保留的最小接口

- `POST /api/external-runs`
- `GET /api/external-runs/{runId}`
- `POST /api/external-runs/{runId}:park`
- `POST /api/external-runs/{runId}:rehydrate`
- `GET /api/artifacts/{artifactId}`
- `POST /api/artifacts/{artifactId}:waive-consumption`
- `GET /api/lineage/artifacts/{artifactId}`

## 11.2 V3.0 建议新增接口

### 路由与运行观察

- `GET /api/external-runs/{runId}/route-decisions`
- `GET /api/external-runs/{runId}/provider-failures`

### 记忆面

- `GET /api/memory/artifacts/{memoryArtifactId}`
- `POST /api/memory/artifacts:search`
- `POST /api/memory/artifacts/{memoryArtifactId}:correct`
- `GET /api/external-runs/{runId}/memory-injections`

### 修复面

- `GET /api/external-runs/{runId}/repair-attempts`
- `POST /api/external-runs/{runId}:repair`
- `GET /api/antibodies/{patternId}`

### Archive / Restore 观察面

- `GET /api/archive/search`
- `POST /api/archive/restore`

---

## 12. V3.0 的测试与验收体系

V3.0 必须同时覆盖两种正确性：

1. **协议正确**
2. **场景正确**

V2.9 更强调第一种，V3.0 必须把第二种补齐。

## 12.1 协议测试

继续保留并扩展：

- journal replay tests
- state transition tests
- capability boundary tests
- lineage invalidation tests
- capsule poison tests
- write fence tests
- manual / archive tests

## 12.2 场景验收包

V3.0 新增 `scenario_acceptance_matrix.csv`，至少覆盖：

1. 普通 chat 请求命中 chat route
2. 代码修复请求命中 code route
3. 视觉输入命中 vision route
4. 主 route transient 失败后 fallback 成功
5. quota exhausted 后切换备用 route
6. memory extract -> sync -> inject 闭环
7. repair lane 自动修复成功
8. repair lane 失败后进入 manual gate
9. 上游 reopened 后下游阻断仍然生效
10. park -> rehydrate -> route re-evaluate 闭环

## 12.3 新增 golden timeline 范围

除了现有 run / artifact / lineage，V3.0 还需要给以下对象建立 golden timeline：

- route decisions
- provider failures
- memory artifacts
- prompt injection receipts
- repair attempts
- antibody learning

---

## 13. V3.0 的施工顺序

V3.0 继续沿用分阶段施工，但阶段重新编排，避免把 Phoenix 能力零散插入现有模块。

| 阶段 | 目标 | 结果 |
|---|---|---|
| S0 | V2.9 -> V3.0 文档与资产收口 | 明确 binding、冲突修复点、bundle manifest |
| S1 | 协议层升级 | 新增 workload、fault、memory、repair 核心枚举/对象/事件 |
| S2 | Journal / Projection 升级 | route、memory、repair 视图可 replay |
| S3 | 路由平面落地 | Router Engine、Fallback Chain、Provider Fault Classifier |
| S4 | Run / Attempt / Recovery lane 升级 | run 主流程具备 retry/cutover/park 语义 |
| S5 | Memory Pipeline 落地 | extract -> sync -> KG -> diary -> inject -> recover |
| S6 | Repair Lane / Antibody 落地 | 自动修复与人工升级闭环 |
| S7 | API / Operator / Archive 扩展 | 记忆、修复、检索观察面齐全 |
| S8 | Scenario Acceptance + Release Gate | 协议正确与场景正确同时进入 CI |

---

## 14. 每阶段施工说明

## S0. 文档与资产收口

### 目标

把 V2.9 的硬冲突先修成 V3.0 文档约束，不带病开发。

### 必做事项

1. 新建 V3.0 README，明确 binding / informative / CI boundary
2. 建立 `bundle_manifest.yaml`
3. 修复 `manualGateType`、event canonical naming、`protocolReleaseTag` 传播规则
4. 在状态矩阵里补齐 `parked_manual` 与 `tentative_upstream`
5. 增加 `ParkRecord`、`RehydrationToken`、`RouteDecision`、`MemoryArtifact`、`RepairAttempt`

### 验收标准

- 所有 machine-readable 文件能通过一致性脚本校验
- 不再存在同名 literal 冲突

## S1. 协议层升级

### 目标

在现有 `src/protocol/` 上扩展出 V3.0 所需的统一语义层。

### 必做文件

- `src/protocol/constants.ts`
- `src/protocol/enums.ts`
- `src/protocol/events.ts`
- `src/protocol/errors.ts`
- `src/protocol/schemas.ts`
- `src/protocol/invariants.ts`
- `tests/protocol-v3-contract.test.ts`

### 施工内容

1. 加入 workload / fault / recovery / memory / repair 枚举
2. 加入 route、memory、repair 核心对象类型
3. 扩展事件目录
4. 为新对象写 schema 校验
5. 把旧 V2.9 错误码升级成 V3.0 统一错误码目录

## S2. Journal / Projection 升级

### 目标

让 route、memory、repair 都进入 truth path，而不是散落在日志或临时文件里。

### 必做文件

- `src/projections/memory-view-projection.ts`
- `src/projections/route-view-projection.ts`
- `src/projections/repair-view-projection.ts`
- `tests/journal-v3.test.ts`

### 施工内容

1. 扩展 journal replay
2. 增加 route、memory、repair 的投影视图
3. 保证 projection 可删可重建

## S3. 路由平面落地

### 目标

把 Phoenix 的“不要主脑，要路由”落实到 V3.0 的实现层，但不污染核心协议。

### 必做文件

- `src/routing/workload-types.ts`
- `src/routing/router-engine.ts`
- `src/routing/route-policy-service.ts`
- `src/routing/fallback-chain-resolver.ts`
- `src/routing/provider-fault-classifier.ts`
- `src/providers/provider-adapter.ts`
- `src/providers/provider-adapter-registry.ts`
- `tests/routing.test.ts`

### 施工内容

1. 实现 workload 分类
2. 实现 route decision 记录
3. 实现 fallback chain
4. 实现 provider fault 分类与 recovery lane 映射
5. 记录 cutover event

## S4. Run / Attempt / Recovery Lane 升级

### 目标

让 run 主流程可以表达 retry、cutover、repair、park、manual gate 等恢复语义。

### 必做事项

1. 扩展 `run-state-machine.ts`
2. 将 `ProviderFailureRecord`、`RouteDecision` 接入 run orchestration
3. 当 provider fault 出现时，根据 `recoveryLane` 进入不同车道
4. 仍然坚持 run 主状态单一来源

## S5. Memory Pipeline 落地

### 目标

把 Phoenix V2 的记忆闭环升级成受治理的 truth-backed artifact 家族。

### 必做文件

- `src/memory/memory-types.ts`
- `src/memory/memory-extractor.ts`
- `src/memory/memory-sync-service.ts`
- `src/memory/knowledge-graph-service.ts`
- `src/memory/diary-service.ts`
- `src/memory/prompt-context-assembler.ts`
- `src/memory/recovery-bootstrap-service.ts`
- `tests/memory.test.ts`
- `tests/integration/memory-pipeline.test.ts`

### 施工内容

1. 抽取 memory artifact
2. 落盘 truth object
3. 构建 knowledge edge projection
4. 记录 diary entry
5. 生成 prompt injection receipt
6. 启动恢复时读取相关 memory artifact

## S6. Repair Lane / Antibody 落地

### 目标

把 Phoenix 的“维修工 + 抗体库”改造成可审计、可验证、可人工升级的恢复车道。

### 必做文件

- `src/remediation/repair-lane-service.ts`
- `src/remediation/antibody-store.ts`
- `src/remediation/repair-policy-service.ts`
- `tests/repair.test.ts`
- `tests/fault_injection/repair-lane.test.ts`

### 施工内容

1. fault -> repair lane 的进入条件
2. repair attempt truth record
3. sandbox verification
4. repair success / fail / needs_manual 的状态推进
5. 抗体模式学习与复用记录

## S7. API / Operator / Archive 扩展

### 目标

对外暴露 route、memory、repair、archive 的查询与操作面。

### 必做事项

1. 扩展 OpenAPI
2. 扩展 handler
3. 让 CLI 与 HTTP 共用 service
4. 增加 operator 查询与 archive restore 能力

## S8. Scenario Acceptance + Release Gate

### 目标

把“协议正确”与“场景正确”一起纳入 CI 与发布闸门。

### 必做事项

1. 引入 scenario fixture
2. 引入 scenario matrix
3. 将 fallback rate、memory injection hit rate、repair regression rate 接入门禁
4. 更新 README 与 bundle manifest

---

## 15. 当前工程的直接开工建议

对于 `/home/siyuah/workspace/hermes_gpt54_starter/control-plane`，V3.0 的第一轮施工建议按下面顺序推进：

1. 先做 S0 和 S1，收口协议层
2. 再做 S2，保证 journal / projection 能承载新增对象
3. 先落路由平面 S3，再做记忆 S5
4. repair lane 必须排在 memory 之后，因为它依赖更完整的 truth 和 recovery 语义
5. API 扩展与 scenario acceptance 最后做

原因很简单：

- 没有统一协议，后面路由、记忆、自愈会各写一套词
- 没有 journal / projection，Phoenix 风格能力会退化成“不可靠日志功能”
- 没有 route 和 recovery 语义，repair lane 很容易变成绕协议的旁路

---

## 16. 给 Hermes 的第一批施工指令建议

V3.0 第一批不应该直接写业务功能，而是先收口协议和目录。

### 指令 A：执行 V3.0 S0 文档与协议收口

目标：

1. 扩展 `src/protocol/*`
2. 对齐 V3.0 的 literal、事件与错误码
3. 新建 V3.0 缺失对象的 schema 占位
4. 补充协议测试

### 指令 B：执行 V3.0 S2 Journal / Projection 扩展

目标：

1. 让 route / memory / repair 进入 journal
2. 新建对应 projection
3. 补 replay 测试

### 指令 C：执行 V3.0 S3 路由平面

目标：

1. 新建 routing/ 与 providers/
2. 实现 route decision 和 provider fault classification
3. 接入现有 orchestration，不重写 sandbox

### 指令 D：执行 V3.0 S5 记忆流水线最小闭环

目标：

1. 抽 memory artifact
2. 生成 injection receipt
3. 做最小 recover bootstrap

---

## 17. V3.0 版本结论

V3.0 的核心不是“再加更多功能”，而是把系统明确拆成三层：

1. **L1 核心规范层**：承载真相、状态、不变量、恢复语义
2. **L2 实现包层**：承载路由、记忆、自愈、operator、测试的参考实现
3. **L3 运行配置层**：承载具体 provider/model、fallback、阈值和门禁

Phoenix V2 对 V3.0 的最大价值，不是教 V3.0 “该选哪家模型”，而是逼着 V3.0 把下面五件事正式制度化：

1. 任务路由不是临时技巧，而是可审计对象
2. 故障切换不是运维经验，而是有 fault class 和 recovery lane 的正式语义
3. 记忆不是 prompt 拼接，而是受治理的 artifact 家族
4. 自愈不是黑箱补丁，而是可追踪的 repair lane
5. 验收不是只看协议矩阵，还要看用户场景矩阵

这五件事完成后，Dark Factory 才会从 V2.9 的“防事故控制面”，进入 V3.0 的“可用、可恢复、可进化的 Agent Control Plane”。
