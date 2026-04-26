# Paperclip × Dark Factory 修订版框架 V2.3

**版本**：2.3  
**日期**：2026-04-21  
**定位**：在 V2.2 基础上，吸收 Gemini、GLM5.1 评审与综合结论后形成的可开工增强版。  
**适用范围**：若与 V2.2 冲突，以本稿为准。

---

## 0. V2.3 相对 V2.2 的一句话变化

V2.3 继续坚持方案 B，但把 V2.2 再向真实运行时推进半步：  
**在“单主状态机 + 软/硬中断 + watchdog + effect ledger + Resume Capsule”的骨架上，新增“外置 finalizer / reaper、树状配额与速率整形、反复犯错记忆层、伪推进识别、前端 displayStatus 合成规则”。**

> **一句话版本**：V2.3 的目标不是让系统更抽象，而是让它在“被强杀、并发竞争、恢复重试、界面展示”这些最容易翻车的地方也能站住。

---

## 1. 结论先行

V2.3 继续坚持方案 B，不推翻原有三层分工：

- **Paperclip**：控制面，负责协作、预算、审批、人工介入、治理展示。
- **Dark Factory**：执行面，负责 runtime、sandbox、verification、artifact、cleanup、补偿与执行证据。
- **Bridge**：集成面，只允许持有最小操作性状态，不演化成新的业务控制面。

V2.3 在 V2.2 基础上，明确补齐四个最关键闭环：

1. **Hard Kill 后由外部 Orchestrator Finalizer / Reaper 接管补偿与清理**，不再假设被杀死的 worker 还能自己“善后”。
2. **预算从“刚性阶段切片”升级为“弹性运行池 + 硬保留清理池 + 树状子配额 + RPM/TPM 限流”**，避免多子 agent 互相饿死或一起撞 429。
3. **Resume Capsule 升级为 Capsule V2**，加入失败记忆、拒绝路径与“给下一个我的交接说明”，降低跨 attempt 重复犯错概率。
4. **Watchdog 从“看是否推进”升级为“看是否有效推进”**，并补上前端 `displayStatus` 合成规则，避免运行中既黑盒又错觉。

---

## 2. V2.3 继承什么、修正什么

### 2.1 继续继承的部分

以下判断继续成立：

- 方案 B 不变，Paperclip 管治理，Dark Factory 管执行。
- run-centric 方向不变，`ExternalRun / RunAttempt / ArtifactRef / TraceRef / ResourceLease` 仍成立。
- Bridge 允许最小状态化，但仅限去重、验签、顺序控制、对账和投递补偿。
- `handoff_required`、`awaiting_input`、`awaiting_approval` 必须分开建模。
- Run 继续只保留**一个主状态机**；中断、租约、恢复、清理都降级为标签与属性。
- 继续承认**不可中断原子区**存在，不把“实时打断 LLM 推理”当成基本假设。
- 继续坚持：**副作用治理优先于完美状态水合**。
- 继续先做 **Resume Capsule**，而非把 full memory snapshot 当作 P0/P1 阻塞项。

### 2.2 相对 V2.2 的收敛性修正

V2.2 已经把系统从“理论完备”拉回到“能开工”。  
V2.3 不是重写，而是把下列边界条件从自然语言补成工程契约：

- 补上 **Hard Kill 的外部接管协议**；
- 补上 **Effect Ledger 的未知态、部分补偿与人工接管语义**；
- 补上 **多子 agent 并发下的预算包络、配额隔离与流量整形**；
- 补上 **Watchdog 的伪推进识别**；
- 补上 **Resume Capsule 的蒸馏与失败记忆层**；
- 补上 **前端 displayStatus 的单值合成规则**。

---

## 3. 核心架构边界（V2.3）

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
  - `lastMilestone`
  - `lastHeartbeatAt`
  - `guardrailUsage`
  - `cleanupState`
  - `compensationState`
  - `quotaState`
  - `stuckReason`
- 能显示 **“cancelling / stuck / compensating / manual_intervention_required”** 这类合成展示态。
- 能渲染结构化 handoff / resume 表单。
- 能发起极窄白名单的升级审批。
- 能查看 `nextAttemptBrief`、`knownFailures` 摘要与风险说明。

