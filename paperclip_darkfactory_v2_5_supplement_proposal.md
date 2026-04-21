# Paperclip × Dark Factory V2.5 补充条款建议稿

**状态**: Draft  
**目的**: 将 V2.5 中仍偏原则性的部分，收敛为实现团队、控制服务团队、前端团队、平台团队都可按同一口径执行的补充合同。  
**适用方式**: 本文作为 V2.5 的补充规范；若与 V2.5 正文冲突，以更严格者为准。  

---

## 0. 设计目标

本补充稿只解决六类问题：

1. 明确 Execution Journal 的权威边界与物理失败窗口。
2. 明确 Finalizer / Reaper / Worker 之间的接管仲裁与 fencing。
3. 明确 Run / Attempt / Child / Control Service 的层级状态模型。
4. 将 compensation 正式纳入 effect model，而不是停留在控制逻辑。
5. 补齐 sanitization 与 restricted evidence 的权限、追溯、补救规则。
6. 给出迁移与验收测试框架，避免 V2.5 停留在原则层。

本文中的 MUST / SHOULD / MAY 采用 RFC 风格解释。

---

## 1. Execution Journal 的权威边界

### 1.1 重新定义“唯一真相源”

V2.5 中“Journal 是唯一执行真相源”应收敛为以下正式表述：

- Journal 是唯一的“权威提交真相源”。
- 所有会影响恢复决策、补偿决策、probe 决策、审计归因的执行事实，最终都 MUST 归并到 Journal。
- 在记录尚未跨过 durable watermark 之前，系统 MAY 处于“已发起但未形成权威提交事实”的短暂不确定窗口。
- Finalizer 在该窗口内 MUST 进入“旁路核实模式”，不得直接假定“Journal 未记即未发生”。

### 1.2 四类事实边界

每一个可写 effect 或关键执行动作，至少必须区分以下四种事实：

1. `intent_recorded`
   - 已写入意图。
   - 尚未允许作为外部世界已变更的证据。
2. `dispatch_visible`
   - 调度层或 adapter 已尝试发出动作。
   - 仍不等于权威提交完成。
3. `journal_committed`
   - 相关记录已 durable append，并跨过 durable watermark。
   - 从此可作为恢复和审计的正式依据。
4. `recovered_unknown`
   - 进程故障或切换期间，真实外部状态无法仅靠 committed journal 直接判断。
   - 必须进入 probe / callback / adapter-log / manual 归并流程。

### 1.3 Journal Watermark 规范

系统 MUST 对每个 attempt 维护以下水位：

- `appendWatermark`: 本地已追加到 Journal 的最大序号。
- `durableWatermark`: 已 durable persist 的最大序号。
- `projectionWatermark`: 各投影视图已消费到的最大序号。
- `graphMaterializeWatermark`: Effect Graph materializer 已重建到的最大序号。

恢复时必须遵循：

- 权威恢复起点是 `durableWatermark`。
- `appendWatermark > durableWatermark` 的尾部区间必须视为“不确定尾部”。
- 不得让 UI、Graph 或 callback projection 反向定义 `durableWatermark`。

### 1.4 恢复判定规则

Finalizer 对 effect 的恢复判定必须遵循：

- 若 `journal_committed=true`，则以 Journal 为主。
- 若 `dispatch_visible=true` 但 `journal_committed=false`，则标记 `recovered_unknown`。
- 对 `recovered_unknown`:
  - `external_probeable_idempotent` -> 优先 probe / adapter 幂等日志归并。
  - `external_probeable_non_idempotent` -> 只读 probe，禁止盲重试。
  - `external_unprobeable_non_idempotent` -> 默认 `manual_required`，除非存在 callback-only 确认路径。
  - `irreversible` -> 直接升级 incident 或 manual follow-up。

### 1.5 建议新增字段

Journal 记录至少新增：

- `intentState`
- `dispatchState`
- `journalCommitState`
- `recoveryState`
- `appendWatermarkAtWrite`
- `durableWatermarkAtDecision`

---

## 2. Finalizer / Reaper / Worker 的接管仲裁与 fencing

### 2.1 目标

