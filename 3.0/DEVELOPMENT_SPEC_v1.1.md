# DEVELOPMENT_SPEC.md

# 基于 Multica 的 Dark Factory 开发文档

**版本**：v1.1  
**目标形态**：Fork Multica，在其现有任务板、runtime、daemon 和自托管骨架上，新增 Dark Factory 的控制平面、任务协议、自动验证闭环、失败回流、人工接管、恢复策略、成本与并发控制、命令沙箱和模型路由。  
**执行方式**：  
- `hermes-agent`：负责代码实现、文件创建、局部重构、测试修复  
- `GPT-5.4`：负责高层规划、关键审查、风险判断、最终拍板  
- 其他模型按本文“模型路由”章节分工

---

# 1. 项目目标

## 1.1 总目标

在 Multica 的现有能力基础上，增加一套最小可运行的 Dark Factory 闭环，实现：

1. 任务进入后自动生成 `task spec`
2. 自动生成 `acceptance spec`
3. 根据任务类型和风险等级完成模型路由
4. 执行代码修改、测试、浏览器验收
5. 验证失败时自动生成结构化报告并回流
6. 多次失败或高风险命中时自动人工接管
7. 人工处理后按恢复策略重新交回 AI 或关闭任务
8. 在 Web 端查看 task spec、验收状态、artifact、handoff、重试历史、预算与执行轨迹

## 1.2 非目标

第一阶段明确不做：

- 不重写 Multica 的 board / issue / comment 主流程
- 不重写 daemon 核心协议
- 不重写 desktop 端
- 不做完整企业审批系统
- 不做生产自动发布
- 不从零重写平台
- 不暴露原始模型 CoT（只展示执行轨迹摘要）

---

# 2. 当前基础与约束

## 2.1 当前可复用能力

默认复用 Multica 当前已存在的这些能力：

- issue / comment / board / status 流程
- agent / runtime / workspace 管理
- 本地 daemon 执行骨架
- WebSocket 实时更新
- 自托管部署骨架
- `packages/core` / `packages/ui` / `packages/views` 分层

## 2.2 必须遵守的仓库约束

根据当前仓库的 `CLAUDE.md` 说明：

- `server/`：Go backend
- `apps/web/`：Next.js
- `apps/desktop/`：Electron
- `packages/core/`：无 UI 的 headless 业务逻辑
- `packages/ui/`：原子 UI 组件
- `packages/views/`：共享业务页面与组件
- 服务端状态必须由 TanStack Query 管理
- 客户端状态必须由 Zustand 管理
- WebSocket 只做 query invalidation，不直接写 store

这些边界必须保留。

---

# 3. 总体技术方案

## 3.1 核心原则

本项目采用 **“借壳做脑”** 方案：

- **壳**：Multica 的 board / issue / runtime / daemon / workspace / self-host
- **脑**：新增 Dark Factory control-plane
- **手**：模型路由 + coder / executor / reviewer / analyst
- **眼**：测试链 + Playwright + artifacts
- **刹车**：handoff policy + protected paths + risk policy + budget policy
- **隔离层**：每个任务独立 worktree + 独立容器

## 3.2 架构图

```text
用户 / Issue / Webhook / 手工创建
        ↓
Multica issue / board / runtime / daemon
        ↓
Dark Factory Control Plane
  - task spec
  - acceptance spec
  - model routing
  - risk policy
  - handoff policy
  - budget / rate limit policy
  - resumption policy
        ↓
执行隔离层
  - git worktree
  - per-task container
  - preview environment
        ↓
执行层
  - GPT-5.4（主脑）
  - GLM-5.1（长时执行）
  - Qwen3-Coder（编码）
  - DeepSeek（根因分析/工具型分析）
  - Qwen3.6（长上下文/廉价跑量）
        ↓
验证层
  - lint / typecheck / unit / integration
  - Playwright E2E
  - screenshots / traces / reports
        ↓
结果回写
  - issue comments
  - run history
  - artifacts
  - handoff
  - verification state
  - execution trace
```

