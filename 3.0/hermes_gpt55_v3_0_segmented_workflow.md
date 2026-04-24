# Hermes + GPT5.5 启动 Paperclip Dark Factory V3.0 的分段式工作流程

> 适用目录：`/home/siyuah/workspace/123`
>
> 当前定位：Paperclip Dark Factory V3.0 delivery-candidate bundle。
>
> 重要边界：这不是最终 release-grade 包。当前已通过轻量一致性复核，但不能声称真实 CI、OpenAPI validator、JSON Schema validator、golden timeline 全部跑通。

---

## 1. 总原则

不要让 Hermes + GPT5.5 一次性吞完整 V3.0 文档后自由发挥。

正确方式是把文档包当成 staged implementation bundle：

1. 先建立文档索引和协议边界。
2. 再冻结机读合同。
3. 再实现协议常量、Journal truth path、状态机、capability/write fence。
4. 最后接 routing、memory、repair、OpenAPI facade、scenario gate、CI release gate。

每个阶段都必须做到：

- 只读指定输入文件。
- 只改指定范围。
- 明确输出产物。
- 明确验收条件。
- 明确禁止事项。
- 完成后停止或提交报告，不能自动跳过 blocking issue。

---

## 2. 推荐启动方式

### 2.1 工作目录

```text
/home/siyuah/workspace/123
```

### 2.2 文档读取优先级

当文件之间出现冲突时，优先级如下：

1. `paperclip_darkfactory_v3_0_invariants.md`
2. `paperclip_darkfactory_v3_0_core_spec.md`
3. 机读合同：
   - `paperclip_darkfactory_v3_0_core_enums.yaml`
   - `paperclip_darkfactory_v3_0_core_objects.schema.json`
   - `paperclip_darkfactory_v3_0_event_contracts.yaml`
   - `paperclip_darkfactory_v3_0_state_transition_matrix.csv`
   - `paperclip_darkfactory_v3_0_runtime_config_registry.yaml`
   - `paperclip_darkfactory_v3_0_external_runs.openapi.yaml`
   - `paperclip_darkfactory_v3_0_memory.openapi.yaml`
4. 实现包 / agent 装配包：
   - `paperclip_darkfactory_v3_0_impl_pack.md`
   - `paperclip_darkfactory_v3_0_agent_assembly_pack.md`
5. 测试与治理资产：
   - `paperclip_darkfactory_v3_0_storage_mapping.csv`
   - `paperclip_darkfactory_v3_0_responsibility_matrix.csv`
   - `paperclip_darkfactory_v3_0_scenario_acceptance_matrix.csv`
   - `paperclip_darkfactory_v3_0_test_asset_spec.md`
   - `paperclip_darkfactory_v3_0_test_traceability.csv`
6. `README.md` 和开工文档作为导航与说明，不应覆盖 normative contract。

### 2.3 总控 Prompt

把下面这段直接交给 Hermes + GPT5.5：

```text
你现在要基于 Paperclip Dark Factory V3.0 delivery-candidate bundle 开始实现工作。

工作目录：
/home/siyuah/workspace/123

第一原则：
1. 不要重写规范。
2. 不要把 informative 文档当成高于 normative 文档的来源。
3. 冲突优先级：
   - paperclip_darkfactory_v3_0_invariants.md
   - paperclip_darkfactory_v3_0_core_spec.md
   - machine-readable assets
   - implementation / assembly packs
   - test / governance assets
4. 任何实现必须保持 protocolReleaseTag = v3.0-agent-control-r1。
5. 任何状态、枚举、事件、API 字段新增或修改，都必须同步更新：
   - core_enums
   - core_objects schema
   - event contracts
   - OpenAPI
   - state matrix
   - test asset spec
   - traceability
   - manifest
6. 每个阶段完成后必须输出：
   - 改了哪些文件
   - 为什么改
   - 跑了哪些验证命令
   - 是否还有 blocking issue
   - 下一阶段建议

请先只做 Phase 0：读取 README、bundle manifest、invariants、core spec，生成一份 implementation map，不要修改代码。
```

---

## 3. 分段式工作流程

## Phase 0：Bundle ingest / implementation map

### 目标

让 Hermes + GPT5.5 先理解 V3.0 文档包，不写代码。

