# Paperclip × Dark Factory 修订版框架 V2.2

**版本**：2.2  
**日期**：2026-04-21  
**定位**：在 V2.1 基础上，吸收 Gemini（2）与 GLM5.1（2）评审后形成的可开工版本。  
**适用范围**：若与 V2.1 冲突，以本稿为准。

---

## 1. 结论先行

V2.2 继续坚持方案 B，不推翻原有分层：

- **Paperclip** 仍是控制面，负责任务协作、预算、审批、人工介入、治理展示。
- **Dark Factory** 仍是执行面，负责 agent runtime、sandbox、verification、artifact、cleanup 与执行证据。
- **Bridge** 仍是集成面，但只允许持有最小操作性状态，不演化成新的业务控制面。

V2.2 的变化，不是再增加一层抽象，而是把 V2.1 从“逻辑完备”收敛成“工程上能落地”：

1. **Run 只保留一个主状态机**；中断、租约、进度、清理都降为标签或属性，避免状态机爆炸。
2. **中断分成软中断和硬中断**；承认存在不可中断区，并为超时后强杀与善后留出协议。
3. **Lease 续租改为 watchdog 驱动**；不能由 agent 自己靠心跳给自己续命。
4. **外部副作用必须进入 effect ledger**；取消、失败、租约到期时先补偿，再结束生命周期。
5. **预算拆分为 execution / verification / reserved cleanup**；执行不能把善后预算吃光。
6. **恢复机制先做 Resume Capsule，不直接做 full memory snapshot**；先保证可恢复，再追求无缝恢复。
7. **动态提权收窄**；第一版不支持任意运行中扩权，只允许极窄白名单并强制 freeze + resume。
8. **观测链路拆分**；Bridge 只处理生命周期与关键里程碑，细粒度 telemetry 走 OTLP / PubSub。
9. **Trace / Artifact 保留策略强绑定**；Paperclip 的保留要求必须透传到 Dark Factory，不能只留一个会过期的链接。

> **一句话版本**：继续坚持方案 B，但把框架升级为“单主状态机 + 软/硬中断 + watchdog 续租 + 补偿事务 + 保留预算 + Resume Capsule”的可开工执行系统。

---

## 2. V2.2 继承与修正什么

### 2.1 继续继承的部分

以下判断继续成立：

- 方案 B 不变，Paperclip 管治理，Dark Factory 管执行。
- run-centric 方向不变，`ExternalRun / RunAttempt / ArtifactRef / TraceRef / ResourceLease` 仍然成立。
- Bridge 允许最小状态化，但仅限去重、验签、顺序控制、对账和投递补偿。
- `handoff_required`、`awaiting_input`、`awaiting_approval` 必须分开建模。
- 不重写 Paperclip 的核心 `company / goal / task` 主模型。

### 2.2 对 V2.1 的收敛性修正

V2.1 的主要问题不是方向错，而是已经接近“理论正确但工程过重”。V2.2 做四个收敛：

- 不再让 `InterruptState / LeaseState / ProgressState / EscalationState` 成为并列主状态机。
- 不再假设任何长模型推理都能实时中断，明确“不可中断原子区”。
- 不再把 `requestEscalation` 设计成任意运行时阻塞等待，而改成极窄白名单 + 冻结恢复。
- 不再把“记忆快照”定义成第一阶段必需品，而是先落成更轻的 Resume Capsule。

---

## 3. 核心架构边界（V2.2）

### 3.1 Paperclip（Control Plane）

继续负责：

- Company / Project / Goal / Task
- Approval / Budget / Comment / Operator Intervention
- `ExternalRun` 身份、治理投影与人工接管入口
- 高优先级治理动作：Cancel / Override / Resume
- 保留策略、审计要求、法律保留（如适用）的上层声明

新增要求：

- 只展示**一个主 Run 状态**，其余通过标签、原因码、摘要呈现。
- 支持展示：`lastMilestone`、`lastHeartbeatAt`、`guardrailUsage`、`cleanupState`、`compensationState`。
- 可渲染结构化 handoff / resume 表单。
- 可发起极窄白名单的运行时升级请求审批。