任何时刻，对同一个 attempt，必须只有一个“执行写权限拥有者”和一个“收场写权限拥有者”。

### 2.2 基本对象

每个 attempt MUST 具备：

- `attemptId`
- `attemptEpoch`
- `executionLeaseId`
- `takeoverLeaseId`
- `fencingToken`
- `writerRole = worker | finalizer | reaper | recovery_service`

### 2.3 Fencing 规则

1. 每次 worker 启动 attempt 时，获取新的 `attemptEpoch` 与 `fencingToken`。
2. Worker 对 Journal、状态投影、artifact finalize、effect dispatch 的写入 MUST 携带当前 `fencingToken`。
3. 一旦 Finalizer 成功接管：
   - 生成新的 `takeoverLeaseId`
   - 提升 `attemptEpoch`
   - 废弃旧 worker 的 `fencingToken`
4. 任何带旧 token 的迟到写入 MUST 被拒绝，并写审计事件 `stale_writer_rejected`。

### 2.4 接管顺序

当出现 `hard_cancel`、`worker_crash`、`lease_expired` 时：

1. Reaper 可先执行“杀执行单元”动作。
2. Finalizer 负责“写收场事实、回放 Journal、做补偿裁决”。
3. Prober 只能写 probe 记录，不得推进主状态。
4. Autopsy 只能生成旁路结论，不得直接推进主状态。
5. 只有 Finalizer 和显式人工 override 才能推进 `finalizing -> failed/cancelled/completed`。

### 2.5 双接管防护

系统 MUST 防止以下并发错误：

- 两个 Finalizer 同时接管同一 attempt。
- Worker 假死恢复后继续 dispatch。
- Reaper 回收资源后，旧 worker 仍可写 artifact close。
- Prober 结论覆盖 Finalizer 的主裁决。

建议增加状态：

- `takeover_pending`
- `takeover_active`
- `takeover_completed`
- `takeover_aborted`

### 2.6 权限矩阵

| 角色 | 可写主状态 | 可写 Journal | 可发起 effect | 可写 compensation | 可写 Autopsy 结论 |
|---|---:|---:|---:|---:|---:|
| Worker | 是 | 是 | 是 | 否 | 否 |
| Finalizer | 是 | 是 | 否 | 是 | 否 |
| Reaper | 否 | 是 | 否 | 否 | 否 |
| Prober | 否 | 是 | 否 | 否 | 否 |
| Autopsy | 否 | 是 | 否 | 否 | 是 |
| Operator Override | 是 | 是 | 受策略限制 | 受策略限制 | 否 |

---

## 3. 层级状态模型

### 3.1 四层状态

系统必须显式区分四层状态：

1. `runState`
2. `attemptState`
3. `childExecutionState`
4. `controlServiceState`

### 3.2 Run State

沿用 V2.5：

- `requested`
- `validating`
- `planning`
- `executing`
- `waiting_input`
- `waiting_approval`
- `finalizing`
- `completed`
- `failed`
- `cancelled`

### 3.3 Attempt State

建议正式化：

- `created`
- `booting`
- `active`
- `frozen`
- `handoff_pending`
- `recon_pending`
- `recon_running`
- `resume_ready`
- `finalizer_owned`
- `succeeded`
- `failed`
- `cancelled`
- `superseded`

规则：

- 同一 Run 在任意时刻最多只有一个 `active` attempt。
- 新 attempt 进入 `active` 前，旧 attempt MUST 进入 `superseded`、`failed` 或 `cancelled`，除非系统处于显式 parallel-branch 模式。

### 3.4 Child Execution State

建议正式化：

- `queued`
- `running`
- `waiting_dependency`
- `blocked`
- `soft_cancel_pending`
- `hard_kill_pending`
- `reaped`
- `completed`
- `failed`
- `cancelled`

### 3.5 Control Service State

控制服务实例状态建议统一：

- `idle`
- `claimed`
- `running`
- `degraded`
- `completed`
- `timed_out`
- `aborted`

### 3.6 聚合规则

父 Run 的状态聚合 MUST 明确：