### 输入文件

- `README.md`
- `paperclip_darkfactory_v3_0_bundle_manifest.yaml`
- `paperclip_darkfactory_v3_0_invariants.md`
- `paperclip_darkfactory_v3_0_core_spec.md`
- `paperclip_darkfactory_v3_0_consistency_report.md`

### 输出产物

- `docs/v3_0_implementation_map.md`

### 验收条件

输出文档必须包含：

- Protocol boundary
- Truth objects
- Event catalog
- Hard invariants
- Implementation phases
- Risks / questions

### 禁止事项

- 不要修改规范文件。
- 不要生成实现代码。
- 不要补充不存在的协议语义。

### 执行 Prompt

```text
Phase 0：建立 V3.0 implementation map。

工作目录：
/home/siyuah/workspace/123

请读取：
- README.md
- paperclip_darkfactory_v3_0_bundle_manifest.yaml
- paperclip_darkfactory_v3_0_invariants.md
- paperclip_darkfactory_v3_0_core_spec.md
- paperclip_darkfactory_v3_0_consistency_report.md

任务：
1. 总结 V3.0 的核心协议边界。
2. 列出必须实现的 truth objects。
3. 列出必须实现的事件。
4. 列出不可被 runtime config 削弱的不变量。
5. 列出 implementation phases。
6. 写入 docs/v3_0_implementation_map.md。
7. 不要修改其他文件。

输出格式：
- Protocol boundary
- Truth objects
- Event catalog
- Hard invariants
- Implementation phases
- Risks / questions
```

---

## Phase 1：Contract freeze / 协议常量与类型层

### 目标

建立项目内部唯一协议字面量入口。

### 输入文件

- `paperclip_darkfactory_v3_0_core_enums.yaml`
- `paperclip_darkfactory_v3_0_core_objects.schema.json`
- `paperclip_darkfactory_v3_0_event_contracts.yaml`
- `paperclip_darkfactory_v3_0_invariants.md`

### 输出产物

TypeScript 项目建议：

- `src/protocol/constants.ts`
- `src/protocol/enums.ts`
- `src/protocol/events.ts`
- `src/protocol/errors.ts`
- `src/protocol/schemas.ts`
- `src/protocol/invariants.ts`
- `tests/protocol/*`

Python 项目建议：

- `src/protocol/constants.py`
- `src/protocol/enums.py`
- `src/protocol/events.py`
- `src/protocol/errors.py`
- `src/protocol/schemas.py`
- `src/protocol/invariants.py`
- `tests/protocol/*`

### 验收条件

- `protocolReleaseTag` 固定为 `v3.0-agent-control-r1`。
- enum literal 来自 `core_enums.yaml`。
- event canonicalName / fullName / version 来自 `event_contracts.yaml`。
- schema 文件可解析。
- 不允许业务代码散落重复协议字符串。

### 执行 Prompt

```text
Phase 1：实现协议常量与类型层。

工作目录：
/home/siyuah/workspace/123

请读取：
- paperclip_darkfactory_v3_0_core_enums.yaml
- paperclip_darkfactory_v3_0_core_objects.schema.json
- paperclip_darkfactory_v3_0_event_contracts.yaml
- paperclip_darkfactory_v3_0_invariants.md

目标：
建立项目内部唯一协议字面量入口。

要求：
1. 所有 enum literal 必须来自 core_enums.yaml。
2. 所有 event canonicalName / fullName / version 必须来自 event_contracts.yaml。
3. protocolReleaseTag 必须固定为 v3.0-agent-control-r1。
4. 不允许手写重复字符串散落在业务代码中。
5. 不实现业务流程，只建立协议常量、类型、schema 加载和基础校验。
6. 给出最小测试，验证：
   - protocolReleaseTag 正确
   - event name 与 event contract 对齐
   - enum values 可导入
   - schema 文件可解析

完成后输出：
- 创建/修改的文件
- 测试命令
- 测试结果
- 是否发现文档/实现冲突
```

---

## Phase 2：Journal truth path

### 目标

实现 append-only truth event journal。

### 输入文件

- `paperclip_darkfactory_v3_0_invariants.md`
- `paperclip_darkfactory_v3_0_core_spec.md`
- `paperclip_darkfactory_v3_0_event_contracts.yaml`
- `paperclip_darkfactory_v3_0_storage_mapping.csv`

