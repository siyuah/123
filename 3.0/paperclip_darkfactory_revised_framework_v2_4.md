# Paperclip × Dark Factory 修订版框架 V2.4

**版本**：2.4  
**日期**：2026-04-21  
**定位**：在 V2.3 基础上，吸收 Gemini 与 GLM5.1 第二轮评审、并结合此前 V2.2/V2.3 的综合结论后形成的运行时增强版。  
**适用范围**：若与 V2.3 冲突，以本稿为准。

---

## 0. V2.4 相对 V2.3 的一句话变化

V2.4 继续坚持方案 B，但把 V2.3 再向真实多智能体生产运行时推进半步：  
**在“单主状态机 + 外置 Finalizer / Reaper + 树状配额 + Capsule V2”的骨架上，进一步补齐“Critic / Autopsy 旁路评估、Resume 前 Rebase & Recon、Effect DAG + WAL、BatchIntent、预分配配额租约、治理意图通道”。**

> **一句话版本**：V2.4 的重点不是再加抽象层，而是把“失败者不可靠、世界线会漂移、强杀会留下半截状态、调度器自己会变瓶颈”这些更接近物理现实的问题写成明确合同。

---

## 1. 结论先行

V2.4 继续坚持方案 B，不推翻原有三层边界：

- **Paperclip**：控制面，负责协作、预算、审批、人工介入、治理展示。
- **Dark Factory**：执行面，负责 runtime、sandbox、verification、artifact、cleanup、补偿与执行证据。
- **Bridge**：集成面，只允许持有最小操作性状态，不演化成新的业务控制面。

V2.4 在 V2.3 基础上，明确再补六个闭环：

1. **不再默认信任失败 Worker 的自我总结**。Resume Capsule 的 Head 允许由 `self / critic / autopsy` 三种来源生成；遇到 Hard Kill、重复失败、未知副作用等高风险场景，必须走独立旁路评估。
2. **任何 Resume 都先经过 `Rebase & Recon`**。下一个 attempt 不应直接接管旧世界线，而应先校验代码基线、外部依赖与关键假设是否漂移。
3. **Effect Ledger 升级为“Ledger + Dependency Graph”**。补偿不再只是倒序遍历 list，而是要理解 effect 之间的依赖拓扑与补偿冻结规则。
4. **执行热路径必须有 WAL**。对外部执行与副作用发起，必须先写入结构化 Write-Ahead Log，再允许真实 dispatch，避免 Hard Kill 后出现“已执行未落账”的黑洞。
5. **多子 agent 的配额调度不能走纯中心化热路径**。必须采用“本地预分配租约 + 异步上报 + 必要时中心重分配”的混合模型，并支持关键路径预算借调。
6. **前端继续保留单值 `displayStatus`，但不能丢掉治理意图**。必须额外输出 `governanceIntent` 与 `blockedBy`，防止“manual_required 覆盖 cancel 意图”之类的信息丢失。

---

## 2. V2.4 继承什么、修正什么

### 2.1 继续继承的部分

以下判断继续成立：

- 方案 B 不变，Paperclip 管治理，Dark Factory 管执行。
- run-centric 方向不变，`ExternalRun / RunAttempt / ArtifactRef / TraceRef / ResourceLease` 仍成立。
- Bridge 允许最小状态化，但仅限去重、验签、顺序控制、对账和投递补偿。
- Run 继续只保留**一个主状态机**；中断、租约、恢复、清理都降级为标签与属性。
- 继续承认**不可中断原子区**存在，不把“实时打断长推理”当成基本假设。
- 继续坚持：**副作用治理优先于完美状态水合**。
- 继续允许 `Freeze + Resume`，但不允许“原地阻塞热会话等审批”。
- 继续把 **cleanup reserve** 视为硬底线，不可被执行阶段侵占。

### 2.2 相对 V2.3 的修正

V2.3 已经补上了强杀后的接管、配额与速率整形、Capsule 失败记忆、伪推进识别与 `displayStatus` 合成。  
V2.4 进一步把下列问题从“有原则”推进到“有 owner、有时序、有 fallback”：

- 谁来写交接说明，以及什么时候不能信任原 Worker；
- Resume 之后如何先对齐当前世界线，而不是直接按旧胶囊继续跑；
- 补偿如何处理 effect 依赖与中途失败；
- Hard Kill 后如何发现“已发出但未落盘”的执行黑洞；
- 调度器如何避免自己成为高并发瓶颈；
- UI 如何同时表达“当前状态”和“治理意图”。

---

## 3. 核心架构边界（V2.4）

### 3.1 Paperclip（Control Plane）

继续负责：

- Company / Project / Goal / Task
- Approval / Budget / Comment / Operator Intervention
- `ExternalRun` 身份、治理投影与人工接管入口
- 高优先级治理动作：Cancel / Override / Resume
- 保留策略、审计要求、法律保留（如适用）的上层声明

新增要求：

- 仍只展示**一个主 Run 状态**，但必须同时接收：
  - `displayStatus`
  - `governanceIntent`
  - `blockedBy`
  - `lastMilestone`
  - `lastHeartbeatAt`
  - `guardrailUsage`
  - `cleanupState`
  - `compensationState`
  - `quotaState`
  - `stuckReason`
  - `residualRiskSummary`