---

# 4. 模型分工

## 4.1 固定角色

- **Lead / 主脑 / 最终 Reviewer**：GPT-5.4
- **Long-run Executor / 长时执行器**：GLM-5.1
- **Coder / 常规编码**：Qwen3-Coder-Next
- **Coder+ / 高难编码**：Qwen3-Coder-Plus
- **Root Cause / 根因分析**：DeepSeek-Reasoner
- **Analyst / 工具型分析**：DeepSeek-Chat
- **Long Context Worker**：Qwen3.6-Plus
- **Bulk Worker**：Qwen3.6-Flash

## 4.2 职责

- **GPT-5.4**：任务拆解、验收标准、路线判断、最终拍板
- **GLM-5.1**：长链路实现、连续修复、主执行线程
- **Qwen3-Coder**：代码实现与局部修补
- **DeepSeek-Reasoner**：失败复盘、复杂问题二审、根因分析
- **DeepSeek-Chat**：issue triage、日志分析、结构化中间结果
- **Qwen3.6-Plus**：长文档/长日志/长上下文整理
- **Qwen3.6-Flash**：摘要、分类、抽取、轻量跑量

---

# 5. 目录结构

## 5.1 新增目录

```text
control-plane/
task-templates/
policies/
runtime/
docs/darkfactory/
```

## 5.2 重点改造目录

```text
server/
packages/core/
packages/views/
packages/ui/
apps/web/
e2e/
```

## 5.3 目标目录骨架

```text
multica-factory/
├─ apps/
│  ├─ web/
│  └─ desktop/
├─ server/
├─ packages/
│  ├─ core/
│  ├─ ui/
│  └─ views/
├─ e2e/
├─ docs/
│  └─ darkfactory/
├─ control-plane/
├─ task-templates/
├─ policies/
├─ runtime/
└─ scripts/
```

---

# 6. 文件级开发清单

## 6.1 顶层新增

### `control-plane/`

```text
control-plane/
├─ package.json
├─ README.md
├─ src/
│  ├─ index.ts
│  ├─ config.ts
│  ├─ intake/
│  │  ├─ issue-ingest.ts
│  │  ├─ webhook-ingest.ts
│  │  └─ manual-ingest.ts
│  ├─ schemas/
│  │  ├─ task.schema.json
│  │  ├─ acceptance.schema.json
│  │  ├─ artifact.schema.json
│  │  ├─ event.schema.json
│  │  └─ execution-trace.schema.json
│  ├─ planners/
│  │  ├─ build-task-spec.ts
│  │  ├─ build-acceptance-spec.ts
│  │  └─ infer-scope.ts
│  ├─ policies/
│  │  ├─ assignment-policy.ts
│  │  ├─ handoff-policy.ts
│  │  ├─ resumption-policy.ts
│  │  ├─ risk-policy.ts
│  │  ├─ budget-policy.ts
│  │  ├─ rate-limit-policy.ts
│  │  ├─ command-policy.ts
│  │  └─ path-policy.ts
│  ├─ workflows/
│  │  ├─ feature-flow.ts
│  │  ├─ bugfix-flow.ts
│  │  ├─ refactor-flow.ts
│  │  └─ research-flow.ts
│  ├─ adapters/
│  │  ├─ multica-api.ts
│  │  ├─ github.ts
│  │  ├─ playwright.ts
│  │  ├─ artifact-store.ts
│  │  └─ execution-runtime.ts
│  ├─ scheduler/
│  │  ├─ project-lead-scan.ts
│  │  └─ retry-queue.ts
│  └─ sandbox/
│     ├─ worktree-manager.ts
│     ├─ container-manager.ts
│     └─ preview-manager.ts
└─ config/
   ├─ model-routing.yaml
   ├─ execution-sandbox.yaml
   └─ budget-limits.yaml
```

### `task-templates/`
- `feature.task.yaml`
- `bugfix.task.yaml`
- `refactor.task.yaml`
- `research.task.yaml`
- `release.task.yaml`

