# V3.1 Backlog and Implementation Roadmap

状态: informative roadmap / backlog
适用基线: Paperclip × Dark Factory V3.0 `agent-control-r1`
protocolReleaseTag: `v3.0-agent-control-r1`

---

## 1. 目的与边界

本文把 V3 文档收敛层中已经识别的下一阶段事项整理为 **V3.1 backlog 与实施路线图**。它用于规划 V3.1-alpha / V3.1-beta / V3.1-rc 的 schema、OpenAPI、event contract、golden timeline、traceability、docs 与 tests 工作。

本文不是 V3.0 binding spec，不替代以下 V3.0 release-gated artifacts：

- `paperclip_darkfactory_v3_0_invariants.md`
- `paperclip_darkfactory_v3_0_core_spec.md`
- `paperclip_darkfactory_v3_0_core_objects.schema.json`
- `paperclip_darkfactory_v3_0_event_contracts.yaml`
- `paperclip_darkfactory_v3_0_external_runs.openapi.yaml`
- `paperclip_darkfactory_v3_0_memory.openapi.yaml`
- `paperclip_darkfactory_v3_0_state_transition_matrix.csv`
- `paperclip_darkfactory_v3_0_runtime_config_registry.yaml`
- `paperclip_darkfactory_v3_0_test_traceability.csv`
- `tests/golden_timelines/v3_0/*.jsonl`

V3.0 `agent-control-r1` **保持不变**。任何进入 V3.1 的候选事项，必须先明确是否触及 binding artifacts；如果触及，需要在独立 V3.1 设计、测试和 release gate 中同步推进，不能在 V3.0 文档中暗改合同。

额外边界：Phoenix Runtime 不是第二套 Paperclip control plane；MemorySidecar 字段不得塞进 Paperclip Task 主模型；Bridge / Adapter 不得成为第二 truth source；具体模型名不得写成协议 MUST。

---

## 2. 优先级与阶段定义

| 优先级 | 含义 | 推荐处理方式 |
| --- | --- | --- |
| P0 | 若不处理，会导致运行时不可观测、恢复不可验收或协议扩展边界不清 | V3.1-alpha 先写 schema/test proposal，再进入 beta 实现 |
| P1 | 影响 operator 使用、跨系统一致性或治理审计，但可在 P0 稳定后推进 | V3.1-beta 建立 UI / audit / reconciliation 验收 |
| P2 | 历史资料治理和长期可维护性，通常不改变当前 runtime 行为 | V3.1-rc 或并行文档归档任务 |

| 阶段 | 目标 | 出口条件 |
| --- | --- | --- |
| V3.1-alpha | 明确候选合同面、字段边界、示例与失败模式 | draft schema / OpenAPI / event proposal、至少一个 failing contract test 或 golden timeline 草案 |
| V3.1-beta | 将已批准合同面落入实现、文档和 release gate | 通过新增 tests，traceability 覆盖新增 release blockers |
| V3.1-rc | 稳定兼容、迁移和归档规则 | manifest / release readiness / docs 完整，V3.0 兼容边界清晰 |

---

## 3. P0 backlog

### P0-1. Provider health 与 circuit breaker 可观测性 schema

**背景**
`3.0/runtime_policy.md` 已定义 circuit breaker 状态 `closed` / `open` / `half_open`，并建议记录最近成功时间、最近失败时间、failure_class 分布和 open reason。V3.0 binding assets 已有 provider failure、route decision、cutover 与 runtime config，但 provider health 的观测记录还没有独立可执行 schema。

**不做的风险**
实现团队可能只在日志中记录熔断状态，导致 release gate 无法验证 provider 是否被正确熔断、是否安全 half_open 探测、是否因错误 failure_class 触发 fallback。operator 也无法区分 provider 故障、quota、auth 与全局降级。

**建议变更范围**
新增 provider health / circuit breaker observation schema，定义 provider role、task_type、state、openedAt、lastSuccessAt、lastFailureAt、failure_class histogram、openReason、probe policy、cooldownUntil、recovery decision。该 schema 应绑定 provider role 和 model role，而不是具体模型名。

**是否触及 binding artifacts**
候选触及。若进入 V3.1 合同，需要新增或扩展 schema / event contracts / OpenAPI / runtime config registry / golden timelines；V3.0 不变。

**需要同步更新的文件类型**
schema、OpenAPI、event contracts、runtime config registry、golden timeline、traceability、docs、tests。

