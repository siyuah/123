# Paperclip + Dark Factory 执行方案审阅与优化建议

## 1. 结论

这份方案的**战略方向是对的**：

- **方案 B**（Paperclip 作为上层 control plane，Dark Factory 作为下层 engineering execution engine）是合理选择。
- “**Bridge 只做映射，不做第二套控制面**”这个原则非常关键，必须保留。
- “**先 validate-only / print-plan，再 real run，再 handoff / resume，再 budget / approval**”的渐进路线也是正确的。

但从“架构判断正确”到“工程上能稳定落地”，目前还缺少 4 个关键件：

1. **Run-centric 数据模型**（现在更像 task-centric 回写）
2. **明确的状态机与事件模型**
3. **幂等 / 回调 / 重试 / 对账机制**
4. **handoff、approval、budget 三种语义的彻底拆分**

一句话优化版：

> 保留方案 B，不重写两边核心；但把集成对象从“Task 直接映射执行”升级为“Task 壳 -> ExternalRun -> RunAttempt -> Artifact/Handoff”，并采用“事件优先 + heartbeat 对账兜底”的一致性模型。

---

## 2. 当前方案最强的部分（建议保留）

### 2.1 边界判断正确

当前方案已经明确：

- Paperclip 管公司 / 项目 / 目标 / 审批 / 评论 / 预算治理
- Dark Factory 管 task spec / acceptance / sandbox / verification / artifacts / cleanup
- Bridge 只做输入输出映射

这个切分非常健康，能避免两个常见灾难：

- Paperclip 被工程语义污染，产品壳失真
- Dark Factory 被高层治理逻辑拖慢，执行内核失焦

### 2.2 路线图总体合理

先接无副作用模式，再接 real run，再接人工介入，再接预算与审批，这是正确的最小闭环顺序。

### 2.3 “尽量新增，不改核心模型”是对的

这能降低 Paperclip upstream 跟进成本，也能保护 Dark Factory runner/orchestrator/sandbox 的稳定性。

---

## 3. 当前方案最大的缺口（必须补）

## 3.1 缺少独立的 ExternalRun 模型

现在的文档更像是：

- Paperclip Task 发起执行
- Dark Factory 回写 status / comment / artifact

这个模式在第一眼看起来很轻，但一旦进入真实世界，就会立刻遇到问题：

- 一个 task 可能有 **validate run / plan run / execute run / resume run** 多次运行
- 一个 run 可能有 **多次 attempt**（重试、恢复、handoff 后继续）
- comment 与 panel 只能展示“最后一次结果”，很难形成完整历史
- task 状态容易被多次 run 互相覆盖

### 建议

在 **Paperclip 中新增 sidecar 实体**，而不是污染核心 Task：

#### ExternalRun

- id
- paperclipTaskId
- mode: `validation | plan | execute | resume`
- status
- phase
- latestAttemptNo
- requestedBy
- inputSnapshotVersion
- budgetCapUsd
- actualCostUsd
- sourceOfTruthUrl
- latestSummary
- createdAt / startedAt / finishedAt

#### RunAttempt

- id
- externalRunId
- attemptNo
- darkFactoryRunId
- status
- phase
- failurePhase
- cleanupSummary
- artifactCount
- startedAt / finishedAt

#### ArtifactRef

- id
- externalRunId
- attemptNo
- type
- label
- url
- contentType
- previewable
- retentionDays
- sha256

> Task 只保留 `latestRunId` / `latestRunProjection`，不要把执行细节直接塞进 Task 主 schema。

---

## 3.2 Task 状态和 Run 状态被混在一起了

当前方案已经在做“摘要映射”，这是对的；但现在映射还不够彻底。

### 问题

Task 是“协作与治理状态”，Run 是“工程执行状态”。

这两者不能混成一套状态，否则会出现：

- task 还是 in_progress，但某次 run 已 failed
- task 等待 operator 判断，但 run 其实已经 stopped
- 多次 run 并行/连续时，task status 被后一次覆盖前一次

### 建议