- 能显示“任务当前在什么状态”和“用户/系统正在试图对它做什么”是两条不同信息。
- 能查看 Capsule 的 `nextAttemptBrief`、`capsuleAuthor`、`confidenceScore` 与 `reconDiffSummary` 摘要。

明确不做：

- 不保存 artifact / trace / WAL 原始数据本体。
- 不直接管理 sandbox / worktree / container 生命周期。
- 不保存原始私有 CoT 或完整模型内存镜像。
- 不承担补偿执行器、调度器或 Critic 的职责。

### 3.2 Bridge（Integration Plane）

继续负责：

- 输入映射
- 输出映射
- 回调验签
- 幂等去重
- 顺序处理
- 对账补偿
- 保留策略与 contract ack 的透传

允许保存的**操作性状态**：

- `idempotencyKey`
- `eventId`
- `lastAcceptedSequenceNo`
- `lastLifecycleEventAt`
- `lastMilestoneAt`
- `deliveryRetryState`
- `reconcileCursor`
- `retentionAckState`

明确限制：

- Bridge 不保存完整细粒度 progress 流。
- Bridge 不保存完整 trace 流。
- Bridge 不做 model routing，不做 verification 策略，不做预算裁决，不做审批判断。
- Bridge 不做 quota scheduler，不做 provider rate limiter，不做 Critic 推理。

### 3.3 Dark Factory（Execution Plane）

继续负责：

- task spec / acceptance spec
- runtime / orchestration / verification
- sandbox / worktree / container / cleanup
- artifact / evidence / execution summary
- retry / downgrade / self-heal 策略
- effect ledger、compensation、lease、resume capsule 的底层落地

新增要求：

- 任何外部可写操作都必须进入 **Effect Ledger + Effect Dependency Graph**。
- 任何真实 dispatch 前都必须先落 **Execution WAL**。
- sub-agent 必须纳入级联中断树与配额树。
- quota scheduler、provider rate limiter、finalizer / reaper、critic / autopsy、recon service 必须属于 Dark Factory 的控制服务域，而不是挂在 agent 进程内部。

### 3.4 Dark Factory Control Services（明确化）

V2.4 明确以下能力属于 **Dark Factory 内部控制服务**：

1. **Orchestrator**
2. **Watchdog**
3. **Quota Scheduler**
4. **Provider Rate Limiter**
5. **Finalizer / Reaper**
6. **Critic / Autopsy Service**
7. **Recon Service**
8. **Execution WAL Writer / Reconciler**

目的不是再增加一层，而是明确：  
**这些能力不能依赖正在执行任务的 agent/worker 本身。**

---

## 4. 状态模型：一个主状态 + 标签 + 调试相位 + 治理意图

### 4.1 TaskStatus（协作层）

Task 继续只表达协作语义：

- `queued`
- `in_progress`
- `blocked`
- `awaiting_input`
- `awaiting_approval`
- `done`
- `cancelled`

### 4.2 Run 主状态（唯一权威状态）

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

说明：

- `finalizing` 覆盖 verification、compensation、cleanup 等收尾阶段。
- `completed / failed / cancelled` 是唯一终态。
- 终态一旦确认，不再被标签反向覆盖。

### 4.3 Run 标签（非主状态）

建议保留：

- `interruptTag = none | soft_cancel_requested | hard_cancel_requested | override_requested | resume_requested`
- `leaseTag = active | grace | expired | retire_pending`
- `recoveryTag = none | auto_retrying | downgraded_mode | recon_pending`
- `cleanupTag = none | cleanup_running | cleanup_pending | compensation_running | compensation_partial | compensation_failed | manual_required`
- `quotaTag = healthy | throttled | limited | exhausted | waiting_rebalance`
- `retentionTag = standard | audit_hold | legal_hold`

### 4.4 调试辅助字段

可保留非权威调试字段：

- `phase = spec | worktree | model_inference | tool_exec | batch_exec | verify | compensate | cleanup | probe_effect | resume_recon`
- `reasonCode`
- `lastMilestone`
- `lastHeartbeatAt`
- `progressCursor`
- `stuckReason`
- `attemptNo`
- `parentAttemptId`

### 4.5 `displayStatus`（给前端看的单值展示态）

后端内部可以保留标签组合，但对前端必须额外输出一个**单值展示态**：

- `validating`
- `planning`
- `executing`
- `verifying`
- `reconciling`
- `awaiting_input`
- `awaiting_approval`
- `retrying`
- `cancelling`
- `compensating`
- `cleaning_up`
- `stuck`
- `manual_intervention_required`
- `completed`
- `failed`
- `cancelled`

### 4.6 `governanceIntent` 与 `blockedBy`（新增）

V2.4 明确：  
**`displayStatus` 不负责表达全部治理意图。**

必须额外输出：

- `governanceIntent = none | cancel_requested | override_requested | resume_requested | operator_review_requested`
- `blockedBy = none | manual_step | approval | dependency | quota_limit | provider_limit | unknown_effect | recon_conflict`

示例：

- 主展示态：`manual_intervention_required`
- 治理意图：`cancel_requested`
- 阻塞原因：`manual_step`