明确不做：

- 不保存 artifact / trace 原始数据本体。
- 不直接管理 sandbox / worktree / container 生命周期。
- 不保存原始私有 CoT 或完整模型内存镜像。
- 不承担补偿执行器角色。

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
- Bridge 不做 quota scheduler，不做 provider rate limiter。

### 3.3 Dark Factory（Execution Plane）

继续负责：

- task spec / acceptance spec
- runtime / orchestration / verification
- sandbox / worktree / container / cleanup
- artifact / evidence / execution summary
- retry / downgrade / self-heal 策略
- effect ledger、compensation、lease、resume capsule 的底层落地

新增要求：

- 必须区分**有副作用工具**与**无副作用工具**。
- 任何外部可写操作都必须带 effect ledger 记录与补偿声明。
- 任何长运行资源都必须受 watchdog + lease 控制。
- sub-agent 必须纳入级联中断树。
- quota scheduler、provider rate limiter、finalizer / reaper 必须属于 Dark Factory 的控制服务域，而不是挂在 agent 进程内部。

### 3.4 Dark Factory Control Services（新增明确化，而非新增分层）

V2.3 明确将以下能力视作 **Dark Factory 内部的控制服务**：

1. **Orchestrator**
2. **Watchdog**
3. **Quota Scheduler**
4. **Provider Rate Limiter**
5. **Finalizer / Reaper**

目的不是再增加一层，而是明确：  
**这些能力不能依赖正在执行任务的 agent/worker 本身。**

---

## 4. 状态模型：一个主状态 + 标签 + 调试相位 + displayStatus

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
- `recoveryTag = none | auto_retrying | downgraded_mode`
- `cleanupTag = none | cleanup_running | cleanup_pending | compensation_running | compensation_partial | compensation_failed | manual_required`
- `quotaTag = healthy | throttled | limited | exhausted`
- `retentionTag = standard | audit_hold | legal_hold`

### 4.4 调试辅助字段

可保留非权威调试字段：

- `phase = spec | worktree | model_inference | tool_exec | verify | compensate | cleanup | probe_effect`
- `reasonCode`
- `lastMilestone`
- `lastHeartbeatAt`
- `progressCursor`
- `stuckReason`
- `attemptNo`
- `parentAttemptId`

### 4.5 displayStatus（新增：给前端看的单一展示态）

后端内部可以保留标签组合，但对前端必须额外输出一个**单值展示态**：

- `validating`
- `planning`
- `executing`
- `verifying`
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

### 4.6 displayStatus 合成优先级（新增）

建议按以下优先级合成，前一条命中即停止：

1. 主状态为 `completed / failed / cancelled` → 同名展示态
2. `cleanupTag=manual_required` 或 `compensationStatus=manual_required` → `manual_intervention_required`
3. `phase=compensate` 或 `cleanupTag=compensation_running` → `compensating`
4. `phase=cleanup` 或 `cleanupTag=cleanup_running` → `cleaning_up`
5. `interruptTag in {soft_cancel_requested, hard_cancel_requested}` → `cancelling`
6. `leaseTag=grace` 且 `stuckReason != null` → `stuck`
7. 主状态为 `waiting_approval` → `awaiting_approval`
8. 主状态为 `waiting_input` → `awaiting_input`
9. `recoveryTag=auto_retrying` → `retrying`
10. 主状态为 `executing` 且 `phase=verify` → `verifying`
11. 其他按主状态映射

---

## 5. 中断模型：承认不可中断区，且把 Hard Kill 的善后外置

### 5.1 中断分类

V2.3 继续定义三类治理动作：

1. `soft_cancel`：在安全点消费，优雅停止。
2. `hard_cancel`：超过宽限时间后强制终止执行单元。
3. `override_or_resume`：冻结当前 attempt，生成 Capsule V2，以新上下文启动新 attempt。

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

### 5.3 硬中断语义（修正）

硬中断不等于“worker 被杀了就结束”。  
V2.3 明确以下时序：