### 输出产物

- `src/journal/journal-service.*`
- `src/journal/event-envelope.*`
- `src/journal/idempotency.*`
- `tests/journal/*`

### 验收条件

- Journal 是唯一 truth path。
- projection 不得反向修改 truth。
- append 支持 idempotencyKey。
- replay 不改变原始 truth event。

### 执行 Prompt

```text
Phase 2：实现 Journal truth path。

工作目录：
/home/siyuah/workspace/123

请读取：
- paperclip_darkfactory_v3_0_invariants.md
- paperclip_darkfactory_v3_0_core_spec.md
- paperclip_darkfactory_v3_0_event_contracts.yaml
- paperclip_darkfactory_v3_0_storage_mapping.csv

目标：
实现最小 Journal append/read/replay 基础设施。

要求：
1. Journal 是唯一 truth path。
2. event envelope 必须包含 eventName、eventVersion、eventId、emittedAt、protocolReleaseTag、traceId、producer、causationId、correlationId、sequenceNo、isReplay。
3. append 必须支持 idempotencyKey。
4. projection 不得反向修改 truth。
5. 不实现完整业务状态机，只实现 truth event 记录与读取。
6. 写测试验证：
   - 缺 protocolReleaseTag 的事件被拒绝
   - 重复 idempotencyKey 不产生重复 truth event
   - sequenceNo 单调递增
   - replay 标记不改变原始 truth event

完成后输出：
- 文件清单
- 测试命令
- 测试结果
- 下一阶段建议
```

---

## Phase 3：Run / Attempt / Artifact / Dependency 状态机

### 目标

将 `state_transition_matrix.csv` 变成可执行状态推进规则。

### 输入文件

- `paperclip_darkfactory_v3_0_state_transition_matrix.csv`
- `paperclip_darkfactory_v3_0_core_enums.yaml`
- `paperclip_darkfactory_v3_0_core_spec.md`
- `paperclip_darkfactory_v3_0_invariants.md`

### 输出产物

- `src/state/state-machine.*`
- `src/state/run-state.*`
- `src/state/attempt-state.*`
- `src/state/artifact-state.*`
- `src/state/dependency-state.*`
- `tests/state/*`

### 验收条件

- 状态 literal 全部来自 `core_enums.yaml`。
- transition 全部来自 `state_transition_matrix.csv`。
- 非法 transition 被拒绝。
- 同一 run 同时最多一个 active attempt。
- `parked_manual` 不是终态。
- rehydrate 必须创建新 attempt。

### 执行 Prompt

```text
Phase 3：实现状态机。

工作目录：
/home/siyuah/workspace/123

请读取：
- paperclip_darkfactory_v3_0_state_transition_matrix.csv
- paperclip_darkfactory_v3_0_core_enums.yaml
- paperclip_darkfactory_v3_0_core_spec.md
- paperclip_darkfactory_v3_0_invariants.md

目标：
将 state_transition_matrix.csv 变成可执行状态推进规则。

要求：
1. 状态 literal 必须全部来自 core_enums.yaml。
2. transition 必须来自 state_transition_matrix.csv。
3. 非法 transition 必须拒绝。
4. parked_manual 不是终态。
5. rehydrate 必须创建新 attempt。
6. 同一 run 同时最多一个 active attempt。
7. artifact reopened / revoked 不得被静默回退。
8. dependency revoked_upstream 不允许 high-risk primary write。

测试至少覆盖：
- run requested -> validating -> planning
- executing -> parked_manual
- parked_manual -> rehydrating -> planning
- attempt active -> parked_manual -> rehydrate_pending -> superseded
- artifact certified -> reopened -> revoked
- dependency clean -> reopened_upstream / revoked_upstream
- 非法 transition 被拒绝

完成后输出：
- 文件清单
- 测试命令
- 测试结果
- 未覆盖 transition 清单
```

---

## Phase 4：Capability broker 与 schema write fence

### 目标

实现高风险操作边界，防止后续业务绕过。

### 输入文件

- `paperclip_darkfactory_v3_0_invariants.md`
- `paperclip_darkfactory_v3_0_core_objects.schema.json`
- `paperclip_darkfactory_v3_0_runtime_config_registry.yaml`
- `paperclip_darkfactory_v3_0_event_contracts.yaml`