这表示“任务当前被人工步骤卡住，同时取消流程尚未完成”。

### 4.7 `displayStatus` 合成优先级

建议按以下优先级合成，前一条命中即停止：

1. 主状态为 `completed / failed / cancelled` → 同名展示态
2. `cleanupTag=manual_required` 或 `compensationStatus=manual_required` → `manual_intervention_required`
3. `phase=compensate` 或 `cleanupTag=compensation_running` → `compensating`
4. `phase=cleanup` 或 `cleanupTag=cleanup_running` → `cleaning_up`
5. `phase=resume_recon` → `reconciling`
6. `interruptTag in {soft_cancel_requested, hard_cancel_requested}` → `cancelling`
7. `leaseTag=grace` 且 `stuckReason != null` → `stuck`
8. 主状态为 `waiting_approval` → `awaiting_approval`
9. 主状态为 `waiting_input` → `awaiting_input`
10. `recoveryTag=auto_retrying` → `retrying`
11. 主状态为 `executing` 且 `phase=verify` → `verifying`
12. 其他按主状态映射

---

## 5. 中断模型：承认不可中断区，但把善后与尸检全部外置

### 5.1 中断分类

V2.4 继续定义三类治理动作：

1. `soft_cancel`：在安全点消费，优雅停止。
2. `hard_cancel`：超过宽限时间后强制终止执行单元。
3. `override_or_resume`：冻结当前 attempt，生成 Capsule，以新上下文启动新 attempt。

### 5.2 不可中断区

必须显式承认以下场景可能不可实时中断：

- 单次长模型推理调用
- 已经发出的外部工具调用
- 原子性 artifact 上传
- 已进入不可中断数据库事务的工具适配层

处理规则：

- 控制面发来 `soft_cancel` 时，Dark Factory 先记录 `interruptTag=soft_cancel_requested`，前端显示 `cancelling`。
- 不可中断区结束后，必须在下一个安全点立即消费中断。
- 超过 `softCancelGraceSec` 仍未安全退出，则升级为 `hard_cancel`。

### 5.3 硬中断语义

硬中断不等于“worker 被杀了就结束”。  
V2.4 明确以下时序：

1. 标记当前 attempt 为 `hard_cancel_requested`；
2. 触发 worker / pod / container 强制终止；
3. 将清理、补偿与 postmortem 责任交给外部控制服务；
4. `Finalizer / Reaper` 根据 Effect Ledger、WAL、resource lease 和 probe 规则接管善后；
5. 若需要恢复线索，由 `Autopsy Service` 生成旁路 Capsule Head 或 incident 摘要；
6. run 进入 `finalizing`；
7. 最后收束为 `cancelled` 或 `failed`。

### 5.4 外部接管协议

Hard Kill 后的清理与尸检不允许依赖被杀的 agent 实体。  
必须由外部控制服务执行：

- **Finalizer**：负责读取 ledger、发起补偿、执行 cleanup、产出 summary。
- **Reaper**：负责回收孤儿资源、强杀未响应子进程、释放 lease。
- **Effect Prober**：当 effect 状态未知时，探测外部系统真实状态，再决定是否补偿。
- **Autopsy Service**：当 Worker 无法可靠生成交接说明时，基于 WAL、trace、error log 与 effect ledger 输出旁路“验尸摘要”。

### 5.5 级联中断树（Cascading Interrupt）

任何主 agent 派生的子 agent、子 attempt、长驻 verification worker 都必须挂在同一棵中断树上：

- `parentAttemptId`
- `childAttemptIds[]`
- `propagationDeadlineSec`
- `orphanReapDeadlineSec`

要求：

- 父 attempt 收到 cancel / hard_cancel 后，必须向所有子执行单元广播。
- 子执行单元未按时确认时，由 Reaper 兜底强杀。
- 不允许出现“父任务已取消，子 agent 继续烧钱”的孤儿运行。

---

## 6. Watchdog：不仅识别伪推进，还要识别合法批处理

### 6.1 原则

Lease 的目的不是“只要有心跳就一直活着”，而是：  
**只有证明自己仍在有效推进，才可以继续占资源。**

### 6.2 有效推进证据

Watchdog 至少应组合以下证据中的一种或多种：

- `lastMilestone` 更新
- 工作树产生新的有效 diff
- 新的 verification 证据产生
- `openTodos` 数量或优先级发生正向变化
- `knownFailures` / `rejectedApproaches` 有新增，表示搜索空间被收缩
- `childTopologySnapshot` 发生推进型变化
- 长推理宽限窗口仍有效

### 6.3 伪推进识别

Watchdog 必须识别以下“看似活跃、实则空转”的模式：

- 连续 N 次调用同一工具，参数高度相似，且未产生新 artifact / 新 diff
- 连续 N 个循环出现同一 `failureSignature`
- 连续 N 次 verify 失败且错误簇未变化
- 工作树 diff 长时间无变化，但工具调用在增加
- 子 agent 被反复拉起在同一 branch 或 hypothesis 上打转

满足阈值时：

1. 标记 `stuckReason`
2. 将 `leaseTag` 置为 `grace`
3. 触发 `soft_cancel`、`downgraded_mode` 或自动 handoff
4. 必要时发起人工介入

