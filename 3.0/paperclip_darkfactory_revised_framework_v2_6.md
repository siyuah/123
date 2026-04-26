# Paperclip × Dark Factory 修订版框架 V2.6

**版本**：2.6  
**日期**：2026-04-21  
**定位**：在 V2.5 基础上，吸收 Claude Code 4.7 主评审、Claude 补充条款建议稿、Gemini 与 GLM5.1 最新一轮评审后形成的“可执行、可迁移、可验收”的收口版。  
**适用范围**：若与 V2.5 冲突，以本稿为准。若与本稿内部冲突，以更严格者为准。

---

## 0. V2.6 相对 V2.5 的一句话变化

V2.6 不再只是继续加防御机制，而是把 V2.5 里最容易被实现团队各自脑补的地方，收敛成六条正式合同：

1. **Execution Journal 不再被表述为“抽象唯一真相源”，而是正式定义为“唯一权威提交真相源”**，并配套四类事实边界与四类 watermark。  
2. **外部接管不再停留在“有 Finalizer 即可”**，而是写成带 `attemptEpoch / fencingToken / writerRole` 的接管仲裁协议。  
3. **Run 的单主状态继续保留，但 Attempt / Child / Control Service 也必须有正式层级状态模型**。  
4. **Compensation 不再只是控制逻辑，而是一级 Effect**，和 primary effect / probe 一样受 Journal、durability、idempotency、recovery policy 约束。  
5. **Sanitization 不再依赖“事后智能清洗”为主路径**，而改为“结构化隔离优先 + 确定性脱敏优先 + 残差 LLM 净化默认关闭”。  
6. **Resume 不再是一条路径**，而是区分 `same_attempt_retry / micro_recovery / full_rehearsal` 三条恢复车道，并把 `mustValidateFirst` 收紧为有预算上限的最高风险验证，而不是无限反证套娃。

> **一句话版本**：V2.6 的重点，是把 V2.5 从“原则正确”推进到“并发、崩溃、迁移、审计、脱敏、恢复都不会被不同团队解释成不同系统”。

---

## 1. 结论先行

V2.6 继续坚持方案 B，不推翻三层边界：

- **Paperclip**：控制面，负责协作、预算、审批、人工介入、治理展示、保留要求与受限证据访问申请。
- **Dark Factory**：执行面，负责 runtime、sandbox、verification、artifact、补偿、恢复、取证与执行证据。
- **Bridge**：集成面，只允许持有最小操作性状态，不升级为新的业务控制面。

但 V2.6 在 V2.5 基础上，再明确十个闭环：

1. **Journal 是唯一权威提交真相源**；Graph、UI projection、callback projection 都不能反向定义 Journal 的 committed 边界。  
2. **Journal 之外允许存在短暂的“已发起但未形成权威提交事实”的物理不确定窗口**；Finalizer 必须进入旁路核实模式，而不是假设“未记即未发”。  
3. **同一 attempt 任意时刻只能有一个执行写权限拥有者和一个收场写权限拥有者**；接管必须使用 epoch 与 fencing。  
4. **Run / Attempt / Child / Control Service 四层状态必须分别定义，再明确聚合规则**；Run 单主状态不等于其余层可以含混。  
5. **Effect DAG 继续存在，但它只是从 Journal + reconcile records 物化出来的裁决视图**；不能回到 Journal / DAG 双真相源。  
6. **黑盒非幂等副作用不再一刀切为手工阻断**；若支持 `callback-only` 或 `intent-token` 语义去重，可在受控条件下自动恢复。  
7. **Control Services 是逻辑角色，不是必须独立部署的微服务集群**；允许 Minimal Dark Factory 部署形态。  
8. **Capsule 升级为 V5**；加入多作者合并、字段级过期、最小披露、语义占位符、验证预算与 merge conflicts。  
9. **Sanitization 改为“sanitize-by-construction”主路径**；禁止默认把 LLM 当成第一道脱敏屏障。  
10. **Resume 分车道**；不再让所有失败都经过重型 Ephemeral Rehearsal，也不再允许未经检查直接原地热恢复。

---

## 2. V2.6 继承什么、修正什么

### 2.1 继续继承的部分

以下判断继续成立：

- 方案 B 不变，Paperclip 管治理，Dark Factory 管执行。  
- `ExternalRun / RunAttempt / ArtifactRef / TraceRef / ResourceLease` 仍成立。  
- Bridge 允许最小状态化，但仅限去重、验签、顺序控制、对账与投递补偿。  
- Run 继续只有**一个权威主状态机**；中断、恢复、租约、清理、限流都降为标签或属性。  
- 继续承认**不可中断原子区**存在，不把“实时中断长推理”当成基本假设。  
- 继续坚持：**副作用治理优先于完美状态水合**。  
- 继续坚持：**cleanup reserve / postmortem reserve 不可被执行阶段侵占**。  
- 继续坚持：**Resume 不能原地无限等待审批热会话**，必须经过明确的 retry / recovery / rehearsal 车道。

### 2.2 相对 V2.5 的修正

V2.5 已经补上了单真相源、Effect Policy、Closure 预算、Capsule V4、Ephemeral Rehearsal 与 UI composite。  
V2.6 进一步把下列问题从“原则正确”推进到“实现不分歧”：

- 把“唯一真相源”正式改写为 **唯一权威提交真相源**。  
- 给 Finalizer / Reaper / Prober / Worker 增加 **接管仲裁和 stale write 防护**。  
- 把 **Attempt / Child / Control Service** 从隐含状态机提升为正式模型。  
- 把 **compensation** 正式纳入 effect model。  
- 把 **sanitization false negative、re-sanitize、purge、break-glass** 写成制度面。  
- 把 **Capsule merge / stale fields / head token budget / authority precedence** 写成规格面。  
- 把 Resume 从一刀切 rehearsal 改成 **三条恢复车道 + 三层 Recon**。  
- 把 “外部不可探测非幂等” 从单一悲观桶细分为 **callback-only / intent-token / manual-only** 恢复策略。  
- 把控制服务从“必须拆八个独立微服务”改成 **逻辑角色可分离、部署形态可合并**。  
- 补上 **Migration Plan + Failure Injection**，让 Definition of Done 可验证而不是停留在陈述。