#### TaskStatus 只保留协作层语义

- queued
- in_progress
- blocked
- awaiting_approval
- handoff_required
- done
- cancelled

#### RunStatus 只保留执行层语义

- requested
- accepted
- preparing
- validating
- planning
- running
- verifying
- handoff_required
- awaiting_resume
- completed
- failed
- cancelled
- timed_out

#### 关键原则

- **TaskStatus 不是 RunStatus 的镜像**
- Task detail panel 展示的是 **Run 的投影**
- 执行事实来源永远在 Dark Factory
- 协作事实来源永远在 Paperclip

---

## 3.3 `handoff_required -> awaiting_approval` 的映射过于粗糙

这个是当前文档里最危险的点之一。

### 为什么危险

`handoff_required` 不一定意味着“需要审批”。
它可能意味着：

- 需要 operator 补充上下文
- 需要人工决策冲突项
- 需要确认产品方向
- 需要授权继续执行

只有最后一种才叫 approval。

### 建议

把这三个语义彻底拆开：

- `approval_required`：治理层审批未满足
- `human_input_required`：执行引擎需要人工补充信息
- `resume_requested`：人工已给出意见，准备继续执行

如果 Paperclip 当前主模型不能新增状态，也要保证：

- `awaiting_approval` 只用于审批
- `handoff_required` 保留给人工接管 / 人工输入

> 不建议第一版把所有 handoff 都投影成 awaiting_approval。

---

## 3.4 API 合同还不够“可运维”

当前文档里已经有：

- `POST /api/external-runs`
- status/comment/artifact 回写接口

但缺了能让系统稳定运行的关键字段。

### 建议 ExternalRunRequest 最小补齐字段

- `contractVersion`
- `externalRunId`
- `idempotencyKey`
- `correlationId`
- `mode`
- `taskSnapshot`
- `approvalSnapshot`
- `budgetPolicy`
- `callbackEndpoints`
- `authScheme`
- `timeoutBudgetSec`
- `requestedAt`

### 建议新增查询与恢复接口

- `GET /api/external-runs/:externalRunId`
- `POST /api/external-runs/:externalRunId/resume`
- `POST /api/external-runs/:externalRunId/cancel`

### 建议所有回调事件具备

- `eventId`
- `eventType`
- `externalRunId`
- `attemptNo`
- `sequenceNo`
- `occurredAt`
- `signature`

> 没有幂等键、事件 ID、sequenceNo，后面一定会碰到重复回写、乱序回写、重试覆盖的问题。

---

## 3.5 触发模型不应只有 heartbeat

当前方案里“Paperclip heartbeat 触发 adapter”是可行的，但不应成为唯一机制。

### 问题

如果只有 heartbeat/polling：

- 触发延迟高
- 更容易重复 dispatch
- 出错后不容易知道是“没触发”还是“触发了但丢了”

### 建议

采用：

- **主路径：事件驱动 / task action 触发**
- **兜底：heartbeat reconciliation 对账**

即：

1. 用户在 Paperclip task 上点击 `Run validation / Generate plan / Run execution`
2. Paperclip 产生 outbox 事件
3. Bridge claim 该事件并调用 Dark Factory
4. Dark Factory 通过 callback 回写
5. Heartbeat 只负责补偿、重试、对账、修复孤儿 run

如果你的系统现在必须 heartbeat 驱动，也建议增加：

- **lease / claim token**
- **dispatch idempotencyKey**
- **stale run reconciliation**

---

## 3.6 缺少输入快照（snapshot）语义

当前任务是活的，comments、goal、budget、approval 都可能在运行过程中变化。

如果不做 snapshot，会出现：

- 计划是按旧描述生成的
- 执行时 description 已变了
- 审批状态在 run 中间变化，不知道以哪次为准

### 建议

每次 ExternalRun 创建时生成：

- `taskSnapshot`
- `goalSnapshot`
- `commentDigest`
- `approvalSnapshot`
- `budgetSnapshot`
- `repoSnapshot`

Dark Factory 执行时以 snapshot 为准；Paperclip UI 可以提示“任务在运行期间发生变更”。

