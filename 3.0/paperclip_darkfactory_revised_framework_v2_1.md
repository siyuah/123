# Paperclip × Dark Factory 修订版框架 V2.1

**版本**：2.1  
**日期**：2026-04-21  
**定位**：在 V2 基础上，吸收最新一轮 Gemini 与 GLM5.1 评审后形成的可开工框架。

---

## 1. 结论先行

本版本继续坚持方案 B：

- **Paperclip** 仍是公司级控制面（control plane），负责任务协作、预算、审批、人工介入与治理投影。
- **Dark Factory** 仍是工程执行面（execution plane），负责 agent runtime、sandbox、verification、artifact、cleanup 与执行证据。
- **Bridge** 仍是集成面（integration plane），但明确承认其需要最小状态化，以承载幂等、回调去重、顺序控制、对账与失败补偿。

与 V2 相比，V2.1 不再只解决“系统之间别打架”，还显式补齐“**如何安全地运行一个包含 LLM / multi-agent 的非确定性执行引擎**”。因此本版新增四条强约束：

1. **执行必须有硬止损**，自动恢复不能无限自旋。
2. **资源必须有租约**，不能依赖上游永远记得清理。
3. **权限必须可降级且可协商**，不能让子 Agent 继承主 Agent 全量权限。
4. **长运行必须可打断、可续命、可观测**，不能把自动恢复做成黑盒。

> **一句话版本**：继续坚持方案 B，但把框架从“run-centric 集成”再升级为“run-centric + interruptible + lease-based + capability-scoped + guardrailed”的可运营执行系统。

---

## 2. 本轮新增吸收点

### 2.1 从原始执行方案保留的部分

以下前提继续成立：

- Paperclip 管治理与协作，Dark Factory 管工程执行，Bridge 只做映射与投影，不直接承担 model routing、verification policy、sandbox policy 等执行决策。fileciteturn0file4
- 交付顺序仍然是：先 `validate-only / print-plan`，再 `real run`，再 `handoff / resume`，最后预算 / 审批 / 产品化增强。fileciteturn0file4
- 不重写 Paperclip 核心 company / goal / task 主模型，不把 execution detail 直接塞进 Task 主表。fileciteturn0file4

### 2.2 从上一版修订框架保留的部分

以下判断不变：

- 从 **task-centric** 升级到 **run-centric** 是必要的。
- `ExternalRun / RunAttempt / ArtifactRef / HandoffRequest` 仍是推荐的显式模型。
- Bridge 允许持有**操作性状态**，但不得拥有**治理状态**。
- `handoff_required` 不能粗暴等于 `awaiting_approval`，审批、人工输入、恢复执行要分层建模。fileciteturn0file3

### 2.3 本轮从 Gemini 吸收的内容

V2.1 新增吸收 Gemini 的四类提醒：

- 自动恢复必须有**止损与爆炸半径控制**，否则会进入 hallucination loop 或资源黑洞。fileciteturn0file0
- 计算资源必须基于 **Lease / TTL** 自毁，不应只依赖 Paperclip 或 Bridge 主动发清理指令。fileciteturn0file0
- `contextBoundary` 不能是静态扁平权限包，还需要 **capability delegation / downgrade** 以限制 sub-agent。fileciteturn0file0
- 需要保留可审计执行轨迹，但应落成 **TraceRef**，而不是把原始私有 CoT 直接定义为产品契约。fileciteturn0file0

### 2.4 本轮从 GLM5.1 吸收的内容

V2.1 新增吸收 GLM5.1 的四类落地点：

- 自动恢复与控制面指令之间存在真实竞态，因此必须有 **Cancel / Override / Resume** 的优先级与中断协议。fileciteturn0file1
- `formSchema` 还不够，Paperclip 与 Dark Factory 之间还要有 **UI capability discovery** 与 **requestEscalation** 契约。fileciteturn0file1
- 长时间自动恢复需要 **KeepAlive / Progress** 事件，不能在 Paperclip 侧表现为黑盒静默。fileciteturn0file1
- Snapshot、Artifact URL、级联删除的生命周期必须有 TTL、刷新与异步清理容忍度。fileciteturn0file1

---

## 3. V2.1 的核心升级

V2 主要解决的是：

- Run 身份建模
- Task / Run 状态拆分
- Bridge 最小状态化
- 结构化 handoff / resume
- 基本幂等与对账

V2.1 额外解决的是：