---

## 3. V2.6 的六条硬约束

### 3.1 唯一主状态不变，但必须存在层级状态模型

- Run 仍只有一个权威主状态。  
- Attempt / Child / Control Service 必须有正式状态集合与聚合规则。  
- UI 允许只把 Run 主状态作为主视觉状态，但诊断层必须可下钻到其余三层。

### 3.2 Journal 是唯一权威提交真相源

- 所有影响恢复、补偿、probe、审计归因的事实，最终都 MUST 归并到 Journal。  
- 在 durable watermark 之前，系统 MAY 处于短暂不确定窗口。  
- Graph、UI、callback、缓存、副本都不得反向定义 committed 事实。  

### 3.3 接管必须有 writer ownership

- 同一 attempt 任意时刻只允许一个“执行写权限拥有者”。  
- 同一 attempt 任意时刻只允许一个“收场写权限拥有者”。  
- 旧 writer 的迟到写入必须可被 fencing 拒绝，并写审计事件。

### 3.4 Effect 与 Compensation 同为一级实体

- `primary | compensation | probe` 是同级 `effectType`。  
- 补偿不是“撤销历史”，只是“记录化的后续纠正动作”。  
- 原 effect 一旦形成 committed 事实，系统不得把它伪装成“从未发生”。

### 3.5 脱敏必须以结构化隔离为主，而不是事后智能清洗为主

- Tool Adapter 与 Worker 输出 SHOULD 优先区分 `operatorSafeSummary` 与 `restrictedRawRef`。  
- 确定性 redaction 与结构分类是默认主路径。  
- 残差 LLM sanitizer 默认为 **off**；只有 incident replay、离线 re-sanitize 或人工授权路径才可启用。

### 3.6 Resume 必须分车道，反证必须有预算上限

- 不允许对所有失败一律走重型 rehearsal。  
- 不允许把 `mustValidateFirst[]` 做成无限递归的“证明别人错”。  
- 恢复前只要求验证**最高风险且最可判定**的假设，受 `validationBudget` 与 `maxValidationSteps` 约束。

---

## 4. 核心架构边界（V2.6）

### 4.1 Paperclip（Control Plane）

继续负责：

- Company / Project / Goal / Task
- Approval / Budget / Comment / Operator Intervention
- `ExternalRun` 身份、治理投影与人工接管入口
- 高优先级治理动作：Cancel / Override / Resume / Access Request
- 保留策略、审计要求、受限证据访问审批

新增要求：

- 默认只展示一个主视觉状态：`uiCompositeKey`。  
- 诊断抽屉必须可展示：`displayStatus / governanceIntent / blockedBy / phase / reasonCode / reconGrade / residualRiskSummary / sourceVersion`.  
- 只允许展示 operator-safe 摘要、引用 ID、脱敏片段，不展示 raw env values、完整请求体、未经脱敏的 trace。  
- 可以发起 `request_full_access` 或 `break_glass_access`，但必须经过策略门与审计。

明确不做：

- 不保存 artifact / trace / restricted evidence 原始本体。
- 不直接管理 sandbox / worktree / container 生命周期。
- 不保存原始私有 CoT 或模型内部 KV cache。

### 4.2 Bridge（Integration Plane）

继续负责：

- 输入映射
- 输出映射
- 回调验签
- 幂等去重
- 顺序处理
- 生命周期事件投递与对账补偿

允许保存的最小操作性状态：

- `idempotencyKey`
- `eventId`
- `lastAcceptedSequenceNo`
- `lastLifecycleEventAt`
- `deliveryRetryState`
- `reconcileCursor`
- `retentionAck`
- `callbackProjectionWatermark`

明确限制：

- Bridge 不保存完整细粒度 progress 流。  
- Bridge 不保存完整 trace 流。  
- Bridge 不做 model routing，不做 verification 策略，不做配额仲裁，不做审批判断，不做恢复裁决。  

### 4.3 Dark Factory（Execution Plane）

继续负责：

- task spec / acceptance spec
- runtime / orchestration / verification
- sandbox / worktree / container / cleanup
- artifact / evidence / execution summary
- effect ledger、compensation、lease、resume capsule、recon 的底层落地
- restricted evidence store 与 journaling

新增要求：

- Journal 是 committed boundary 的唯一来源。  
- Effect Graph、callback projection、UI projection 全部由 Journal 物化。  
- 任一可写外部操作都必须声明：`effectSafetyClass`、`probePolicy`、`pessimisticFallbackPolicy`、`durabilityClass`、`dedupeCapability`。  
- 任一恢复车道都必须记录 `recoveryLane` 与 `reconEvidenceCompleteness`。  

### 4.4 Dark Factory Control Roles（逻辑角色，可合并部署）

V2.6 明确以下角色是**逻辑角色**，不是必须独立部署的服务边界：

- `Worker`
- `Finalizer`
- `Reaper`
- `Prober`
- `Critic`
- `Autopsy`
- `Recon`
- `Quota Scheduler`
- `Sanitization Pipeline`

允许三种部署形态：

1. **Minimal Dark Factory**
   - `runtime-gateway`
   - `worker-pool`
   - `recovery-daemon`（合并 Finalizer + Reaper + Prober + template Autopsy）
   - `journal + restricted evidence`
   - `quota logic` 以库形式内嵌到 runtime-gateway

