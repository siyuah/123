# V3 Implementation Entrypoint

状态: informative developer entrypoint  
适用基线: Paperclip × Dark Factory V3.0 `agent-control-r1`  
protocolReleaseTag: `v3.0-agent-control-r1`

---

## 1. 入口结论

本文是开发者进入当前 V3.0 代码与文档包的推荐唯一入口。实现、评审、验收与后续扩展应先从这里建立边界，再进入 binding protocol artifacts、运行层策略和历史参考资料。

当前实现基线以 **V3.0 agent-control-r1** 为准。V2.9 companion-bound 资料仅作为历史参考和设计输入，不覆盖 V3。Phoenix V2 / 不死鸟材料仅作为 runtime policy、provider routing、memory sidecar、自愈 backlog 的参考，不改变 V3 协议合同。

最重要的原则：**不要把 Phoenix V2 变成第二套 control plane**。Phoenix Runtime 是 Agent Runtime 能力层，不是 Paperclip Task / approval / governance 的替代权威。

---

## 2. 版本权威与冲突优先级

### 2.1 当前 binding baseline

- 规范版本: V3.0
- protocolReleaseTag: `v3.0-agent-control-r1`
- 当前合同解释以根目录 V3 bundle 为准，而不是 `3.0/` 下的 V2.x 历史草稿。
- 机器可读资产、journal reducer/projection、control-plane CLI、release readiness gate 已形成当前开发与验收基线。

### 2.2 历史参考材料的地位

`3.0/` 下的 V2.5、V2.9 companion-bound、Scheme B、Hermes GPT-5.5 workflow、Phoenix / 不死鸟相关记录是重要设计输入，但默认不是 V3 binding contract。它们可以用于理解为何 V3 做了如下选择：

- 将 Paperclip control plane 与 Dark Factory execution plane 分开；
- 将 Journal 作为执行事实来源；
- 将 Bridge / Adapter 作为幂等投影与回执层；
- 将 provider routing、fallback、memory、recover 归入 Phoenix Runtime 能力层；
- 将 release gate、manifest、golden timelines、runtime contracts 作为 CI 可执行基线。

如果历史资料与 V3 bundle 冲突，先按 V3 binding artifacts 执行，再把冲突记录为 V3.1 backlog，不得直接覆盖 V3 合同。

---

## 3. 层边界

### 3.1 Paperclip Control Plane

Paperclip Control Plane 负责用户可见和治理可审计的控制面状态：

- `Task`
- approval
- governance
- user-facing state

边界规则：Paperclip 可以引用执行层状态和 projection，但不直接吞并 Dark Factory 的 journal 事实，也不把 provider / memory / retry 内部细节提升为 Task 主模型字段。

### 3.2 Bridge / Adapter

Bridge / Adapter 负责连接控制面与执行面，并把执行事实安全投影给 Paperclip：

- idempotency
- projection
- callback receipt
- reconciliation cursor

边界规则：Bridge / Adapter 可以维护游标、回执和幂等键；它不是新的 truth source，不应在没有 journal 依据时自行升级执行状态。

### 3.3 Dark Factory Execution Plane

Dark Factory Execution Plane 负责执行事实、尝试、产物和故障分类：

- `Run`
- `RunAttempt`
- `Journal`
- `ArtifactRef`
- `failure_class`

边界规则：Journal 是执行事实来源。Run / RunAttempt / ArtifactRef 的状态变化必须能由 journal 或验证过的事件链解释。

### 3.4 Phoenix Runtime Capabilities

Phoenix Runtime Capabilities 是 Agent Runtime 能力层，可被 Bridge / Dark Factory 调用或承载，但不改写 V3 control-plane 合同：

- `RouterEngine`
- `ProviderAdapter`
- `CircuitBreaker`
- `MemorySidecar`
- `PromptContextBuilder`
- `PhoenixRecover`

边界规则：Phoenix Runtime 可决定 provider role、fallback、degraded mode、上下文注入和恢复流程；但这些能力不得把具体模型名、sidecar 内部字段或恢复启发式写成 V3 core protocol MUST。

---

## 4. 文档与资产分类

### 4.1 Binding / release-gated artifacts

以下根目录资产是当前 V3 binding 或 release-gated 基线，必须优先阅读和保护：

- `README.md`
- `paperclip_darkfactory_v3_0_invariants.md`
- `paperclip_darkfactory_v3_0_core_spec.md`
- `paperclip_darkfactory_v3_0_core_enums.yaml`
- `paperclip_darkfactory_v3_0_core_objects.schema.json`
- `paperclip_darkfactory_v3_0_event_contracts.yaml`
- `paperclip_darkfactory_v3_0_state_transition_matrix.csv`
- `paperclip_darkfactory_v3_0_runtime_config_registry.yaml`
- `paperclip_darkfactory_v3_0_external_runs.openapi.yaml`
- `paperclip_darkfactory_v3_0_memory.openapi.yaml`
- `paperclip_darkfactory_v3_0_storage_mapping.csv`
- `paperclip_darkfactory_v3_0_responsibility_matrix.csv`
- `paperclip_darkfactory_v3_0_scenario_acceptance_matrix.csv`
- `paperclip_darkfactory_v3_0_test_traceability.csv`
- `paperclip_darkfactory_v3_0_bundle_manifest.yaml`
- `tests/golden_timelines/v3_0/*.jsonl`
- `dark_factory_v3/*.py`
- `tools/v3_control_plane.py`
- `tools/v3_release_readiness.py`
- `tools/v3_release_dry_run.py`
- `.github/workflows/v3-*.yml`
- `Makefile` V3 targets

### 4.2 Informative V3 implementation docs