- 只要存在 `attemptState=active` 且未进入人工门，`runState` 可维持 `executing`。
- 若存在人工输入门，Run 可进入 `waiting_input` 或 `waiting_approval`。
- 只要 Finalizer 已接管，Run MUST 进入 `finalizing`。
- 任一 child 的 `manual_required` 不必自动导致 Run terminal，但 MUST 反映到 `blockedBy` 或 `uiCompositeKey`。
- Attempt 层的 `recon_running` 不可直接映射为 Run 主状态，除非整个 Run 被 resume gate 阻塞。

### 3.7 状态覆盖优先级

建议优先级如下：

`finalizing > waiting_approval > waiting_input > executing > planning > validating > requested`

终态裁决优先级：

- `cancelled` 高于 `failed`，仅当存在有效 cancel 且策略允许收束为 cancelled。
- `failed` 高于 `completed`，若存在未闭环高风险 effect 或 cleanup 未完成，不得宣称 completed。

---

## 4. Compensation 作为一级 Effect

### 4.1 规范要求

补偿动作不再视为普通控制逻辑，而 MUST 被建模为一级 effect。

### 4.2 新增字段

每个 effect 节点至少新增：

- `effectType = primary | compensation | probe`
- `compensatesEffectId`
- `originEffectId`
- `compensationAttemptNo`
- `compensationIdempotencyKey`
- `compensationSafetyClass`

### 4.3 记录要求

补偿动作 MUST：

- 写入 Journal
- 具备 `effectSafetyClass`
- 具备 `probePolicy`
- 具备 `pessimisticFallbackPolicy`
- 具备自己的 `effectCommitState`

### 4.4 原则

- 补偿不是“历史抹除”，而是“后续纠正动作”。
- 原始 effect 一旦成立，系统不得把其事实从 Journal 中删除或伪装为未发生。
- `compensation_completed` 只能表示“补偿动作完成”，不能表示“原 effect 未发生”。

### 4.5 补偿失败后的处理

- 不允许无限递归“补偿补偿”。
- 对 compensation effect 的再次修正，必须被建模为新的 effect，而不是回写旧 effect。
- 系统 SHOULD 限制 `maxCompensationDepth=1`，超出后默认 `manual_required`。

---

## 5. Sanitization 与 Restricted Evidence 的补充规则

### 5.1 Sanitization 版本化

任何可外发的投影、Capsule、callback，都 MUST 记录：

- `sanitizationPolicyVersion`
- `sanitizationRunId`
- `redactionRuleSetVersion`
- `classifierModelVersion`
- `residualSanitizerVersion`
- `sanitizationDecisionHash`

### 5.2 漏检处置

若发现 false negative，系统 MUST 支持：

1. 标记 `sanitizationIncidentId`
2. 回溯受影响对象：
   - Capsule
   - callback payload
   - operator projection
   - search index
   - cache 副本
3. 启动 re-sanitize 任务
4. 对下游副本做 purge 或 tombstone
5. 生成审计记录

### 5.3 访问控制

Restricted Evidence Store 建议采用分层控制：

- `project_scope`
- `tenant_scope`
- `region_scope`
- `incident_scope`

访问动作至少分为：

- `view_metadata`
- `view_excerpt`
- `request_full_access`
- `break_glass_access`
- `export_reference`

### 5.4 审批与 break-glass

- 普通 operator 不得直接看 raw evidence。
- `request_full_access` SHOULD 需要双人审批或等价策略门。
- `break_glass_access` MUST 写明原因、时长、审批链和自动过期时间。
- 所有 evidence 访问 MUST 形成不可改写审计日志。

### 5.5 加密与密钥管理

至少要求：

- at-rest encryption
- envelope encryption
- key rotation policy
- 项目级或租户级隔离
- evidence ref 与明文内容分离存储

### 5.6 Operator Surface 规则

Paperclip 面板上禁止直接显示：

- raw env values
- full request/response body
- 未经脱敏的 trace excerpt
- restricted evidence inline body

仅允许显示：

- 摘要
- 引用 ID
- 脱敏片段
- 风险说明

---

## 6. Capsule V4 的合并、过期与预算规则