2. **Standard**
   - 在 Minimal 基础上拆出 `sanitization service` 与 `quota scheduler`

3. **Full**
   - 仅在高吞吐、多租户、强审计场景下，才把上述角色分别独立部署

约束：

- 逻辑角色可合并部署，但**权限边界、writer ownership、审计边界不可合并消失**。  
- 无论采用哪种形态，都必须满足 fencing、budget reserve、restricted evidence 与 Journal boundary 的合同。

---

## 5. 层级状态模型与 UI 合同

### 5.1 Run 主状态（唯一权威）

Run 继续只保留一个主状态：

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

终态优先级：

- 存在有效 cancel 且策略允许时，`cancelled` 高于 `failed`  
- 只要存在未闭环高风险 effect、cleanup 未完成、incident 未裁决，不得宣称 `completed`

### 5.2 Attempt 状态

Attempt MUST 至少具备：

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

- 同一 Run 任意时刻最多只有一个 `active` attempt，除非系统处于显式 parallel-branch 模式。  
- 新 attempt 进入 `active` 前，旧 attempt MUST 进入 `superseded`、`failed` 或 `cancelled`。  

### 5.3 Child Execution 状态

Child / auxiliary executor / verification worker MUST 至少具备：

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

### 5.4 Control Service 状态

Control Service 实例建议统一：

- `idle`
- `claimed`
- `running`
- `degraded`
- `completed`
- `timed_out`
- `aborted`

### 5.5 聚合规则

- 只要存在 `attemptState=active` 且未进入人工门，Run 可维持 `executing`。  
- 若存在人工输入门，Run 可进入 `waiting_input` 或 `waiting_approval`。  
- Finalizer 成功接管后，Run MUST 进入 `finalizing`。  
- 任一 child 的 `manual_required` 不必自动使 Run terminal，但 MUST 反映到 `blockedBy` 与诊断层。  
- `recon_running` 是 Attempt 层状态；除非整个 Run 被 resume gate 阻塞，否则不直接提升为 Run 主状态。  

### 5.6 调试标签与 UI 展示字段

保留以下非主状态字段：

- `displayStatus`
- `governanceIntent`
- `blockedBy`
- `phase`
- `reasonCode`
- `reconGrade`
- `residualRiskSummary`
- `cleanupTag`
- `recoveryTag`
- `retentionTag`

前端规则：

- 默认操作视图：只展示 `uiCompositeKey`。  
- 治理诊断视图：展示上述诊断字段与对应 `sourceVersion / updatedAt`。  
- 诊断抽屉不得反向成为新的主状态源。  

### 5.7 `uiCompositeKey` 的降维规则

V2.6 不要求后端维护无限膨胀的笛卡尔积字典。  
后端 SHOULD 只输出有限元状态：

- `healthy_executing`
- `waiting_on_human`
- `cancelling`
- `recovering`
- `blocked_manual`
- `blocked_unknown_effect`
- `finalizing_cleanup`
- `done_completed`
- `done_failed`
- `done_cancelled`

同时附带 `contextJson`：

- `displayStatus`
- `governanceIntent`
- `blockedBy`
- `phase`
- `reasonCode`
- `reconGrade`
- `residualRiskSummary`

约束：

- 主视觉态必须是有限集合。  
- 上下文细节由诊断层补足。  
- 不允许让后端通过 if-else 穷举所有组合爆炸场景。  

---

## 6. 中断模型、接管仲裁与 Closure 预算

### 6.1 中断分类

V2.6 继续定义：

1. `soft_cancel`
2. `hard_cancel`
3. `override_or_resume`

处理规则：

- `soft_cancel` 在安全点消费。  
- 超过 `softCancelGraceSec` 仍未退出，则升级为 `hard_cancel`。  
- `override_or_resume` 不允许原地无限等待；必须 freeze 当前 attempt 并进入新 attempt。  

### 6.2 不可中断区

必须显式承认下列场景可能不可实时中断：

- 单次长模型推理调用
- 已发出的外部工具调用
- 原子性 artifact 上传 / publish
- 已进入不可中断数据库事务的 adapter

要求：

- 不可中断区结束后，必须在下一个安全点立即消费中断。  
- 若外部治理动作发生在不可中断区，UI 应显示 `cancelling` 或等价治理态，而不是“假死”。  

### 6.3 接管仲裁对象

每个 attempt MUST 至少具备：

- `attemptId`
- `attemptEpoch`
- `executionLeaseId`
- `takeoverLeaseId`
- `fencingToken`
- `writerRole = worker | finalizer | reaper | recovery_service`

### 6.4 Fencing 规则

1. Worker 启动 attempt 时，获取新的 `attemptEpoch` 与 `fencingToken`。  
2. Worker 对 Journal、状态投影、artifact finalize、effect dispatch 的写入 MUST 携带当前 `fencingToken`。  
3. 一旦 Finalizer 接管：
   - 生成新的 `takeoverLeaseId`
   - 提升 `attemptEpoch`
   - 废弃旧 worker 的 `fencingToken`
4. 任何带旧 token 的迟到写入 MUST 被拒绝，并写审计事件 `stale_writer_rejected`。  

### 6.5 接管顺序与角色权限

当出现 `hard_cancel`、`worker_crash`、`lease_expired` 时：

1. Reaper 可以先执行“杀执行单元”。  
2. Finalizer 负责“写收场事实、回放 Journal、做补偿裁决”。  
3. Prober 只能写 probe 记录，不得推进主状态。  
4. Autopsy 只能生成 advisory，不得直接推进主状态。  
5. 只有 Finalizer 和显式人工 override 才能推进 `finalizing -> failed/cancelled/completed`。  

建议状态：

- `takeover_pending`
- `takeover_active`
- `takeover_completed`
- `takeover_aborted`

