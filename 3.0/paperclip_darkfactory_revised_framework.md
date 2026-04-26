# Paperclip × Dark Factory 修订版框架（最终整合稿）

## 1. 结论先行

本修订版的最终判断如下：

1. **继续坚持方案 B，不改方向。** 仍然维持 Paperclip 作为上层 control plane，Dark Factory 作为下层 execution plane。
2. **从 task-centric 升级为 run-centric。** Task 继续是业务与协作壳，但真正的执行编排单位必须是 `ExternalRun`。
3. **承认 Bridge 的最小状态化，但禁止其膨胀成第二控制面。** Bridge 可以持有投递可靠性与回调去重所需的操作性状态；业务治理状态必须归 Paperclip，执行真相必须归 Dark Factory。
4. **以 GLM5.1 的落地路径为主，吸收 Gemini 的两个高价值补充。** 即：补齐上下文边界（context boundary），并在 handoff 之前先定义自动重试 / 自动降级策略。

这意味着：

> **最终方案不是“让 Paperclip 吃掉 Dark Factory”，也不是“立刻再造一个执行网关平台”，而是让 Paperclip 拥有 Run 的身份与治理投影，让 Bridge 只承担最小可靠性职责，让 Dark Factory 继续拥有执行事实与证据。**

---

## 2. 本次修订吸收了什么，放弃了什么

### 2.1 保留原始方案的部分

保留原始执行计划中的这些正确前提：

- 方案 B 仍是正确方向：Paperclip 负责公司、项目、目标、任务、审批、预算、人工介入；Dark Factory 负责 task spec、sandbox、verification、artifact、cleanup。原始 JSON 已明确这一层次分工与“Bridge 只做映射”的原则。【24:5†paperclip_darkfactory_scheme_b_execution_plan.json†L1-L45】【24:11†paperclip_darkfactory_scheme_b_execution_plan.json†L1-L34】
- 第一阶段仍优先接通 `validate-only / print-plan`，再接 `real run`，再接 `handoff / resume`，最后再接预算和高风险治理联动。这一点来自原始 roadmap，本修订版不推翻，只重排实现重心。【24:13†paperclip_darkfactory_scheme_b_execution_plan.json†L1-L76】【24:17†paperclip_darkfactory_scheme_b_execution_plan.json†L1-L57】
- 不重写 Paperclip 核心 company / goal / task 模型，不把 executionSummary 直接塞进核心 task schema，不第一版做深度 execution UI。这些边界要继续保留。【24:14†paperclip_darkfactory_scheme_b_execution_plan.json†L1-L75】【24:17†paperclip_darkfactory_scheme_b_execution_plan.json†L1-L57】

### 2.2 吸收 GLM5.1 的部分

本修订版主要吸收 GLM5.1 的四个落地点：

- 原方案是“方向正确但工程细节过轻”的 V1；真正的缺口集中在 run 模型、状态拆分、运维契约、交互协议。【24:4†GLM5.1的回答.ini†L1-L23】
- 不能再把 `handoff_required` 粗暴映射为 `awaiting_approval`；审批、人工输入、恢复执行是三类不同交互。【24:2†GLM5.1的回答.ini†L1-L19】
- Bridge 必须被承认会承担快照、幂等、签名校验、排序、对账等职责，因此需要轻量持久化，而不是假装完全无状态。【24:1†GLM5.1的回答.ini†L1-L18】【24:7†GLM5.1的回答.ini†L1-L14】
- 第一版要有降级路径，不要强行一口气实现完整五件套；可以先在 Paperclip 侧落轻量 run 投影，再逐步演进到正式表结构。【24:1†GLM5.1的回答.ini†L1-L18】

### 2.3 吸收 Gemini 的部分

本修订版额外吸收 Gemini 的三个高价值提醒：