**验收方式**
注入连续 `transient_provider` / `provider_unavailable`，验证 breaker `closed → open → half_open → closed/open` 记录可回放；确认 open 状态不再发送普通请求；确认 half_open 只运行低风险探测；确认 `provider_auth` 不被盲目 retry。

**推荐阶段**
V3.1-alpha。

### P0-2. RunAttempt runtime metadata 合同化边界

**背景**
`runtime_policy.md` 建议 RunAttempt / attempt metadata / journal event 可记录 `provider_role`、`model_role`、`failure_class`、`retryable`、`fallback_triggered`、`attempt_index`、`circuit_breaker_state`、`degraded_mode`。V3.0 core spec 当前已有 `RouteDecision`、`ProviderFailureRecord` 和 `providerFaultClass → recoveryLane`，但这些 runtime 字段是否进入 binding contract 仍需 V3.1 判定。

**不做的风险**
不同实现可能分别把字段写在日志、projection、provider adapter 或 Task 扩展字段里，导致审计口径不一致；fallback 后产物无法可靠关联到 attempt；release readiness 只能验证主协议，不知道 runtime policy 是否真正执行。

**建议变更范围**
先定义 RunAttempt runtime metadata proposal，区分 required、recommended、implementation-private 三层。优先合同化 provider role、failure_class、retryable、fallback_triggered、attempt_index；model_role 只作为能力抽象，不允许写成具体模型名；不得把这些字段塞进 Paperclip Task 主模型。

**是否触及 binding artifacts**
候选触及。若 required 字段进入 V3.1，需要同步 core object schema、event contracts、external runs OpenAPI、journal reducer/projection、golden timelines 和 traceability。

**需要同步更新的文件类型**
schema、OpenAPI、event contracts、golden timeline、traceability、docs、tests。

**验收方式**
构造 retry / fallback / invalid_request / quota_exceeded 场景，断言每个 RunAttempt metadata 均可回放、字段不含 secret、不含具体模型 MUST，并能解释最终 recovery lane。

**推荐阶段**
V3.1-alpha。

### P0-3. MemorySidecar metadata schema、storage profile、KG edge schema 与 DiaryStore retention policy

**背景**
`3.0/memory_sidecar.md` 已定义 AutoExtractor、SessionMemory、MemorySync、LongTermMemory、KnowledgeGraph、DiaryStore、PromptContextBuilder、PhoenixRecover 的边界，并列出 metadata 建议字段。V3.0 memory binding assets 已要求 MemoryArtifact、PromptInjectionReceipt、consent scope 与 retention policy，但 sidecar 内部 metadata、KG edge 和 DiaryStore retention 仍是 informative 设计。

**不做的风险**
记忆可能被实现为不可审计黑盒：过期记忆继续注入、KG 边缺少 source/confidence、DiaryStore 混入 secret 或临时任务进度、session memory 被误升格为 long-term memory。恢复后还可能把历史上下文误当成 system 指令。

**建议变更范围**
建立独立 MemorySidecar schema / OpenAPI 或 storage profile，覆盖 metadata、scope、sensitivity、redaction_level、KG edge、DiaryStore retention、revocation / correction、PromptContextBuilder selection receipt。保持 MemorySidecar 是 runtime sidecar，不改变 Paperclip Task 主模型，不替代 Dark Factory Journal。

**是否触及 binding artifacts**
候选触及。若 V3.1 将 sidecar metadata 与 receipt 合同化，需要更新 memory OpenAPI、schema、event contracts、runtime config、golden timelines 和 traceability；V3.0 Task 主模型不变。

**需要同步更新的文件类型**
schema、OpenAPI、event contracts、runtime config registry、golden timeline、traceability、docs、tests。

**验收方式**
新增 memory extract / sync / kg / diary / inject / recover 测试：验证 source、confidence、ttl、scope、sensitivity、redaction_level；覆盖 denied / redacted / allowed 三类 injection timeline；验证 revoked/expired memory 不再注入。

**推荐阶段**
V3.1-alpha。

### P0-4. PhoenixRecover 重启恢复 smoke test / golden timeline

**背景**
`memory_sidecar.md` 已把 PhoenixRecover 定位为重启后恢复必要上下文、检查同步完整性、避免失忆或错误注入。V3.0 golden timelines 覆盖 manual park / rehydrate、routing、lineage、memory denied、repair，但尚未覆盖 runtime 重启后的 memory / journal / projection 恢复 smoke。