### 6.6 权限矩阵

| 角色 | 可写主状态 | 可写 Journal | 可发起 primary effect | 可写 compensation | 可写 advisory |
|---|---:|---:|---:|---:|---:|
| Worker | 是 | 是 | 是 | 否 | 否 |
| Finalizer | 是 | 是 | 否 | 是 | 否 |
| Reaper | 否 | 是 | 否 | 否 | 否 |
| Prober | 否 | 是 | 否 | 否 | 否 |
| Critic / Autopsy | 否 | 是 | 否 | 否 | 是 |
| Operator Override | 是 | 是 | 受策略限制 | 受策略限制 | 否 |

### 6.7 Closure 预算

V2.6 继续保留双保留预算：

- `reservedCleanupBudgetUsd`
- `postmortemReserveBudgetUsd`

原则：

- 执行阶段不能侵占 closure reserve。  
- Finalizer、Prober、Autopsy、Recon 的预算从对应 reserve 走，不与普通 Worker 抢最后一口预算。  
- 若 reserve 耗尽，系统 MUST 输出 `cleanup_incomplete`、`postmortem_degraded` 等显式摘要，而不是静默失败。  

---

## 7. Watchdog：有效推进、BatchIntent 与误杀复盘

### 7.1 有效推进证据

续租判断至少应基于以下一项：

- `progressCursor` 推进
- `lastMilestone` 更新
- `decisionCheckpoint` 变化
- `worktreeDiffFingerprint` 变化
- `artifactSetDelta`
- `BatchIntent` 内部的合法计数推进

`keepalive` 只证明“进程还活着”，不证明“任务仍在有效推进”。

### 7.2 伪推进识别

Watchdog SHOULD 记录：

- `watchdogRuleId`
- `evidenceWindow`
- `matchedSignals[]`
- `suppressedSignals[]`
- `batchIntentContext`
- `decision = continue | warn | throttle | kill | escalate`

必须支持误杀复盘：

- 是否误杀合法批处理
- 是否漏掉无效循环
- 哪条规则贡献最大
- 是否需要 per-workload tuning

### 7.3 BatchIntent

当 Agent 进入合法批处理前，必须可声明：

- `batchIntentId`
- `plannedIterations`
- `expectedToolPattern`
- `expectedArtifactDelta`
- `maxNoDiffIterations`
- `expiryAt`

规则：

- 有效的 `BatchIntent` 可以放宽伪推进阈值。  
- 超出 `BatchIntent` 范围或过期后，Watchdog 重新按普通规则裁决。  

---

## 8. Execution Journal：唯一权威提交真相源

### 8.1 正式定义

V2.6 将“Journal 是唯一真相源”正式收敛为：

- Journal 是唯一的**权威提交真相源**。  
- 所有会影响恢复决策、补偿决策、probe 决策、审计归因的执行事实，最终都 MUST 归并到 Journal。  
- 在记录尚未跨过 durable watermark 之前，系统 MAY 处于“已发起但未形成权威提交事实”的短暂不确定窗口。  
- Finalizer 在该窗口内 MUST 进入**旁路核实模式**，不得直接假定“Journal 未记即未发生”。  

### 8.2 四类事实边界

每个可写 effect 或关键执行动作，至少必须区分：

1. `intent_recorded`
2. `dispatch_visible`
3. `journal_committed`
4. `recovered_unknown`

解释：

- `intent_recorded`：已写入意图，但不能作为外部世界已变更的证据。  
- `dispatch_visible`：adapter 已尝试发出动作，但仍不等于 committed。  
- `journal_committed`：相关记录已 durable append，并跨过 durable watermark。  
- `recovered_unknown`：崩溃或切换期间，真实外部状态无法仅靠 committed journal 直接判断。  

### 8.3 Watermark 规范

系统 MUST 对每个 attempt 维护：

- `appendWatermark`
- `durableWatermark`
- `projectionWatermark`
- `graphMaterializeWatermark`

恢复规则：

- 权威恢复起点是 `durableWatermark`。  
- `appendWatermark > durableWatermark` 的尾部区间视为“不确定尾部”。  
- UI、Graph、callback projection 不得反向定义 `durableWatermark`。  

### 8.4 Journal 与 Graph 的关系

- Effect Graph 是裁决视图，不是第二真相源。  
- Graph 只能从以下材料物化：
  - committed Journal
  - probe records
  - callback reconcile records
  - operator adjudication records
- 任一 reconcile 结果想成为权威事实，必须回写成新的 Journal record。  
- Worker 可以维护临时 in-memory graph 以优化调度，但该图不得拥有独立权威语义。  

### 8.5 恢复裁决规则

Finalizer 对 effect 的恢复判定必须遵循：

- 若 `journal_committed=true`，则以 Journal 为主。  
- 若 `dispatch_visible=true` 但 `journal_committed=false`，则标记 `recovered_unknown`。  
- 对 `recovered_unknown`：
  - `external_probeable_idempotent` -> 优先 probe / adapter 幂等日志归并  
  - `external_probeable_non_idempotent` -> 只读 probe，禁止盲重试  
  - `external_unprobeable_non_idempotent` -> 走 callback-only / intent-token / manual-only 子策略  
  - `irreversible` -> 升级 incident 或 manual follow-up  

---

## 9. Effect Model：Primary / Compensation / Probe 一等化

### 9.1 统一 Effect 结构

每个 effect 节点至少具备：

- `effectId`
- `effectType = primary | compensation | probe`
- `effectSafetyClass`
- `originEffectId`
- `compensatesEffectId`
- `dependsOnEffectIds[]`
- `compensationAttemptNo`
- `compensationIdempotencyKey`
- `durabilityClass`
- `probePolicy`
- `pessimisticFallbackPolicy`
- `effectCommitState`