- **执行护栏**：自动恢复何时停
- **租约机制**：资源何时死
- **中断协议**：治理指令如何打断执行
- **能力协商**：UI 与权限如何动态握手
- **运行期观测**：长运行如何持续可见
- **保留策略**：snapshot / artifact / trace 何时过期

因此，V2.1 推荐新增四份硬文档作为开工附件：

1. `interrupt-and-progress.md`
2. `resource-lease-and-retention.md`
3. `agent-capability-policy.md`
4. `execution-guardrails.md`

---

## 4. 架构边界（修订后）

### 4.1 Paperclip（Control Plane）

继续负责：

- Company / Project / Goal / Task
- Approval / Budget / Comment / Operator Intervention
- `ExternalRun` 身份与治理投影
- Handoff / Resume 的结构化交互入口
- 长运行的治理可见性（但不是执行事实源）

新增能力：

- 渲染 `interventionRequest` 表单
- 展示 `Progress` / `KeepAlive` / `lastHeartbeatAt`
- 处理 `requestEscalation`（动态提权）
- 处理 `Cancel / Override / Resume` 高优先级治理动作

明确不做：

- 不保存完整 artifact 本体
- 不保存 sandbox / container / worktree 真实生命周期
- 不直接接触高风险运行时密钥材料
- 不存储原始模型私有推理内容

### 4.2 Bridge（Integration Plane）

继续负责：

- 输入映射
- 输出映射
- 状态投影
- 回调验签
- 幂等去重
- 顺序处理
- 对账补偿

新增约束：

- 对同一 `externalRunId` 采用**单写者串行化**（single-writer per run）或等价的 advisory lock / row lock 语义，防止并发回调互相覆盖。
- 可持久化以下**操作性状态**：
  - `idempotencyKey`
  - `eventId`
  - `lastAcceptedSequenceNo`
  - `lastHeartbeatAt`
  - `reconcileCursor`
  - `deliveryRetryState`
- 仍禁止持有以下**治理状态**：
  - 最终审批结论
  - 最终预算裁决
  - Task 协作语义主记录
  - Dark Factory 完整执行真相

### 4.3 Dark Factory（Execution Plane）

继续负责：

- task spec / acceptance spec
- runtime / verification / orchestration
- sandbox / worktree / container / cleanup
- artifact / evidence / execution summary
- retry / auto-downgrade / self-heal 策略

新增约束：

- 每个 Attempt 都必须有 **guardrails**。
- 每个有成本的资源都必须有 **lease / TTL**。
- sub-agent 必须使用 **capability downgrade**。
- 长运行必须持续产生 **keepalive / progress**。
- 输出 **TraceRef**，但不直接要求原始 CoT 落库到 Paperclip。

---

## 5. 数据模型（V2.1）

### 5.1 Task

保留为业务壳，不再重复。

### 5.2 ExternalRun

建议补充以下字段：

- `interruptState = none | cancel_requested | override_requested | resume_requested`
- `lastHeartbeatAt`
- `currentLeaseState = active | renewal_due | expired | retired`
- `uiCapabilityVersionSeen`
- `requestedEscalationState = none | pending | approved | rejected`

### 5.3 RunAttempt

建议补充以下字段：

- `autoRetryCount`
- `autoDowngradeCount`
- `guardrailSnapshotId`
- `leaseId`
- `progressCursor`
- `finalizationMode = completed | failed | cancelled | lease_expired`

### 5.4 ContextBoundarySnapshot

在上一版 `contextBoundary` 基础上，显式区分：

- `systemPromptPolicy`
- `toolAllowlist`
- `networkAccessLevel`
- `filesystemScope`
- `secretMountPolicy`
- `approvalPrerequisites`
- `capabilityDelegationPolicy`

### 5.5 TraceRef（新增）

新增 `TraceRef`，用于治理可审计执行轨迹，而不是直接搬运原始思维链。

建议字段：

- `traceId`
- `runId`
- `attemptNo`
- `modelVersion`
- `promptPolicyVersion`
- `toolCallLedgerUrl`
- `stepSummaryUrl`
- `decisionCheckpointUrl`
- `failureRationaleUrl`
- `retentionClass`
- `expiresAt`

### 5.6 ResourceLease（新增）

建议新增 `ResourceLease` 或等价内部对象：