### `policies/`
- `protected-paths.yaml`
- `allowed-commands.yaml`
- `handoff-rules.yaml`
- `resumption-rules.yaml`
- `severity-matrix.yaml`
- `workspace-policy.yaml`
- `budget-limits.yaml`
- `rate-limit.yaml`

### `runtime/`
- `artifacts/`
- `reports/`
- `screenshots/`
- `traces/`
- `task-runs/`
- `preview-env/`

### `docs/darkfactory/`
- `architecture.md`
- `task-spec.md`
- `acceptance-spec.md`
- `runtime-policy.md`
- `handoff-rules.md`
- `resumption-policy.md`
- `verification-pipeline.md`
- `execution-isolation.md`
- `budget-and-rate-limit.md`
- `observability.md`
- `rollout-plan.md`

## 6.2 修改现有文件

### 根目录
- `CLAUDE.md`
- `AGENTS.md`
- `package.json`
- `docker-compose.selfhost.yml`
- 可选：`playwright.config.ts`

### server
新增：
- `server/internal/darkfactory/taskspec/*`
- `server/internal/darkfactory/acceptance/*`
- `server/internal/darkfactory/artifacts/*`
- `server/internal/darkfactory/verification/*`
- `server/internal/darkfactory/handoff/*`
- `server/internal/darkfactory/resumption/*`
- `server/internal/darkfactory/projectlead/*`
- `server/internal/darkfactory/budget/*`
- `server/internal/darkfactory/executiontrace/*`

新增 API：
- `server/internal/api/taskspec_handlers.go`
- `server/internal/api/acceptance_handlers.go`
- `server/internal/api/artifact_handlers.go`
- `server/internal/api/verification_handlers.go`
- `server/internal/api/handoff_handlers.go`
- `server/internal/api/resumption_handlers.go`
- `server/internal/api/budget_handlers.go`
- `server/internal/api/executiontrace_handlers.go`

新增事件：
- `server/internal/realtime/darkfactory_events.go`

新增迁移：
- `server/migrations/*darkfactory*.sql`

新增 sqlc queries：
- `server/pkg/db/queries/darkfactory_*.sql`

### packages/core
新增：

```text
packages/core/src/darkfactory/
├─ models/
├─ api/
├─ queries/
├─ stores/
└─ ws/
```

### packages/views
新增：

```text
packages/views/src/darkfactory/
├─ pages/
├─ sections/
└─ components/
```

### packages/ui
新增：

```text
packages/ui/src/darkfactory/
├─ badges/
├─ cards/
├─ timeline/
├─ log-viewer/
└─ progress/
```

### apps/web
新增 route：
- `apps/web/app/factory/page.tsx`
- `apps/web/app/factory/issues/[id]/page.tsx`
- `apps/web/app/factory/projects/[id]/page.tsx`
- `apps/web/app/factory/runtimes/page.tsx`

### e2e
新增：
- `e2e/darkfactory/task-spec-flow.spec.ts`
- `e2e/darkfactory/verification-flow.spec.ts`
- `e2e/darkfactory/handoff-flow.spec.ts`
- `e2e/darkfactory/resumption-flow.spec.ts`
- `e2e/darkfactory/project-lead-flow.spec.ts`
- `e2e/darkfactory/execution-trace-flow.spec.ts`

---

# 7. 执行隔离与预览环境

## 7.1 强制隔离策略

第一阶段采用 **每个 Task = 一个 git worktree + 一个独立 Docker container**。

强制规则：

1. 每个 Task 必须创建独立 branch：
   - `task/<task_id>`
2. 每个 Task 必须创建独立 git worktree：
   - `.worktrees/<task_id>/`
3. 每个 Task 必须在独立容器中执行：
   - 非 root 用户
   - 仅挂载当前 worktree
   - 不挂载宿主机 home 目录
   - 默认无外网，或严格白名单出网