### 9.2 补偿原则

- 补偿不是“历史抹除”，而是“后续纠正动作”。  
- 原始 effect 一旦 committed，系统不得删除或伪装成“未发生”。  
- `compensation_completed` 只表示补偿动作完成，不表示原 effect 未发生。  

### 9.3 补偿拓扑与深度限制

- 补偿必须按依赖拓扑裁决，而不是简单倒序遍历 list。  
- 若上游补偿失败，下游补偿 MAY 冻结、降级或直接 `manual_required`。  
- 系统 SHOULD 限制 `maxCompensationDepth=1`；超出后默认人工处理。  

### 9.4 `external_unprobeable_non_idempotent` 的细分策略

V2.6 不再一刀切地把该类 effect 全部导向 `manual_required`，而是增加：

- `dedupeCapability = none | callback_only | intent_token | provider_idempotency_key`
- `blastRadiusClass = low | medium | high`
- `confirmationChannel = none | callback | adapter_audit | operator`

恢复规则：

1. `callback_only`
   - 不允许 blind retry
   - 允许等待确定性 callback 归并
2. `intent_token` / `provider_idempotency_key`
   - 在 `blastRadiusClass <= medium` 且策略允许时，允许有限次数自动重试
   - 重试必须复用同一 `semanticIntentId`
3. `none`
   - 默认 `manual_required`
   - 对高影响场景可直接 incident

### 9.5 不可逆副作用

若 `effectSafetyClass=irreversible`：

- 必须在 run 启动前由策略显式允许。  
- 不允许 auto-retry 重复执行。  
- 失败时只允许 waiver / incident / operator follow-up，不得伪装成已回滚。  

---

## 10. Durability 分层：强一致只用在值得强一致的地方

### 10.1 原则

V2.6 继续承认物理世界不完美，但把“哪些可以丢、哪些绝不能丢”写成分层合同。

### 10.2 建议 `durabilityClass`

- `ephemeral_local`
- `local_append`
- `local_sync`
- `durable_async`
- `durable_pre_dispatch`

### 10.3 默认映射

- 只读工具、临时 scratch、可重建中间结果 -> `local_append` 或 `local_sync`
- probe 记录 -> `durable_async`
- 可补偿外部写 -> 至少 `durable_async`
- 高风险、不可逆、不可安全探测的外部写 -> `durable_pre_dispatch`

### 10.4 允许的物理不完美

- 允许低风险尾部 `append > durable` 丢失少量记录。  
- 不允许高风险外部写在 `durable_pre_dispatch` 缺失时就被发出。  
- 若系统降级到 `template_autopsy` 或 `cleanup_incomplete`，必须显式体现在 UI、callback 与审计记录里。  

---

## 11. 配额、限流与公平性

### 11.1 预算字段

建议保留并扩展：

- `executionBudgetUsd`
- `verificationBudgetUsd`
- `reservedCleanupBudgetUsd`
- `postmortemReserveBudgetUsd`
- `executionWallClockSec`
- `reservedCleanupWallClockSec`
- `runBurstPolicy`
- `tenantFairnessPolicy`
- `projectFairnessPolicy`

### 11.2 Quota Lease

子执行单元优先使用本地预分配额度：

- `childSpendLeaseUsd`
- `childTokenLease`
- `childRpmLease`
- `childLeaseExpiresAt`

只有本地额度耗尽时，才向中心请求续配。  
这将 99% 的热路径裁决转为本地计算，避免把 Scheduler 变成全局锁点。

### 11.3 父级回收池

V2.6 继续放弃兄弟实时借调，保留：

- `parentReclaimPoolUsd`
- `parentReclaimPoolTokens`
- `reclaimDelaySec`

未使用配额回收到父级回收池，再由父级统一再分配。

### 11.4 超支与 eventually reconciliation

必须明确：

- 是否允许短时 overrun  
- overrun 上限  
- overrun 记账方式  
- 超支后是否冻结新 child lease  

### 11.5 控制服务预算

Finalizer / Prober / Autopsy / Recon 使用独立 reserve。  
当 LLM 尸检不可用时，Autopsy MUST 自动降级为 `template_autopsy`，不得因预算耗尽而卡死收场链路。

---

## 12. Capsule V5：多作者合并、最小披露与有界验证

### 12.1 升级目标

V2.6 将 Capsule 从 V4 升级为 V5，解决四个问题：

1. 多作者冲突  
2. 字段过期与世界线漂移  
3. 语义脱敏后如何不把调试线索洗瞎  
4. 反证门如何防止无限套娃  

### 12.2 作者与权威等级

建议：

- `capsuleAuthor = self | critic | autopsy | template_autopsy | operator`
- `capsuleAuthority = advisory | advisory_with_validation | operator_locked`

说明：

- Critic / Autopsy 只有“建议权”，没有绝对执行权。  
- `operator_locked` 可覆盖 Head 字段，但不得篡改原始 Journal 事实。  

### 12.3 Capsule V5 结构

#### Head（最高优先级注入区）

- `currentGoal`
- `highestPriorityTodo`
- `mustValidateFirst[]`
- `mustNotRepeat[]`
- `refutableHypotheses[]`
- `nextAttemptBrief`
- `validationBudgetUsd`
- `maxValidationSteps`
- `staleFieldSet[]`

#### Body（结构化恢复区）

- `openTodos`
- `knownFailures`
- `rejectedApproaches`
- `activeHypotheses`
- `decisionCheckpoint`
- `environmentSnapshot`
- `assumptionSet`
- `batchIntentSnapshot`
- `recoveryLaneRecommendation`

#### Tail（证据与引用区）

- `recentToolLedgerTail`
- `artifactRefs`
- `traceRefs`
- `restrictedEvidenceRefs`
- `probeRefs`
- `capsuleMergeConflicts[]`