---

## 3.7 预算与审批还需要一层“策略 / 计量”拆分

当前文档已经意识到“谁是真实计量源，谁是展示层”这个问题，这是非常对的。

### 建议明确为：

#### Paperclip

- 预算策略 owner
- 审批策略 owner
- 风险门槛 owner

#### Dark Factory

- 实际 cost meter owner
- 执行阶段 cost enforcement owner
- verification / cleanup 成本归集 owner

#### Bridge

- 成本摘要投影
- 预算可视化同步
- 超限事件回写

### 再补一个关键点

**Task budget** 和 **Run budget** 不应完全等同。

建议同时存在：

- `taskBudgetCapUsd`
- `runBudgetCapUsd`
- `estimatedCostUsd`
- `actualCostUsd`
- `reservedCostUsd`

否则一个 task 连续触发几次 plan/execute，很容易把预算语义搞乱。

---

## 3.8 Artifact 需要元数据，而不只是链接

当前文档里已经提出 artifact links，这很好，但还差“能被治理层理解”的元数据。

### 建议 ArtifactRef 最小元数据

- type
- label
- url
- contentType
- sizeBytes
- previewable
- redactionLevel
- retentionDays
- createdAt
- sha256

### 原则

- comments 只写摘要与 milestone
- panel 展示可操作 artifact 清单
- 完整证据链仍留在 Dark Factory

---

## 3.9 还缺少可靠性和恢复设计

建议显式补一节：

### 必须定义的异常场景

- Dark Factory 已完成，但 callback 失败
- callback 成功，但 Paperclip 持久化失败
- heartbeat 与 callback 同时更新同一个 run
- run 超时但 cleanup 仍在进行
- cleanup 失败但主执行已结束
- operator 发起 resume，但原 run 已 terminal
- 同一个 task 被重复触发 execution

### 建议机制

- 事件幂等写入
- last-write-not-by-clock，而是 **按 sequenceNo / attemptNo**
- 终态不可逆
- orphan run reconciliation
- dead letter queue / failed callback queue
- 周期性 `GET run detail` 对账

---

## 3.10 安全与权限边界还没写透

建议补一节 Security & Access Model：

- repo credential 不经由 Paperclip 明文下发
- Dark Factory 从 secrets manager 获取最小权限凭证
- `baseCommit` 必须固定，避免漂移
- writeback/push/merge 行为必须带 approval gate
- artifact URL 建议签名或经代理层鉴权
- 审计日志必须带 correlationId

---

## 4. 推荐的优化版架构

## 4.1 分层不变，但内部对象升级

### Layer 1 - Paperclip Control Plane

保留：

- Company
- Project
- Goal
- Task
- Comment
- Approval
- Budget
- Agent

新增 sidecar：

- **ExternalRun**
- **RunProjection**
- **HandoffRequest**
- **ArtifactRef**

### Layer 2 - Bridge / Adapter

保留“薄映射”原则，但补充：

- input snapshot builder
- idempotency manager
- callback verifier
- status projector
- reconciliation worker

### Layer 3 - Dark Factory Engine

保持不变，仍负责：

- orchestrator
- sandbox
- verification
- artifact store
- execution summary
- cleanup
- handoff / resume internals

---

## 4.2 推荐的事件模型

建议以事件为主，而不是只靠状态回写：

- `run.requested`
- `run.accepted`
- `run.started`
- `run.phase_changed`
- `run.blocked`
- `run.handoff_required`
- `run.resume_requested`
- `run.completed`
- `run.failed`
- `run.cancelled`
- `artifact.produced`
- `cleanup.completed`
- `cleanup.failed`

Paperclip 只做投影：

- panel
- task status projection
- comment milestones
- artifact list

---

## 5. 推荐的优化版路线图

## Phase 0：合同 + 状态机 + 幂等（必须先于一切）

新增交付物：

- `external-run-domain-model.md`
- `external-run-state-machine.md`
- `callback-auth-and-idempotency.md`
- `snapshot-semantics.md`