4. 所有 artifacts 必须写入：
   - `runtime/artifacts/<task_id>/`
   - 或对象存储前缀 `artifacts/<task_id>/`

## 7.2 执行容器要求

容器要求：

- 基础镜像固定版本
- Node / Go / Playwright 版本固定
- 禁止 privileged 模式
- 禁止挂载 Docker socket
- 默认只读基础层
- 允许写入的目录仅限：
  - `/workspace`
  - `/tmp`
  - `/artifacts`

## 7.3 Preview Environment 启动逻辑

任何涉及 UI / 浏览器验证的 Task，必须执行以下步骤：

1. 在 task 容器内拉起 preview server
2. 使用固定命令启动，例如：
   - `pnpm dev --port <allocated_port>`
   - 或项目定义的 preview script
3. 对健康检查 URL 轮询：
   - `http://127.0.0.1:<port>/health` 或主页
4. 若在 `preview_boot_timeout_sec` 内未通过，标记 preview 启动失败
5. 启动 Playwright
6. 验证结束后保存：
   - screenshot
   - trace
   - HTML report
7. 销毁 preview 环境和 task 容器

## 7.4 Preview 配置字段

建议在配置文件中增加：

```yaml
preview:
  boot_timeout_sec: 120
  healthcheck_path: /
  max_wait_for_ready_sec: 180
  port_pool_start: 41000
  port_pool_end: 41999
```

---

# 8. Git 工作流与竞态控制

## 8.1 Git 工作流

每个 Task 必须遵循以下 Git 规则：

- 独立分支执行：`task/<task_id>`
- 基于 `base_commit` 创建 worktree
- 所有自动修改仅允许落在 task branch
- 验证通过后生成 PR
- 默认采用 **Squash Merge**
- 自动生成：
  - PR summary
  - verification report
  - rollback notes

## 8.2 Writer Lock 规则

同一 Task 同一时刻只允许一个 writer。

角色权限：

- `Lead`：只读
- `Reviewer`：只读
- `Reasoner`：只读
- `Analyst`：只读
- `Executor`：可写（在主执行阶段）
- `Coder`：可写（在编码阶段）

如果同一 workspace 中多个 Task 修改路径重叠，则：

1. 优先按 `writer_lock_key` 加锁
2. 冲突 Task 排队
3. 必要时拆到不同 worktree 或强制串行

## 8.3 Task Spec 增加的 Git 字段

```yaml
workspace_id:
git_branch:
base_commit:
writer_lock_key:
merge_strategy: squash
```

---

# 9. 数据协议

## 9.1 Task Spec

```yaml
task_id: DF-2026-000001
task_type: feature
title: Add invite member flow
goal: Allow workspace admins to invite members by email
scope:
  include:
    - apps/web/src/**
    - server/internal/**
    - packages/core/**
  exclude:
    - infra/**
    - migrations/**
risk_level: medium
acceptance_required: true
allowed_tools:
  - read
  - grep
  - edit
  - write
  - bash
  - playwright
forbidden_paths:
  - .env
  - migrations/**
handoff_rules:
  - retry_count_gte_4
  - protected_path_touched
resumption_policy: resume_from_failed_gate
budget_limit_usd: 8
max_tokens_per_run: 800000
max_retries: 4
max_reasoner_calls: 2
max_lead_calls: 3
workspace_id: workspace-01
git_branch: task/DF-2026-000001
base_commit: abcdef123456
writer_lock_key: apps-web-invite-flow
merge_strategy: squash
deliverables:
  - pull_request
  - verification_report
  - rollback_notes
```

## 9.2 Acceptance Spec

```yaml
task_id: DF-2026-000001
criteria:
  - Admin can open invite dialog
  - Admin can send invite by email
  - Duplicate pending invite is handled
  - Invite status is visible in UI
  - Unit tests added
  - Playwright invite flow passes
verification:
  - typecheck
  - unit
  - playwright
```

## 9.3 Artifact Meta