### 12.4 语义占位符与最小披露

为防止脱敏破坏上下文，Capsule SHOULD 优先携带：

- `typedPlaceholder`
- `digest`
- `semanticSurrogate`
- `restrictedEvidenceRef`

示例：

- `DB_ERROR_REF:err_abc123`
- `PAYLOAD_DIGEST:sha256:...`
- `SECRET_FINGERPRINT:kms:v3:...`

要求：

- 不在 Head 中直接放 raw secret / PII / 明文 token。  
- 允许通过语义占位符保留排错语境。  

### 12.5 多作者合并优先级

建议优先级：

1. `operator_locked`
2. 最新有效 `self`
3. `autopsy` 的 `advisory_with_validation`
4. `critic` 的 `advisory_with_validation`
5. `template_autopsy`

规则：

- 高优先级可覆盖低优先级 Head 字段。  
- Body 与 Tail 默认合并引用，不直接覆盖原始证据。  
- 冲突项必须写入 `capsuleMergeConflicts[]`。  

### 12.6 过期规则

- `expiresAt` 必须影响恢复流程，而不是只做展示。  
- Head 过期 -> 必须重跑 `mustValidateFirst[]`，并降低 confidence。  
- `environmentSnapshot` 过期 -> 必须触发 Recon。  
- `assumptionSet` 过期 -> 不得直接执行 `nextAttemptBrief`。  
- `operator_locked` 内容过期 -> 必须人工重新确认。  

### 12.7 有界验证，而不是无限反证

V2.6 收紧 `mustValidateFirst[]`：

- 只要求验证最高风险且最可判定的 1~N 个假设。  
- 受 `validationBudgetUsd`、`maxValidationSteps`、`maxValidationWallClockSec` 限制。  
- 不允许在同一恢复车道内触发 “critic of critic” 套娃。  
- 若验证无法完成，允许降级为 `manual_required` 或 `resume_with_warning`。  

---

## 13. Sanitization 与 Restricted Evidence：结构化隔离优先

### 13.1 主路径：Sanitize by Construction

Tool Adapter 与 Worker 输出 SHOULD 优先分成：

- `operatorSafeSummary`
- `restrictedRawRef`
- `safeExcerpt[]`
- `semanticSurrogates[]`

主路径原则：

- 不试图在事后清洗一整坨混杂 raw data。  
- 优先在生成时就把“安全摘要”和“受限原文”拆开。  

### 13.2 确定性脱敏优先

任何可外发的 projection、Capsule、callback 都 MUST 记录：

- `sanitizationPolicyVersion`
- `sanitizationRunId`
- `redactionRuleSetVersion`
- `classifierModelVersion`
- `sanitizationDecisionHash`

默认管线：

1. deterministic redaction  
2. structured classifier / field policy  
3. excerpt selection  
4. restricted evidence ref 绑定  

### 13.3 残差 LLM sanitizer 默认关闭

`residualSanitizerVersion` 可以存在，但默认策略为：

- `mode = off` 用于在线主路径  
- 只有在 incident replay、离线 re-sanitize、或人工授权路径下才可启用  

理由：

- 避免延迟翻倍  
- 避免过度清洗破坏排错语境  
- 避免让非确定性 LLM 充当第一道安全边界  

### 13.4 漏检处置与重洗

发现 false negative 时，系统 MUST 支持：

1. 标记 `sanitizationIncidentId`
2. 回溯受影响对象：
   - Capsule
   - callback payload
   - operator projection
   - search index
   - cache 副本
3. 启动 re-sanitize 任务
4. 对下游副本做 purge 或 tombstone
5. 生成不可改写审计记录

### 13.5 Restricted Evidence 访问控制

建议 scope：

- `project_scope`
- `tenant_scope`
- `region_scope`
- `incident_scope`

访问动作：

- `view_metadata`
- `view_excerpt`
- `request_full_access`
- `break_glass_access`
- `export_reference`

规则：

- 普通 operator 不得直接看 raw evidence。  
- `request_full_access` SHOULD 需要双人审批或等价策略门。  
- `break_glass_access` MUST 记录原因、时长、审批链与自动过期时间。  
- 所有 evidence 访问 MUST 形成不可改写审计日志。  

### 13.6 加密与密钥管理

至少要求：

- at-rest encryption
- envelope encryption
- key rotation policy
- 项目级或租户级隔离
- evidence ref 与明文内容分离存储

---

## 14. Resume 链路：三条恢复车道 + 三层 Recon

### 14.1 三条恢复车道

V2.6 将恢复拆为：

1. `same_attempt_retry`
   - 仅用于当前 active attempt 内的短暂工具失败或瞬态网络抖动
   - 不改变 attempt ownership
   - 不生成新 attempt

2. `micro_recovery`
   - 生成新 attempt，但允许复用原 worktree
   - 只做最轻量前置检查
   - 适用于 `environment_transient_failure`、`minor_logic_error`、短时间失败回退

3. `full_rehearsal`
   - 生成新 attempt
   - 在隔离克隆工作区执行完整 Rebase & Recon
   - 适用于等待审批、长时间挂起、世界线漂移、unknown effect 未闭环等场景

### 14.2 车道选择规则

必须至少满足以下条件之一才允许 `micro_recovery`：

- 上次失败分类属于低风险瞬态或微小逻辑错误  
- 不存在 `pendingExternalUnknown=true`  
- 不涉及审批等待后的恢复  
- 不存在已知 branch drift / secret fingerprint drift / callback contract drift  
- `elapsedSinceFreezeSec` 未超过阈值

否则必须进入 `full_rehearsal`。

### 14.3 三层 Recon

`full_rehearsal` SHOULD 至少拆为：

1. `code_artifact_recon`
2. `env_dependency_recon`
3. `external_state_recon`