1. 标记当前 attempt 为 `hard_cancel_requested`。
2. 触发 worker / pod / container 强制终止。
3. 将 **当前 attempt 的清理与补偿责任** 交给外部 `Finalizer / Reaper`。
4. `Finalizer / Reaper` 根据落盘的 effect ledger、resource lease、artifact session 和 probe 规则接管善后。
5. run 进入 `finalizing`。
6. 最后收束为 `cancelled` 或 `failed`。

### 5.4 外部接管协议（新增）

Hard Kill 后的清理不允许依赖被杀的 agent 实体。  
必须由外部控制服务执行：

- **Finalizer**：负责读取 effect ledger、发起补偿、执行 cleanup、产出 summary。
- **Reaper**：负责回收孤儿资源、强杀未响应子进程、释放 lease。
- **Effect Prober**：当 effect 状态未知时，探测外部系统真实状态，再决定是否补偿。

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

## 6. Lease 与 Watchdog：不是只看活着，而是看是否在有效推进

### 6.1 原则

Lease 的目的不是“只要有心跳就一直活着”，而是：  
**只有证明自己仍在有效推进，才可以继续占资源。**

### 6.2 续租权从 agent 收回

V2.3 继续坚持：

- agent 进程**不能单独凭心跳为自己续租**；
- Bridge 也**不能仅凭 keepalive 替下游续租**；
- 续租必须由独立 watchdog 判断。

### 6.3 有效推进证据（升级）

仅有 `progressCursor` 增加还不够。  
Watchdog 至少应组合以下证据中的一种或多种：

- `lastMilestone` 更新
- 工作树产生新的有效 diff
- 新的 verification 证据产生
- `openTodos` 数量或优先级发生正向变化
- `knownFailures` / `rejectedApproaches` 有新增，表示搜索空间被收缩
- `childTopologySnapshot` 发生推进型变化（子任务完成、失败被吸收、结果汇总）
- 长推理宽限窗口仍有效

### 6.4 伪推进识别（新增）

Watchdog 必须识别以下“看似活跃、实则空转”的模式：

- 连续 N 次调用同一工具，参数高度相似，且未产生新 artifact / 新 diff
- 连续 N 个循环出现同一 `failureSignature`
- 连续 N 次 verify 失败且错误簇未变化
- 工作树 diff 长时间无变化，但工具调用在增加
- 子 agent 被反复拉起在同一分支或同一 hypothesis 上打转

满足阈值时：

1. 标记 `stuckReason`
2. 将 `leaseTag` 置为 `grace`
3. 触发 `soft_cancel` 或 `downgraded_mode`
4. 必要时发起人工介入或自动 handoff

### 6.5 推荐字段

- `ttlSec`
- `renewBeforeSec`
- `stuckThresholdSec`
- `softCancelGraceSec`
- `hardKillAfterSec`
- `pseudoProgressWindow`
- `maxRepeatedFailureSignature`
- `maxNoDiffToolCycles`

### 6.6 进度与心跳的职责分离

- `keepalive` 只证明“进程还活着”，**不等于**“任务在推进”。
- `milestone`、`effectiveProgressScore` 才用于证明“有实质性进展”。
- Paperclip 面板只显示最近活跃时间、最近里程碑和卡住原因，不接收全部心跳明细。

---

## 7. 外部副作用治理：Effect Ledger V2 与“补偿有限性原则”

### 7.1 为什么这是 P0/P1

V2.3 继续明确：  
**外部副作用失控的成本，远高于恢复不完美。**

因此，effect ledger、补偿契约、外部接管协议，仍然排在 full memory snapshot 前面。

### 7.2 Effect Ledger V2（升级）

任何外部可写动作都必须生成 effect 记录：

- `effectId`
- `runId`
- `attemptNo`
- `toolName`
- `effectType`
- `effectClass = reversible | compensatable | irreversible`
- `targetRef`
- `createdAt`
- `issuedAt`
- `ackAt`
- `effectCommitState = proposed | issued | acked | unknown`
- `compensationActionRef`
- `compensationStatus = not_needed | pending | running | completed | partial | probe_required | manual_required | waived`
- `operatorNote`

### 7.3 工具权限分级

建议将工具分成三类：

1. **read-only**：无 effect ledger。
2. **write-compensatable**：必须有 effect ledger 和 rollback / cleanup 声明。
3. **write-irreversible**：默认禁止；如需开放，必须提前审批并显式标记为不可自动回滚。