```json
{
  "task_id": "DF-2026-000001",
  "run_id": "RUN-001",
  "type": "playwright-trace",
  "path": "runtime/traces/RUN-001.zip",
  "created_at": "2026-04-19T12:00:00Z"
}
```

## 9.4 Verification Result

```json
{
  "task_id": "DF-2026-000001",
  "run_id": "RUN-001",
  "gate": "playwright",
  "status": "failed",
  "summary": "Invite submit button disabled after email input",
  "evidence": {
    "trace": "runtime/traces/RUN-001.zip",
    "screenshot": "runtime/screenshots/RUN-001-step-4.png",
    "stderr": "button remains disabled"
  },
  "next_hint": "check form validation and disabled condition"
}
```

## 9.5 Handoff Event

```json
{
  "task_id": "DF-2026-000001",
  "reason": "protected_path_touched",
  "retry_count": 3,
  "final_decider": "gpt-5.4",
  "status": "handoff_required"
}
```

## 9.6 Resumption Event

```json
{
  "task_id": "DF-2026-000001",
  "resume_mode": "resume_from_failed_gate",
  "manual_resolution_summary": "Human fixed validation rule in frontend form",
  "next_gate": "playwright",
  "status": "resume_pending"
}
```

## 9.7 Execution Trace

```json
{
  "task_id": "DF-2026-000001",
  "run_id": "RUN-001",
  "stage": "analyzing_failure",
  "current_action": "Inspecting form validation and disabled submit condition",
  "last_tool": "playwright",
  "retry_count": 2,
  "budget_used_usd": 3.42,
  "next_step": "Patch frontend validation logic and rerun playwright"
}
```

---

# 10. API 设计

## 10.1 Task Spec
- `GET /factory/issues/:id/task-spec`
- `PUT /factory/issues/:id/task-spec`

## 10.2 Acceptance
- `GET /factory/issues/:id/acceptance`
- `PUT /factory/issues/:id/acceptance`

## 10.3 Verification
- `POST /factory/runs/:id/verification`
- `GET /factory/runs/:id/verification`
- `GET /factory/issues/:id/verification-history`

## 10.4 Artifacts
- `POST /factory/runs/:id/artifacts`
- `GET /factory/issues/:id/artifacts`

## 10.5 Handoff
- `POST /factory/issues/:id/handoff`
- `GET /factory/issues/:id/handoff`

## 10.6 Resumption
- `POST /factory/issues/:id/resume`
- `GET /factory/issues/:id/resumption`

## 10.7 Budget
- `GET /factory/issues/:id/budget`
- `POST /factory/issues/:id/budget-events`

## 10.8 Execution Trace
- `GET /factory/runs/:id/execution-trace`

## 10.9 Project Lead
- `POST /factory/projects/:id/scan`
- `GET /factory/projects/:id/lead-status`

---

# 11. WebSocket 事件

新增事件类型：

- `factory:taskspec.updated`
- `factory:acceptance.updated`
- `factory:verification.updated`
- `factory:artifact.added`
- `factory:handoff.created`
- `factory:resumption.updated`
- `factory:budget.updated`
- `factory:executiontrace.updated`
- `factory:projectlead.updated`

规则：

- 事件只触发 query invalidation
- 不直接写 Zustand
- 服务端状态继续走 TanStack Query

---

# 12. 前端页面设计

## 12.1 Factory Dashboard
展示：
- 任务总数
- 进行中任务
- 自动通过率
- handoff 数量
- 最近失败任务
- runtime 健康状态
- 当前预算消耗
- 当前排队任务数

## 12.2 Issue 详情页
新增 Dark Factory 面板：
- Task Spec
- Acceptance
- Verification
- Artifacts
- Handoff
- Resumption
- Retry Timeline
- Budget
- Execution Trace

## 12.3 Project Lead 页面
展示：
- 项目扫描结果
- 阻塞 issue
- 重试过多 issue
- 无人领取 issue
- 建议 follow-up

## 12.4 Runtime Policy 页面
展示：
- 当前 runtime
- 允许模型
- protected paths
- allowed commands
- policy 版本
- sandbox 版本
- 预览环境配置