### 6.1 多作者合并优先级

当存在多份 Capsule 或多方建议时，建议采用以下优先级：

1. `operator_locked`
2. `self` 产出的最新有效 Capsule
3. `autopsy` 产出的 `advisory_with_validation`
4. `critic` 产出的 `advisory_with_validation`
5. `template_autopsy`

规则：

- 高优先级可覆盖低优先级 Head 字段。
- Body 和 Tail 默认合并引用，不直接覆盖原始证据关系。
- 冲突项必须写入 `capsuleMergeConflicts[]`。

### 6.2 过期规则

`expiresAt` 不应只作为展示字段，而 MUST 影响恢复流程：

- Head 过期 -> 必须重跑 `mustValidateFirst[]`，且默认降级 confidence。
- `environmentSnapshot` 过期 -> 必须触发 resume recon。
- `assumptionSet` 过期 -> 不得直接执行 `nextAttemptBrief`。
- `operator_locked` 内容过期 -> 必须要求人工重新确认。

### 6.3 Token Budget 合同

Head 应给出硬预算，例如：

- `maxHeadTokens`
- `maxBodySummaryTokens`
- `maxHypotheses`
- `maxMustValidateFirst`
- `maxMustNotRepeat`

裁剪顺序建议：

1. 保留 `currentGoal`
2. 保留 `highestPriorityTodo`
3. 保留 `mustValidateFirst[]`
4. 保留最高风险 `refutableHypotheses[]`
5. 保留 `mustNotRepeat[]`
6. 其他移动到 Body 或 ref

---

## 7. Resume Recon 的三层模型

### 7.1 三层检查

Resume Recon 建议拆为三层：

1. `code_artifact_recon`
2. `env_dependency_recon`
3. `external_state_recon`

### 7.2 Code / Artifact Recon

至少检查：

- branch / base commit 漂移
- patch set dry-run
- lockfile / artifact hash
- build graph 变化

### 7.3 Env / Dependency Recon

至少检查：

- runtime version
- dependency version
- secret version or fingerprint
- feature flag snapshot
- infra topology fingerprint

### 7.4 External State Recon

至少检查：

- 外部 API contract fingerprint
- quota / auth 健康状态
- 只读业务状态 probe
- irreversible / unknown effect 的现实状态引用

### 7.5 分级建议

建议 `amber` 与 `red` 的判定标准写成规则表，而不是文字说明。例如：

- patch dry-run 冲突但可自动修正 -> `amber`
- secret fingerprint 变化但 scope 不变 -> `amber`
- callback contract 变化且 effect 未闭环 -> `red`
- 外部权限失效导致关键 probe 不可执行 -> `red`

---

## 8. Watchdog 与 BatchIntent 的可解释性

### 8.1 Watchdog 结论必须可解释

每次 Watchdog 触发动作时，必须产出：

- `watchdogRuleId`
- `evidenceWindow`
- `matchedSignals[]`
- `suppressedSignals[]`
- `batchIntentContext`
- `decision = continue | warn | throttle | kill | escalate`

### 8.2 误杀复盘

系统 MUST 支持对 Watchdog 决策做事后复盘：

- 是否误杀合法批处理
- 是否漏掉无效循环
- 哪条规则贡献最大
- 是否需要 per-workload tuning

---

## 9. 配额与公平性补充

### 9.1 三层公平性

除父级回收池外，还应有：

- `tenantFairnessPolicy`
- `projectFairnessPolicy`
- `runBurstPolicy`

### 9.2 超支归并

当异步 usage report 延迟导致超支时，系统应明确：

- 是否允许短时 overrun
- overrun 上限
- overrun 记账方式
- 超支后是否冻结新 child lease

---

## 10. UI 合同补充

### 10.1 双层展示

前端 MUST 区分：

1. 默认操作视图: 只展示 `uiCompositeKey`
2. 治理诊断视图: 展示 `displayStatus / governanceIntent / blockedBy / phase / reasonCode / reconGrade / residualRiskSummary`

### 10.2 组件规则

- `uiCompositeKey` 是唯一主视觉状态。
- 诊断抽屉不得反向成为新的主状态源。
- 所有诊断字段都必须带来源版本与更新时间。

