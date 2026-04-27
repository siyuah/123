# Paperclip × Dark Factory V3.0 / V3.1 开发进度交接文档

状态: Informative / Non-binding / Out-of-bundle handoff
适用基线: Paperclip × Dark Factory V3.0 `agent-control-r1`
protocolReleaseTag: `v3.0-agent-control-r1`
生成时间: 2026-04-27T23:17:20+08:00

---

## 1. 当前总进度结论

当前工作已经从 **V3.0 release-gated bundle 收尾** 推进到 **V3.1 / Paperclip upstream 集成 POC 阶段**。

简要判断：

1. `/home/siyuah/workspace/123` 已完成 V3.0/V3.1 文档整理的主体收尾。
2. V3.0 binding artifacts 没有被未来开发文档污染；新增规划资料已隔离在 `3.0/future_development/`。
3. `3.0/future_development/` 的文档均属于 informative / non-binding / out-of-bundle，不改变 `v3.0-agent-control-r1`。
4. 本地 `123` 仓库当前在 `main`，相对 `origin/main` 已有本地提交领先；本交接文档也应作为 informative 文档上传到 `siyuah/123`。
5. Paperclip upstream 的 Dark Factory bridge plugin POC 已进入 PR 阶段；当前重点不是 V3.0 协议再设计，而是 PR review / CI / PR description 收尾。

---

## 2. `/home/siyuah/workspace/123` 当前状态

最近一次只读检查结果：

```text
repo: /home/siyuah/workspace/123
branch: main
status: ## main...origin/main [ahead 2]
working tree: clean
recent commits:
  ada9b7e Classify V3 future development docs as out-of-bundle
  5c0205a Classify GPT-5.5 handoff command in V3 manifest
  4f7786e Add Hermes GPT-5.5 handoff command
```

说明：

- `ahead 2` 表示已有两个本地文档/manifest 分类提交尚未同步到远端。
- 当前工作树在生成本交接文档前是干净的。
- 新增的 future-development 文档已归入 `paperclip_darkfactory_v3_0_bundle_manifest.yaml` 的 `informativeOutOfBundle`。
- `3.0/future_development/*.md` 不应进入 manifest 的 release-gated `files:` binding 清单。

---

## 3. 已完成的 V3.0/V3.1 文档整理

### 3.1 新增隔离目录

已新增：

```text
3.0/future_development/
```

该目录用于承接下一阶段开发文档，不属于 V3.0 release-gated bundle。

现有核心文件：

```text
3.0/future_development/README.md
3.0/future_development/PAPERCLIP_UPSTREAM_INTEGRATION_PLAN.md
3.0/future_development/NEXT_DEVELOPMENT_TASKS.md
3.0/future_development/HERMES_GPT55_EXECUTION_COMMANDS.md
```

本文件也是该目录下的交接文档，规范地位同样是 informative / non-binding / out-of-bundle。

### 3.2 已更新入口与 manifest

已更新或确认：

```text
README.md
3.0/V3_IMPLEMENTATION_ENTRYPOINT.md
paperclip_darkfactory_v3_0_bundle_manifest.yaml
```

主要目的：

- 给 `3.0/future_development/` 建立清晰入口；
- 明确 future-development 文档不改变 V3.0 binding baseline；
- 将新增规划文档登记到 `informativeOutOfBundle`；
- 避免 future-development 文档进入 release-gated `files:` 清单。

---

## 4. V3.0 binding 边界

后续任何开发都必须继续保留以下边界：

1. V3.0 `agent-control-r1` 是当前 binding baseline。
2. `3.0/future_development/` 只承接 informative planning / handoff / backlog。
3. 不把 V3.1 backlog 的候选语义暗改进 V3.0 binding artifacts。
4. 不把 Phoenix Runtime 写成第二套 Paperclip control plane。
5. 不把 MemorySidecar 字段塞进 Paperclip Task / Issue 主模型。
6. 不让 Bridge / Adapter / plugin DB 成为第二 truth source。
7. Dark Factory Journal 仍是执行事实来源。
8. 不创建、不移动 release tag；不创建或修改 GitHub Release，除非用户明确授权。

---

## 5. Paperclip upstream plugin POC 当前状态

Paperclip upstream 仓库：

```text
repo: /home/siyuah/workspace/paperclip_upstream
branch: dark-factory-bridge-plugin-poc
tracking: fork/dark-factory-bridge-plugin-poc
working tree: clean
PR: https://github.com/paperclipai/paperclip/pull/4591
```

当前分支最近提交：

```text
fc5a4f38 fix(plugins): address Dark Factory bridge review comments
264e0ef5 fix(plugins): align Dark Factory projection metadata
c7161115 feat(plugins): add mock Dark Factory bridge projection POC
```