## 12.5 Execution Trace UI
展示：
- 当前阶段
- 当前动作
- 最近一次工具调用
- 当前 blocker
- 当前 retry 数
- 当前预算消耗
- 下一步计划

注意：只展示**执行轨迹摘要**，不展示原始模型 CoT。

---

# 13. Control Plane 逻辑

## 13.1 Intake 流程

输入来源：
- Multica issue 创建
- Webhook
- 手工触发

处理步骤：
1. 读取 issue 内容
2. 判断任务类型
3. 生成 `task spec`
4. 生成 `acceptance spec`
5. 计算风险等级
6. 计算预算和优先级
7. 选择模型与角色
8. 分配 sandbox 资源
9. 启动对应 workflow

## 13.2 Assignment Policy

- feature 低风险：`gpt-5.4 + glm-5.1 + qwen3-coder-next`
- feature 高风险：`gpt-5.4 + glm-5.1 + qwen3-coder-plus + deepseek-reasoner`
- bugfix 多次失败：增加 `deepseek-reasoner`
- research：`qwen3.6-plus + gpt-5.4`
- triage：`qwen3.6-flash + deepseek-chat`

## 13.3 Handoff Policy

满足任一条件则转人工：
- retry >= 4
- touched protected path
- scope expanded beyond task
- changed security/payment logic
- reviewer 判定 rollback 风险过高
- budget exhausted

## 13.4 Resumption Policy

恢复模式只有三种：

1. `resume_from_failed_gate`
   - 人工修复后，从失败关卡继续
   - 例如：Playwright 失败，人工修复后直接重跑 Playwright

2. `resume_from_replan`
   - 人工修改改变了任务范围或验收标准
   - 需要重新生成 task spec / acceptance spec

3. `manual_close`
   - 人工已完成任务，不再交回 AI

默认规则：

- 人工改动不改变目标和验收：`resume_from_failed_gate`
- 人工改动改变范围或目标：`resume_from_replan`
- 人工已完成并确认关闭：`manual_close`

## 13.5 Budget Policy

每个 Task 必须有预算字段：

- `budget_limit_usd`
- `max_tokens_per_run`
- `max_retries`
- `max_reasoner_calls`
- `max_lead_calls`

调度规则：

- 低风险任务优先使用低成本模型
- DeepSeek-Reasoner 仅在 retry >= 2 或高风险时启用
- 超预算时不再自动重试，转 handoff 或 pending review

## 13.6 Rate Limit Policy

按模型维度维护并发池：

- 每种模型有单独并发上限
- 按 API key 维度控制 RPM / TPM
- 超限任务进入排队队列，不直接失败
- 高优先级任务可抢占低优先级队列

## 13.7 Project Lead Scheduler

周期扫描：
- 超时未推进 issue
- 重试多次 issue
- 测试失败未处理 issue
- 已阻塞 issue

处理动作：
- 更新 lead-status
- 创建 follow-up
- 发提醒 comment
- 必要时触发 handoff

---

# 14. Workflow 设计

## 14.1 `feature-flow.ts`

1. 读取 issue
2. 生成 task spec
3. 生成 acceptance spec
4. 申请 writer lock
5. 创建 task branch + worktree
6. 创建 task container
7. 调用 Lead 规划
8. 调用 Executor 执行主流程
9. 调用 Coder 修改代码
10. 若涉及 UI，拉起 preview environment
11. 跑 typecheck/test/playwright
12. 若失败，生成 verification result
13. 由 Reasoner 根因分析
14. 回到 Executor 重试
15. 多次失败、预算耗尽或高风险命中则 Handoff
16. 成功后写回 artifacts + summary
17. 释放 lock、销毁容器、保留工件

## 14.2 `bugfix-flow.ts`

1. 读取 issue 与相关日志
2. 由 Analyst/Flash 先整理错误信息
3. 创建隔离环境
4. Coder 修复
5. 跑验证
6. 若失败 2 次以上，Reasoner 介入
7. GPT-5.4 决定继续自动修或转人工
8. 清理环境并落盘 artifacts