- 如果不控制好职责，Bridge 会从“薄适配层”膨胀为事实上的第二控制面，这个风险必须正面承认并通过边界设计避免。【24:3†gemini的回答.ini†L1-L17】【24:10†gemini的回答.ini†L1-L19】
- API 契约里不能只有 repo、commit、task，还必须定义动态上下文边界，例如系统提示词策略、工具权限白名单、环境变量注入策略等，否则契约更像传统 CI/CD，而不像 agent runtime contract。【24:8†gemini的回答.ini†L1-L13】
- Dark Factory 在抛出人工 handoff 之前，应当先具备自动重试、自动降级、自反思式多轮尝试能力；否则“暗工厂”自动化闭环不彻底。【24:6†gemini的回答.ini†L1-L18】

---

## 3. 修订后的架构判断

### 3.1 三层架构不变，但边界更清晰

#### Layer 1：Paperclip（Control Plane）

仍负责：

- Company / Project / Goal / Task
- 审批、预算、评论、人工介入
- 协作状态与治理视图
- Run 的治理投影与人工交互入口

新增但受控的能力：

- `ExternalRun` 的身份层
- `RunProjection` / `LatestRunSnapshot`（可先轻量实现）
- Handoff / Resume 的结构化交互模型

**Paperclip 不做的事：**

- 不成为 sandbox / worktree / container 的事实来源
- 不保存完整 verification 证据与执行明细
- 不做 model routing / verification policy / cleanup 决策

#### Layer 2：Bridge（Integration Plane）

职责重新定义为：

- 输入映射
- 输出映射
- 状态投影
- artifact 引用投影
- 回调验签
- 幂等去重
- 事件排序
- 对账与补偿

**Bridge 可以有状态，但只能是“操作性状态”，不能是“治理状态”。**

允许 Bridge 持有的状态：

- `idempotencyKey` 去重记录
- callback `eventId / sequenceNo` 水位线
- 对账游标
- 请求 / 回调签名验证结果
- 投递失败重试队列

禁止 Bridge 持有的状态：

- 业务审批结论
- 最终 task 协作状态语义
- 预算决策主记录
- Dark Factory 的完整执行事实

#### Layer 3：Dark Factory（Execution Plane）

仍负责：

- task spec / acceptance spec
- runtime profile / verification profile
- worktree / container / sandbox 生命周期
- verification / artifacts / traces / previews
- lifecycleSummary / executionSummary
- handoff / resume 内部逻辑
- cleanup 与资源回收

新增约束：

- 对外不仅输出运行摘要，还要输出最小可观测 execution graph summary（例如 step、agent role、subtask 数量、失败边），但不要求第一版暴露完整 agent 内部对话。

---

## 4. 最终的数据模型

### 4.1 核心原则

- **Task 是业务壳，不是执行实例。**
- **Run 才是工程执行的一等公民。**
- **Attempt 是一次具体尝试。**
- **ArtifactRef 是治理侧对产物的引用，不是产物本体。**
- **Handoff 是结构化交互，不是评论流语义猜测。**

### 4.2 推荐实体

#### Task（保留）

职责：

- 业务语义
- 组织归属
- 协作入口
- 审批与预算挂钩
- 顶层状态展示

建议字段：

- `id`
- `title`
- `description`
- `linkedGoalId`
- `assignee`
- `budgetPolicyId`
- `approvalPolicyId`
- `taskKind = engineering`
- `externalExecutor = darkfactory`
- `repoRef`
- `runtimeProfileHint`
- `verificationProfileHint`
- `riskHint`
- `latestRunProjection`（V0 可先存在 metadata JSON）

#### ExternalRun（新增，推荐落在 Paperclip 域）

职责：

- 表示一次逻辑执行请求
- 连接 Task 与 Dark Factory run identity
- 作为治理侧的 run 主记录

建议字段：

- `runId`
- `taskId`
- `executor = darkfactory`
- `mode = validation | plan | execute | resume`
- `status`
- `substatus`
- `currentAttemptNo`
- `sourceRequestId`
- `snapshotId`
- `budgetSnapshotId`
- `approvalSnapshotId`
- `contextBoundaryId`
- `externalRunRef`
- `startedAt`
- `endedAt`
- `lastEventSeq`
- `latestSummary`