### 输出产物

- `src/capability/capability-broker.*`
- `src/capability/capability-lease.*`
- `src/schema/write-fence.*`
- `tests/capability/*`
- `tests/schema/*`

### 验收条件

- attempt 执行前必须获得 `ExecutionCapabilityLease`。
- `observedCapabilitySet` 超出 `grantedCapabilitySet` 时，必须产生审计事实。
- `profileConformanceStatus=unverifiable` 时，不得进入 high-risk write。
- 旧 writer 不得覆盖 V3.0 对象。
- repair/manual/archive restore 都不能绕过 write fence。

### 执行 Prompt

```text
Phase 4：实现 capability broker 与 schema write fence。

工作目录：
/home/siyuah/workspace/123

请读取：
- paperclip_darkfactory_v3_0_invariants.md
- paperclip_darkfactory_v3_0_core_objects.schema.json
- paperclip_darkfactory_v3_0_runtime_config_registry.yaml
- paperclip_darkfactory_v3_0_event_contracts.yaml

目标：
实现执行前 capability lease 校验与 mixed-version write fence。

要求：
1. attempt 执行前必须获得 ExecutionCapabilityLease。
2. observedCapabilitySet 超出 grantedCapabilitySet 时，必须产生审计事实。
3. profileConformanceStatus=unverifiable 时，不得进入 high-risk write。
4. 旧 writer 不得覆盖 V3.0 对象。
5. write fence 拒绝必须产生 schema.write_fence.rejected 事件或错误响应。
6. repair/manual/archive restore 都不能绕过 write fence。

测试至少覆盖：
- conformant lease 通过
- exceeded_declared 被检测
- broker_bypass_attempted 被检测
- unverifiable 阻断 high-risk write
- writerSchemaVersion < minWriterSchemaVersion 被拒绝
- schema.write_fence.rejected 事件字段完整

完成后输出：
- 文件清单
- 测试命令
- 测试结果
- 是否有需要回补文档的地方
```

---

## Phase 5：Routing / provider failure / recovery lane

### 目标

实现 workload routing、provider fault classification、recovery lane mapping。

### 输入文件

- `paperclip_darkfactory_v3_0_agent_assembly_pack.md`
- `paperclip_darkfactory_v3_0_core_enums.yaml`
- `paperclip_darkfactory_v3_0_event_contracts.yaml`
- `paperclip_darkfactory_v3_0_runtime_config_registry.yaml`

### 输出产物

- `src/routing/router-engine.*`
- `src/routing/provider-fault-classifier.*`
- `src/routing/recovery-lane-mapper.*`
- `src/routing/fallback-chain-resolver.*`
- `tests/routing/*`

### 验收条件

- 每次 route decision 必须记录 `route.decision.recorded.v1`。
- provider 原始错误必须先分类为 `providerFaultClass`。
- `providerFaultClass` 必须唯一映射到 `recoveryLane`。
- 不允许保留 “A or B” 形式的歧义恢复。
- fallback chain 来自 runtime config registry，不要硬编码成协议真义。

### 执行 Prompt

```text
Phase 5：实现 routing / provider failure / recovery lane。

工作目录：
/home/siyuah/workspace/123

请读取：
- paperclip_darkfactory_v3_0_agent_assembly_pack.md
- paperclip_darkfactory_v3_0_core_enums.yaml
- paperclip_darkfactory_v3_0_event_contracts.yaml
- paperclip_darkfactory_v3_0_runtime_config_registry.yaml

目标：
实现 workload routing、provider fault classification、recovery lane mapping。

要求：
1. 每次 route decision 必须记录 route.decision.recorded.v1。
2. provider 原始错误必须先分类为 providerFaultClass。
3. providerFaultClass 必须唯一映射到 recoveryLane。
4. 不允许保留 A or B 形式的歧义恢复。
5. cutover 必须记录 provider.failure.recorded.v1 和 route.cutover.performed.v1。
6. fallback chain 来自 runtime config registry，不要硬编码成协议真义。

测试至少覆盖：
- chat/code/reasoning/vision workload 选择不同 route
- transient_timeout -> retry 或 fallback 的唯一映射
- quota_exhausted -> cutover_fallback_route
- auth_invalid 默认不 cutover
- context_length_exceeded 进入 poisoned/preflight 相关处理
- route decision event 字段完整

完成后输出：
- 文件清单
- 测试命令
- 测试结果
- provider fault mapping 表
```

