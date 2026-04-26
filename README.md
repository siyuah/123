# Paperclip × Dark Factory V3.0 Delivery Bundle

状态: delivery-candidate  
规范版本: 3.0  
protocolReleaseTag: `v3.0-agent-control-r1`  
companionAppendixVersion: `3.0-companion.1`  
implPackVersion: `3.0-impl.1`  
agentAssemblyPackVersion: `3.0-assembly.1`  
scenarioPackVersion: `3.0-scenarios.1`

---

## 1. 这份 bundle 的用途

本目录是 V3.0 的完整交付版文档包，用于把以下三层内容收敛成单一发布物：

1. 核心规范层: 真相对象、事件、状态、不变量、恢复语义
2. 参考实现层: API surface、operator surface、routing / memory / repair / archive 的实现约束
3. 运行治理层: runtime registry、scenario gate、发布门禁与验收资产

本包的目标不是“说明设计方向”，而是让实现者、审计器、回放器、operator 工具与 CI gate 对同一条时间线给出同一结论。

---

## 2. 规范层级与冲突优先级

### 2.1 层级

V3.0 按以下层级解释，优先级从高到低：

1. `paperclip_darkfactory_v3_0_invariants.md`
2. `paperclip_darkfactory_v3_0_core_spec.md`
3. machine-readable 资产
   - `paperclip_darkfactory_v3_0_core_enums.yaml`
   - `paperclip_darkfactory_v3_0_core_objects.schema.json`
   - `paperclip_darkfactory_v3_0_event_contracts.yaml`
   - `paperclip_darkfactory_v3_0_state_transition_matrix.csv`
   - `paperclip_darkfactory_v3_0_runtime_config_registry.yaml`
4. `paperclip_darkfactory_v3_0_impl_pack.md`
5. `paperclip_darkfactory_v3_0_agent_assembly_pack.md`
6. `paperclip_darkfactory_v3_0_test_asset_spec.md`
7. OpenAPI、mapping、matrix、bundle manifest

### 2.2 冲突处理规则

- 若 `invariants` 与任何其他文件冲突，以 `invariants` 为准。
- 若 `core_spec` 与 machine-readable 资产冲突，视为发布阻断，必须修正到一致。
- 若 OpenAPI 与核心对象 schema 冲突，以核心对象 schema 和 `core_spec` 为准；OpenAPI 必须回补。
- `runtime_config_registry` 只能调参数，不能削弱核心规范与不变量。
- `impl_pack` 与 `agent_assembly_pack` 提供参考实现与装配约束，不得重写核心语义。

---

## 3. binding / informative / CI boundary

### 3.1 Binding 资产

以下文件属于 binding 资产，直接参与协议解释、对象验证或发布门禁：

- `paperclip_darkfactory_v3_0_core_spec.md`
- `paperclip_darkfactory_v3_0_invariants.md`
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
- `paperclip_darkfactory_v3_0_bundle_manifest.yaml`

### 3.2 Informative 资产

以下文件属于 informative 资产，但仍要求与 binding 资产保持语义一致：

- `paperclip_darkfactory_v3_0_impl_pack.md`
- `paperclip_darkfactory_v3_0_agent_assembly_pack.md`
- `paperclip_darkfactory_v3_0_test_asset_spec.md`
- `DARK_FACTORY_V3_0_开工文档.md`

### 3.3 CI boundary

CI 至少必须做以下检查：

1. `protocolReleaseTag` 在 schema、OpenAPI、event envelope、错误响应、bundle manifest 中传播闭合
2. `event_contracts` 中的 `canonicalName`、`fullName`、`version` 与 `core_enums` 对齐
3. `state_transition_matrix` 中的状态值必须全部出自 `core_enums`
4. OpenAPI 响应对象与 `core_objects.schema.json` 的同名对象字段不可缺主字段
5. `runtime_config_registry` 中的 `source` 必须在 `core_spec`、`impl_pack` 或 `agent_assembly_pack` 中可解析
6. `scenario_acceptance_matrix` 中标记为 `release_blocker=true` 的场景必须进入发布 gate

---

## 4. 文件清单与职责

### 核心规范

- `paperclip_darkfactory_v3_0_core_spec.md`: 核心对象、状态机、truth path、恢复语义与硬边界
- `paperclip_darkfactory_v3_0_invariants.md`: schema 与 OpenAPI 无法表达的不变量