## 14.3 `refactor-flow.ts`

1. GPT-5.4 规划范围
2. 创建独立 branch/worktree/container
3. Coder-Plus 实现
4. 跑测试
5. GPT-5.4 审核
6. DeepSeek-Reasoner 二审
7. 若通过，交付

## 14.4 `research-flow.ts`

1. Qwen3.6-Plus 汇总资料
2. DeepSeek-Chat 做结构化抽取
3. GPT-5.4 输出结论与后续行动建议

---

# 15. 验证闭环

## 15.1 必跑关卡
- format
- lint
- typecheck
- unit
- integration（按任务需要）
- Playwright E2E（UI 变更任务必跑）

## 15.2 失败处理
失败时必须生成：
- `verification result`
- stderr
- git diff
- screenshot
- trace
- next_hint
- 当前预算消耗
- 当前阶段摘要

## 15.3 回流链
固定升级链：

1. `Qwen3.6-Flash` 整理失败日志
2. `Qwen3-Coder-Next` 再修
3. `DeepSeek-Reasoner` 做根因分析
4. `GLM-5.1` 继续执行修复
5. `GPT-5.4` 决定继续还是 handoff

---

# 16. 安全与治理

## 16.1 Protected Paths
默认禁止：
- `.env`
- `migrations/**`
- `infra/**`
- `scripts/prod/**`
- `~/.ssh/**`
- `/etc/**`

## 16.2 Allowed Commands
允许：
- `pnpm typecheck`
- `pnpm test`
- `pnpm lint`
- `pnpm playwright test`
- `go test ./...`
- `go build ./...`
- `git status`
- `git diff`

默认禁止：
- `curl *`
- `wget *`
- `nc *`
- `rm -rf *`
- 任意生产环境发布命令
- 任意 secrets 读取命令
- 任意外部下载并执行

## 16.3 包管理器安全规则

即使 package manager 被允许，也不代表任意脚本安全。

规则：

1. 默认安装依赖必须使用：
   - `pnpm install --ignore-scripts`
2. 若需要执行 install/postinstall 脚本：
   - 必须显式审批
   - 或仅在高隔离容器中运行
3. 不允许 agent 自由拼接 shell 安装命令

## 16.4 命令沙箱规则

优先使用结构化工具，不优先使用自由 bash。

例如优先：
- `run_typecheck()`
- `run_unit_tests()`
- `run_playwright()`
- `start_preview_server()`

而不是任意字符串形式 shell。

## 16.5 Shell 静态检查

每次执行 shell 前必须做静态扫描，阻止：

- 网络请求命令
- 敏感文件读取
- 危险删除
- 外部下载执行
- 未批准的长驻后台进程

## 16.6 网络策略

容器默认：
- 无外网
- 如需安装依赖，仅允许白名单镜像源
- 如需访问测试 API，仅允许白名单域名

## 16.7 人工接管
必须保留人工 gate：
- 最终高风险发布
- 涉及支付/安全/权限系统
- 核心路径大范围重构
- 触碰受保护目录
- 超预算后继续推进

---

# 17. 修改说明

## 17.1 `CLAUDE.md`
追加章节：
- `## Dark Factory Rules`
- `## Task Spec Contract`
- `## Acceptance and Verification`
- `## Handoff Conditions`
- `## Resumption Conditions`
- `## Budget and Rate Limit`
- `## Sandbox and Command Policy`
- `## Artifact Requirements`

## 17.2 `package.json`
新增脚本：
- `df:control`
- `df:build`
- `df:seed`
- `df:e2e`
- `df:verify`

## 17.3 `docker-compose.selfhost.yml`
新增：
- `control-plane` service
- `runtime_artifacts` volume
- 可选 `preview-network` 与 `sandbox-worker` 相关配置

---

# 18. 开发顺序

## 第一周
目标：跑通最小闭环和隔离骨架