明确不做：

- 不保存 artifact / trace 原始数据本体。
- 不直接管理 sandbox / worktree / container 生命周期。
- 不保存原始私有 CoT 或完整模型内存镜像。

### 3.2 Bridge（Integration Plane）

继续负责：

- 输入映射
- 输出映射
- 回调验签
- 幂等去重
- 顺序处理
- 对账补偿

允许保存的**操作性状态**：

- `idempotencyKey`
- `eventId`
- `lastAcceptedSequenceNo`
- `lastLifecycleEventAt`
- `lastMilestoneAt`
- `deliveryRetryState`
- `reconcileCursor`

明确限制：

- Bridge 不保存完整细粒度 progress 流。
- Bridge 不保存完整 trace 流。
- Bridge 不做 model routing，不做 verification 策略，不做预算裁决，不做审批判断。

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

---

## 4. V2.2 的状态模型：一个主状态 + 一组标签

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

Run 只保留一个主状态：

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

以下内容不再是独立状态机，而是标签或属性：

- `interruptTag = none | soft_cancel_requested | hard_cancel_requested | override_requested | resume_requested`
- `leaseTag = active | grace | expired | retire_pending`
- `recoveryTag = none | auto_retrying | downgraded_mode`
- `cleanupTag = none | cleanup_running | cleanup_pending | compensation_running | compensation_failed`
- `retentionTag = standard | audit_hold | legal_hold`

### 4.4 调试辅助字段

可额外保留非权威调试字段：

- `phase = spec | worktree | model_inference | tool_exec | verify | compensate | cleanup`
- `reasonCode`
- `lastMilestone`
- `lastHeartbeatAt`
- `progressCursor`

### 4.5 收束规则

- 标签永远不能单独构成终态。
- 若租约到期导致强制终止，主状态最终仍收束为 `failed` 或 `cancelled`，并通过 `reasonCode=lease_expired` 表示原因。
- 若 cleanup 失败，主状态不回滚，但 `cleanupTag=cleanup_pending` 必须保留，直到补偿完成或进入人工处理。

---

## 5. 中断模型：承认不可中断区，定义软/硬两条路径

### 5.1 中断分类

V2.2 定义三类治理动作：

1. `soft_cancel`：在安全点消费，优雅停止。
2. `hard_cancel`：超过宽限时间后强制终止执行单元。
3. `override_or_resume`：冻结当前 attempt，生成 Resume Capsule，以新上下文启动新 attempt。

### 5.2 不可中断区

必须显式承认以下场景可能不可实时中断：

- 单次长模型推理调用
- 已经发出的外部工具调用
- 原子性 artifact 上传
- 已进入不可中断数据库事务的工具适配层

处理规则：

- 控制面发来 `soft_cancel` 时，Dark Factory 先记录 `interruptTag=soft_cancel_requested`，UI 表示为“cancelling”。
- 不可中断区结束后，必须在下一个安全点立即消费中断。
- 超过 `softCancelGraceSec` 仍未安全退出，则升级为 `hard_cancel`。

### 5.3 硬中断语义

硬中断不等于“直接删记录”，而是：

1. 标记当前 attempt 为 `hard_cancel_requested`。
2. 触发 worker / pod / container 强制终止。
3. 启动 orphan reaper 与 lease reaper。
4. 进入 `finalizing`，尝试补偿和清理。
5. 最后收束为 `cancelled` 或 `failed`。

### 5.4 级联中断树（Cascading Interrupt）

任何主 agent 派生的子 agent、子 attempt、长驻 verification worker 都必须挂在同一棵中断树上：

- `parentAttemptId`
- `childAttemptIds[]`
- `propagationDeadlineSec`
- `orphanReapDeadlineSec`

要求：

- 父 attempt 收到 cancel / hard_cancel 后，必须向所有子执行单元广播。
- 子执行单元未按时确认时，由 reaper 兜底强杀。
- 不允许出现“父任务已取消，子 agent 继续烧钱”的孤儿运行。

---

## 6. Lease 与 Watchdog：谁有资格续租

### 6.1 原则