PR 变更范围仍限制在：

```text
packages/plugins/examples/paperclip-dark-factory-bridge-plugin/
```

当前 PR diff 规模：

```text
12 files changed, 958 insertions(+)
```

### 5.1 已实现的 POC 语义

POC 目标是 Paperclip 插件形式的 Dark Factory bridge/projection 示例，不是 upstream core 改造。

已覆盖方向：

- dashboard widget：展示 provider/runtime/degraded health；
- detail tab：展示 linked run、journal cursor、projection status、callback receipt；
- mock API routes：projection、journal cursor、provider health、rehydrate request；
- namespace DB migration：只存 projection/cache/cursor/receipt/request metadata；
- UI disclaimer：明确 projection-only；
- tests：覆盖 manifest、routes、projection truth metadata、rehydrate receipt、disclaimer 等。

必须保持的语义：

```text
source: "dark-factory-projection"
authoritative: false
truthSource: "dark-factory-journal"
terminalStateAdvanced: false
```

### 5.2 Greptile / review 修复点

已在本地确认的 P2 修复方向：

1. `issueId` 在 route params 中已做 guard 校验，避免 `.slice()` TypeError。
2. `receiptId` 已改为 deterministic，和稳定 `idempotencyKey` 语义一致。
3. `journal_cursors` 已增加 `(company_id, issue_id)` unique index。
4. 测试从 worker import `PROJECTION_DISCLAIMER`，避免字符串漂移。

### 5.3 当前未完全关闭的问题

PR #4591 仍需收尾：

1. GitHub Checks 公开页面显示 `verify` 和 `e2e` 失败，但未登录无法看到完整 failed logs。
2. PR description 仍可能未完全符合 `.github/PULL_REQUEST_TEMPLATE.md`，需要网页手动替换为完整 Markdown。
3. 不应在没有完整 CI 日志时猜测 root cause，也不应随意修改 lockfile/workflow。

---

## 6. 建议下一步

### 6.1 对 `siyuah/123`

1. 上传本地领先提交和本交接文档到 `https://github.com/siyuah/123`。
2. 上传前必须运行：

```bash
cd /home/siyuah/workspace/123
make manifest-v3
make validate-v3
python3 tools/validate_v3_bundle.py
git diff --check
rm -rf dark_factory_v3/__pycache__ tests/__pycache__ tools/__pycache__
git status -sb
```

3. 确认新增交接文档只在 `informativeOutOfBundle` 中，不进入 release-gated `files:` 清单。

### 6.2 对 upstream PR #4591

继续推进但不要混入 `123` 的 V3.0 binding 修改：

1. 复核 PR description，按 upstream PR template 完整填写。
2. 获取 GitHub Actions `verify` / `e2e` 的完整失败日志后再修复。
3. 如需修改 lockfile / workflow，必须先确认失败与 PR 变更直接相关。
4. 保持 POC 范围在 plugin example 目录，不修改 Paperclip Task / Issue 主模型。

---

## 7. 给下一位 Hermes + GPT-5.5 的复制命令

```text
请接手 Paperclip × Dark Factory 当前状态，先分别检查两个仓库：

1. /home/siyuah/workspace/123
   - git status -sb
   - git log --oneline --decorate --max-count=8
   - git diff --stat
   - 确认 3.0/future_development/*.md 均为 informative / non-binding / out-of-bundle
   - 确认这些文件只在 paperclip_darkfactory_v3_0_bundle_manifest.yaml 的 informativeOutOfBundle 中，不在 files binding 清单
   - 运行 make validate-v3、python3 tools/validate_v3_bundle.py、git diff --check
   - 不要 tag，不要创建或修改 GitHub Release

2. /home/siyuah/workspace/paperclip_upstream
   - git status -sb
   - git log --oneline --decorate --max-count=8
   - git diff --stat origin/master...HEAD
   - 继续复核 PR #4591: https://github.com/paperclipai/paperclip/pull/4591
   - 重点处理 PR description 和 GitHub Actions verify/e2e 失败日志
   - 不要修改 upstream master，不要把 plugin DB / bridge / adapter 写成 truth source
   - 不要修改 Paperclip Task / Issue 主模型
```

---

## 8. 当前交接结论

当前项目不是停在“设计讨论”阶段，而是已经进入：

```text
V3.0 release bundle 已稳定
→ V3.1 / future-development 文档已隔离
→ Paperclip upstream integration plan 已成形
→ Dark Factory bridge plugin POC 已提交 PR
→ 当前剩余工作是 PR 收尾、CI 日志定位、PR description 修正，以及后续 V3.1 runtime observability / MemorySidecar / PhoenixRecover 的非绑定规划落地
```

本文件仅作为交接和上传记录，不改变 V3.0 binding artifacts。