---

## Phase 6：Manual gate / park / rehydrate

### 目标

实现人工挂起与恢复闭环。

### 输入文件

- `paperclip_darkfactory_v3_0_invariants.md`
- `paperclip_darkfactory_v3_0_core_spec.md`
- `paperclip_darkfactory_v3_0_event_contracts.yaml`
- `paperclip_darkfactory_v3_0_state_transition_matrix.csv`

### 输出产物

- `src/manual/manual-gate-service.*`
- `src/manual/park-record.*`
- `src/manual/rehydration-token.*`
- `tests/manual/*`

### 验收条件

- park 必须产生 `ParkRecord`。
- park 必须释放执行资源并保留 truth obligation。
- `RehydrationToken` 必须单次成功消费。
- rehydrate 必须重新 claim、preflight、route decision。
- rehydrate 必须产生新 attempt。
- 旧 attempt 必须 superseded 或非活跃。

### 执行 Prompt

```text
Phase 6：实现 manual gate、park、rehydrate。

工作目录：
/home/siyuah/workspace/123

请读取：
- paperclip_darkfactory_v3_0_invariants.md
- paperclip_darkfactory_v3_0_core_spec.md
- paperclip_darkfactory_v3_0_event_contracts.yaml
- paperclip_darkfactory_v3_0_state_transition_matrix.csv

目标：
实现 park / rehydrate truth flow。

要求：
1. park 必须产生 ParkRecord。
2. park 必须释放执行资源并保留 truth obligation。
3. RehydrationToken 必须单次成功消费。
4. rehydrate 必须重新 claim、preflight、route decision。
5. rehydrate 必须产生新 attempt。
6. 旧 attempt 必须 superseded 或非活跃。
7. parked attempt 不得继续追加 high-risk effect。
8. 必须记录 manual_gate.parked.v1 和 manual_gate.rehydrated.v1。

测试至少覆盖：
- executing -> parked_manual
- parked_manual -> rehydrating -> planning
- token 第一次消费成功
- token 第二次消费失败
- rehydrate 创建 newAttemptId
- oldAttemptId 不再 active
- parked attempt high-risk write 被拒绝

完成后输出：
- 文件清单
- 测试命令
- 测试结果
- park/rehydrate timeline 示例
```

---

## Phase 7：Lineage / artifact certification / waiver

### 目标

实现 artifact 可信状态与下游传播。

### 输入文件

- `paperclip_darkfactory_v3_0_core_spec.md`
- `paperclip_darkfactory_v3_0_invariants.md`
- `paperclip_darkfactory_v3_0_core_objects.schema.json`
- `paperclip_darkfactory_v3_0_event_contracts.yaml`
- `paperclip_darkfactory_v3_0_state_transition_matrix.csv`

### 输出产物

- `src/lineage/*`
- `src/artifacts/*`
- `src/waivers/*`
- `tests/lineage/*`
- `tests/artifacts/*`

### 验收条件

- artifact certification state 是消费资格的唯一协议来源。
- reopened/revoked 必须传播到下游 consumer。
- revoked_upstream 不得放行新的 high-risk primary write。
- waiver 只能影响授权范围内的 consumer。
- waiver 不得改写上游 artifact certification history。

### 执行 Prompt

```text
Phase 7：实现 artifact certification、lineage invalidation、waiver。

工作目录：
/home/siyuah/workspace/123

请读取：
- paperclip_darkfactory_v3_0_core_spec.md
- paperclip_darkfactory_v3_0_invariants.md
- paperclip_darkfactory_v3_0_core_objects.schema.json
- paperclip_darkfactory_v3_0_event_contracts.yaml
- paperclip_darkfactory_v3_0_state_transition_matrix.csv

目标：
实现 artifact 状态、lineage edge、waiver 和下游 invalidation。

要求：
1. artifactCertificationState 是消费资格的唯一协议来源。
2. reopened/revoked 必须传播到下游 consumer。
3. revoked_upstream 不得放行新的 high-risk primary write。
4. waiver 只能影响授权范围内的 consumer。
5. waiver 不得改写上游 artifact certification history。
6. 记录 artifact.certification.changed、lineage.invalidation.started、lineage.invalidation.propagated。

测试至少覆盖：
- tentative -> certified
- certified -> reopened
- reopened -> revoked
- reopened upstream blocks consumer
- revoked_upstream blocks high-risk write
- waiver only applies scoped consumer
- waiver cannot override revoked_upstream

完成后输出：
- 文件清单
- 测试命令
- 测试结果
- lineage propagation 示例
```