#### RunAttempt（新增）

职责：

- 表示一个 run 的第 N 次尝试
- 支持 retry / resume / auto-downgrade 的执行历史

建议字段：

- `runId`
- `attemptNo`
- `trigger = initial | retry | resume | auto_downgrade`
- `darkFactoryAttemptRef`
- `status`
- `failurePhase`
- `reasonCode`
- `costUsed`
- `startedAt`
- `endedAt`

#### RunSnapshot（新增）

职责：

- 固化执行时刻的输入上下文
- 解决“移动靶子”问题

建议字段：

- `snapshotId`
- `taskTitle`
- `taskDescription`
- `taskCommentsDigest`
- `goalDigest`
- `repo`
- `baseCommit`
- `budgetPolicySnapshot`
- `approvalPolicySnapshot`
- `contextBoundarySnapshot`
- `createdAt`

#### ArtifactRef（新增）

职责：

- 保存 Paperclip 侧能治理的产物引用
- 不把完整 artifact 二进制搬进 Paperclip

建议字段：

- `artifactId`
- `runId`
- `attemptNo`
- `kind`
- `displayName`
- `url`
- `mimeType`
- `sha256`
- `sizeBytes`
- `retentionClass`
- `redactionLevel`
- `createdAt`

#### HandoffRequest / ResumeRequest（新增）

职责：

- 承载人工输入要求
- 明确“要什么信息”和“怎么回填”

建议字段：

- `handoffId`
- `runId`
- `attemptNo`
- `type = approval_required | human_input_required | conflict_resolution_required | resume_requested`
- `formSchema`
- `promptText`
- `requiredFields`
- `deadline`
- `resolution`
- `resolvedBy`
- `resolvedAt`

### 4.3 V0 的务实落地方式

第一阶段不必立刻全量建表。可以采用两步法：

- **V0**：Task 上新增 `latestRunProjection` 与 `latestRunSnapshot` 元数据字段，Bridge 使用轻量 SQLite / Redis / Postgres 存幂等与对账水位。
- **V1**：当 `plan / execute / retry / resume` 跑通后，在 Paperclip 正式引入 `ExternalRun / RunAttempt / ArtifactRef / HandoffRequest` 表。

这样既吸收 GLM5.1 提出的降级路径，也避免 task-centric 方案长期固化。【24:1†GLM5.1的回答.ini†L1-L18】

---

## 5. 状态机修订

### 5.1 任务状态与运行状态必须拆开

原始方案把 Dark Factory 信号直接摘要投影到 Task 状态上，这个方向可以保留，但不能让 Task 与 Run 语义混在一起。原始方案已承认只是“摘要映射”，但示例中仍存在 `handoff_required -> awaiting_approval` 的粗糙映射，本修订版对此做出明确拆分。【24:13†paperclip_darkfactory_scheme_b_execution_plan.json†L1-L76】【24:2†GLM5.1的回答.ini†L1-L19】

#### TaskStatus（协作层）

- `queued`
- `in_progress`
- `blocked`
- `awaiting_approval`
- `awaiting_input`
- `handoff_required`
- `done`
- `cancelled`

#### RunStatus（执行层）

- `requested`
- `accepted`
- `validating`
- `planning`
- `running`
- `verifying`
- `completed`
- `failed`
- `cancel_requested`
- `cancelled`
- `timed_out`
- `cleanup_pending`
- `cleaned`

#### InterventionType（人工介入层）

- `approval_required`
- `human_input_required`
- `conflict_resolution_required`
- `resume_requested`

### 5.2 映射规则

- `run.status in {validating, planning, running, verifying}` -> `taskStatus = in_progress`
- `run.failed && autoRetryRemaining > 0` -> `taskStatus = in_progress`，并显示“自动恢复中”
- `interventionType = approval_required` -> `taskStatus = awaiting_approval`
- `interventionType = human_input_required` -> `taskStatus = awaiting_input`
- `interventionType = conflict_resolution_required` -> `taskStatus = handoff_required`
- `run.completed` -> `taskStatus = done`
- `run.cancelled` -> `taskStatus = cancelled`

