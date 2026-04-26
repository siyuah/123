# Hermes + GPT-5.5 Execution Commands

状态: Informative / Non-binding / Out-of-bundle handoff commands
适用基线: Paperclip × Dark Factory V3.0 `agent-control-r1`
protocolReleaseTag: `v3.0-agent-control-r1`
所在目录: `3.0/future_development/`
是否进入 V3.0 binding: 否

---

## 使用方式

把下面任一命令块完整复制给 Hermes + GPT-5.5。每个命令块都要求模型先检查仓库状态、读取指定文件、执行任务、运行验证、输出中文报告。

---

## 命令 0 — 接手 123 文档整理与验证

```text
[Workspace: /home/siyuah/workspace]
请接手 /home/siyuah/workspace/123 的 Paperclip × Dark Factory V3 文档整理任务。

必须先读取：
- /home/siyuah/workspace/123/README.md
- /home/siyuah/workspace/123/3.0/V3_IMPLEMENTATION_ENTRYPOINT.md
- /home/siyuah/workspace/123/3.0/V3_1_BACKLOG_AND_IMPLEMENTATION_ROADMAP.md
- /home/siyuah/workspace/123/3.0/future_development/README.md
- /home/siyuah/workspace/123/3.0/future_development/PAPERCLIP_UPSTREAM_INTEGRATION_PLAN.md
- /home/siyuah/workspace/123/3.0/future_development/NEXT_DEVELOPMENT_TASKS.md
- /home/siyuah/workspace/123/3.0/future_development/HERMES_GPT55_EXECUTION_COMMANDS.md
- /home/siyuah/workspace/123/paperclip_darkfactory_v3_0_bundle_manifest.yaml

任务：
1. 检查 git 状态与 HEAD/origin/main 差异。
2. 确认 3.0/future_development/ 下文件全部标注为 informative / out-of-bundle。
3. 确认这些文件已经列入 paperclip_darkfactory_v3_0_bundle_manifest.yaml 的 informativeOutOfBundle，而不是 files release-gated 清单。
4. 运行 make manifest-v3 和 make validate-v3。
5. 清理 __pycache__。
6. 如果 consistency report 只发生 checkedAt/timestamp 变化，请恢复 report 文件；如果有实质变化，解释原因。
7. 输出中文报告：改动文件、验证结果、当前 git status、下一步建议。

硬边界：
- 不修改 V3.0 binding protocol contract 语义。
- 不创建 tag，不创建 GitHub Release，不 push。
- 不把 MemorySidecar 字段塞进 Paperclip Task 主模型。
- 不让 Bridge / Adapter 成为第二 truth source。
```

---

## 命令 1 — 生成 Paperclip plugin POC 设计，不改 upstream core

```text
[Workspace: /home/siyuah/workspace]
请基于 /home/siyuah/workspace/123/3.0/future_development/PAPERCLIP_UPSTREAM_INTEGRATION_PLAN.md 和 /home/siyuah/workspace/123/3.0/future_development/NEXT_DEVELOPMENT_TASKS.md，进入 /home/siyuah/workspace/paperclip_upstream 做 Paperclip plugin POC 设计检查。

必须先只读检查：
- /home/siyuah/workspace/paperclip_upstream/packages/plugins/examples/plugin-hello-world-example/src/manifest.ts
- /home/siyuah/workspace/paperclip_upstream/packages/plugins/examples/plugin-orchestration-smoke-example/src/manifest.ts
- /home/siyuah/workspace/paperclip_upstream/server/src/services/plugin-host-services.ts
- /home/siyuah/workspace/paperclip_upstream/ui/src/api/plugins.ts
- /home/siyuah/workspace/paperclip_upstream/docker/docker-compose.yml
- /home/siyuah/workspace/paperclip_upstream/.github/workflows/pr.yml

任务：
1. 检查 paperclip_upstream git 状态，确认是否在 master/origin/master。
2. 不修改 upstream core，先输出 plugin POC 文件落点建议。
3. 设计插件 paperclip-dark-factory-bridge-plugin 的 manifest、API routes、dashboard widget、task detail tab、namespace DB schema。
4. 明确 projection/cache/cursor/receipt 不是 truth source。
5. 输出需要创建/修改的具体文件路径、验收命令、风险和 stop point。

硬边界：
- 本轮只做设计检查和文件落点建议，除非明确授权，不创建文件。
- 不改 Paperclip Task 主模型。
- 不把 Dark Factory Journal 事实复制成 Paperclip truth。
```

---

## 命令 2 — 创建 Paperclip plugin POC 分支并实现 mock projection