---

## Phase 8：Memory pipeline

### 目标

实现 MemoryArtifact、correction、search、PromptInjectionReceipt。

### 输入文件

- `paperclip_darkfactory_v3_0_agent_assembly_pack.md`
- `paperclip_darkfactory_v3_0_core_objects.schema.json`
- `paperclip_darkfactory_v3_0_memory.openapi.yaml`
- `paperclip_darkfactory_v3_0_runtime_config_registry.yaml`
- `paperclip_darkfactory_v3_0_event_contracts.yaml`

### 输出产物

- `src/memory/*`
- `tests/memory/*`

### 验收条件

- memory artifact 必须有 source trace、subjectRef、confidence、consentScope、currentState。
- corrected/revoked/expired artifact 不得作为 active 输入注入。
- cross-session memory 需要 consent 时，缺失 consent 必须阻断。
- prompt injection 必须留下 PromptInjectionReceipt。

### 执行 Prompt

```text
Phase 8：实现 memory pipeline。

工作目录：
/home/siyuah/workspace/123

请读取：
- paperclip_darkfactory_v3_0_agent_assembly_pack.md
- paperclip_darkfactory_v3_0_core_objects.schema.json
- paperclip_darkfactory_v3_0_memory.openapi.yaml
- paperclip_darkfactory_v3_0_runtime_config_registry.yaml
- paperclip_darkfactory_v3_0_event_contracts.yaml

目标：
实现 MemoryArtifact、correction、search、PromptInjectionReceipt。

要求：
1. memory artifact 必须有 source trace、subjectRef、confidence、consentScope、currentState。
2. corrected/revoked/expired artifact 不得作为 active 输入注入。
3. cross-session memory 需要 consent 时，缺失 consent 必须阻断。
4. prompt injection 必须留下 PromptInjectionReceipt。
5. memory projection 可以重建，不得反向定义 truth。
6. 记录 memory.artifact.created、memory.artifact.corrected、memory.injection.recorded。

测试至少覆盖：
- 创建 memory artifact
- correction 改变 currentState
- revoked artifact 不注入
- expired artifact 不注入
- consent 缺失时 cross-session injection 被拒绝
- injection receipt 字段完整

完成后输出：
- 文件清单
- 测试命令
- 测试结果
- memory injection policy 摘要
```

---

## Phase 9：Repair lane

### 目标

实现修复流程，但确保 repair 不是后门写入通道。

### 输入文件

- `paperclip_darkfactory_v3_0_agent_assembly_pack.md`
- `paperclip_darkfactory_v3_0_invariants.md`
- `paperclip_darkfactory_v3_0_core_objects.schema.json`
- `paperclip_darkfactory_v3_0_event_contracts.yaml`
- `paperclip_darkfactory_v3_0_runtime_config_registry.yaml`

### 输出产物

- `src/repair/*`
- `tests/repair/*`

### 验收条件

- repair lane 只能由 `recoveryLane=enter_repair_lane` 或明确 operator action 进入。
- repair attempt 必须有 trigger、plan、outcome、verificationEvidenceRef。
- repair 成功必须经过 sandbox verification。
- high-risk repair 默认需要 operator approval。
- repair 不得绕过 capability broker、schema write fence、lineage block、manual gate。

### 执行 Prompt