### 7.4 补偿有限性原则（新增）

V2.3 明确承认：

- 补偿不一定成功；
- 补偿可能只成功一部分；
- 硬中断时 effect 的真实状态可能未知；
- 某些副作用只能探测、不能可靠撤销；
- 系统允许存在**需要人工擦屁股的脏状态**。

因此：

- 不允许无限重试补偿；
- `compensation_failed` 不再被视作一个足够清晰的终点；
- 应显式升级为 `partial`、`probe_required` 或 `manual_required`；
- 当进入 `manual_required` 时，必须产出 incident 摘要与下一步建议。

### 7.5 终止时序（修正）

当 run 因 `failed / cancelled / lease_expired` 进入收尾时，时序如下：

1. 停止继续创建新副作用。
2. 进入 `finalizing`。
3. 由 Finalizer 对 effect ledger 做 probe / compensation。
4. 再做 container / worktree / sandbox cleanup。
5. 写出 `compensationSummary`、`cleanupSummary`、`residualRiskSummary`。
6. 收束主状态。

### 7.6 未知态 effect（新增）

当 worker 被 Hard Kill，且某个 effect 处于“请求已发出但未确认”的窗口时：

- 不得假设 effect 一定未生效；
- `effectCommitState` 必须转入 `unknown`；
- `Effect Prober` 应先探测外部系统现状；
- 探测失败时，`compensationStatus=probe_required`；
- 超过策略阈值后升级为 `manual_required`。

---

## 8. 预算与配额：从“刚性三切”升级为“弹性运行池 + 硬保留清理池 + 树状配额”

### 8.1 V2.3 的预算判断

V2.2 的核心洞见是对的：  
**清理预算必须硬保留，不能被执行阶段吃光。**

但 V2.3 进一步调整为：

- 运行中的执行与验证可以共享一个**弹性运行池**；
- 清理预算必须保留为**硬底线**；
- 对前端和策略仍可保留 execution / verification 的“提示预算”或“软水位线”，但不再要求完全刚性切割。

### 8.2 推荐预算字段

建议 `budgetPolicy` 升级为：

- `runBudgetUsd`
- `cleanupReserveUsd`
- `executionHintUsd`
- `verificationHintUsd`
- `runWallClockSec`
- `cleanupReserveWallClockSec`
- `warningWatermarks = {execution: 0.6, verification: 0.8}`

解释：

- `runBudgetUsd - cleanupReserveUsd` 构成运行池；
- execution / verification 在运行池内共享，但超出 hint 时可报警、降级或限制；
- `cleanupReserveUsd` 与 `cleanupReserveWallClockSec` 不可侵占。

### 8.3 树状配额（新增）

多智能体并发下，必须建立自顶向下的 quota envelope：

- 父 run 持有总预算与总 wall clock 包络
- 每个 child attempt 必须分配：
  - `childSpendCapUsd`
  - `childWallClockCapSec`
  - `childToolCallCap`
  - `childProviderRateClass`
- 支持 `maxConcurrentChildren`
- 支持 `maxChildrenPerBranch`

### 8.4 Provider RPM/TPM 限流（新增）

除金钱预算外，还必须有供应商速率整形：

- 按 provider / model 建 `token bucket`
- 至少支持：
  - `rpmLimit`
  - `tpmLimit`
  - `burst`
  - `cooldownAfter429Sec`
- Quota Scheduler 负责多子 agent 之间的公平分享
- repeated 429 应触发：
  - backoff
  - 降低并发
  - 降级模型
  - 必要时阻断某个 runaway child

### 8.5 公平性与反饿死规则

建议：

- 正常 child 使用 weighted fair share
- 单个 child 连续超配、重复失败或长期无有效推进时，进入 `quotaTag=limited`
- 不允许单个 child 烧光父 run 的整个运行池
- cleanup reserve 不可被 child 消耗

### 8.6 预算耗尽策略（修正）

当运行池耗尽时：