这些文档帮助实现和操作，但不得单独覆盖 binding artifacts：

- `paperclip_darkfactory_v3_0_impl_pack.md`
- `paperclip_darkfactory_v3_0_agent_assembly_pack.md`
- `paperclip_darkfactory_v3_0_test_asset_spec.md`
- `DARK_FACTORY_V3_0_开工文档.md`
- `docs/v3_control_plane_cli.md`
- `docs/v3_release_readiness.md`
- `docs/v3_0_release_notes.md`
- `3.0/V3_IMPLEMENTATION_ENTRYPOINT.md`
- `3.0/runtime_policy.md`
- `3.0/memory_sidecar.md`

### 4.3 Historical / reference materials

以下文件保留为历史演进、review、Scheme B 或 workflow 参考；使用时必须显式标注“不覆盖 V3 binding artifacts”：

- `3.0/paperclip_darkfactory_revised_framework*.md`
- `3.0/paperclip_darkfactory_revised_framework_v2_9_companion_bound.md`
- `3.0/paperclip_darkfactory_v2_9_impl_pack.md`
- `3.0/paperclip_darkfactory_v2_9_external_runs.openapi.yaml`
- `3.0/paperclip_darkfactory_v2_9_runtime_config_registry.yaml`
- `3.0/paperclip_darkfactory_scheme_b_execution_plan.json`
- `3.0/paperclip_darkfactory_optimized_review*.md`
- `3.0/DEVELOPMENT_SPEC*.md`
- `3.0/hermes_gpt55_v3_0_segmented_workflow.md`
- `3.0/hermes-80315662261f.md`

- `3.0/future_development/README.md`
- `3.0/future_development/PAPERCLIP_UPSTREAM_INTEGRATION_PLAN.md`
- `3.0/future_development/NEXT_DEVELOPMENT_TASKS.md`
- `3.0/future_development/HERMES_GPT55_EXECUTION_COMMANDS.md`

---

## 5. 建议阅读顺序

1. 本文 `3.0/V3_IMPLEMENTATION_ENTRYPOINT.md`。
2. 根目录 `README.md` 的规范层级、binding / informative / CI boundary。
3. `paperclip_darkfactory_v3_0_invariants.md` 与 `paperclip_darkfactory_v3_0_core_spec.md`。
4. 机器可读合同：core enums、core objects schema、event contracts、OpenAPI、state matrix、responsibility/storage matrix、runtime config registry。
5. `tests/golden_timelines/v3_0/*.jsonl` 与 `paperclip_darkfactory_v3_0_test_traceability.csv`。
6. runtime 和 CLI：`dark_factory_v3/`、`tools/v3_control_plane.py`、`docs/v3_control_plane_cli.md`。
7. release gates：`Makefile`、`tools/v3_release_readiness.py`、`tools/v3_release_dry_run.py`、GitHub Actions workflows。
8. 运行层策略：`3.0/runtime_policy.md`。
9. 记忆 sidecar：`3.0/memory_sidecar.md`。
10. 最后再读 V2.9 companion-bound、Scheme B、Phoenix V2 / 不死鸟与 Hermes workflow 作为参考资料。

---

## 6. 实现前 checklist

开始任何实现前，先完成以下检查：

- [ ] `git status --short`，确认不会覆盖用户改动。
- [ ] 明确 `HEAD` 与 `origin/main` 是否同步。
- [ ] 确认修改是否触及 binding artifacts；若触及，需要同步 manifest、traceability、golden timelines 或 tests。
- [ ] 确认新语义是否属于 Paperclip control plane、Bridge / Adapter、Dark Factory execution plane，还是 Phoenix Runtime capabilities。
- [ ] 若是 runtime routing / fallback / memory / recover 能力，优先落入 `3.0/runtime_policy.md` 或 `3.0/memory_sidecar.md`，不要直接扩展 Paperclip Task 主模型。
- [ ] 若新增字段进入 RunAttempt / Journal / ArtifactRef，需要判断是否应进入 schema、OpenAPI、event contracts、projection 和 golden timeline。
- [ ] 若只新增 informative 文档，避免把具体模型名、provider 名或历史术语写成 MUST。
- [ ] 运行 `make validate-v3` 与 `make test-v3-contracts`；如果生成 `__pycache__`，清理后再检查 status。

---

## 7. 禁止事项

- 不要重写现有 V3 协议合同来适配历史 V2.9 文档。
- 不要把具体模型名写成协议级 MUST。
- 不要把 Phoenix Runtime 写成 Paperclip control plane。
- 不要把 `MemorySidecar` 字段塞进 Paperclip `Task` 主模型。
- 不要让 Bridge / Adapter 成为第二 truth source。
- 不要把 `__pycache__`、timestamp-only `checkedAt` 或临时报告当作设计变更提交。
- 不要创建或移动 release tag，不要创建 GitHub Release，除非任务明确授权。

---

## 8. 进入 V3.1 backlog 的候选方向

以下方向适合进入 V3.1 backlog，而不是在 V3.0 agent-control-r1 中破坏合同。完整拆解见 `3.0/V3_1_BACKLOG_AND_IMPLEMENTATION_ROADMAP.md`，该文件是 informative roadmap / backlog，不覆盖 V3.0 binding artifacts。

- provider health 与 circuit breaker 的可观测性 schema；
- RunAttempt provider role / model role / failure_class 字段的正式合同化；
- MemorySidecar 的独立 OpenAPI 或 storage profile；
- PhoenixRecover 的重启恢复验收集；
- degraded mode 的 operator UI 与 audit trail；
- Bridge reconciliation cursor 的跨系统一致性测试；
- 将历史 V2.9 companion-bound 资料归档成带 normativity metadata 的 reference bundle。