---

## 11. 迁移计划要求

### 11.1 迁移分期

从 V2.4 迁移到 V2.5 建议至少分四步：

1. 双写观测期
   - 保留旧 WAL / Effect DAG
   - 新增 Journal append 与 materializer
   - 只做比对，不做裁决
2. 阴影裁决期
   - Finalizer 同时跑旧恢复逻辑与新恢复逻辑
   - 以旧逻辑执行，以新逻辑打差异报告
3. 新逻辑主裁决期
   - 新 Journal / Graph 成为主裁决源
   - 旧逻辑降为 fallback
4. 旧逻辑清退期
   - 停止旧双写
   - 封存兼容读取层

### 11.2 兼容规则

- 老 run 不要求强制重写历史记录，但必须可映射到新投影层。
- 历史 attempt 若缺少新字段，应显式标记 `legacy_semantics=true`。
- 不允许把历史缺失字段静默解释为“安全默认值”。

---

## 12. Failure Injection 与验收测试

### 12.1 测试原则

Definition of Done 不应只写结果陈述，还必须附带可重复的 failure injection 用例。

### 12.2 最小测试矩阵

至少应覆盖以下场景：

1. Worker 在 `dispatch_visible` 后、`journal_committed` 前崩溃
2. Finalizer 接管时 Graph 落后于 Journal
3. 旧 worker 迟到写入被 fencing 拒绝
4. `external_unprobeable_non_idempotent` 进入 unknown 后不会盲重试
5. Sanitizer 漏检后触发 re-sanitize 与 purge
6. Autopsy 因预算耗尽降级为模板
7. Resume 时 code drift 为 `amber`
8. Resume 时 external state drift 为 `red`
9. BatchIntent 合法批处理不被误杀
10. cleanup reserve 耗尽后仍能正确输出 `cleanup_incomplete`

### 12.3 验收输出

每个用例都应产出：

- 事件时间线
- Journal 片段
- 期望状态转移
- 期望 UI composite
- 期望 callback
- 期望保留对象

---

## 13. 需要新增的正式文档

建议在 Phase 0 文档列表基础上再加六份：

1. `journal-authority-boundary-and-watermark.md`
2. `takeover-fencing-and-writer-ownership.md`
3. `hierarchical-state-model-run-attempt-child.md`
4. `compensation-as-first-class-effect.md`
5. `restricted-evidence-access-and-re-sanitization.md`
6. `migration-and-failure-injection-plan.md`

---

## 14. 建议新增 Schema 字段摘要

### 14.1 Attempt / Takeover

- `attemptEpoch`
- `fencingToken`
- `executionLeaseId`
- `takeoverLeaseId`
- `writerRole`
- `legacySemantics`

### 14.2 Journal

- `intentState`
- `dispatchState`
- `journalCommitState`
- `recoveryState`
- `appendWatermarkAtWrite`
- `durableWatermarkAtDecision`

### 14.3 Effect

- `effectType`
- `compensatesEffectId`
- `originEffectId`
- `compensationAttemptNo`
- `compensationIdempotencyKey`

### 14.4 Sanitization

- `sanitizationPolicyVersion`
- `sanitizationRunId`
- `redactionRuleSetVersion`
- `classifierModelVersion`
- `residualSanitizerVersion`
- `sanitizationDecisionHash`
- `sanitizationIncidentId`

### 14.5 Capsule

- `capsuleMergeConflicts[]`
- `maxHeadTokens`
- `headTruncationPolicy`
- `staleFieldSet[]`

---

## 15. 最终落点

V2.5 的方向是对的，但要让它真正变成工程合同，至少还需要三种收口：

1. 把“唯一真相源”改写成带水位和失败窗口的正式定义。
2. 把“外部接管”改写成带 fencing 和 writer ownership 的仲裁协议。
3. 把“恢复、脱敏、补偿”从原则层推进到 schema、测试、迁移、审计都可执行的规格层。

这三步补齐后，V2.5 才能从“很成熟的架构判断”进入“不会在实现阶段再次分裂”的状态。