1. 停止产生新 patch / 新子任务 / 新副作用；
2. 若仍有运行池中剩余的 verification 窗口，可做最小必要验证；
3. 使用 `cleanupReserve` 完成 compensation + cleanup；
4. 输出 `budgetExhausted`、`residualRiskSummary` 与建议动作；
5. 收束到 `failed` 或 `cancelled`，而不是继续偷偷运行。

---

## 9. 恢复模型：Resume Capsule V2，重点不是“记住一切”，而是“别再犯同样的错”

### 9.1 V2.3 的判断

V2.3 继续不把 full memory snapshot 当成 P0/P1。  
但它明确承认：  
**对 LLM 来说，“之前试过什么且为什么失败”往往比“当前工作树长什么样”更关键。**

因此，Resume Capsule 必须从“状态转存”升级成“失败记忆 + 交接蒸馏”。

### 9.2 Capsule V2 的生成时机

以下场景必须生成 Capsule V2：

- handoff
- awaiting_input / awaiting_approval
- override_or_resume
- 长等待审批的 freeze
- 租约到期前的安全挂起
- 伪推进被 watchdog 判定后的强制换手
- 硬中断后的可恢复残留态（若能安全生成）

### 9.3 Capsule V2 的结构（新增 Head / Body / Tail）

#### Head（高优先级 prompt 注入区）
必须小而硬，供下一个 attempt 最优先消费：

- `nextAttemptBrief`：**给下一个我的交接说明**
- `currentGoal`
- `mustNotRepeat`
- `topKnownFailures`
- `highestPriorityTodo`
- `stopConditions`

#### Body（结构化恢复区）
保留执行上下文：

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
- `artifactRefs`
- `traceRefs`
- `remainingBudgetSnapshot`

#### Tail（证据与引用区）
仅存引用，不把所有细节塞进 prompt：

- `verificationRefs`
- `logRefs`
- `incidentRefs`
- `expiresAt`

### 9.4 新增字段（回应“失忆死循环”）

V2.3 明确新增：

- `rejectedApproaches[]`
- `failureSignatures[]`
- `doNotRepeatUntil`
- `nextAttemptBrief`
- `remainingRisks`
- `operatorHints`

### 9.5 蒸馏要求（新增）

生成 Capsule V2 时，不允许只是堆结构化字段。  
必须强制产出一段短小、明确、可执行的交接说明，模板建议：

1. 我已经尝试过什么；
2. 为什么失败；
3. 哪些路暂时不要再走；
4. 现在最应该先做什么；
5. 如果再次失败，应优先检查什么。

### 9.6 明确不包含什么

Capsule V2 仍不要求：

- 持久化原始私有 CoT
- 完整复制模型内部 KV cache
- 强绑定某个模型供应商的私有会话机制

### 9.7 Full Memory Snapshot 的位置

仍可作为后续增强项，但不是 V2.3 的 T0 阻塞项。

---

## 10. 动态提权：继续保留，但只能 Freeze + Resume

### 10.1 原则

V2.3 继续不完全砍掉 `requestEscalation`，但明确它不能成为“运行时任意扩权”的通道。

### 10.2 第一版允许的升级类型

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

### 10.3 处理方式

所有升级请求都必须走：

1. 冻结当前 attempt；
2. 生成 Capsule V2；
3. 进入 `waiting_input` 或 `waiting_approval`；
4. 审批通过后以新 capsule 启动新 attempt。

不允许“阻塞式等待 + 原地持有昂贵上下文 + 一边续租一边等人”。

---

## 11. 观测链路与前端展示：Lifecycle 走 Bridge，细粒度 Telemetry 走 Observability

### 11.1 原则

Bridge 只处理影响生命周期的核心事件，不能变成高频 telemetry 管道。

### 11.2 Bridge 处理的事件

建议仅保留：

- `run_state_changed`
- `display_status_changed`
- `interrupt_acknowledged`
- `guardrail_exhausted`
- `quota_limited`
- `compensation_started / completed / partial / manual_required`
- `cleanup_started / completed / manual_required`
- `resume_capsule_available`
- `lease_expired`
- `last_milestone_changed`
- `stuck_detected`

### 11.3 Observability 专线处理的内容

细粒度 telemetry 建议直接从 Dark Factory 发往 OTLP / PubSub / 日志平台，例如：

