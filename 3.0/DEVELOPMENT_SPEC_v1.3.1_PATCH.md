# DEVELOPMENT_SPEC v1.3.1 修订清单

## 目的

本文件是对 `DEVELOPMENT_SPEC_v1.3.md` 的 **P0 级修订补丁**。
目标不是重写整份文档，而是在正式交给 `hermes-agent + GPT-5.4` 大规模执行前，补齐会直接影响安全性、一致性和可执行性的关键缺口。

本补丁仅处理以下 6 个 P0 问题：

1. 禁止 `pnpm *` 通配符，改为精确命令白名单
2. 明确 Handoff → Resume 的 worktree / branch / commit 对齐机制
3. 为 Resume 增加 `resume_base_commit` 锚点
4. 增加 `awaiting_scope_approval` 状态与超时策略
5. 明确模型 fallback 映射表
6. 拆分 `setup_timeout` 与 `boot_timeout`

---

## 1. Allowed Commands 修订

### 问题

`pnpm *` 会破坏沙箱边界，允许 Agent 通过：
- `pnpm run ...`
- `pnpm exec ...`
- 任意 package.json script

绕过 `pnpm install --ignore-scripts` 的初衷。

### 修订要求

删除所有宽泛通配符：
- 禁止：`pnpm *`
- 禁止：`go *`
- 禁止：`git *`

仅允许精确命令白名单。

### 新的白名单建议

```yaml
allowed_commands:
  - pnpm install --ignore-scripts
  - pnpm test
  - pnpm build
  - pnpm typecheck
  - pnpm lint
  - go test ./...
  - go build ./...
  - git status
  - git diff
  - git rev-parse HEAD
  - git checkout <task-branch>
  - playwright test
```

### 文档改动位置

修改：
- `18.2 Allowed Commands`
- `policies/allowed-commands.yaml`

---

## 2. Handoff → Resume 的 Worktree / Git 对齐机制

### 问题

如果 Handoff 时执行 finally 清理并删除 worktree，那么人工在本地修复后 push 到 task branch，Resume 必须明确：
- 如何重建 worktree
- 从哪个 commit 恢复
- 如何避免覆盖人工修改

### 修订要求

新增统一规则：

#### Handoff 时
- 不立即永久删除 task branch
- worktree 可以清理，但必须保留：
  - `task_branch`
  - `latest_remote_commit`
  - `base_commit`
  - `handoff_reason`

#### Resume 时
必须显式执行：

```text
1. 读取 task branch
2. 拉取远端最新 commit
3. 用 latest task branch commit 重新创建 worktree
4. 将该 commit 记录为 resume_base_commit
5. 从 resume_base_commit 继续执行
```

### 状态对齐原则

- Handoff 前的本地工作目录不作为恢复依据
- Resume 必须以远端 task branch 最新 commit 为准
- AI 不得基于旧 worktree 快照恢复

### 文档改动位置

新增章节：
- `## Handoff to Resume Worktree Reconstruction`

修改：
- `6.5 Worktree Cleanup`
- `13.5 Handoff / Resume`
- `16.x Manual Intervention`

---

## 3. Resume Event / API 增加 Commit 锚点

### 问题

人工修复后如果没有新的 commit 锚点，AI 恢复执行时可能仍基于旧状态，导致：
- 覆盖人工修改
- 验证永远失败
- Git 状态错乱

### 修订要求

所有 Resume 相关事件和 API Payload 必须新增：

```json
{
  "resume_base_commit": "abc123...",
  "manual_resolution": "human fixed form validation bug"
}
```

### 新字段定义

- `resume_base_commit`: 人工完成修复后，允许 AI 恢复的最新 task branch commit
- `previous_base_commit`: 原任务开始时的基线 commit
- `resume_requested_by`: 发起恢复的人或系统

### API 修订

新增或修改：
- `POST /factory/issues/:id/resume`

请求体至少包含：
- `resume_base_commit`
- `resume_mode`
- `manual_resolution`

### 文档改动位置

修改：
- `9.6 Resume Event`
- `11 API 设计`
- `13.5 Resumption Policy`

---

## 4. Scope Change Pending 状态与审批超时策略

### 问题

Agent 申请扩大任务范围时，当前文档缺乏明确的中间状态。
此时任务既不能继续执行，也不属于 handoff，导致状态机断层。

### 修订要求

任务主状态增加：

```text
awaiting_scope_approval
```

### 状态定义

- `awaiting_scope_approval`：
  Agent 已提交 scope change request，等待人工审批

### 超时策略

每个 scope change request 必须包含：
- `created_at`
- `expires_at`
- `requested_scope_delta`
- `reason`