- `leaseId`
- `resourceType = container | worktree | sandbox | agent_session`
- `resourceRef`
- `runId`
- `attemptNo`
- `ttlSec`
- `renewBeforeSec`
- `lastRenewedAt`
- `expiresAt`
- `leaseState = active | grace | expired | destroyed`

---

## 6. 状态机修订（V2.1 增量）

### 6.1 TaskStatus

继续使用：

- `queued`
- `in_progress`
- `blocked`
- `awaiting_approval`
- `awaiting_input`
- `handoff_required`
- `done`
- `cancelled`

### 6.2 RunStatus

在上一版基础上补充：

- `auto_recovering`
- `interrupt_pending`
- `lease_grace`
- `lease_expired`

### 6.3 ProgressState（新增）

用于长运行观测，不作为主状态机终态：

- `alive`
- `waiting_for_tool`
- `waiting_for_verification`
- `waiting_for_input`
- `auto_retrying`
- `auto_downgrading`
- `cleanup_running`
- `quiet_but_healthy`

### 6.4 InterruptState（新增）

用于描述控制面高优先级治理意图：

- `none`
- `cancel_requested`
- `override_requested`
- `resume_requested`
- `interrupt_acknowledged`
- `interrupt_applied`
- `interrupt_rejected`

---

## 7. 中断与进度协议

> 新增：`interrupt-and-progress.md`

### 7.1 原则

- `Cancel`、`Override`、`Resume` 都是**治理指令**，优先级高于普通状态回写。
- Dark Factory 的自动恢复不能无视上层治理指令继续盲跑。fileciteturn0file1
- 但治理指令也不应粗暴覆盖已经完成的终态；必须通过状态机消费。

### 7.2 指令优先级

推荐优先级：

1. `Emergency Cancel`
2. `Override Context / Override Budget / Override Risk Gate`
3. `Resume with Input`
4. 普通状态回写
5. KeepAlive / Progress

### 7.3 中断点（Interrupt Safe Points）

Dark Factory 至少在以下边界消费治理指令：

- tool call 之间
- verification stage 切换前
- auto-retry loop 轮次之间
- auto-downgrade 轮次之间
- artifact publish 前
- cleanup 开始前

### 7.4 KeepAlive / Progress 事件

长运行期间，Dark Factory 应发送轻量进度事件：

```json
{
  "eventType": "progress",
  "externalRunId": "pc_run_456",
  "attemptNo": 2,
  "progressState": "auto_retrying",
  "summary": "Retry 2/4 after test failure in verification stage.",
  "lastHeartbeatAt": "2026-04-21T18:00:00Z"
}
```

规则：

- `Progress` 可不占用主状态序列，也可占用独立 `progressSeq`。
- `KeepAlive` 仅刷新活跃时间，不更新主状态。
- Paperclip 超时判断应优先基于 `lastHeartbeatAt`，不能只看主状态是否变化。fileciteturn0file1

### 7.5 冲突处理

- 若 `cancel_requested` 到达时 run 已 `completed`，记录“取消未赶上”，不覆写终态。
- 若 `override_requested` 到达时 run 正在 `auto_recovering`，当前轮次应尽快在安全点中断，并以新上下文启动新 Attempt。
- 若 `resume_requested` 与 `auto_retrying` 冲突，优先消费 `resume_requested`，因为它带来新的信息输入。

---

## 8. 资源租约与保留策略

> 新增：`resource-lease-and-retention.md`

### 8.1 租约原则

任何有计算成本的资源都必须基于租约：

- container
- worktree
- sandbox
- agent session
- long-lived verification worker

如果 Bridge 挂掉、Paperclip 删除事件丢失，资源也应在租约过期后自毁，而不是永久悬挂。fileciteturn0file0

### 8.2 Lease 机制

建议机制：

- 创建资源时签发 `leaseId`
- 默认 `ttlSec`
- 周期性 `renewLease`
- 超过 `renewBeforeSec` 未续租进入 `grace`
- 超过 `expiresAt` 自动 `destroyed`

### 8.3 资源终结规则

- `completed / failed / cancelled` 后触发主动清理
- 主动清理失败时不阻塞 Task 终态，但记录 `cleanup_pending`
- 租约过期时允许 Dark Factory 执行底层强制清理
- Paperclip 可将资源状态展示为：`cleanup_running` / `cleanup_pending` / `cleanup_completed`

### 8.4 Snapshot 保留

推荐策略：