- 每 30 秒细粒度进度
- token / model call 统计
- sub-agent span
- step 级耗时
- 详细 verification 流水
- repeated failure signature 聚类
- provider 429 / backoff 详情

### 11.4 Paperclip 面板展示原则

Paperclip 只需要看见：

- 主状态
- `displayStatus`
- 最近里程碑
- 最近活跃时间
- 当前是否卡住
- 卡住原因
- guardrail 消耗比例
- quota 状态
- cleanup / compensation 是否完成
- 是否需要人工介入

不需要承载高频 step-by-step 流水。

---

## 12. Trace 与 Artifact 的保留策略：继续强绑定，不允许“只给一个会过期的 URL”

### 12.1 问题定义

TraceRef / ArtifactRef 如果只存链接、不存保留约束，数月后很容易 404。  
V2.3 继续把“引用”升级为“引用 + 保留契约”。

### 12.2 RetentionPolicy

建议保留：

- `retentionClass = standard_30d | audit_1y | legal_hold`
- `retainUntil`
- `allowEarlyPurge = false | true`
- `legalHold = true | false`

### 12.3 约束关系

- Paperclip 声明的是**最低保留要求**。
- Dark Factory 可以保留更久，但不能比要求更短。
- Bridge 必须把 retention policy 下发并拿到 ack。
- 若 audit / legal hold run 的 TraceRef 失效，应视为契约缺陷，而不是正常过期。

### 12.4 Artifact 访问

- Paperclip 存 ref，不存永久裸 URL。
- 实际访问通过短效签名 URL 或代理鉴权发放。
- URL 过期可刷新，但 ref 与 retention policy 必须长期有效。

---

## 13. 合同增量（V2.3）

### 13.1 `POST /api/external-runs` 建议字段（更新）