默认规则：
- 超过 `expires_at` 未审批 → 自动转 `handoff_required`
- 每个 task 增加：
  - `max_scope_changes: 2`
- 超过允许次数 → 直接 handoff

### 数据模型修订

为 `factory_scope_change_requests` 增加字段：
- `expires_at`
- `approved_by`
- `approved_at`
- `rejected_at`
- `status`

### 文档改动位置

修改：
- `10.1 ER 模型`
- `14.5 Scope Change Policy`
- `Task Status Machine`

---

## 5. 模型 Fallback 映射表

### 问题

熔断器只有 open/half-open/closed 还不够。
必须明确某角色某模型不可用时，任务如何降级，否则执行层会出现不同实现。

### 修订要求

在 `config/model-routing.yaml` 中新增：

```yaml
fallback_model:
  lead:
    primary: gpt-5.4
    fallback: glm-5.1
    fallback_requires_human_approval: true

  executor:
    primary: glm-5.1
    fallback: deepseek-chat
    fallback_requires_human_approval: false

  coder:
    primary: qwen3-coder-next
    fallback: qwen3-coder-plus
    fallback_requires_human_approval: false

  reviewer:
    primary: gpt-5.4
    fallback: deepseek-reasoner
    fallback_requires_human_approval: true

  root_cause:
    primary: deepseek-reasoner
    fallback: gpt-5.4
    fallback_requires_human_approval: false

  bulk_worker:
    primary: qwen3.6-flash
    fallback: qwen3.6-plus
    fallback_requires_human_approval: false
```

### 新规则

- Lead / Reviewer 降级时默认需要人工确认
- Bulk Worker / Analyst / Executor 可以自动降级
- 如果 primary 和 fallback 都 unavailable：
  - 进入 `paused_due_to_model_unavailable`
  - 等待恢复或人工处理

### 文档改动位置

修改：
- `4.3 Model Routing`
- `Circuit Breaker`
- `config/model-routing.yaml`

---

## 6. 拆分 setup_timeout 与 boot_timeout

### 问题

依赖安装、缓存恢复、构建准备和 Preview Server 启动不能共用一个超时。
否则冷启动任务会因为依赖安装慢而被误判为 preview 启动失败。

### 修订要求

将原先单一的 preview timeout 拆成两段：

```yaml
preview_lifecycle:
  setup_timeout_seconds: 180
  boot_timeout_seconds: 30
```

### 阶段定义

#### setup_timeout
涵盖：
- 容器创建
- worktree mount
- 缓存挂载
- 依赖安装
- 构建准备

#### boot_timeout
仅涵盖：
- Preview Server 进程启动
- 监听端口
- 健康检查通过

### 错误码

新增区分：
- `PREVIEW_SETUP_TIMEOUT`
- `PREVIEW_BOOT_TIMEOUT`
- `PREVIEW_HEALTHCHECK_FAILED`

### 文档改动位置

修改：
- `5.3 Preview Lifecycle`
- `5.4 Preview Timeout`
- `Playwright / Preview 错误码表`

---

## 7. 建议新增 Cancel / Abort API（P1，建议顺手补）

虽然这不在本次 6 个 P0 强制修订里，但建议一起补：

- `POST /factory/issues/:id/cancel`
- `POST /factory/runs/:id/abort`

这样人工发现方向完全错误时，可以主动停机，而不是等预算耗尽。

---

## 8. v1.3.1 最小改动清单

正式修订时，至少修改这些文件：

```text
DEVELOPMENT_SPEC_v1.3.md
policies/allowed-commands.yaml
config/model-routing.yaml
control-plane/src/policies/resumption-policy.ts
control-plane/src/policies/handoff-policy.ts
control-plane/src/policies/concurrency-policy.ts
control-plane/src/sandbox/worktree-manager.ts
control-plane/src/sandbox/preview-manager.ts
control-plane/src/api/resume.ts
control-plane/src/api/scope-change.ts
control-plane/src/api/cancel.ts
```

---

## 9. 开工前检查表

在正式把文档交给 agent 之前，必须确认：

- [ ] `pnpm *` 已彻底移除
- [ ] Resume API 已包含 `resume_base_commit`
- [ ] worktree 重建流程已写清楚
- [ ] 已新增 `awaiting_scope_approval` 状态
- [ ] 已增加 `max_scope_changes`
- [ ] 已补全 fallback 映射表
- [ ] 已拆分 `setup_timeout` / `boot_timeout`

如果以上任一项未完成，则不建议放开自动实现。

---

## 10. 最终建议

v1.3 已经足够好，不需要推翻。
正确做法是：

**先打一版 v1.3.1 的小修订补丁，再正式交给 hermes-agent + GPT-5.4 大规模执行。**