```text
Phase 9：实现 repair lane。

工作目录：
/home/siyuah/workspace/123

请读取：
- paperclip_darkfactory_v3_0_agent_assembly_pack.md
- paperclip_darkfactory_v3_0_invariants.md
- paperclip_darkfactory_v3_0_core_objects.schema.json
- paperclip_darkfactory_v3_0_event_contracts.yaml
- paperclip_darkfactory_v3_0_runtime_config_registry.yaml

目标：
实现 RepairAttempt、repair policy、verification、antibody pattern 记录。

要求：
1. repair lane 只能由 recoveryLane=enter_repair_lane 或明确 operator action 进入。
2. repair attempt 必须有 trigger、plan、outcome、verificationEvidenceRef。
3. repair 成功必须经过 sandbox verification。
4. high-risk repair 默认需要 operator approval。
5. repair 不得绕过 capability broker、schema write fence、lineage block、manual gate。
6. antibody 只能作为复用建议，不能取代验证。
7. 记录 repair.attempt.started、repair.attempt.completed、antibody.pattern.learned。

测试至少覆盖：
- repair attempt started 字段完整
- repair_succeeded 需要 verificationEvidenceRef
- repair_needs_manual when high-risk approval missing
- repair_failed 不推进主状态为成功
- repair cannot bypass schema write fence
- antibody learned event 字段完整

完成后输出：
- 文件清单
- 测试命令
- 测试结果
- repair safety boundary 摘要
```

---

## Phase 10：OpenAPI facade

### 目标

最后接 HTTP/API，避免 API handler 先污染核心语义。

### 输入文件

- `paperclip_darkfactory_v3_0_external_runs.openapi.yaml`
- `paperclip_darkfactory_v3_0_memory.openapi.yaml`
- `paperclip_darkfactory_v3_0_impl_pack.md`
- `paperclip_darkfactory_v3_0_core_objects.schema.json`

### 输出产物

- `src/api/*`
- `tests/api/*`

### 验收条件

- handler 不直接写 projection store。
- handler 不直接修改 truth object。
- 所有 mutation request 必须校验 `protocolReleaseTag`。
- 所有 error response 必须包含 `protocolReleaseTag`。
- API response 字段必须支持 operator 判断 route/memory/repair/lineage/manual 状态。

### 执行 Prompt

```text
Phase 10：实现 OpenAPI facade。

工作目录：
/home/siyuah/workspace/123

请读取：
- paperclip_darkfactory_v3_0_external_runs.openapi.yaml
- paperclip_darkfactory_v3_0_memory.openapi.yaml
- paperclip_darkfactory_v3_0_impl_pack.md
- paperclip_darkfactory_v3_0_core_objects.schema.json

目标：
实现 HTTP/API facade，但不得让 handler 绕过 domain service。

要求：
1. handler 不直接写 projection store。
2. handler 不直接修改 truth object。
3. 所有 mutation request 必须校验 protocolReleaseTag。
4. 所有 error response 必须包含 protocolReleaseTag。
5. API response 字段必须能支持 operator 判断 route/memory/repair/lineage/manual 状态。
6. colon-style action path 如果框架不兼容，可以在实现层映射为等价 subresource path，但 OpenAPI 需保留或记录兼容策略。

测试至少覆盖：
- POST /external-runs
- GET /external-runs/{runId}
- park
- rehydrate
- route decisions list
- provider failures list
- repair attempts list
- memory search
- memory correct
- memory injections list
- error response protocolReleaseTag

完成后输出：
- 文件清单
- 测试命令
- 测试结果
- OpenAPI compatibility notes
```

---

## Phase 11：Scenario acceptance 与 release gate

### 目标

把 V3.0 文档包与实现推进到可 release-gate 的状态。

### 输入文件

- `paperclip_darkfactory_v3_0_scenario_acceptance_matrix.csv`
- `paperclip_darkfactory_v3_0_test_asset_spec.md`
- `paperclip_darkfactory_v3_0_test_traceability.csv`
- `paperclip_darkfactory_v3_0_bundle_manifest.yaml`
- `paperclip_darkfactory_v3_0_consistency_report.md`

### 输出产物

- `scripts/paperclip_darkfactory_v3_0_contract_consistency_check.*`
- `reports/v3_0_release_gate_report.*`
- `tests/scenarios/*`
- golden timeline JSONL 示例文件

### 验收条件

- manifest 中每个文件存在。
- 非 manifest 自身文件 sha256 匹配。
- event contracts 与 core enums 对齐。
- state matrix 状态来自 core enums。
- OpenAPI mutation request 和 error response 携带 `protocolReleaseTag`。
- runtime config source 可解析。
- `release_blocker=true` 的 scenario 都有测试或 traceability row。
- blocking issue 让 CI fail。