1. Fork 并跑通 Multica
2. 新建 `control-plane/`
3. 新建 `task-templates/`
4. 新建 `policies/`
5. 后端增加 task-spec API
6. 前端显示 Task Spec Panel
7. 引入 worktree + container 骨架
8. 写第一条 E2E：issue → task spec 可见

## 第二周
目标：打通验证、预览环境与工件

1. 增加 verification API
2. 增加 artifact API
3. 增加 preview-manager
4. 接入 Playwright 报告
5. 写第二条 E2E：verification 失败展示

## 第三周
目标：打通 handoff 与恢复

1. 增加 handoff API
2. 增加 resumption API
3. 前端增加 Handoff Panel
4. 前端增加 Resumption Panel
5. 写第三条 E2E：命中规则后人工接管
6. 写第四条 E2E：人工处理后恢复

## 第四周
目标：Project Lead、预算、执行轨迹

1. 增加 project-lead scheduler
2. 增加 Project Lead 页面
3. 接入 model-routing.yaml
4. 接入 budget/rate-limit policy
5. 增加 Execution Trace UI
6. 写第五条 E2E：scan 后生成 follow-up / lead 状态

---

# 19. DoD（完成定义）

以下全部满足才算第一阶段完成：

1. 可以在 self-host 环境正常运行
2. issue 创建后自动生成 task spec
3. issue 详情页可看到 task spec / acceptance
4. 至少一条 feature-flow 能跑到 verification
5. verification 失败会生成 artifacts 和 structured report
6. handoff 规则生效
7. resumption 规则生效
8. task 运行在独立 worktree + container
9. preview environment 可自动拉起并回收
10. budget / rate limit 策略已接入
11. project-lead scan 能产出结果
12. 至少 5 条 E2E 全通过

---

# 20. 直接给 Agent 的执行指令

```md
你正在一个 Multica fork 上开发 Dark Factory 功能。请遵守以下规则：

1. 不要重写现有 board、issue、comment、daemon 主体逻辑。
2. 基于现有 monorepo 分层开发：
   - server/ 放后端
   - packages/core/ 放 headless 逻辑
   - packages/views/ 放共享业务页面
   - packages/ui/ 放原子组件
   - apps/web/ 只做 route 挂载
3. 先创建以下新增目录：
   - control-plane/
   - task-templates/
   - policies/
   - runtime/
   - docs/darkfactory/
4. 第一阶段必须完成：
   - task spec API
   - acceptance API
   - verification API
   - artifact API
   - handoff API
   - resumption API
   - issue 详情页的 Task Spec / Verification / Handoff / Resumption 面板
   - 最少 5 条 e2e
5. 模型路由按以下角色：
   - GPT-5.4：Lead / Reviewer
   - GLM-5.1：Executor
   - Qwen3-Coder-Next：Coder
   - Qwen3-Coder-Plus：High-risk Coder
   - DeepSeek-Reasoner：Root Cause
   - DeepSeek-Chat：Analyst
   - Qwen3.6-Plus：Long Context Worker
   - Qwen3.6-Flash：Bulk Worker
6. 任何服务端状态必须走 Query，不允许复制到 Zustand。
7. WebSocket 事件只做 invalidation，不允许直接写 store。
8. 每个 Task 必须运行在独立 git worktree + 独立容器中。
9. UI 任务必须自动拉起 preview environment，再跑 Playwright。
10. 任何 shell 命令都必须经过 command policy 检查。
11. 默认依赖安装使用 `pnpm install --ignore-scripts`。
12. 每完成一个大步骤，输出：
   - 已创建/修改文件清单
   - 当前未完成项
   - 本地验证结果
13. 先完成最小闭环，再做 project-lead 和 execution trace。
```

---

# 21. 执行建议

先让 agent 做这条顺序：

**跑通 Multica → 新增 control-plane → 打通 task spec → 打通隔离执行 → 打通 verification → 打通 handoff/resumption → 最后做 project-lead、预算和执行轨迹。**
