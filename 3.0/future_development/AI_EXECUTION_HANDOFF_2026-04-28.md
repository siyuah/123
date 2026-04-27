# Paperclip × Dark Factory 产品主线 AI 执行交接文档

状态: Informative / Non-binding / Out-of-bundle execution handoff
适用基线: Paperclip × Dark Factory V3.0 `agent-control-r1`
protocolReleaseTag: `v3.0-agent-control-r1`
生成时间: 2026-04-28T03:26:00+08:00
目标读者: 下一位接手的 Hermes + GPT-5.5 / AI coding agent

---

## 0. 本文档的规范地位

本文档只用于后续 AI 接手执行，不是 V3.0 binding spec，不修改 V3.0 release-gated artifacts 的语义，也不创建新的 Paperclip control plane。

硬边界：

1. `/home/siyuah/workspace/123` 是 Paperclip × Dark Factory V3.0 协议、控制平面骨架、release gate 与后续规划文档仓库。
2. `/home/siyuah/workspace/paperclip_upstream` 是基于 upstream Paperclip 的产品代码底座。
3. V3.0 `agent-control-r1` 已固化；本文件不把 V3.1/Phoenix/MemorySidecar 候选语义暗改进 V3.0 binding artifacts。
4. Paperclip 是 control plane；Dark Factory / Phoenix Runtime 不是第二套 Paperclip control plane。
5. Dark Factory Journal 是执行事实来源；Bridge / Adapter / plugin DB 只能做 projection/cache/cursor/receipt，不能成为第二 truth source。
6. MemorySidecar 是 runtime sidecar；不要把 MemorySidecar 内部字段塞进 Paperclip Task / Issue 主模型。
7. 除非用户明确授权，不要 push 到 upstream `paperclipai/paperclip`，不要 push tag，不要创建/修改 GitHub Release，不要修改 GitHub default branch。
8. 不要读取、打印、提交 token、password、API key、connection string；如日志或文件中出现敏感值，只报告路径/类型并用 `[REDACTED]`。

---

## 1. 当前仓库状态快照

### 1.1 `siyuah/123` 文档与 V3 仓库

```text
local repo: /home/siyuah/workspace/123
remote: https://github.com/siyuah/123.git
branch: main
HEAD: a0e256f1014c3be847ca9a932d2dc8e91812f9da
origin/main: a0e256f1014c3be847ca9a932d2dc8e91812f9da
status before this document: ## main...origin/main
```

已存在 future-development 文档目录：

```text
3.0/future_development/README.md
3.0/future_development/PAPERCLIP_UPSTREAM_INTEGRATION_PLAN.md
3.0/future_development/NEXT_DEVELOPMENT_TASKS.md
3.0/future_development/HERMES_GPT55_EXECUTION_COMMANDS.md
3.0/future_development/DEVELOPMENT_HANDOFF_2026-04-27.md
```

这些文件已在 `paperclip_darkfactory_v3_0_bundle_manifest.yaml` 的 `informativeOutOfBundle` 中登记，不进入 release-gated `files:` binding 清单。

### 1.2 Paperclip 产品底座仓库

```text
local repo: /home/siyuah/workspace/paperclip_upstream
upstream remote: origin = https://github.com/paperclipai/paperclip.git
product fork remote: fork = https://github.com/siyuah/paperclip.git
current branch: dark-factory-product-main
HEAD: f831a025fc3f16097e5c332850ecbfc170811d09
tracking: fork/dark-factory-product-main
working tree: clean at last check
fork branch: siyuah/paperclip:dark-factory-product-main exists
fork branch sha: f831a025fc3f16097e5c332850ecbfc170811d09
fork default branch: master
fork visibility: PUBLIC
```

最近关键提交：

```text
f831a025 Productize Dark Factory bridge plugin baseline
  - latest product-main commit
  - only modifies pnpm-lock.yaml
  - makes product fork lockfile policy independent from upstream PR policy

e1fea933 Revert "chore: update lockfile for dark factory bridge plugin example"
a96d70a9 chore: update lockfile for dark factory bridge plugin example
fc5a4f38 fix(plugins): address Dark Factory bridge review comments
264e0ef5 fix(plugins): align Dark Factory projection metadata
c7161115 feat(plugins): add mock Dark Factory bridge projection POC
```

---

## 2. 已完成事项

### 2.1 V3.0 release / 文档边界