### 成功标准

- 能清楚回答“一条 task 如何对应多次 run / 多次 attempt”
- 能清楚回答“重复触发、回调乱序、resume”如何处理

## Phase 1：Manual validate / plan（零副作用）

交付物：

- `POST /api/external-runs`
- `GET /api/external-runs/:id`
- Paperclip `ExternalRun V0`
- Run Panel V0
- milestone comment writer

### 成功标准

- 同一 task 可看到多次 validation / plan 记录
- panel 可展示最新 run 与历史 run

## Phase 2：状态回调 + artifact refs

交付物：

- callback receiver
- idempotent event store
- artifact projection
- reconciliation worker

### 成功标准

- callback 失败后可自动对账恢复
- artifact links 与 run attempt 正确绑定

## Phase 3：real run + cleanup summary

交付物：

- Run execution action
- failure phase projection
- cleanup summary projection
- terminal state rules

### 成功标准

- 即使 container/sandbox 失败，也能在 panel 中看到 run 级别失败与 cleanup 结论

## Phase 4：handoff / resume

交付物：

- handoff banner
- operator note -> resume request
- run attempt +1 语义

### 成功标准

- operator 处理意见能形成新的 resume attempt，而不是覆盖旧 run 历史

## Phase 5：budget / approval governance

交付物：

- run budget vs task budget
- approval gate mapping
- high-risk policy integration

### 成功标准

- 高风险任务在 execute 前被策略层明确拦截或放行

---

## 6. 我建议你直接改掉的几句话

### 6.1 原表述

> Dark Factory 的 summary / status / artifacts / handoff 回写到 Paperclip

### 建议改成

> Dark Factory 以事件和摘要回写 Paperclip；Paperclip 持有 ExternalRun/ArtifactRef 等 sidecar 投影对象，不把执行明细写入核心 Task 模型。

### 6.2 原表述

> handoff_required -> awaiting_approval 映射

### 建议改成

> handoff_required 默认映射为人工介入需求，而非审批需求；只有命中治理策略时才投影为 awaiting_approval。

### 6.3 原表述

> Paperclip heartbeat 触发 adapter

### 建议改成

> Paperclip task action / outbox event 为主触发路径，heartbeat 仅用于对账、恢复和兜底重试。

### 6.4 原表述

> comments 只写摘要与事件

### 建议补充成

> comments 只写用户可理解的 milestone 事件；phase 级细粒度变化保存在 ExternalRun history，不直接刷屏评论流。

---

## 7. 优化后的 DoD（推荐替换原版本）

1. Paperclip 中一条 engineering task 可触发多个 ExternalRun（validation / plan / execute）。
2. 每个 ExternalRun 至少支持 1..N 个 RunAttempt，并可表达 resume。
3. Paperclip Run Panel 能看到：最新状态、历史 attempts、failure phase、cleanup summary、artifact refs。
4. Dark Factory 回写具备 eventId / sequenceNo / idempotency 机制。
5. Heartbeat 或 reconciliation job 能修复 callback 失败造成的状态漂移。
6. `handoff_required` 与 `awaiting_approval` 语义已拆分。
7. Task 不承载 executionSummary 原文，执行事实仍以 Dark Factory 为准。
8. 同一 idempotencyKey 不会产生重复 real run。

---

## 8. 最终判断

**这份方案不是方向错，而是“还差半层运行域模型”。**

你现在的版本已经把：

- 上下层职责边界
- 桥接原则
- 迭代顺序
- UI 摘要策略

这些最难想清楚的地方想对了。

真正需要优化的是：

- 从 **task-centric 回写** 升级到 **run-centric 集成**
- 从 **状态直写** 升级到 **事件 + 投影**
- 从 **单次执行假设** 升级到 **多 run / 多 attempt / 可恢复** 的真实运行模型

如果只让我给一个最终建议，那就是：

> **继续坚持方案 B，但请在 Phase 0 先补出 ExternalRun / RunAttempt / Event / Snapshot / Idempotency 五件套，再开始第一版集成。**

