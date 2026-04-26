# Future Development Workspace

状态: Informative / Non-binding / Out-of-bundle future-development workspace
适用基线: Paperclip × Dark Factory V3.0 `agent-control-r1`
protocolReleaseTag: `v3.0-agent-control-r1`
是否进入 V3.0 binding: 否

---

## 1. 用途

本文件夹用于承接 V3.0 release-gated bundle 之外的下一阶段开发文档、Paperclip upstream 集成计划、任务拆解和 Hermes + GPT-5.5 执行命令。

这里的内容默认是 **informative / out-of-bundle**：

- 不修改 V3.0 binding protocol contract；
- 不替代根目录 release-gated artifacts；
- 不改变 `v3.0-agent-control-r1`；
- 不把历史 V2.x 或 V3.1 backlog 的候选语义暗改进 V3.0；
- 不直接修改 `paperclipai/paperclip` upstream core。

## 2. 本目录文件

| 文件 | 用途 | 规范地位 |
| --- | --- | --- |
| `PAPERCLIP_UPSTREAM_INTEGRATION_PLAN.md` | Paperclip upstream 与 Dark Factory / Phoenix Runtime 的集成方向、层边界、风险与验收 | informative plan |
| `NEXT_DEVELOPMENT_TASKS.md` | 下一阶段开发文档，按 Phase / 子任务 / DoD 拆解 | informative execution plan |
| `HERMES_GPT55_EXECUTION_COMMANDS.md` | 可直接复制给 Hermes + GPT-5.5 的分阶段执行命令 | informative handoff commands |

## 3. 阅读顺序

1. 先读根目录 `README.md` 和 `3.0/V3_IMPLEMENTATION_ENTRYPOINT.md`，确认当前 V3.0 binding baseline。
2. 再读 `3.0/V3_1_BACKLOG_AND_IMPLEMENTATION_ROADMAP.md`、`3.0/runtime_policy.md`、`3.0/memory_sidecar.md`。
3. 最后读本目录三份文档，作为下一阶段开发任务输入。

## 4. 硬边界

后续执行本目录计划时必须保留以下边界：

1. Paperclip 是 control plane；Dark Factory / Phoenix Runtime 不是第二套 Paperclip control plane。
2. Bridge / Adapter 只做幂等投影、callback receipt、cursor reconciliation，不是第二 truth source。
3. Dark Factory Journal 是执行事实来源。
4. MemorySidecar 是 runtime sidecar，不把字段塞进 Paperclip Task 主模型。
5. Provider routing / fallback / circuit breaker / degraded mode 先作为 runtime policy 与观测能力推进；除非进入独立 V3.1 合同设计，否则不改 V3.0 binding artifacts。