1. V3.0 RC1 release / tag / post-release verifier 相关工作已完成并稳定。
2. `3.0/future_development/` 已作为 future-development 工作区建立。
3. `PAPERCLIP_UPSTREAM_INTEGRATION_PLAN.md`、`NEXT_DEVELOPMENT_TASKS.md`、`HERMES_GPT55_EXECUTION_COMMANDS.md`、`DEVELOPMENT_HANDOFF_2026-04-27.md` 已作为 informative / non-binding / out-of-bundle 文档归档。
4. V3.0 binding artifacts 保持为 `agent-control-r1` 基线；future docs 不改变 protocol release tag。
5. manifest 已包含 future docs 的 `informativeOutOfBundle` 分类。

### 2.2 Paperclip upstream / product mainline

1. 已确认 upstream Paperclip 是可运行产品底座：React/Vite UI、Express API server、plugin system、Docker/Compose entrypoints 均存在。
2. 已实现 Dark Factory bridge plugin POC，路径为：

```text
packages/plugins/examples/paperclip-dark-factory-bridge-plugin/
```

3. 插件 POC 的原则：
   - dashboard widget 展示 runtime/provider/degraded health；
   - detail tab 展示 linked run、journal cursor、projection status、callback receipt；
   - mock API routes 提供 projection / cursor / provider health / rehydrate request；
   - namespace DB 只存 projection/cache/cursor/receipt/request metadata；
   - `rehydrate` 只返回 request/receipt，不代表终态成功；
   - projection 响应必须标记 `authoritative: false` 与 `truthSource: "dark-factory-journal"`。
4. 官方 upstream PR #4591 已存在，但官方 CI 曾因 upstream lockfile policy 出现 `ERR_PNPM_OUTDATED_LOCKFILE`；该问题不再阻塞用户自己的产品主线。
5. 用户已明确产品方向：开发自己的产品，不再让 upstream PR #4591 作为主线阻塞。
6. 产品分支 `dark-factory-product-main` 已推送到用户 fork `siyuah/paperclip`，并跟踪 `fork/dark-factory-product-main`。
7. 产品分支允许提交 `pnpm-lock.yaml`，因为这是用户自有产品分支，不受 upstream 普通 PR 的 lockfile 禁止策略约束。

---

## 3. 当前必须继续遵守的非目标

1. 不要把 PR #4591 的 upstream policy 当作产品主线 blocker。
2. 不要改 `origin` 指向；`origin` 应保持为 `paperclipai/paperclip`，用于后续 upstream sync。
3. 不要把 `fork` 改成 upstream；`fork` 应保持为用户产品远程 `siyuah/paperclip`。
4. 不要默认修改 `siyuah/paperclip` default branch；当前 default branch 仍是 `master`，是否切换到 `dark-factory-product-main` 需要用户单独授权。
5. 不要在没有验证的情况下启动 release/tag/default-branch 操作。
6. 不要把插件 DB、Paperclip issue model、Bridge projection 混成执行事实来源。

---

## 4. 接下来开发任务总览

### Phase A — 产品分支远端/CI 状态复核

目标：确认 `dark-factory-product-main` 已在 `siyuah/paperclip` 存在，检查 GitHub Actions 是否触发，记录失败/成功状态。

验收：

- 本地 `HEAD` 等于 `fork/dark-factory-product-main`。
- `gh api repos/siyuah/paperclip/branches/dark-factory-product-main` 返回同一 SHA。
- 如果 Actions 有运行，必须记录 workflow、status、conclusion、URL；若失败，只读查看失败日志，不猜测原因。

### Phase B — 产品分支本地验证

目标：重新跑产品分支最小可信验证，确认当前 checkout 可安装、插件可测试/构建。

建议命令：

```bash
cd /home/siyuah/workspace/paperclip_upstream
pnpm install --frozen-lockfile --ignore-scripts
pnpm --filter @paperclipai/plugin-dark-factory-bridge-example test
pnpm --filter @paperclipai/plugin-dark-factory-bridge-example typecheck
pnpm --filter @paperclipai/plugin-dark-factory-bridge-example build
```

验收：以上命令通过；如失败，必须先定位最小失败日志，不要盲目改 workflow 或 lockfile。

### Phase C — 本地产品启动 smoke test

目标：启动 Paperclip 产品 UI/API，验证本地产品底座可跑。

先读：

```text
doc/GOAL.md
doc/PRODUCT.md
doc/SPEC-implementation.md
doc/DEVELOPING.md
doc/DATABASE.md
AGENTS.md
```

建议步骤：