Lease 的目的不是“只要有心跳就永远活着”，而是“只有证明自己仍在推进，才可以继续占资源”。

### 6.2 续租权从 agent 收回

V2.2 明确：

- agent 进程**不能单独凭心跳为自己续租**。
- Bridge 也**不能仅凭收到 keepalive 就替下游续租**。
- 续租必须由独立 watchdog 判断，并至少依据以下一种证据：
  - `progressCursor` 推进
  - `lastMilestone` 更新
  - 明确的阶段切换
  - 策略允许的长推理宽限

### 6.3 Watchdog 判定规则

推荐字段：

- `ttlSec`
- `renewBeforeSec`
- `stuckThresholdSec`
- `softCancelGraceSec`
- `hardKillAfterSec`

推荐流程：

1. 正常推进：watchdog 允许续租。
2. 长时间无推进：进入 `leaseTag=grace`。
3. 宽限期仍无推进：发 `soft_cancel`。
4. 再超时：执行 `hard_cancel`。
5. 资源强制回收并进入清理。

### 6.4 进度与心跳的职责分离

- `keepalive` 只证明“进程还活着”，**不等于**“任务在推进”。
- `progressCursor` / `milestone` 才用于证明“有进展”。
- Paperclip 面板只显示最近活跃时间与最近里程碑，不接收全部心跳明细。

---

## 7. 外部副作用治理：Effect Ledger 与补偿事务

### 7.1 为什么这是 P0/P1 重点

V2.2 明确把“外部副作用可回滚”放在“完整状态水合”之前。原因很简单：

- 恢复失败通常影响效率；
- 外部副作用失控会直接造成真实资损、脏环境、错误 PR、外部系统污染。

因此，**补偿事务优先级高于 full memory snapshot**。

### 7.2 Effect Ledger（新增）

任何外部可写动作都必须生成 effect 记录：

- `effectId`
- `runId`
- `attemptNo`
- `toolName`
- `effectType`
- `effectClass = reversible | compensatable | irreversible`
- `targetRef`
- `createdAt`
- `compensationActionRef`
- `compensationStatus = not_needed | pending | running | completed | failed | waived`

### 7.3 工具权限分级

建议将工具分成三类：

1. **read-only**：无 effect ledger。
2. **write-compensatable**：必须有 effect ledger 和 rollback / cleanup 声明。
3. **write-irreversible**：默认禁止；如需开放，必须提前审批并显式标记为不可自动回滚。

### 7.4 终止时序

当 run 因 `failed / cancelled / lease_expired` 进入收尾时，时序如下：

1. 停止继续创建新副作用。
2. 进入 `finalizing`。
3. 对已记录 effect 执行 compensation。
4. 再做 container / worktree / sandbox cleanup。
5. 写出 `compensationSummary` 与 `cleanupSummary`。
6. 收束主状态。

### 7.5 不可逆副作用

若 effectClass 为 `irreversible`：

- 必须在 run 启动前由 `contextBoundary` 或审批策略显式允许。
- 不允许盲目 auto-retry 重复执行同一不可逆动作。
- 失败时只允许记录 waiver / incident，不伪装成“已回滚”。

---

## 8. 预算模型：执行预算、验证预算、保留清理预算

### 8.1 预算拆分

V2.2 将 budgetPolicy 拆成三段：

- `executionBudgetUsd`
- `verificationBudgetUsd`
- `reservedCleanupBudgetUsd`

必要时也可加时间预算对应拆分：

- `executionWallClockSec`
- `verificationWallClockSec`
- `reservedCleanupWallClockSec`

### 8.2 原则

- 执行阶段**不能消费** `reservedCleanupBudget`。
- 验证阶段优先消费 `verificationBudget`。
- 一旦执行预算耗尽，系统进入 `finalizing`，使用保留预算做最小验证、补偿和清理。
- 保留预算只服务于“体面地结束”，不允许被重新借给继续生成代码。

### 8.3 推荐耗尽策略

当 `executionBudget` 用尽时：