```text
[Workspace: /home/siyuah/workspace]
请在 /home/siyuah/workspace/paperclip_upstream 创建隔离分支并实现 Paperclip Dark Factory bridge plugin POC 的 mock projection 版本。

前置读取：
- /home/siyuah/workspace/123/3.0/future_development/PAPERCLIP_UPSTREAM_INTEGRATION_PLAN.md
- /home/siyuah/workspace/123/3.0/future_development/NEXT_DEVELOPMENT_TASKS.md
- Paperclip plugin examples 和 plugin host service 相关文件

执行要求：
1. git status -sb，确认无未解释改动。
2. 创建分支：dark-factory-bridge-plugin-poc。
3. 新增 paperclip-dark-factory-bridge-plugin，优先放在现有 plugin examples 或仓库约定位置。
4. 实现 mock routes：
   - GET /issues/:issueId/dark-factory/projection
   - GET /issues/:issueId/dark-factory/journal-cursor
   - GET /issues/:issueId/dark-factory/provider-health
   - POST /issues/:issueId/dark-factory/rehydrate-request
5. 实现最小 dashboard widget / task detail tab，展示 linked Run id、journal cursor、projection status、callback receipt、degraded/blocked/needs approval、provider health。
6. 不连接真实 Dark Factory，不读取 secret，不写 token。
7. 运行仓库现有 typecheck/test/build 命令；如果命令不可用，先检查 package scripts 并报告实际可用命令。
8. 输出中文报告：新增文件、验证结果、未完成项、下一步。

硬边界：
- 不改 Paperclip Task 主模型。
- 不改 upstream master，必须在隔离分支。
- plugin namespace DB 只保存 projection/cache/cursor/receipt，不保存 truth。
```

---

## 命令 3 — Bridge / Adapter 一致性测试计划与最小测试

```text
[Workspace: /home/siyuah/workspace]
请为 Paperclip Dark Factory bridge plugin POC 增加 Bridge / Adapter 一致性测试计划与最小测试。

读取：
- /home/siyuah/workspace/123/3.0/future_development/PAPERCLIP_UPSTREAM_INTEGRATION_PLAN.md
- /home/siyuah/workspace/123/3.0/future_development/NEXT_DEVELOPMENT_TASKS.md
- 当前 paperclip_upstream plugin POC 文件

任务：
1. 定义 projection/cursor/receipt 的最小 contract，不进入 Paperclip Task 主模型。
2. 增加测试覆盖：
   - same journal replay idempotency
   - duplicate callback receipt
   - out-of-order callback
   - missing journal gap
   - cursor monotonicity
   - projection rebuild from zero
3. 每个测试都要断言 Bridge 不能在无 journal 依据时推进 terminal success。
4. 运行对应 test/typecheck。
5. 输出中文报告：测试文件、覆盖场景、失败/通过结果、剩余风险。

硬边界：
- Bridge / Adapter 不是 truth source。
- Projection 可以 stale，但不能伪装成 authoritative success。
```

---

## 命令 4 — V3.1 runtime observability proposal

```text
[Workspace: /home/siyuah/workspace]
请在 /home/siyuah/workspace/123 中新增或完善 V3.1 runtime observability 的 informative proposal，放在 3.0/future_development/ 下，不修改 V3.0 binding artifacts。

必须读取：
- README.md
- 3.0/V3_IMPLEMENTATION_ENTRYPOINT.md
- 3.0/V3_1_BACKLOG_AND_IMPLEMENTATION_ROADMAP.md
- 3.0/runtime_policy.md
- 3.0/future_development/PAPERCLIP_UPSTREAM_INTEGRATION_PLAN.md

任务：
1. 设计 provider health / circuit breaker observation proposal。
2. 设计 degraded mode operator projection / audit trail proposal。
3. 明确哪些字段只是 V3.1-alpha candidate，哪些未来可能触及 schema/OpenAPI/event/golden timeline。
4. 更新 paperclip_darkfactory_v3_0_bundle_manifest.yaml 的 informativeOutOfBundle。
5. 运行 make manifest-v3、make validate-v3，清理 __pycache__。
6. 输出中文报告。

硬边界：
- 不改 V3.0 binding protocol contract。
- 不写具体模型名为协议 MUST。
- 不创建 release tag / GitHub Release / push。
```

---

## 命令 5 — MemorySidecar 与 PhoenixRecover proposal

```text
[Workspace: /home/siyuah/workspace]
请在 /home/siyuah/workspace/123 中新增或完善 MemorySidecar / PhoenixRecover 的下一阶段 informative proposal，放在 3.0/future_development/ 下，不干扰 V3.0 binding bundle。

必须读取：
- README.md
- 3.0/V3_IMPLEMENTATION_ENTRYPOINT.md
- 3.0/memory_sidecar.md
- 3.0/V3_1_BACKLOG_AND_IMPLEMENTATION_ROADMAP.md
- 3.0/future_development/NEXT_DEVELOPMENT_TASKS.md

任务：
1. 设计 MemorySidecar storage profile proposal：metadata、scope、sensitivity、redaction_level、KG edge、DiaryStore retention、revocation/correction、PromptContextBuilder selection receipt。
2. 设计 PhoenixRecover smoke timeline proposal：runtime restart、sidecar reload、journal replay、projection consistency check、safe degraded recovery、operator warning。
3. 明确 memory 不覆盖 system/developer/user latest instruction，不覆盖 V3 binding artifacts，不覆盖 Dark Factory Journal。
4. 更新 manifest informativeOutOfBundle。
5. 运行 make manifest-v3、make validate-v3，清理 __pycache__。
6. 输出中文报告。

硬边界：
- 不把 MemorySidecar 字段塞进 Paperclip Task 主模型。
- 不把 memory 作为 truth source。
- 不保存或展示任何 secret/token/API key；如发现凭据，替换为 [REDACTED]。
```