```bash
cd /home/siyuah/workspace/paperclip_upstream
pkill -f "paperclip" || true
pkill -f "tsx.*index.ts" || true
pnpm dev
```

另开检查：

```bash
curl -fsS http://localhost:3100/api/health
curl -fsS http://localhost:3100/api/companies
```

验收：

- API health 返回成功；
- UI 可通过 `http://localhost:3100` 访问；
- 如果 3100 被占用，按 repo/fork 说明使用自动端口或清理进程；
- 不要提交本地 DB/cache/build artifacts。

### Phase D — Docker/Compose 部署验证

目标：确认产品可通过 Docker/Compose 跑起来。

先读：

```text
Dockerfile
docker/docker-compose.yml
docker/docker-compose.quickstart.yml
doc/DOCKER.md
.env.example
```

验收：

- Compose 配置中的环境变量都使用示例或本地安全值；
- 不提交真实 secret；
- 容器启动后 `/api/health` 成功；
- 记录端口、服务名、必要 env、失败日志。

### Phase E — Dark Factory bridge plugin 从 mock POC 进入产品化

目标：把 mock projection POC 逐步扩展为产品可观测桥接层，但仍保持 Journal truth-source 边界。

推荐子任务：

1. 定义 plugin projection cache 的最小稳定 schema 与 migration。
2. 增加 journal replay/cursor reconciliation 的 mock-to-real adapter seam。
3. 增加同一 journal replay、duplicate callback、out-of-order callback、missing journal gap、cursor monotonicity、projection rebuild 测试。
4. 增加 UI 中 degraded/provider/circuit breaker 观测卡片。
5. 增加 operator-visible audit trail，但不把 terminal state 直接推进为成功。

验收：

- projection response 继续包含 `authoritative: false`；
- `truthSource` 继续是 `dark-factory-journal`；
- plugin DB 无 token/secret/provider key；
- Paperclip Task / Issue 主模型未被 MemorySidecar 或 runtime 内部字段污染。

### Phase F — V3.1 informative planning 后续落地

目标：继续在 `3.0/future_development/` 或 V3.1 roadmap 中记录下一阶段协议候选，不污染 V3.0 binding artifacts。

候选方向：

- provider health / circuit breaker observability schema；
- RunAttempt runtime metadata：`provider_role`、`model_role`、`failure_class`、`retryable`、`fallback_triggered`；
- MemorySidecar metadata schema / storage profile / KG edge schema / DiaryStore retention policy；
- PhoenixRecover restart smoke timeline；
- Bridge reconciliation cursor cross-system consistency tests；
- V2.9 companion-bound reference bundle 的 normativity metadata。

---

## 5. 给下一位 Hermes + GPT-5.5 的直接执行命令

复制以下整段给 Hermes + GPT-5.5：