**禁止规则：**

- 禁止把所有 handoff 都映射成 `awaiting_approval`
- 禁止用 TaskStatus 表达 Dark Factory 内部 phase
- 禁止用 Comment 文本作为唯一的恢复执行输入来源

---

## 6. 集成契约修订

### 6.1 `POST /api/external-runs`

请求体建议至少包含：

```json
{
  "contractVersion": "2026-04-21",
  "source": "paperclip",
  "externalTaskId": "pc_task_123",
  "externalRunId": "pc_run_456",
  "idempotencyKey": "pc_run_456_mode_plan_attempt_1",
  "correlationId": "corr_789",
  "requestedMode": "plan",
  "taskSnapshot": {
    "title": "Fix onboarding validation bug",
    "description": "Investigate and fix the broken onboarding validation flow",
    "commentsDigest": [
      {
        "author": "operator",
        "body": "Please prioritize regression safety."
      }
    ]
  },
  "repo": {
    "url": "git@github.com:org/repo.git",
    "defaultBranch": "main",
    "baseCommit": "abc123"
  },
  "executionProfile": {
    "taskType": "bugfix",
    "riskLevel": "medium",
    "verificationProfile": "web-app",
    "runtimeProfile": "node-web"
  },
  "budgetPolicy": {
    "usdLimit": 8,
    "cancelOnExceed": true
  },
  "approvalSnapshot": {
    "highRiskApproved": false
  },
  "contextBoundary": {
    "systemPromptPolicy": "engineering-bugfix-safe",
    "toolAllowlist": ["git", "npm", "playwright"],
    "envTemplate": "web-app-ci",
    "secretMountPolicy": "repo-default"
  },
  "callback": {
    "statusUrl": "https://paperclip/api/external-runs/status",
    "artifactUrl": "https://paperclip/api/external-runs/artifacts",
    "handoffUrl": "https://paperclip/api/external-runs/handoffs",
    "authMode": "signed-hmac"
  }
}
```

### 6.2 Dark Factory -> Paperclip 回调契约

每个回调事件至少包含：

- `contractVersion`
- `externalRunId`
- `attemptNo`
- `eventId`
- `sequenceNo`
- `eventType`
- `runStatus`
- `phase`
- `reasonCode`
- `summary`
- `costSummary`
- `artifactRefs`
- `interventionRequest`
- `emittedAt`

### 6.3 必须新增的契约字段

这些字段来自对原始方案的补洞，优先级很高：

- `contractVersion`
- `externalRunId`
- `idempotencyKey`
- `correlationId`
- `snapshotId`
- `attemptNo`
- `eventId`
- `sequenceNo`
- `contextBoundary`
- `budgetPolicy`
- `approvalSnapshot`
- `resourcePolicy`

### 6.4 上下文边界（Gemini 吸收项）

`contextBoundary` 至少应覆盖：

- 系统提示词策略名，而不是直接传完整 prompt
- 工具白名单
- 环境模板名
- 密钥挂载策略
- 网络访问等级
- 允许的文件系统路径级别
- 审批前置条件

这样既能给 LLM/Agent 执行环境足够上下文，又不把高敏内容原样暴露到治理面或日志面。【24:8†gemini的回答.ini†L1-L13】

---

## 7. 可靠性与一致性规则

### 7.1 事实归属原则

- **执行事实来源：Dark Factory**
- **协作与治理事实来源：Paperclip**
- **投递可靠性事实来源：Bridge**

这三者必须严格分层，避免“谁都能改状态，最后谁都不可信”。原始方案已有“执行细节以 Dark Factory 为准、任务协作状态以 Paperclip 为准”的原则，本修订版只是把 Bridge 的边界再明确了一层。【24:17†paperclip_darkfactory_scheme_b_execution_plan.json†L1-L57】