```json
{
  "externalRunId": "pc_run_789",
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
    "defaultChildSpendCapUsd": 2,
    "defaultChildWallClockCapSec": 300,
    "providerRateClasses": {
      "primary-llm": {
        "rpmLimit": 60,
        "tpmLimit": 120000,
        "burst": 10,
        "cooldownAfter429Sec": 30
      }
    }
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
    "maxNoDiffToolCycles": 5
  },
  "effectPolicy": {
    "recordSideEffects": true,
    "requireCompensationForWritableTools": true,
    "allowIrreversibleEffects": false,
    "unknownEffectMustProbe": true
  },
  "resumePolicy": {
    "emitResumeCapsule": true,
    "capsuleVersion": "v2",
    "requireNextAttemptBrief": true,
    "fullMemorySnapshotRequired": false
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

### 13.2 回调建议新增字段

- `runStatus`
- `displayStatus`
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
- `resumeCapsuleRef`
- `retentionAck`

### 13.3 Effect Ledger 记录建议新增字段

- `effectCommitState`
- `probeSummary`
- `compensationStatus`
- `manualInterventionTicketRef`
- `operatorNote`

---

## 14. V2.3 的路线图

### Phase 0：先把“边界条件合同”定死

必须产出：

1. `bridge-contract.md`
2. `state-machine.md`
3. `interrupt-and-kill-policy.md`
4. `lease-watchdog-policy.md`
5. `effect-ledger-and-compensation-v2.md`
6. `quota-and-rate-shaping.md`
7. `resume-capsule-v2.md`
8. `display-status-policy.md`
9. `retention-policy.md`

必须决定：

- 唯一主 Run 状态集合
- `displayStatus` 合成规则
- Hard Kill 的外部接管协议
- watchdog 的有效推进与伪推进判定
- effect class 与补偿有限性原则
- 树状配额和 provider 限流策略
- Capsule V2 字段集与蒸馏模板
- retention policy handshake

### Phase 1：零副作用模式先跑通

目标：

- 打通 `validate-only / print-plan`
- 面板展示主状态 + `displayStatus`
- 关键里程碑可见
- 高频 telemetry 不进入 Bridge 主库

成功标准：

- Paperclip 能可靠看到 validating / planning 生命周期
- 乱序或重复事件不会打乱主状态
- 前端不会因为标签组合而出现状态错觉

### Phase 2：真实执行，但先把副作用治理和配额治理做好

目标：

- 接通 `real run`
- 接入 Effect Ledger V2
- 接入 Finalizer / Reaper
- 接入树状配额与 provider 限流
- cleanup reserve 生效

成功标准：

- 取消或失败后，副作用可补偿、可探测或显式升级为人工介入
- 单个 runaway child 不会饿死其他 child
- repeated 429 不会拖垮整个 run

### Phase 3：接通中断、冻结与恢复

目标：

- soft / hard cancel
- cascading interrupt
- Capsule V2
- 冻结后新 attempt 恢复

成功标准：

- 父任务取消后没有孤儿子 agent
- 长推理阶段可展示 `cancelling` 而非假死
- handoff 后能携带 `nextAttemptBrief` 与失败记忆启动新 attempt

### Phase 4：上线有效推进识别与运行时换手

目标：

- watchdog 伪推进识别
- repeated failure signature 聚类
- stuck → soft_cancel / handoff / downgraded_mode

成功标准：

- 空转不会靠心跳长期续租
- 同一错误不会跨 attempt 无脑重复
- stuck 场景可被前端看见且可操作

### Phase 5：有限动态提权与保留治理

目标：

- 上线窄白名单 requestEscalation
- 上线 retention policy handshake
- 审计保留可验证

成功标准：

- 审批等待时不会原地热阻塞会话
- audit hold 的 TraceRef / ArtifactRef 不会失效

### Phase 6：后续增强

后放内容：

- full memory snapshot
- 更复杂的 sub-agent 可视化
- 深度 execution drill-down UI
- 更复杂的跨 executor 抽象

---

## 15. V2.3 的 Definition of Done

达到以下条件，可认为 V2.3 最小闭环成立：

1. Run 在系统中只有一个主状态可见。
2. 前端始终能得到一个确定的 `displayStatus`。
3. Cancel 能穿透父/子执行单元，不留下孤儿 lease。
4. Hard Kill 后由外部 Finalizer / Reaper 接管补偿与清理。
5. 所有外部可写副作用均有 Effect Ledger V2 记录。
6. effect 允许进入 `unknown / probe_required / manual_required`，而不是伪装成“已回滚”。
7. 运行池与 cleanup reserve 已分离，且 reserve 不可侵占。
8. 多子 agent 有树状配额与 provider 速率整形。
9. Watchdog 能识别伪推进，而不是只认心跳。
10. handoff / freeze / stuck 换手会生成 Capsule V2。
11. Capsule V2 含 `nextAttemptBrief`、`rejectedApproaches`、`failureSignatures`。
12. 高频 telemetry 不经过 Bridge 主库。
13. TraceRef / ArtifactRef 已与 retention policy 强绑定。

---

## 16. 最终决策与优先级

### 16.1 最终决策

继续坚持方案 B，但对实现方式做以下最终解释：

- **Paperclip** 拥有 run 身份与治理投影。
- **Dark Factory** 拥有执行真相、资源真相、补偿真相与配额真相。
- **Bridge** 只拥有最小操作性状态，不拥有业务控制权。
- **Finalizer / Reaper / Quota Scheduler / Watchdog** 属于 Dark Factory 的控制服务，不属于 agent 自身。

### 16.2 实施优先级（更新）

V2.3 的优先级顺序应为：

1. **Effect Ledger V2 + Finalizer / Reaper + 补偿有限性契约**
2. **硬保留 cleanup reserve + 树状配额 + provider 限流**
3. **soft / hard interrupt + cascading interrupt**
4. **watchdog 的有效推进 / 伪推进判定**
5. **Resume Capsule V2（含失败记忆与交接说明）**
6. **displayStatus 合成规则**
7. **窄白名单 requestEscalation**
8. **full memory snapshot（后放）**

---

## 17. 收尾判断

V2.2 已经证明方向是对的。  
V2.3 做的不是推倒重来，而是把“挂了以后谁收尸、并发时谁限流、恢复后怎么别再犯同样的错、前端怎么别把人看糊涂”这些真实生产问题写进合同。

> **一句话收尾**：V2.3 的目标，不是让系统看起来更聪明，而是让它在最容易出事故的地方也足够诚实、可控、能善后。