### 6.4 `BatchIntent`（新增）

V2.4 明确：  
**合法的批量作业不能因为“看起来很重复”而被误杀。**

因此，当 agent 预期要执行相似的循环操作时，必须先向 Orchestrator 声明：

- `batchId`
- `declaredAction`
- `expectedIterations`
- `checkpointEvery`
- `successMetric`
- `expirySec`

规则：

- 有效 `BatchIntent` 存在时，Watchdog 不以“参数相似”本身判定伪推进；
- 但必须改为检查“批处理检查点是否推进”；
- 若超过声明范围、长时间没有 checkpoint、或 successMetric 不再改善，则仍触发伪推进制裁；
- `BatchIntent` 只允许豁免“形态相似”，不允许豁免预算、时长与副作用安全边界。

### 6.5 推荐字段

- `ttlSec`
- `renewBeforeSec`
- `stuckThresholdSec`
- `softCancelGraceSec`
- `hardKillAfterSec`
- `pseudoProgressWindow`
- `maxRepeatedFailureSignature`
- `maxNoDiffToolCycles`
- `batchIntentRequiredForLoopExemption`

---

## 7. 外部副作用治理：从 Effect Ledger 升级到 Effect Graph

### 7.1 为什么这仍然是 P0

V2.4 继续明确：  
**恢复失真会影响效率；副作用失控会直接造成真实资损、脏环境与错误外部写入。**

因此，Effect Graph、补偿契约、WAL 与外部接管协议，仍然排在 full memory snapshot 前面。

### 7.2 Effect 记录必须包含依赖关系

任何外部可写动作都必须生成 effect 记录，至少包含：

- `effectId`
- `runId`
- `attemptNo`
- `toolName`
- `effectType`
- `effectClass = reversible | compensatable | irreversible`
- `targetRef`
- `dependsOnEffectIds[]`
- `compensationBarrierPolicy = continue_if_safe | block_downstream | manual_gate`
- `createdAt`
- `issuedAt`
- `ackAt`
- `effectCommitState = proposed | issued | acked | unknown`
- `compensationActionRef`
- `compensationStatus = not_needed | pending | running | completed | partial | blocked_by_dependency | probe_required | manual_required | waived`
- `operatorNote`

### 7.3 补偿拓扑规则（新增）

补偿不再只是对 effect list 做简单倒序，而必须遵守：

1. 先根据 `dependsOnEffectIds[]` 构建 Effect DAG；
2. 默认按**逆拓扑序**尝试补偿；
3. 若某上游节点补偿失败：
   - 若下游 `compensationBarrierPolicy=block_downstream`，则下游转入 `blocked_by_dependency`；
   - 若 `continue_if_safe`，则允许继续补偿，但必须记录风险；
   - 若 `manual_gate`，则直接升级为 `manual_required`；
4. Finalizer 必须在 summary 中写明“哪些 effect 已补偿、哪些因为依赖冻结、哪些需要人工处理”。

### 7.4 补偿有限性原则

V2.4 继续承认：

- 补偿不一定成功；
- 补偿可能只成功一部分；
- Hard Kill 时 effect 的真实状态可能未知；
- 某些副作用只能探测、不能可靠撤销；
- 系统允许存在**需要人工擦屁股的脏状态**。

因此：

- 不允许无限重试补偿；
- `compensation_failed` 不再是足够清晰的终点；
- 应显式升级为 `partial`、`blocked_by_dependency`、`probe_required` 或 `manual_required`；
- 当进入 `manual_required` 时，必须产出 incident 摘要与下一步建议。

### 7.5 未知态 effect

当 worker 被 Hard Kill，且某个 effect 处于“请求已发出但未确认”的窗口时：

- 不得假设 effect 一定未生效；
- `effectCommitState` 必须转入 `unknown`；
- `Effect Prober` 应先探测外部系统现状；
- 探测失败时，`compensationStatus=probe_required`；
- 超过策略阈值后升级为 `manual_required`。

---

## 8. Execution WAL：防止“已执行未落账”的半截子黑洞

### 8.1 原则

V2.4 明确：  
**对外部执行与副作用发起，必须先写 WAL，再允许真实 dispatch。**

这不是为了保存原始思维，而是为了在 Hard Kill、进程崩溃或网络闪断后，让 Finalizer 能知道：

- 模型到底准备做什么；
- 哪个工具请求是否已真正发出；
- 哪个副作用已进入不可逆窗口；
- 哪一步属于“已执行未记账”的危险尾部。

### 8.2 WAL 记录什么，不记录什么

WAL 必须记录**执行级结构化事件**，例如：

- `walSeq`
- `attemptId`
- `recordType = tool_intent | tool_dispatch | tool_ack | effect_proposed | effect_dispatch | effect_ack | artifact_upload_start | artifact_upload_done | batch_checkpoint`
- `timestamp`
- `idempotencyKey`
- `payloadRef`
- `effectRef`

WAL **不要求**记录：

- 原始私有 CoT
- 完整模型 KV cache
- 不可控的逐 token 内部推理

### 8.3 Dispatch 规则

对任何可能产生外部效果的动作，执行时序必须是：