### 7.2 幂等与排序

- 请求侧用 `idempotencyKey`
- 回调侧用 `eventId`
- 同一 `externalRunId + attemptNo` 上按 `sequenceNo` 单调递增处理
- 重放事件允许被接受但不得重复生效
- 过期事件记录日志但不覆盖当前状态

### 7.3 冲突解决协议

为解决 Gemini 和 GLM 都指出的并发一致性问题，本修订版定义如下协议：

1. `completed` 与 `cancelled` 为终态
2. `cancel_requested` 不是终态，只是治理意图
3. 如果 Paperclip 发出取消时 Dark Factory 已完成执行：
   - 若执行已进入 `completed`，保持完成，记录“取消未赶上”
   - 若执行尚未进入终态，Dark Factory 应尽力终止，并回写最终终态
4. 预算缩减不直接改写已运行 attempt 的状态，而是产生新的治理事件，由 Dark Factory 在下一个边界点消费
5. 对账 Worker 只能补偿缺失，不得推翻更高 `sequenceNo` 的已确认终态

### 7.4 资源生命周期

新增跨系统级联规则：

- Task 被软删除 / 项目归档 -> Paperclip 发出 `resource_retire_requested`
- Bridge 记录并转发到 Dark Factory
- Dark Factory 触发 worktree/container/artifact retention cleanup
- 回调资源清理完成摘要
- Paperclip 标记 run / artifact ref 为 retired

这样可以补上 GLM5.1 提到的“孤儿 Run 与计算资源清理”缺口。【24:0†GLM5.1的回答.ini†L1-L18】【24:7†GLM5.1的回答.ini†L1-L14】

---

## 8. 自动化闭环修订

为了吸收 Gemini 对“暗工厂闭环不够彻底”的批评，本修订版规定：

### 8.1 人工 handoff 之前必须先尝试自动恢复

Dark Factory 在抛出人工介入前，至少按策略执行：

- 自动 retry
- 自动降级 runtime profile
- 自动切换 verification intensity
- 自动请求更保守的 patch strategy
- 自动生成最小可执行 plan 重新尝试

### 8.2 只有在以下情况才进入人工介入

- 缺关键业务上下文
- 需要审批放行
- 检测到互斥冲突无法自动决策
- 达到预算 / 风险 / 权限阈值
- 自动恢复策略已耗尽

### 8.3 对上层展示的不是“完整自言自语”，而是“自动恢复摘要”

Paperclip Run Panel 只需看到：

- 已尝试几次自动恢复
- 当前卡在哪一类问题
- 还缺什么输入
- 若不处理会发生什么

不需要第一版暴露完整 agent 对话日志，但要能知道系统不是“第一次失败就把锅甩给人”。【24:6†gemini的回答.ini†L1-L18】

---

## 9. 交互与 UI 协议

### 9.1 Run Panel V1

在原有 Run Panel 基础上，建议展示：

- current mode
- run status
- current phase
- attempt count
- reason code
- cost summary
- latest artifact refs
- cleanup status
- intervention type
- Open full run detail

### 9.2 Handoff / Resume 不能只靠评论流

原始方案强调 comments 只写摘要，这点继续保留；但对于 `human_input_required / resume_requested`，必须引入结构化 form schema，而不是只让 operator 写自然语言评论。【24:17†paperclip_darkfactory_scheme_b_execution_plan.json†L1-L57】【24:7†GLM5.1的回答.ini†L1-L14】

推荐最小交互协议：

- `formSchema`：JSON schema 或轻量字段描述
- `prefill`：Dark Factory 提供当前默认值
- `validationRules`：字段级校验
- `submitAction`：resume / approve / reject / clarify

### 9.3 预算与审批展示

- Paperclip 展示预算消耗、风险等级、是否等待审批
- Dark Factory 决定具体消耗发生在哪个 phase
- Bridge 只投影摘要，不做预算裁决

---