1. 停止产生新 patch / 新子任务 / 新副作用。
2. 如果还有 `verificationBudget`，可执行最小必要验证。
3. 使用 `reservedCleanupBudget` 完成 compensation + cleanup。
4. 输出 `budgetExhausted` 摘要与剩余风险说明。

---

## 9. 恢复模型：先做 Resume Capsule，不直接上 Full Memory Snapshot

### 9.1 V2.2 的判断

“状态水合”重要，但第一阶段不应该把它定义成“完整记忆镜像恢复”。V2.2 先落成更轻、更稳的 **Resume Capsule**。

### 9.2 Resume Capsule 的用途

在以下场景生成：

- handoff
- awaiting_input / awaiting_approval
- override_or_resume
- 长等待审批的 freeze
- 租约到期前的安全挂起
- 硬中断后的可恢复残留态

### 9.3 Resume Capsule 的内容

建议字段：

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
- `pendingInputs`
- `childTopologySnapshot`
- `lastSafePoint`
- `artifactRefs`
- `traceRefs`
- `expiresAt`

### 9.4 明确不包含什么

Resume Capsule 不要求：

- 持久化原始私有 CoT
- 完整复制模型内部 KV cache
- 强绑定到某一个模型供应商私有会话实现

### 9.5 Full Memory Snapshot 的位置

Full memory snapshot 可以作为 **后续增强项**，但不是 V2.2 的 P0 / P1 阻塞项。

---

## 10. 动态提权：保留，但收窄到极窄白名单

### 10.1 原则

V2.2 不完全砍掉 `requestEscalation`，但明确它不能成为“运行时任意扩权”的通道。

### 10.2 第一版允许的升级类型

只建议支持以下窄场景：

1. **补充人工输入**：例如缺业务参数、缺确认。
2. **有限预算上调**：例如在预设 ceiling 内增加少量预算。
3. **临时只读能力**：例如额外只读查询一个系统。
4. **预审批写能力激活**：仅限启动前已声明、运行中激活的少数能力。

以下情况不建议第一版支持：

- 任意新增高风险写权限
- 任意新增公网 / 内网高权限网络访问
- 任意新增 secrets scope
- 无限等待审批后原地继续热会话

### 10.3 处理方式：Freeze + Resume

所有升级请求都必须走：

1. 冻结当前 attempt。
2. 生成 Resume Capsule。
3. 进入 `waiting_input` 或 `waiting_approval`。
4. 审批通过后以新 capsule 启动新 attempt。

不允许“阻塞式等待 + 原地持有昂贵上下文 + 一边续租一边等人”。

---

## 11. 观测链路拆分：Lifecycle 走 Bridge，Telemetry 走 Observability

### 11.1 原则

Bridge 只处理影响生命周期的核心事件，不能变成高频 telemetry 管道。

### 11.2 Bridge 处理的事件

建议仅保留：

- `run_state_changed`
- `interrupt_acknowledged`
- `guardrail_exhausted`
- `compensation_started / completed / failed`
- `cleanup_started / completed / failed`
- `resume_capsule_available`
- `lease_expired`
- `last_milestone_changed`

### 11.3 Observability 专线处理的内容

细粒度 telemetry 建议直接从 Dark Factory 发往 OTLP / PubSub / 日志平台，例如：

- 每 30 秒细粒度进度
- token / model call 统计
- sub-agent span
- step 级耗时
- 详细 verification 流水

### 11.4 Paperclip 面板展示原则

Paperclip 只需要看见：

- 主状态
- 最近里程碑
- 最近活跃时间
- 当前是否卡住
- guardrail 消耗比例
- cleanup / compensation 是否完成

不需要承载高频 step-by-step 流水。

---

## 12. Trace 与 Artifact 的保留策略必须强绑定

### 12.1 问题定义

TraceRef / ArtifactRef 如果只存链接、不存保留约束，数月后很容易变成 404。V2.2 明确把“引用”升级为“引用 + 保留契约”。

### 12.2 RetentionPolicy（新增）

建议新增：

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

## 13. 合同增量（V2.2）