1. 生成结构化执行意图；
2. 先将意图 durable append 到 WAL；
3. 赋予幂等键并下发给 executor / tool adapter；
4. 收到 ack / result 后，再写回 WAL 与 Effect Ledger；
5. 若中途进程被杀，由 Finalizer 通过 WAL tail 与外部 probe 做 reconcile。

### 8.4 WAL 与 Finalizer 的关系

Finalizer 接管时，必须同时读取：

- Effect Ledger
- WAL 尾部
- Resource Lease
- Artifact Session
- Tool Adapter 幂等日志（如有）

只看 ledger 不足以解释“半截子状态”；WAL 是补齐这段物理现实的最小底座。

---

## 9. 配额与限流：从树状配额升级为“租约 + 重分配”模型

### 9.1 V2.4 的预算判断

V2.4 继续坚持：

- **运行池可以弹性共享**；
- **cleanup reserve 必须硬保留**；
- **子 agent 不能直接共享一个无限热池**；
- **调度器不应位于每一次请求的强依赖热路径上**。

### 9.2 推荐预算字段

建议 `budgetPolicy` 保留并扩展为：

- `runBudgetUsd`
- `cleanupReserveUsd`
- `executionHintUsd`
- `verificationHintUsd`
- `runWallClockSec`
- `cleanupReserveWallClockSec`
- `warningWatermarks = {execution: 0.6, verification: 0.8}`

### 9.3 配额租约（Quota Lease，新增）

每个 child attempt 不应对每次请求都去中央调度器要额度，而应先得到一段**本地可消费租约**：

- `quotaLeaseId`
- `childSpendCapUsd`
- `childWallClockCapSec`
- `localRpmLease`
- `localTpmLease`
- `leaseRefreshThreshold`
- `leaseExpiresAt`

规则：

- 大部分热路径请求在本地租约内完成；
- child 异步上报实际消耗；
- 只有本地租约将耗尽、被降级、或需要重分配时，才访问中央调度器；
- 这样 99% 的正常请求不需要每次都走跨进程 / 跨网络仲裁。

### 9.4 动态重分配（新增）

V2.4 明确：  
**静态 child cap 会在强依赖链路里制造资源死锁。**

因此，Quota Scheduler 需要支持：

- `waiting_dependency` 子任务让出部分运行池；
- 关键路径 child 获得 `criticalPathBoost`；
- 同一父 run 下允许 sibling 之间做预算借调；
- 但 cleanup reserve 永远不可被借出。

必要规则：

- 只允许在同一父 run 的运行池内部重分配；
- 不允许突破父级硬上限；
- 不允许把高风险 runaway child 无限制续命；
- 每次重分配都必须写入调度事件，便于审计与复盘。

### 9.5 Provider RPM/TPM 限流

除金钱预算外，还必须有供应商速率整形：

- 按 provider / model 建本地 token bucket
- 中央 Scheduler 维护全局 envelope
- repeated 429 应触发：
  - backoff
  - 降低并发
  - 降级模型
  - 必要时阻断某个 runaway child

### 9.6 预算耗尽策略

当运行池耗尽时：

1. 停止产生新 patch / 新子任务 / 新副作用；
2. 若仍有运行池中的最小 verification 窗口，可做必要验证；
3. 使用 `cleanupReserve` 完成 compensation + cleanup；
4. 输出 `budgetExhausted`、`residualRiskSummary` 与建议动作；
5. 收束到 `failed` 或 `cancelled`，而不是继续偷偷运行。

---

## 10. 恢复模型：Capsule V3，重点不是“记住一切”，而是“别再被上一个自己带偏”

### 10.1 V2.4 的判断

V2.4 继续不把 full memory snapshot 当成 P0/P1。  
但它进一步明确：

- 失败 Worker 的自我总结不总是可靠；
- 失败记忆不能无限追加；
- 下一个 attempt 应该优先消费“高价值、低毒性、与当前世界线仍相关”的恢复信息。

因此，Resume Capsule 升级为 **Capsule V3**。

### 10.2 Capsule V3 的作者来源（新增）

Capsule V3 的 Head 可以有三种来源：

- `capsuleAuthor = self`：正常 freeze / handoff 场景，由当前 Worker 生成；
- `capsuleAuthor = critic`：命中重复失败、明显幻觉、未知副作用、或 operator 要求复核时，由独立 Critic 生成或覆盖 Head；
- `capsuleAuthor = autopsy`：Hard Kill、worker crash、超时回收等场景，由外部 Autopsy Service 基于 WAL、trace、error log 生成。

### 10.3 Critic / Autopsy 触发条件

建议至少在以下场景触发旁路作者：

- `hard_kill`
- `worker_crash`
- `maxRepeatedFailureSignature` 命中
- `unknown_effect` 或 `probe_required` 未闭环
- `residualRiskSummary` 非空且影响下一个 attempt 决策
- 操作员显式请求“重新评估上一轮失败”

### 10.4 Capsule V3 的结构

#### Head（最高优先级注入区）

Head 必须小而硬，建议强制预算上限；至少包含：

- `nextAttemptBrief`
- `currentGoal`
- `mustNotRepeat`
- `topKnownFailures`
- `highestPriorityTodo`
- `stopConditions`
- `capsuleAuthor`
- `confidenceScore`