## 10. 推荐路线图（重排后）

### Phase 0：契约与状态机

目标：先把“怎么不打架”定义清楚。

输出：

- `bridge-contract.md`
- `state-machine.md`
- `handoff-form-schema.md`
- `context-boundary.md`
- `reliability-rules.md`

必须决定：

- 是否先用轻量持久化（推荐：SQLite 或 Postgres）
- `externalRunId` / `idempotencyKey` 规则
- `sequenceNo` 处理规则
- 取消与完成冲突协议
- context boundary 最小字段集

### Phase 1：零副作用模式跑通

目标：只跑 `validate-only / print-plan`。

输出：

- Paperclip task action：Run validation
- Paperclip task action：Generate plan
- Bridge V0（含去重、验签、回写）
- Run Panel V1
- `latestRunProjection` 元数据实现

成功标准：

- Paperclip 能发起 plan / validation
- Paperclip 能看到 run summary
- 回调乱序与重复不会把状态打乱

### Phase 2：正式引入 Run 实体

目标：从“元数据投影”升级到“显式 Run 模型”。

输出：

- `ExternalRun` 表
- `RunAttempt` 表
- `ArtifactRef` 表
- 迁移脚本与读写路径

成功标准：

- 同一 Task 的多次 plan / execute / retry / resume 历史可追溯
- 最新视图与历史视图都可用

### Phase 3：接通 real run

目标：跑通真实执行与失败摘要。

输出：

- Run execution action
- cleanup summary
- artifact refs 回写
- failure phase 可视化

成功标准：

- 即使运行失败，也能在 Paperclip 看到 phase、reason、cleanup 结果

### Phase 4：接通结构化 handoff / resume

目标：让人工介入有清晰的表单与状态。

输出：

- `HandoffRequest` / `ResumeRequest`
- operator form renderer
- resume bridge
- intervention banner

成功标准：

- 失败任务可明确区分等待审批、等待输入、等待冲突决策
- operator 输入可被机器可靠消费

### Phase 5：预算 / 审批 / 自动恢复策略

目标：把治理和自动化闭环连起来。

输出：

- 预算回写
- 风险审批 gate
- auto-retry / auto-downgrade policy
- cancel / complete 冲突处理

成功标准：

- Dark Factory 不会轻易把问题直接抛给人
- Paperclip 能从治理视角理解系统为何停下来

### Phase 6：产品化增强

输出：

- artifact preview
- verification drill-down
- minimal execution graph summary
- org-role -> runtime hints
- goal template -> execution template hints

---

## 11. 最终决策规则

### 留在 Paperclip 的

- Company / Project / Goal / Task
- 预算视图与审批视图
- 协作状态
- Run 身份与治理投影
- Handoff / Resume 的结构化交互

### 留在 Dark Factory 的

- task spec / acceptance spec
- agent runtime / routing / orchestration
- sandbox / worktree / container
- verification 证据
- artifact 本体
- cleanup 真相
- 自动恢复内部逻辑

### 只允许存在于 Bridge 的

- 输入输出映射
- 回调验签
- 幂等去重
- 顺序控制
- 对账补偿
- 失败投递重试

### 明确不做的

- 现在不做完整 execution gateway 微服务平台化
- 现在不让 Bridge 成为预算、审批、状态治理事实源
- 现在不把完整 agent 内部对话搬到 Paperclip
- 现在不做深度双向实时同步

---

## 12. 一句话版本

> **最终修订版的核心不是推翻方案 B，而是把方案 B 从“Task 驱动的轻集成”升级为“Run 驱动、Bridge 最小状态化、Dark Factory 自动恢复优先、Paperclip 负责治理投影”的可落地架构。**

---

## 13. 建议你下一步立即产出的两份文档

1. `paperclip-darkfactory-bridge-contract.md`
2. `paperclip-darkfactory-state-machine.md`

如果你愿意，下一步我建议直接继续把这两份拆出来，写成可以交给工程团队开工的接口与状态机文档。