```text
请接手 Paperclip × Dark Factory 产品主线。用户偏好中文报告。必须先检查状态再行动，不要读取/打印/提交任何 secret/token/password/API key/connection string；如发现敏感值只报告路径/类型并用 [REDACTED]。不要 push 到 paperclipai/paperclip upstream，不要 push tag，不要创建/修改 GitHub Release，不要修改 default branch，除非用户明确授权。

工作目录与边界：
1. /home/siyuah/workspace/123 是 V3.0 协议/release gate/未来规划文档仓库。V3.0 agent-control-r1 已固化。future_development 文档只允许 informative / non-binding / out-of-bundle。
2. /home/siyuah/workspace/paperclip_upstream 是用户产品代码底座。origin=https://github.com/paperclipai/paperclip.git 只用于 upstream sync；fork=https://github.com/siyuah/paperclip.git 是用户产品远程。产品主线分支是 dark-factory-product-main。

第一步：检查 123 仓库，不要修改 binding artifacts：
cd /home/siyuah/workspace/123
export PATH="$HOME/.local/bin:$PATH"
git status -sb
git branch --show-current
git rev-parse HEAD
git rev-parse origin/main
git log --oneline --decorate --max-count=6
python3 - <<'PY'
from pathlib import Path
import yaml, re
m=yaml.safe_load(Path('paperclip_darkfactory_v3_0_bundle_manifest.yaml').read_text())
info=set(m.get('informativeOutOfBundle', []) or [])
files={e['path'] for e in m.get('files', []) or []}
paths=sorted(str(p) for p in Path('3.0/future_development').glob('*.md'))
status_re=re.compile(r'状态:\s*Informative\s*/\s*Non-binding\s*/\s*Out-of-bundle|Status:\s*Informative\s*/\s*Non-binding\s*/\s*Out-of-bundle', re.I)
print('future_docs=', paths)
print('missing_from_informativeOutOfBundle=', [p for p in paths if p not in info])
print('present_in_binding_files=', [p for p in paths if p in files])
print('missing_status_triad=', [p for p in paths if not status_re.search(Path(p).read_text(encoding='utf-8'))])
PY

第二步：检查产品分支远端状态：
cd /home/siyuah/workspace/paperclip_upstream
git status -sb
git branch --show-current
git rev-parse HEAD
git rev-parse fork/dark-factory-product-main
git log --oneline --decorate --max-count=8
git remote -v
gh api repos/siyuah/paperclip/branches/dark-factory-product-main --jq '{name: .name, sha: .commit.sha, protected: .protected}'
gh repo view siyuah/paperclip --json nameWithOwner,defaultBranchRef,isFork,parent,pushedAt,visibility,url --jq '{nameWithOwner, defaultBranch: .defaultBranchRef.name, isFork, parent: .parent.nameWithOwner, pushedAt, visibility, url}'
gh run list -R siyuah/paperclip --limit 10 --json databaseId,workflowName,displayTitle,headBranch,headSha,status,conclusion,createdAt,url

第三步：运行产品分支最小验证；如果失败，停止并报告失败命令与最小日志，不要盲目修改 lockfile/workflow：
cd /home/siyuah/workspace/paperclip_upstream
pnpm install --frozen-lockfile --ignore-scripts
pnpm --filter @paperclipai/plugin-dark-factory-bridge-example test
pnpm --filter @paperclipai/plugin-dark-factory-bridge-example typecheck
pnpm --filter @paperclipai/plugin-dark-factory-bridge-example build

第四步：如果以上均通过，进入本地启动 smoke test。先读 AGENTS.md、doc/GOAL.md、doc/PRODUCT.md、doc/SPEC-implementation.md、doc/DEVELOPING.md、doc/DATABASE.md。然后启动：
cd /home/siyuah/workspace/paperclip_upstream
pkill -f "paperclip" || true
pkill -f "tsx.*index.ts" || true
pnpm dev

另开检查：
curl -fsS http://localhost:3100/api/health
curl -fsS http://localhost:3100/api/companies

最后用中文报告：
- 两个仓库的分支、HEAD、clean/dirty 状态；
- dark-factory-product-main 本地和 fork 是否同 SHA；
- GitHub Actions 当前状态和 URL；
- pnpm install/test/typecheck/build 是否通过；
- 本地启动 smoke test 是否通过；
- 是否发现 secret 风险；
- 下一步是否进入 Docker/Compose 验证或 bridge plugin 产品化。
```

---

## 6. 上传/维护本文档时的验证要求

如果修改本文档或新增 future-development 文档，必须：

1. 确认文档顶部包含 `Informative / Non-binding / Out-of-bundle` 状态。
2. 将路径加入 `paperclip_darkfactory_v3_0_bundle_manifest.yaml` 的 `informativeOutOfBundle`。
3. 不要加入 manifest `files:` release-gated 清单。
4. 运行：

```bash
cd /home/siyuah/workspace/123
make manifest-v3
make validate-v3
python3 tools/validate_v3_bundle.py
git diff --check
rm -rf dark_factory_v3/__pycache__ tests/__pycache__ tools/__pycache__
git status -sb
```

5. 如果 `paperclip_darkfactory_v3_0_consistency_report.json` / `.md` 只有 `checkedAt` 时间戳变化且验证已通过，可恢复这两个报告，避免噪声。
6. 提交时只包含本文档、manifest 必要分类变化，以及必要的 README/入口链接变化；不要混入 runtime/schema/test/release tag 变更。

---

## 7. 当前下一步建议

建议下一位 AI 先做 **Phase A + Phase B**：

1. 读取本文档和 `DEVELOPMENT_HANDOFF_2026-04-27.md`。
2. 复核 `siyuah/123` future docs 分类。
3. 复核 `siyuah/paperclip:dark-factory-product-main` 与本地 `f831a025fc3f16097e5c332850ecbfc170811d09` 是否一致。
4. 查看 fork Actions。
5. 重新运行 `pnpm install --frozen-lockfile --ignore-scripts` 与 plugin test/typecheck/build。
6. 通过后再进入本地 `pnpm dev` smoke test。

本文档本身不代表上述验证已经全部通过；它是下一位 AI 的执行入口与边界说明。