#### Body（结构化恢复区）

- `capsuleId`
- `runId`
- `attemptNo`
- `worktreeRef`
- `patchSetRef`
- `openTodos`
- `decisionCheckpoint`
- `recentToolLedgerTail`
- `activeHypotheses`
- `knownFailures`
- `rejectedApproaches`
- `failureSignatures`
- `pendingInputs`
- `childTopologySnapshot`
- `lastSafePoint`
- `remainingBudgetSnapshot`
- `environmentSnapshot`
- `assumptionSet`
- `failureMemoryStoreRef`

#### Tail（证据与引用区）

- `verificationRefs`
- `logRefs`
- `incidentRefs`
- `walRefs`
- `expiresAt`

### 10.5 失败记忆的蒸馏与淘汰

Capsule V3 明确禁止“失败记忆 append-only 膨胀”。

至少要有以下约束：

- `mustNotRepeat` 只保留最高优先级的少量项目；
- 重复出现的 `failureSignatures` 必须聚类折叠；
- `rejectedApproaches` 必须合并同类项，而不是逐轮无界增长；
- `recentToolLedgerTail` 只保留最近、最相关的一小段；
- 详细失败历史放入 `failureMemoryStoreRef`，按需检索，而不是全部塞入 prompt。

实现原则：

- P0 阶段先做**有界蒸馏 + artifact 引用**；
- P2 阶段可扩展到更复杂的 retrieval / RAG，但不是 V2.4 阻塞项。

---

## 11. Resume 前必须先做 `Rebase & Recon`

### 11.1 原则

V2.4 明确：  
**任何 Capsule 恢复，都不能直接按旧交接说明继续执行。**  
新的 attempt 必须先确认自己仍然处于同一条世界线上。

### 11.2 进入点

以下场景启动新 attempt 时，必须先进入 `phase=resume_recon`：

- awaiting_approval / awaiting_input 之后恢复
- 长时间 freeze 之后恢复
- override_or_resume
- handoff
- watchdog 触发的强制换手
- Autopsy 后的恢复

### 11.3 `Rebase & Recon` 最小流程

1. 获取 capsule 记录时的 `baseCommit` / `worktreeRef` / `environmentSnapshot`；
2. 读取当前分支、主干、依赖版本与关键外部系统指纹；
3. 比较差异，生成 `reconDiffSummary`；
4. 对 patchSet 做 dry-run rebase / merge 检查；
5. 重新验证 `assumptionSet` 中的关键假设；
6. 若有必要，执行轻量只读探测或最小 smoke test；
7. 仅当 recon 通过后，才正式消费 `nextAttemptBrief` 并进入执行。

### 11.4 冲突处理

若 `Rebase & Recon` 发现：

- 主干已发生冲突性变更；
- 第三方 API 行为改变；
- 关键 schema / contract 漂移；
- 原先假设已明显失效；

则必须：

- 将 `blockedBy` 置为 `recon_conflict`，或
- 回退到 `planning` / `manual_intervention_required`，或
- 生成新的 Critic Head，明确推翻旧 `nextAttemptBrief` 中已过期的建议。

### 11.5 重要说明

`Rebase & Recon` 不是可选优化，而是 Resume 链路的第一隐含阶段。  
**先对齐世界线，再执行交接建议。**

---

## 12. 动态提权：继续保留，但只能 Freeze + Resume

### 12.1 原则

V2.4 继续不完全砍掉 `requestEscalation`，但明确它不能成为“运行时任意扩权”的通道。

### 12.2 第一版允许的升级类型

只建议支持以下窄场景：

1. 补充人工输入
2. 预设 ceiling 内的有限预算上调
3. 临时只读能力
4. 启动前已声明、运行中激活的预审批写能力

不建议第一版支持：

- 任意新增高风险写权限
- 任意新增公网 / 内网高权限网络访问
- 任意新增 secrets scope
- 无限等待审批后原地继续热会话

### 12.3 处理方式

所有升级请求都必须走：

1. 冻结当前 attempt；
2. 生成 Capsule V3；
3. 进入 `waiting_input` 或 `waiting_approval`；
4. 审批通过后先做 `Rebase & Recon`；
5. 再以新 capsule 启动新 attempt。

---

## 13. 观测链路、回调与保留策略

### 13.1 Bridge 处理的生命周期事件

建议仅保留：

- `run_state_changed`
- `display_status_changed`
- `governance_intent_changed`
- `blocked_by_changed`
- `interrupt_acknowledged`
- `guardrail_exhausted`
- `quota_rebalanced`
- `compensation_started / completed / partial / manual_required`
- `cleanup_started / completed / manual_required`
- `resume_capsule_available`
- `recon_completed`
- `lease_expired`
- `stuck_detected`
- `wal_gap_detected`

### 13.2 Observability 专线处理的内容

细粒度 telemetry 建议直接从 Dark Factory 发往 OTLP / PubSub / 日志平台，例如：

- 每 30 秒细粒度进度
- token / model call 统计
- sub-agent span
- step 级耗时
- repeated failure signature 聚类
- provider 429 / backoff 详情
- BatchIntent checkpoint
- WAL append / reconcile 指标