**不做的风险**
运行时重启后可能丢失必要 sidecar 状态、重复注入过期 memory、断开 attempt linkage、或在 journal/projection 未一致时继续执行。该类问题往往只在生产恢复场景暴露，难以后验证明。

**建议变更范围**
新增 PhoenixRecover smoke test 与 golden timeline，描述 runtime restart、sidecar reload、journal replay、projection consistency check、safe degraded recovery 和 operator warning。重点验证恢复路径保守、安全、可审计，而不是追求无条件继续执行。

**是否触及 binding artifacts**
候选触及测试与事件样例。如果只新增 informative smoke 文档，不触及 V3.0；若成为 V3.1 release blocker，则需新增 golden timeline、traceability 和可能的 event contracts。

**需要同步更新的文件类型**
golden timeline、event contracts、traceability、docs、tests；必要时 schema / OpenAPI。

**验收方式**
模拟 runtime 重启：先写入 long-term memory、KG edge、DiaryStore summary 与 journal event，再重启加载；断言过期 session memory 不被当作长期事实，损坏 sidecar 进入保守恢复并告警，journal truth 优先级高于 memory。

**推荐阶段**
V3.1-alpha。

---

## 4. P1 backlog

### P1-1. Degraded mode operator UI 与 audit trail

**背景**
`runtime_policy.md` 要求 degraded mode 只能作为运行可用性策略，不能伪装为完整成功；进入 degraded mode 时应暴露给 operator，并在 journal / report 中留下可追踪证据。当前 V3.0 文档已描述 degraded 的边界，但 operator UI 与审计轨迹还未形成独立验收项。

**不做的风险**
用户或 operator 可能把 degraded / partial 输出误认为完整成功；incident 排查时无法知道为何降级、谁确认、哪些输出受影响；安全策略可能在 fallback 中被无意放宽。

**建议变更范围**
定义 degraded mode projection 字段、operator view、audit event、acknowledgement workflow 与 report summary。UI 应显示 degraded reason、scope、affected run/attempt、fallback chain、operator acknowledgement 与恢复建议。

**是否触及 binding artifacts**
候选触及 projection / OpenAPI / event contracts；若只作为 operator doc 可先保持 informative。

**需要同步更新的文件类型**
OpenAPI、event contracts、schema、docs、tests、traceability；如引入 UI contract，还需 operator acceptance matrix。

**验收方式**
构造 global outage / provider_unavailable 场景，验证 operator UI 或 projection 暴露 degraded 状态；audit trail 包含原因、时间、scope、acknowledgement；最终报告不宣称完整成功。

**推荐阶段**
V3.1-beta。

### P1-2. Bridge reconciliation cursor 跨系统一致性测试

**背景**
V3 entrypoint 明确 Bridge / Adapter 负责 idempotency、projection、callback receipt、reconciliation cursor，但不是新的 truth source。当前 V3.0 release gate 更关注 journal reducer/projection 与 golden timelines，跨系统 cursor 一致性仍需更明确测试。

**不做的风险**
Paperclip view、Bridge projection 与 Dark Factory Journal 可能在重放、重复 callback、网络分区或延迟传播时产生分叉。Bridge 若错误地把 projection 当 truth source，可能无 journal 依据地推进状态。

**建议变更范围**
新增 reconciliation cursor consistency test plan，覆盖 cursor monotonicity、idempotent replay、duplicate callback receipt、out-of-order event handling、projection rebuild 与 source-of-truth boundary。明确 Bridge 只能从 journal 派生，不能反向裁决 truth。

**是否触及 binding artifacts**
候选触及 tests / golden timelines / event contracts；如果新增 cursor 对象或 API，则触及 schema / OpenAPI。

**需要同步更新的文件类型**
golden timeline、event contracts、OpenAPI、schema、traceability、docs、tests。

**验收方式**
使用同一 journal 序列多次 replay，断言 projection 结果一致；注入重复 callback 与乱序事件，断言 cursor 不回退、不跳过未处理 truth record、不产生无 journal 依据的状态升级。

**推荐阶段**
V3.1-beta。

---

## 5. P2 backlog

### P2-1. 历史 V2.9 companion-bound 资料归档为带 normativity metadata 的 reference bundle

**背景**
`3.0/V3_IMPLEMENTATION_ENTRYPOINT.md` 已说明 V2.9 companion-bound、Scheme B、Phoenix V2 / 不死鸟与 Hermes workflow 是历史参考和设计输入，不覆盖 V3 binding artifacts。当前这些资料已经被 manifest 分类为 informative out-of-bundle，但还缺少独立 reference bundle 的 normativity metadata、索引和冲突说明。