#### Code / Artifact Recon

- branch / base commit 漂移
- patch set dry-run
- lockfile / artifact hash
- build graph 变化

#### Env / Dependency Recon

- runtime version
- dependency version
- secret fingerprint
- feature flag snapshot
- infra topology fingerprint

#### External State Recon

- 外部 API contract fingerprint
- quota / auth 健康状态
- 只读业务状态 probe
- irreversible / unknown effect 的现实状态引用

### 14.4 风险分级与容忍度

建议：

- `green`
- `amber`
- `red`

示例：

- patch dry-run 冲突但可自动修正 -> `amber`
- secret fingerprint 变化但 scope 不变 -> `amber`
- callback contract 变化且 effect 未闭环 -> `red`
- 外部权限失效导致关键 probe 不可执行 -> `red`

要求：

- `amber` 不等于阻断；可以 `resume_with_warning`。  
- `red` 必须阻断自动恢复，走人工或重新 planning。  
- 缺少环境 twin 或无法完整克隆外部运行态，不得自动判 `red`；应根据 `evidenceCompleteness` 与 live read-only probes 综合评定。  

### 14.5 外部状态真空的处理

V2.6 明确：

- Ephemeral clone 只解决 code / artifact 层问题。  
- 外部运行态不要求“克隆一个数据库宇宙”。  
- 对外部世界的 Recon 依赖：
  - read-only probe
  - contract fingerprint
  - adapter health
  - callback status
  - operator provided evidence

若外部状态证据不完整：

- 可以给出 `amber + partial_evidence`  
- 而不是默认输出 `red`

---

## 15. 观测、回调、保留与 Operator Surface

### 15.1 Bridge 处理的生命周期事件

仅保留：

- `run_state_changed`
- `interrupt_acknowledged`
- `guardrail_exhausted`
- `compensation_started / completed / failed`
- `cleanup_started / completed / failed`
- `resume_capsule_available`
- `lease_expired`
- `recon_started / completed`
- `takeover_started / completed`

### 15.2 Observability 专线

细粒度 telemetry 直接走 OTLP / PubSub / 日志平台：

- token / model call 统计
- sub-agent span
- step 级耗时
- verification 流水
- sanitizer / recon 内部明细

### 15.3 RetentionPolicy

建议：

- `retentionClass = standard_30d | audit_1y | legal_hold`
- `retainUntil`
- `allowEarlyPurge`
- `legalHold`

约束：

- Paperclip 声明最低保留要求  
- Dark Factory 可以保留更久，但不能更短  
- restricted evidence 的 purge / tombstone 必须遵守 legal hold 与 incident 审计要求

### 15.4 Operator Surface 规则

禁止在 Paperclip 面板中直接显示：

- raw env values
- full request/response body
- 未经脱敏的 trace excerpt
- restricted evidence inline body

仅允许显示：

- 摘要
- 引用 ID
- 脱敏片段
- 风险说明
- 访问申请入口

---

## 16. 合同增量（V2.6）

### 16.1 `POST /api/external-runs` 建议字段（更新）

```json
{
  "externalRunId": "pc_run_456",
  "requestedMode": "execute",
  "contextBoundary": {
    "toolAllowlist": ["git", "npm", "playwright"],
    "networkAccessLevel": "repo-default",
    "secretMountPolicy": "repo-default",
    "capabilityDelegationPolicy": "subagents-must-downgrade"
  },
  "budgetPolicy": {
    "executionBudgetUsd": 12,
    "verificationBudgetUsd": 4,
    "reservedCleanupBudgetUsd": 4,
    "postmortemReserveBudgetUsd": 2,
    "executionWallClockSec": 1800,
    "reservedCleanupWallClockSec": 300
  },
  "interruptPolicy": {
    "softCancelGraceSec": 60,
    "hardKillAfterSec": 180,
    "cascadeToSubagents": true
  },
  "leasePolicy": {
    "ttlSec": 3600,
    "renewBeforeSec": 300,
    "stuckThresholdSec": 240,
    "watchdogRequired": true
  },
  "effectPolicy": {
    "recordSideEffects": true,
    "requireCompensationForWritableTools": true,
    "allowIrreversibleEffects": false,
    "defaultDedupeCapability": "none"
  },
  "resumePolicy": {
    "emitResumeCapsule": true,
    "defaultRecoveryLane": "micro_recovery",
    "fullRehearsalRequiredAfterApprovalWait": true
  },
  "sanitizationPolicy": {
    "sanitizeByConstructionRequired": true,
    "residualLlMSanitizerDefault": "off"
  },
  "observabilityPolicy": {
    "lifecycleViaBridge": true,
    "fineTelemetryVia": "otlp"
  },
  "retentionPolicy": {
    "retentionClass": "audit_1y",
    "allowEarlyPurge": false
  }
}
```

### 16.2 回调建议新增字段

- `runStatus`
- `attemptState`
- `phase`
- `reasonCode`
- `uiCompositeKey`
- `displayStatus`
- `governanceIntent`
- `blockedBy`
- `reconGrade`
- `lastMilestone`
- `guardrailUsage`
- `compensationSummary`
- `cleanupSummary`
- `resumeCapsuleRef`
- `retentionAck`
- `sourceVersion`

### 16.3 Schema 字段摘要

#### Attempt / Takeover

- `attemptEpoch`
- `fencingToken`
- `executionLeaseId`
- `takeoverLeaseId`
- `writerRole`
- `legacySemantics`

#### Journal

- `intentState`
- `dispatchState`
- `journalCommitState`
- `recoveryState`
- `appendWatermarkAtWrite`
- `durableWatermarkAtDecision`

#### Effect

- `effectType`
- `compensatesEffectId`
- `originEffectId`
- `compensationAttemptNo`
- `compensationIdempotencyKey`
- `dedupeCapability`
- `confirmationChannel`
- `semanticIntentId`