- 活跃 run：完整 snapshot 在线保留
- 终态 run：30 天保留完整 snapshot
- 超过 30 天：仅保留摘要 + hash，原文归档或删除
- 法务 / 审计类 run 可使用更长 retention class

### 8.5 Artifact URL 与 Trace URL

禁止长期裸露永久 URL。推荐：

- Paperclip 存 **artifactRef**，不是永久可用外链
- 访问时通过短效签名 URL 或代理鉴权发放
- `expiresInSec` 应短于默认会话生命周期
- 提供 `refreshArtifactAccess` / `refreshTraceAccess` 接口
- 允许 URL 过期后重新请求，不要求 UI 持久缓存链接。fileciteturn0file1

### 8.6 异步删除容忍度

若 Dark Factory 清理失败：

- Task / Run 允许先进入业务终态
- Paperclip 将资源标为 `retire_pending`
- 对账 Worker 周期性重试清理
- 超过阈值进入 `manual_ops_required`

---

## 9. 能力协商与动态提权

> 新增：`agent-capability-policy.md`

### 9.1 UI Capability Discovery

在 `formSchema` 之前，Paperclip 应公开自身能力：

```json
{
  "uiCapabilityVersion": "2026-04-21",
  "components": [
    "text_input",
    "textarea",
    "select",
    "radio_group",
    "checkbox_group",
    "file_upload",
    "kv_editor"
  ]
}
```

Dark Factory 只能下发双方都支持的交互组件；否则必须降级为兼容 schema。fileciteturn0file1

### 9.2 Runtime Request Escalation

真实执行中，可能出现运行时需要新增能力的情况，例如：

- 请求访问额外数据库
- 请求提升网络访问级别
- 请求临时开放额外工具
- 请求更高预算阈值

因此新增：`requestEscalation`。

建议字段：

- `escalationId`
- `runId`
- `attemptNo`
- `requestedCapabilityDelta`
- `reason`
- `riskSummary`
- `expiresAt`
- `decision = pending | approved | rejected`

### 9.3 Capability Delegation & Downgrade

对子 Agent 明确要求：

- 子 Agent 默认**不能继承**主 Agent 全量权限。
- 创建 sub-agent / sub-attempt 时，必须显式给出缩减后的：
  - tool allowlist
  - network access
  - filesystem scope
  - secret scope
- 没有显式授予，就视为不可用。fileciteturn0file0

---

## 10. 执行护栏与 AI 运行时安全

> 新增：`execution-guardrails.md`

### 10.1 Guardrail 原则

自动恢复不是“尽力多试几次”这么简单，而是要有**硬护栏**。否则会进入模型自旋、重复生成错误 patch、反复验证失败、持续消耗成本的死循环。fileciteturn0file0

### 10.2 每个 Attempt 建议的硬限制

建议至少有：

- `maxAutoRetryLoops`
- `maxAutoDowngradeSteps`
- `maxModelCalls`
- `maxToolCalls`
- `maxPromptTokens`
- `maxCompletionTokens`
- `maxWallClockSec`
- `maxVerificationRuns`
- `maxCostUsd`

### 10.3 触发人工介入的条件

满足任一条件即不再继续自动恢复：

- 超出任一 guardrail
- 权限不足且需要提权
- 缺关键业务信息
- 需要审批 gate
- 检测到重复失败模式
- 租约即将到期且不值得续租

### 10.4 对治理侧暴露的不是 CoT，而是摘要化轨迹

建议治理侧展示：

- 已重试次数
- 最近失败阶段
- 最近失败原因族（reason family）
- 当前降级层级
- 当前 guardrail 消耗百分比
- TraceRef 链接

不要求在 Paperclip 中直接持久化原始私有 CoT。fileciteturn0file0

---

## 11. 回调契约（V2.1 增量）

### 11.1 `POST /api/external-runs`

在 V2 基础上新增：

- `guardrails`
- `uiCapabilitiesSeen`
- `leasePolicy`
- `progressPolicy`
- `tracePolicy`

示意：