### 机读合同

- `paperclip_darkfactory_v3_0_core_enums.yaml`: 唯一枚举文字面量
- `paperclip_darkfactory_v3_0_core_objects.schema.json`: 核心对象 schema
- `paperclip_darkfactory_v3_0_event_contracts.yaml`: 事件 envelope 与事件目录
- `paperclip_darkfactory_v3_0_state_transition_matrix.csv`: Run / Attempt / Artifact / Dependency 状态迁移
- `paperclip_darkfactory_v3_0_runtime_config_registry.yaml`: 运行参数面与门禁键注册表

### 实现与装配

- `paperclip_darkfactory_v3_0_impl_pack.md`: API / operator / storage / observability / archive 的参考实现说明
- `paperclip_darkfactory_v3_0_agent_assembly_pack.md`: 路由、provider adapter、memory pipeline、repair lane 与 scenario gate 的装配约束

### 交付与验收

- `paperclip_darkfactory_v3_0_external_runs.openapi.yaml`: external runs / artifact / lineage / repair / archive HTTP facade
- `paperclip_darkfactory_v3_0_memory.openapi.yaml`: memory artifact / correction / search / injection 查询 HTTP facade
- `paperclip_darkfactory_v3_0_storage_mapping.csv`: truth object 到持久化与投影存储的映射
- `paperclip_darkfactory_v3_0_responsibility_matrix.csv`: 领域归属、写入 owner、审核 owner 与门禁 owner
- `paperclip_darkfactory_v3_0_test_asset_spec.md`: fixture、golden timeline、property、fault injection 与 scenario acceptance 的测试规范
- `paperclip_darkfactory_v3_0_scenario_acceptance_matrix.csv`: 场景验收矩阵
- `paperclip_darkfactory_v3_0_bundle_manifest.yaml`: 本 bundle 的权威目录、边界与摘要

---

## 5. protocolReleaseTag 传播规则

V3.0 要求以下位置显式携带 `protocolReleaseTag`，不允许只靠服务端隐式默认：

- create request
- park request
- rehydrate request
- waiver request
- memory create / correct request
- run / artifact / lineage / memory view
- error response
- event envelope
- bundle manifest

任何缺失都会被视为协议不完整，而不是可忽略细节。

---

## 6. 发布判定

只有当以下条件同时满足，V3.0 bundle 才可进入 release candidate：

1. 本目录所有 binding 文件齐全
2. machine-readable 资产之间无 literal 冲突
3. OpenAPI 与 schema 的主字段一致
4. `scenario_acceptance_matrix` 中的 release blocker 场景全部通过
5. bundle manifest 中的文件摘要与实际产物一致

未满足上述条件时，本包最多只能算 development bundle，不得宣称完成发布。

---

## 7. V3.0 开发入口与运行层参考

`3.0/V3_IMPLEMENTATION_ENTRYPOINT.md` 是推荐开发入口，用于把当前 V3.0 binding artifacts、V2.9 companion-bound 历史资料、Hermes GPT-5.5 workflow、Scheme B、Phoenix V2 / 不死鸟材料统一分类到可执行开发路径。

`3.0/V3_1_BACKLOG_AND_IMPLEMENTATION_ROADMAP.md` 是 V3.1 roadmap / backlog 入口，用于规划 provider health、RunAttempt runtime metadata、MemorySidecar schema、PhoenixRecover、degraded mode、Bridge cursor 与 V2.9 reference bundle；它不覆盖 V3.0 binding artifacts，不改变 `v3.0-agent-control-r1`。

`3.0/runtime_policy.md` 是运行层策略文档，收敛 provider role、failure_class、retry、fallback、circuit breaker 与 degraded mode；它不把具体模型名写成协议合同。

`3.0/memory_sidecar.md` 是 Agent Runtime 记忆 sidecar 文档，定义 AutoExtractor、SessionMemory、MemorySync、LongTermMemory、KnowledgeGraph、DiaryStore、PromptContextBuilder 与 PhoenixRecover 的边界；它不覆盖现有 binding protocol artifacts，不改变 Paperclip Task 主模型，也不改变 Dark Factory Journal 的事实来源地位。