### 执行 Prompt

```text
Phase 11：实现 scenario acceptance 与 release gate。

工作目录：
/home/siyuah/workspace/123

请读取：
- paperclip_darkfactory_v3_0_scenario_acceptance_matrix.csv
- paperclip_darkfactory_v3_0_test_asset_spec.md
- paperclip_darkfactory_v3_0_test_traceability.csv
- paperclip_darkfactory_v3_0_bundle_manifest.yaml
- paperclip_darkfactory_v3_0_consistency_report.md

目标：
实现 release-blocking consistency checker 和 scenario gate。

要求：
1. 检查 manifest 中每个文件存在。
2. 检查 sha256，manifest 自身 SELF_HASH_EXCLUDED 除外。
3. 检查 event contracts 与 core enums 对齐。
4. 检查 state matrix 状态来自 core enums。
5. 检查 OpenAPI mutation request 和 error response 携带 protocolReleaseTag。
6. 检查 runtime config source 可解析。
7. 检查 release_blocker=true 的 scenario 都有测试或 traceability row。
8. 生成机器可读和人可读报告。
9. 任何 blocking issue 应让 CI fail。

测试至少覆盖：
- manifest 缺文件会失败
- manifest hash mismatch 会失败
- event name mismatch 会失败
- undeclared state 会失败
- OpenAPI missing protocolReleaseTag 会失败
- release blocker scenario missing traceability 会失败

完成后输出：
- checker 脚本路径
- 执行命令
- 报告路径
- 当前 gate 是否通过
```

---

## 4. 推荐推进节奏

### 第一轮只做 Phase 0-2

原因：这三步决定后续架构边界。

- Phase 0：理解文档。
- Phase 1：协议常量 / 类型。
- Phase 2：Journal truth path。

这三步完成后再进入状态机和业务流程。

### 第二轮做 Phase 3-4

原因：状态机和 capability/write fence 是安全边界。

- Phase 3：状态机。
- Phase 4：capability broker + schema write fence。

### 第三轮做 Phase 5-9

原因：routing、manual、lineage、memory、repair 是业务能力层。

- Phase 5：routing。
- Phase 6：manual gate。
- Phase 7：lineage。
- Phase 8：memory。
- Phase 9：repair。

### 第四轮做 Phase 10-11

原因：API facade 和 release gate 应该在核心语义稳定后接入。

- Phase 10：OpenAPI facade。
- Phase 11：scenario acceptance / release gate。

---

## 5. 防止 GPT5.5 漂移的规则

每次派活时都加上这些约束：

```text
禁止事项：
1. 不要改写规范文件，除非任务明确要求更新 bundle。
2. 不要新增协议字段而不更新 schema / OpenAPI / traceability。
3. 不要把 runtime config 当成可以削弱 invariants 的机制。
4. 不要让 API handler 直接绕过 domain service 写 truth。
5. 不要让 repair/manual/archive restore 绕过 schema write fence。
6. 不要把 projection store 当成 truth source。
7. 不要声称 release-grade，除非真实 CI、OpenAPI validator、JSON Schema validator、golden timeline 全部通过。
8. 遇到文档冲突必须停止并报告，不要自行选择一个解释继续写。
```

---

## 6. 每阶段完成报告模板

要求 Hermes + GPT5.5 每个阶段都按这个格式报告：

```text
Phase N 完成报告

1. 本阶段目标

2. 输入文件

3. 修改/创建文件

4. 实现摘要

5. 验证命令

6. 验证结果

7. 与 V3.0 文档的对应关系

8. 发现的问题
   - Blocking:
   - Non-blocking:

9. 下一阶段建议

10. 是否可以进入下一阶段
```

---

## 7. 一句话结论

应该拆。

最佳拆法不是按文档章节拆，而是按实现依赖链拆：

```text
文档理解
-> 协议字面量
-> Journal truth path
-> 状态机
-> capability / write fence
-> routing
-> manual gate
-> lineage
-> memory
-> repair
-> API facade
-> scenario / release gate
```

这样 Hermes + GPT5.5 不会被整包文档淹没，也不会一上来写出绕过协议边界的代码。
