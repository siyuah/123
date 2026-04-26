# Paperclip Upstream Integration Plan

状态: Informative / Non-binding / Out-of-bundle integration plan
适用基线: Paperclip × Dark Factory V3.0 `agent-control-r1`
protocolReleaseTag: `v3.0-agent-control-r1`
所在目录: `3.0/future_development/`
是否进入 V3.0 binding: 否

---

## 1. 结论

当前最稳妥的开发方向是：**先在 123 仓库沉淀 informative 集成计划与验收边界，再以 Paperclip plugin / bridge projection 的方式做 POC，最后才评估 upstream-friendly contribution。**

不建议第一步直接修改 Paperclip upstream core，也不建议把 Dark Factory / Phoenix Runtime 的字段直接并入 Paperclip Task 主模型。原因是：

- Paperclip 负责用户可见的 control plane、approval、governance、task state；
- Dark Factory 负责 execution plane、Run、RunAttempt、Artifact、Journal、failure classification；
- Phoenix Runtime 负责 provider routing、fallback、circuit breaker、memory sidecar、recover；
- Bridge / Adapter 负责幂等投影、cursor、receipt 与 reconciliation。

四层边界清晰时，Paperclip 可以安全展示 Dark Factory 状态；边界混合时，会产生第二 truth source、状态漂移和审计不可解释。

---

## 2. 开发方向

### 2.1 Phase 0 — 文档与边界冻结

目标：把 V3.0 当前合同、V3.1 backlog、Paperclip upstream 集成方向整理成可执行文档。

产出：

- `3.0/future_development/PAPERCLIP_UPSTREAM_INTEGRATION_PLAN.md`
- `3.0/future_development/NEXT_DEVELOPMENT_TASKS.md`
- `3.0/future_development/HERMES_GPT55_EXECUTION_COMMANDS.md`
- README / manifest 中的 informative out-of-bundle 分类

禁止：

- 不修改 V3.0 core spec / schema / OpenAPI / event contracts 的语义；
- 不创建 release tag；
- 不创建 GitHub Release；
- 不把本目录文件加入 release-gated `files` 清单。

### 2.2 Phase 1 — Paperclip plugin POC

目标：在 Paperclip plugin 系统中实现最小可见集成，而不是改 core。

建议插件名：`paperclip-dark-factory-bridge-plugin`

最小能力：

- dashboard widget：展示 runtime/provider health 摘要；
- task detail tab：展示 linked Run id、journal cursor、projection status、callback receipt、degraded / blocked / needs approval；
- plugin API route：读取 Dark Factory projection / cursor / provider health；
- plugin namespace DB：只保存 projection/cache/cursor/receipt，不保存 truth。

建议 API：

```text
GET  /issues/:issueId/dark-factory/projection
GET  /issues/:issueId/dark-factory/journal-cursor
GET  /issues/:issueId/dark-factory/provider-health
POST /issues/:issueId/dark-factory/rehydrate-request
```

### 2.3 Phase 2 — Bridge / Adapter 一致性

目标：让 Paperclip 看到的状态能被 Dark Factory Journal 解释，且重复回放、乱序回调、网络分区不会产生错误推进。

必须覆盖：

- same journal replay idempotency；
- duplicate callback receipt；
- out-of-order callback；
- missing journal gap；
- cursor monotonicity；
- projection rebuild from zero；
- stale projection warning。

### 2.4 Phase 3 — Runtime observability

目标：把 provider health、circuit breaker、fallback、degraded mode 变成可观测状态，而不是散落在日志中的内部实现。

优先做 informative proposal，不直接合同化到 V3.0：

- provider role / model role，不写具体模型名；
- failure_class histogram；
- breaker state: `closed` / `open` / `half_open`；
- cooldownUntil / openReason / lastFailureAt / lastSuccessAt；
- degraded mode reason / scope / operator acknowledgement。

### 2.5 Phase 4 — MemorySidecar 独立化

目标：将长期记忆、KG、Diary、PromptContextBuilder、PhoenixRecover 保持为独立 runtime sidecar。

必须避免：

- 不把 MemorySidecar 字段塞进 Paperclip Task 主模型；
- 不把 memory 当成 system 指令或协议事实；
- 不让过期、撤销、低置信度或含敏感信息的 memory 进入 prompt；
- 不让 memory 覆盖 Dark Factory Journal。

### 2.6 Phase 5 — Upstream-friendly contribution

目标：在 POC 和一致性测试稳定后，评估哪些改动适合回馈 Paperclip upstream。

优先贡献：

- plugin 示例或文档；
- 外部执行系统 projection pattern；
- plugin API / dashboard extension 的通用增强；
- 不含 Dark Factory 私有语义的 adapter template。

不优先贡献：

- Dark Factory core protocol；
- Phoenix Runtime provider routing 细节；
- MemorySidecar 内部 schema；
- 特定组织治理策略。

---

## 3. 映射表

| Dark Factory / Phoenix 概念 | Paperclip 集成位置 | 边界 |
| --- | --- | --- |
| Run / RunAttempt | plugin detail tab / projection API | Paperclip 只展示，不成为 truth |
| Journal cursor | plugin namespace DB / status badge | cursor 可缓存，但事实来自 Journal |
| ArtifactRef / lineage | task detail extension / external link | 不改 Paperclip Task 主模型 |
| Provider health | dashboard widget | runtime observability，不写具体模型 MUST |
| Circuit breaker | dashboard / warning / audit view | 先 informative，不改 V3.0 binding |
| Degraded mode | operator warning / task detail badge | 不伪装成 full success |
| MemorySidecar | independent sidecar / optional projection | 不进入 Task 主模型 |
| PhoenixRecover | rehydrate request / recovery warning | 保守恢复，Journal 优先 |

---

## 4. 主要风险与控制

| 风险 | 表现 | 控制方式 |
| --- | --- | --- |
| 第二 truth source | Bridge 在无 journal 依据时推进状态 | 只允许 projection 派生；cursor 单调；rebuild from zero |
| Task 模型污染 | provider/memory/retry 字段进入 Paperclip Task 主模型 | 使用 plugin tab / projection / sidecar |
| 降级伪成功 | degraded 输出被当成完整成功 | operator badge、audit trail、report summary |
| provider 语义锁死 | 具体模型名成为协议 MUST | 使用 provider role / model role |
| 回调重复或乱序 | terminal success 被重复触发或提前触发 | idempotency key、receipt、sequence validation |
| memory 污染 prompt | 过期或撤销记忆注入 | TTL、revocation、confidence、sensitivity、receipt |
| upstream 难以接受 | core 改动过大 | 先 plugin POC，再抽通用 extension pattern |

---

## 5. 验收原则

1. `make validate-v3` 通过。
2. 新增文件均在 `informativeOutOfBundle` 分类中，不进入 V3.0 release-gated `files`。
3. Paperclip POC 至少通过 typecheck/test/build。
4. Bridge 一致性测试至少覆盖重复、乱序、gap、rebuild、cursor monotonicity。
5. 所有 operator-visible state 都能追溯到 journal、receipt 或明确的 runtime observation。