#### Sanitization

- `sanitizationPolicyVersion`
- `sanitizationRunId`
- `redactionRuleSetVersion`
- `classifierModelVersion`
- `residualSanitizerVersion`
- `sanitizationDecisionHash`
- `sanitizationIncidentId`

#### Capsule

- `capsuleMergeConflicts[]`
- `maxHeadTokens`
- `maxValidationSteps`
- `headTruncationPolicy`
- `staleFieldSet[]`
- `recoveryLaneRecommendation`

---

## 17. 迁移计划与 Failure Injection

### 17.1 迁移分期

从 V2.5 迁移到 V2.6 建议至少四步：

1. **双写观测期**
   - 保留旧 projection
   - 新增 Journal watermark、attempt epoch、effectType 扩展字段
   - 只做比对，不做裁决

2. **阴影裁决期**
   - Finalizer 同时跑旧恢复逻辑与 V2.6 恢复逻辑
   - 以旧逻辑执行，以新逻辑出差异报告

3. **V2.6 主裁决期**
   - 新 Journal / takeover fencing / effect model 成为主裁决源
   - 旧逻辑降为 fallback

4. **旧逻辑清退期**
   - 停止旧双写
   - 封存兼容读取层
   - 历史 run 标注 `legacySemantics=true`

### 17.2 最小 Failure Injection 测试矩阵

至少覆盖：

1. Worker 在 `dispatch_visible` 后、`journal_committed` 前崩溃  
2. Finalizer 接管时 Graph 落后于 Journal  
3. 旧 worker 迟到写入被 fencing 拒绝  
4. `external_unprobeable_non_idempotent` 进入 unknown 后不会盲重试  
5. 具备 `intent_token` 的黑盒副作用可做受控去重重试  
6. Sanitizer 漏检后触发 re-sanitize 与 purge  
7. Autopsy 因预算耗尽降级为 `template_autopsy`  
8. Resume 时 code drift 为 `amber`  
9. Resume 时 external state drift 为 `red`  
10. 合法 BatchIntent 不被误杀  
11. cleanup reserve 耗尽后仍正确输出 `cleanup_incomplete`  
12. `micro_recovery` 不会绕过高风险 unknown effect gate  

### 17.3 验收输出

每个用例都应产出：

- 事件时间线
- Journal 片段
- 期望状态转移
- 期望 UI composite
- 期望 callback
- 期望保留对象

---

## 18. Phase 0 文档清单（V2.6）

在 V2.5 基础上，建议至少补齐以下文档：

1. `journal-authority-boundary-and-watermark.md`
2. `takeover-fencing-and-writer-ownership.md`
3. `hierarchical-state-model-run-attempt-child.md`
4. `compensation-as-first-class-effect.md`
5. `restricted-evidence-access-and-re-sanitization.md`
6. `resume-lanes-and-recon-grading.md`
7. `minimal-dark-factory-deployment-profile.md`
8. `migration-and-failure-injection-plan.md`

---

## 19. V2.6 的 Definition of Done

达到以下条件，可认为 V2.6 最小闭环成立：

1. Journal 已被正式定义为**唯一权威提交真相源**，并带有 watermark。  
2. Finalizer / Reaper / Worker 的接管仲裁已具备 epoch + fencing。  
3. Run / Attempt / Child / Control Service 四层状态模型与聚合规则已落实。  
4. compensation 已被正式纳入一级 effect model。  
5. sanitization 主路径已改为结构化隔离 + 确定性脱敏，残差 LLM sanitizer 默认关闭。  
6. Capsule V5 已具备 merge precedence、stale field rule、validation budget。  
7. Resume 已区分 `same_attempt_retry / micro_recovery / full_rehearsal` 三条车道。  
8. `external_unprobeable_non_idempotent` 已具备 callback-only / intent-token / manual-only 的明确恢复策略。  
9. 控制角色可以采用 Minimal Dark Factory 部署形态，但仍满足权限与审计合同。  
10. Migration Plan 与 Failure Injection 已可重复执行。  

---

## 20. 最终决策与实施优先级

### 20.1 最终决策

继续坚持方案 B，并把 V2.6 解释为：

- **Paperclip** 拥有 run 身份、治理投影、访问审批与 operator surface。  
- **Dark Factory** 拥有执行真相、资源真相、受限证据真相与收场真相。  
- **Bridge** 只拥有最小操作性状态，不拥有业务控制权，不拥有 committed 真相定义权。  

### 20.2 实施优先级

V2.6 的优先级顺序应为：

1. **Journal authority boundary + watermark**
2. **takeover fencing + writer ownership**
3. **effect model 升级为 primary / compensation / probe**
4. **sanitization-by-construction + restricted evidence access**
5. **resume lanes + recon grading**
6. **Capsule V5 merge / stale / validation budget**
7. **Minimal Dark Factory deployment profile**
8. **migration + failure injection**
9. **更复杂的 full memory snapshot、深度 drill-down UI（后放）**

---

## 21. 收尾判断

V2.6 的目标，不是把系统继续抽象化，而是把 V2.5 已经非常成熟的判断，压成一组实现团队、前端团队、控制服务团队、平台团队都能按同一口径执行的合同。

它做了三个关键取舍：

1. **坚持单一 committed source，但承认物理不确定尾部存在**  
2. **坚持强治理边界，但拒绝把所有控制角色都做成昂贵微服务**  
3. **坚持安全与恢复，但拒绝让脱敏、反证、排演演变成吞吐和运维黑洞**

> **一句话收尾**：V2.6 不是再加一层防御，而是把“谁说了算、谁能接管、什么必须记录、什么只能最小披露、什么时候该轻恢复、什么时候必须重排演”写成可执行合同。