```json
{
  "externalRunId": "pc_run_456",
  "requestedMode": "execute",
  "contextBoundary": {
    "systemPromptPolicy": "engineering-bugfix-safe",
    "toolAllowlist": ["git", "npm", "playwright"],
    "networkAccessLevel": "repo-default",
    "filesystemScope": "task-worktree",
    "secretMountPolicy": "repo-default",
    "capabilityDelegationPolicy": "subagents-must-downgrade"
  },
  "guardrails": {
    "maxAutoRetryLoops": 4,
    "maxModelCalls": 80,
    "maxToolCalls": 120,
    "maxWallClockSec": 1800,
    "maxCostUsd": 20
  },
  "leasePolicy": {
    "defaultTtlSec": 3600,
    "renewBeforeSec": 300,
    "selfDestructOnExpiry": true
  },
  "progressPolicy": {
    "heartbeatEverySec": 30,
    "emitProgressEvents": true
  },
  "uiCapabilitiesSeen": {
    "uiCapabilityVersion": "2026-04-21",
    "components": ["text_input", "textarea", "select", "file_upload"]
  },
  "tracePolicy": {
    "retainTraceSummary": true,
    "retainRawPrivateReasoning": false
  }
}
```

### 11.2 Dark Factory -> Paperclip 回调事件

新增事件类型：

- `progress`
- `keepalive`
- `interrupt_acknowledged`
- `escalation_requested`
- `lease_renewed`
- `lease_expired`
- `trace_available`

### 11.3 回调字段增量

建议新增：

- `interruptState`
- `progressState`
- `lastHeartbeatAt`
- `leaseState`
- `guardrailUsage`
- `traceRefs`
- `requestedCapabilityDelta`

---

## 12. 推荐路线图（V2.1）

### Phase 0：契约与状态机

新增必须产出：

- `bridge-contract.md`
- `state-machine.md`
- `interrupt-and-progress.md`
- `resource-lease-and-retention.md`
- `agent-capability-policy.md`
- `execution-guardrails.md`

### Phase 1：零副作用模式

在 V2 目标基础上额外要求：

- `KeepAlive / Progress` 能在 Paperclip 面板可见
- Bridge 对同一 run 的重复 / 乱序进度事件可安全处理

### Phase 2：显式 Run 模型

在 V2 基础上额外要求：

- `ExternalRun` 持有 `lastHeartbeatAt / interruptState / leaseState`
- `TraceRef` 与 `ResourceLease` 至少有引用层实现

### Phase 3：real run

在 V2 基础上额外要求：

- 即使执行长时间自动恢复，Paperclip 也能看到它仍然活着
- 取消指令能在安全点穿透到 Dark Factory

### Phase 4：结构化 handoff / resume / escalation

在 V2 基础上额外要求：

- 支持 `requestEscalation`
- 支持 UI capability-aware 的表单渲染
- 子 Agent 权限策略可追踪

### Phase 5：预算 / 审批 / Guardrails 联动

新增要求：

- 审批可作为提权或高风险操作的前置 gate
- Guardrail 消耗可纳入治理展示
- 自动恢复超过阈值后自动升级人工介入

---

## 13. V2.1 的最终决策规则

### 留在 Paperclip 的

- 公司 / 项目 / 目标 / 任务
- 预算与审批治理
- `ExternalRun` 身份与治理投影
- Handoff / Resume / Escalation 结构化交互
- Progress / KeepAlive 的治理可见性

### 留在 Dark Factory 的

- Agent runtime / orchestration / routing
- Sandbox / Worktree / Container
- Verification 证据与 artifact 本体
- 自动恢复策略与执行护栏实际执行
- Lease 自毁与底层清理真实动作
- Trace 原始数据的内部保管

### 只留在 Bridge 的

- 输入输出映射
- 验签
- 幂等
- 顺序控制
- 对账补偿
- 投递失败重试

### 明确不做的

- 不把 Bridge 平台化成新的 execution gateway 产品
- 不让 Paperclip 成为 artifact / trace 原始数据仓库
- 不让 sub-agent 默认继承主 Agent 全量权限
- 不让自动恢复无限自旋
- 不让资源依赖上游永久记忆来清理

---

## 14. 下一步建议

如果要立刻交给工程团队开工，推荐先拆两条主线：

### 主线 A：可靠性与状态机

先写：

1. `paperclip-darkfactory-bridge-contract.md`
2. `paperclip-darkfactory-state-machine.md`
3. `interrupt-and-progress.md`
4. `resource-lease-and-retention.md`

### 主线 B：AI Runtime 安全与交互

再写：

1. `agent-capability-policy.md`
2. `execution-guardrails.md`
3. `handoff-form-schema.md`

---

## 15. 一句话收尾

> **V2 解决的是“系统别打架”，V2.1 解决的是“AI 别失控、资源别失联、治理能打断、权限能收敛”。**