### 13.1 `POST /api/external-runs` 建议新增字段

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
    "allowIrreversibleEffects": false
  },
  "resumePolicy": {
    "emitResumeCapsule": true,
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
- `phase`
- `reasonCode`
- `tags[]`
- `lastMilestone`
- `lastHeartbeatAt`
- `guardrailUsage`
- `compensationSummary`
- `cleanupSummary`
- `resumeCapsuleRef`
- `retentionAck`

---

## 14. V2.2 的路线图

### Phase 0：先把文档和状态模型收敛

必须产出：

1. `bridge-contract.md`
2. `state-machine.md`
3. `interrupt-and-kill-policy.md`
4. `lease-watchdog-policy.md`
5. `effect-ledger-and-compensation.md`
6. `resume-capsule.md`
7. `retention-policy.md`

必须决定：

- 唯一主 Run 状态集合
- 软/硬中断时序
- watchdog 续租证据
- effect class 与补偿要求
- 预算拆分规则
- Resume Capsule 字段集
- retention policy handshake

### Phase 1：零副作用模式先跑通

目标：

- 打通 `validate-only / print-plan`
- 面板只展示一个主状态 + 标签
- 关键里程碑可见
- 高频 telemetry 不进入 Bridge 主库

成功标准：

- Paperclip 能可靠看到 validating / planning 生命周期
- 乱序或重复事件不会打乱主状态
- 不发生 progress 心跳风暴压垮 Bridge

### Phase 2：真实执行，但先把副作用治理做好

目标：

- 接通 `real run`
- 接入 effect ledger
- 对可写工具启用 compensation contract
- 预算拆分生效

成功标准：

- 取消或失败后，外部副作用可补偿或显式豁免
- cleanup 和 compensation 可写回摘要
- reserved cleanup budget 不被执行阶段吞噬

### Phase 3：接通中断、冻结与恢复

目标：

- soft / hard cancel
- cascading interrupt
- Resume Capsule
- 冻结后新 attempt 恢复

成功标准：

- 父任务取消后没有孤儿子 agent
- 长推理阶段可展示“cancelling”而非假死
- handoff 后能以 Resume Capsule 启动新 attempt

### Phase 4：有限动态提权与保留治理

目标：

- 上线窄白名单 requestEscalation
- 上线 retention policy handshake
- 审计保留可验证

成功标准：

- 审批等待时不会原地热阻塞会话
- audit hold 的 TraceRef / ArtifactRef 不会过期失效

### Phase 5：后续增强

后放内容：

- full memory snapshot
- 更复杂的 sub-agent 可视化
- 深度 execution drill-down UI
- 更复杂的跨 executor 抽象

---

## 15. V2.2 的 Definition of Done

达到以下条件，可认为 V2.2 最小闭环成立：

1. Run 在系统中只有一个主状态可见。
2. Cancel 能穿透父/子执行单元，不留下孤儿 lease。
3. 外部可写副作用均有 effect ledger 记录。
4. cancel / fail / lease expiry 后会先尝试 compensation，再 cleanup。
5. executionBudget、verificationBudget、reservedCleanupBudget 三段预算已生效。
6. handoff / freeze 会生成 Resume Capsule。
7. 高频 telemetry 不经过 Bridge 主库。
8. TraceRef / ArtifactRef 已与 retention policy 强绑定。

---

## 16. 最终决策与优先级

### 16.1 最终决策

继续坚持方案 B，但对实现方式做以下最终解释：

- **Paperclip** 拥有 run 身份与治理投影。
- **Dark Factory** 拥有执行真相、资源真相和补偿真相。
- **Bridge** 只拥有最小操作性状态，不拥有业务控制权。

### 16.2 实施优先级

V2.2 的优先级顺序应为：

1. **effect ledger + compensation contract**
2. **reserved cleanup budget**
3. **soft / hard interrupt + cascading interrupt**
4. **watchdog + lease**
5. **Resume Capsule**
6. **窄白名单 requestEscalation**
7. **full memory snapshot（后放）**

> **一句话收尾**：V2.2 的目标不是把系统做得更复杂，而是把 V2.1 压缩成一个真正能开工、能终止、能补偿、能恢复、能审计的执行框架。