**不做的风险**
新读者可能误把 V2.9 companion-bound 或历史 DEVELOPMENT_SPEC 当作当前 V3 合同，尤其在术语、事件名、runtime config 或 provider routing 与 V3.0 不一致时，容易引入实现漂移。

**建议变更范围**
建立 reference bundle 索引，给每个历史文件标注 source、version、normativity、superseded_by、usable_for、must_not_override、known_conflicts。必要时增加冲突映射表，把 V2.9 概念映射到 V3.0 binding artifacts 或 V3.1 backlog。

**是否触及 binding artifacts**
通常不触及。除非发现当前 README / manifest 分类错误，仅做非规范性链接与 metadata 更新。

**需要同步更新的文件类型**
docs、manifest informative classification、reference metadata、README link；通常不改 schema / OpenAPI / event contracts / golden timelines。

**验收方式**
验证每个历史文件都有 normativity metadata；README 与 entrypoint 明确“reference only”；validate-v3 通过；没有把历史术语提升为 V3.0 MUST。

**推荐阶段**
V3.1-rc。

---

## 6. 实施顺序建议

1. **V3.1-alpha / P0 合同面冻结**：先为 provider health、RunAttempt runtime metadata、MemorySidecar schema、PhoenixRecover smoke 写 proposal 与 failing tests / golden timeline 草案。
2. **V3.1-beta / P1 operator 与 bridge 验收**：在 P0 字段稳定后，补 degraded operator UI / audit trail 和 Bridge reconciliation cursor 跨系统一致性测试。
3. **V3.1-rc / P2 reference governance**：整理 V2.9 companion-bound reference bundle，确保历史资料不会覆盖 V3 binding artifacts。

每一阶段都必须维护以下边界：

- 不把具体模型名写成协议 MUST。
- 不把 Phoenix Runtime 写成第二套 Paperclip control plane。
- 不把 MemorySidecar 字段塞进 Paperclip Task 主模型。
- 不让 Bridge / Adapter 成为第二 truth source。
- 不在 V3.0 `agent-control-r1` 下暗改 binding protocol contract。

---

## 7. V3.1 变更影响矩阵

| backlog | 优先级 | 阶段 | binding 影响 | 主要更新资产 |
| --- | --- | --- | --- | --- |
| provider health / circuit breaker observability schema | P0 | V3.1-alpha | 候选触及 | schema、OpenAPI、event contracts、runtime config、golden timeline、traceability、tests、docs |
| RunAttempt runtime metadata contract boundary | P0 | V3.1-alpha | 候选触及 | schema、OpenAPI、event contracts、golden timeline、traceability、tests、docs |
| MemorySidecar metadata / storage / KG / Diary retention | P0 | V3.1-alpha | 候选触及 | memory OpenAPI、schema、event contracts、runtime config、golden timeline、traceability、tests、docs |
| PhoenixRecover restart smoke / golden timeline | P0 | V3.1-alpha | 候选触及 tests/events | golden timeline、event contracts、traceability、tests、docs |
| degraded mode operator UI / audit trail | P1 | V3.1-beta | 候选触及 projection/API/events | OpenAPI、event contracts、schema、traceability、tests、docs |
| Bridge reconciliation cursor consistency tests | P1 | V3.1-beta | 候选触及 tests/API/events | golden timeline、event contracts、OpenAPI、schema、traceability、tests、docs |
| V2.9 reference bundle with normativity metadata | P2 | V3.1-rc | 通常不触及 | docs、manifest informative classification、reference metadata、README |

---

## 8. 下一步 V3.1-alpha 启动 checklist

- [ ] 为 P0-1 / P0-2 决定 runtime metadata 哪些字段进入 required，哪些保持 recommended。
- [ ] 为 P0-3 决定 MemorySidecar schema 与 existing `paperclip_darkfactory_v3_0_memory.openapi.yaml` 的关系。
- [ ] 为 P0-4 新增 PhoenixRecover restart smoke timeline 草案。
- [ ] 为每个 P0 项增加至少一个 traceability obligation 草案。
- [ ] 确认所有新增字段仍使用 role / class / abstract capability，不使用具体模型名作为协议 MUST。
- [ ] 确认所有新增 memory 字段留在 sidecar / memory artifact / receipt，不进入 Paperclip Task 主模型。
- [ ] 确认 Bridge cursor 测试只验证 journal-derived projection，不赋予 Bridge truth authority。