### 13.3 RetentionPolicy

V2.4 继续要求：

- `TraceRef` / `ArtifactRef` 不能只是会过期的 URL；
- 保留要求由 Paperclip 向下声明，Dark Factory 返回 ack；
- 审计 run 下，WAL / incident / capsule ref 的保留等级必须与 trace 一致，不能先于审计对象过期。

---

## 14. 合同增量（V2.4）

### 14.1 `POST /api/external-runs` 建议字段（更新）

```json
{
  "externalRunId": "pc_run_901",
  "requestedMode": "execute",
  "contextBoundary": {
    "toolAllowlist": ["git", "npm", "playwright"],
    "networkAccessLevel": "repo-default",
    "secretMountPolicy": "repo-default",
    "capabilityDelegationPolicy": "subagents-must-downgrade"
  },
  "budgetPolicy": {
    "runBudgetUsd": 16,
    "cleanupReserveUsd": 4,
    "executionHintUsd": 8,
    "verificationHintUsd": 4,
    "runWallClockSec": 1800,
    "cleanupReserveWallClockSec": 300,
    "warningWatermarks": {
      "execution": 0.6,
      "verification": 0.8
    }
  },
  "quotaPolicy": {
    "maxConcurrentChildren": 4,
    "maxChildrenPerBranch": 2,
    "allowSiblingBudgetReallocation": true,
    "criticalPathBoost": true,
    "defaultQuotaLease": {
      "childSpendCapUsd": 0.5,
      "childWallClockCapSec": 120,
      "localRpmLease": 20,
      "localTpmLease": 40000,
      "leaseRefreshThreshold": 0.2
    },
    "asyncUsageReportSec": 10
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
    "watchdogRequired": true,
    "pseudoProgressWindow": 6,
    "maxRepeatedFailureSignature": 3,
    "maxNoDiffToolCycles": 5,
    "batchIntentRequiredForLoopExemption": true
  },
  "effectPolicy": {
    "recordSideEffects": true,
    "trackEffectDependencies": true,
    "requireCompensationForWritableTools": true,
    "requireExecutionWal": true,
    "unknownEffectMustProbe": true,
    "allowIrreversibleEffects": false
  },
  "resumePolicy": {
    "emitResumeCapsule": true,
    "capsuleVersion": "v3",
    "requireRebaseRecon": true,
    "capsuleAuthoring": {
      "default": "self",
      "criticTriggers": ["repeated_failure", "unknown_effect", "operator_requested"],
      "autopsyTriggers": ["hard_kill", "worker_crash"]
    },
    "failureMemoryMode": "bounded_plus_retrievable",
    "fullMemorySnapshotRequired": false
  },
  "uiPolicy": {
    "emitDisplayStatus": true,
    "emitGovernanceIntent": true,
    "emitBlockedBy": true
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

### 14.2 回调建议新增字段

- `runStatus`
- `displayStatus`
- `governanceIntent`
- `blockedBy`
- `phase`
- `reasonCode`
- `tags[]`
- `lastMilestone`
- `lastHeartbeatAt`
- `guardrailUsage`
- `quotaState`
- `stuckReason`
- `compensationSummary`
- `cleanupSummary`
- `residualRiskSummary`
- `reconDiffSummary`
- `resumeCapsuleRef`
- `retentionAck`

### 14.3 Effect / WAL 记录建议新增字段

- `dependsOnEffectIds[]`
- `compensationBarrierPolicy`
- `effectCommitState`
- `probeSummary`
- `manualInterventionTicketRef`
- `walSeq`
- `recordType`
- `idempotencyKey`
- `payloadRef`

---

## 15. V2.4 的路线图

### Phase 0：先把新增边界合同定死

必须产出：

1. `bridge-contract.md`
2. `state-machine.md`
3. `interrupt-and-kill-policy.md`
4. `lease-watchdog-and-batch-intent.md`
5. `effect-graph-and-compensation.md`
6. `execution-wal-and-reconciliation.md`
7. `quota-leases-and-rebalancing.md`
8. `resume-capsule-v3.md`
9. `rebase-and-recon.md`
10. `display-status-and-governance-intent.md`
11. `retention-policy.md`

必须决定：

- 唯一主 Run 状态集合
- `displayStatus`、`governanceIntent`、`blockedBy` 的前端合同
- Hard Kill 的外部接管与 Autopsy 协议
- Watchdog 的有效推进、伪推进与 BatchIntent 规则
- Effect DAG 与补偿冻结规则
- WAL 的最小记录模型与回放策略
- 配额租约、异步上报与 sibling 重分配规则
- Capsule V3 字段集、作者来源与蒸馏边界
- `Rebase & Recon` 的最小校验流程
- retention policy handshake

### Phase 1：零副作用模式先跑通

目标：

- 打通 `validate-only / print-plan`
- 面板展示主状态 + `displayStatus` + `governanceIntent`
- 关键里程碑可见
- 高频 telemetry 不进入 Bridge 主库

成功标准：

- Paperclip 能可靠看到 validating / planning 生命周期
- 乱序或重复事件不会打乱主状态
- UI 不会因为标签组合而出现状态错觉

### Phase 2：真实执行，但先把副作用真相与热路径真相补齐

目标：

- 接通 `real run`
- 接入 Effect Graph
- 接入 Execution WAL
- 接入 Finalizer / Reaper / Autopsy
- 接入 quota lease 与 provider 限流

成功标准：

- 取消或失败后，副作用可补偿、可探测或显式升级为人工介入
- Hard Kill 后不存在“已执行未落账但系统完全不知情”的黑洞
- 单个 runaway child 不会饿死其他 child

### Phase 3：接通中断、冻结与恢复

目标：

- soft / hard cancel
- cascading interrupt
- Capsule V3
- `Rebase & Recon`
- 冻结后新 attempt 恢复

成功标准：

- 父任务取消后没有孤儿子 agent
- 长推理阶段可展示 `cancelling` 而非假死
- handoff 后能携带可信的 `nextAttemptBrief` 与失败记忆启动新 attempt
- Resume 不会直接站在过期世界线上继续干活

### Phase 4：上线有效推进识别与合法批处理豁免

目标：

- watchdog 伪推进识别
- BatchIntent
- repeated failure signature 聚类
- stuck → soft_cancel / handoff / downgraded_mode

成功标准：

- 空转不会靠心跳长期续租
- 合法批量迁移不会被形态相似性误杀
- 同一错误不会跨 attempt 无脑重复

### Phase 5：有限动态提权与保留治理

目标：

- 上线窄白名单 requestEscalation
- 上线 retention policy handshake
- 审计保留可验证

成功标准：

- 审批等待时不会原地热阻塞会话
- audit hold 的 TraceRef / ArtifactRef / WALRef 不会失效

### Phase 6：后续增强

后放内容：

- full memory snapshot
- 更复杂的 retrieval / RAG failure memory store
- 更复杂的 sub-agent 可视化
- 深度 execution drill-down UI
- 更复杂的跨 executor 抽象

---

## 16. V2.4 的 Definition of Done

达到以下条件，可认为 V2.4 最小闭环成立：

1. Run 在系统中只有一个主状态可见。
2. 前端始终能得到确定的 `displayStatus`，同时保留 `governanceIntent` 与 `blockedBy`。
3. Cancel 能穿透父/子执行单元，不留下孤儿 lease。
4. Hard Kill 后由外部 Finalizer / Reaper / Autopsy 接管补偿、清理与 postmortem。
5. 所有外部可写副作用均有 Effect Graph 记录。
6. Effect 支持 `unknown / blocked_by_dependency / probe_required / manual_required`，而不是伪装成“已回滚”。
7. 所有高风险 dispatch 前都有 WAL durable append。
8. 运行池与 cleanup reserve 已分离，且 reserve 不可侵占。
9. 多子 agent 有 quota lease、provider 速率整形与 sibling 重分配。
10. Watchdog 能识别伪推进，并支持 BatchIntent 豁免合法批处理。
11. handoff / freeze / crash 后会生成 Capsule V3，且标注 `capsuleAuthor`。
12. Capsule V3 具备失败记忆蒸馏，不发生无界膨胀。
13. Resume 一定经过 `Rebase & Recon`。
14. 高频 telemetry 不经过 Bridge 主库。
15. TraceRef / ArtifactRef / WALRef 已与 retention policy 强绑定。

---

## 17. 最终决策与优先级

### 17.1 最终决策

继续坚持方案 B，但对实现方式做以下最终解释：

- **Paperclip** 拥有 run 身份与治理投影。
- **Dark Factory** 拥有执行真相、资源真相、补偿真相、配额真相与 postmortem 真相。
- **Bridge** 只拥有最小操作性状态，不拥有业务控制权。
- **Finalizer / Reaper / Quota Scheduler / Watchdog / Critic / Autopsy / Recon Service** 属于 Dark Factory 控制服务，不属于 agent 自身。

### 17.2 实施优先级（更新）

V2.4 的优先级顺序应为：

1. **Effect Graph + Execution WAL + Finalizer / Reaper / Autopsy**
2. **硬保留 cleanup reserve + quota lease + provider 限流 + sibling 重分配**
3. **soft / hard interrupt + cascading interrupt**
4. **Resume 前 `Rebase & Recon`**
5. **Capsule V3（含 Critic / Autopsy 旁路作者与失败记忆蒸馏）**
6. **watchdog 的有效推进 / 伪推进判定 + BatchIntent**
7. **`displayStatus` + `governanceIntent` + `blockedBy` 前端合同**
8. **窄白名单 requestEscalation**
9. **full memory snapshot / 高级 retrieval（后放）**

---

## 18. 收尾判断

V2.3 已经把系统从“看起来能跑”推进到了“多数情况下不会乱跑”。  
V2.4 继续做的，不是推倒重来，而是再把几个最危险的物理边界写进合同：

- 失败者不一定会诚实总结；
- 世界线会在等待审批时继续变化；
- 强杀会留下“已执行未落账”的尾巴；
- 调度器自己也可能成为系统瓶颈；
- 前端不能为了简洁而吞掉治理意图。

> **一句话收尾**：V2.4 的目标，不是让系统显得更聪明，而是让它在恢复、补偿、调度、展示这些最容易出事故的地方，既诚实又可控，还能收场。
