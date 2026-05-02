# Dark Factory / Paperclip 吸收 Phoenix V4.8 经验的优化实施文档

状态: implementation-plan  
适用项目: `/home/siyuah/workspace/123` 与 `/home/siyuah/workspace/paperclip_upstream`  
参考材料: Phoenix V4.8 图文架构提炼、Dark Factory V3.0 bundle、内部预览服务、Paperclip bridge HTTP 集成测试  
目标读者: 实现工程师、测试工程师、operator、协议审计人员

---

## 0. 总体判断

Phoenix V4.8 的强项是运行时产品能力：模型路由、信用兜底、自愈、Guardrail、结构化记忆、并行执行、自动适配。

Dark Factory / Paperclip 当前的强项是协议可信度：Journal truth path、schema / OpenAPI / enum / state matrix、projection、release gate、bridge 集成测试。

本优化计划的原则是：

```text
保留 Dark Factory 的协议内核
  + 吸收 Phoenix V4.8 的运行时运营层
  = 可审计、可恢复、可解释、可产品化的 Agent Control Plane
```

不要照搬 Phoenix 的 11 个大模块。当前项目应该优先吸收 6 个能力：

1. Provider 健康监控与信用兜底
2. 路由决策可解释化
3. Guardrail 与审批分级
4. 故障剧本与自愈闭环
5. 结构化 Journal Facts
6. 契约漂移检测与自动适配报告

---

## 1. 当前项目基线

### 1.1 现有资产

`/home/siyuah/workspace/123` 已经具备：

- FastAPI 内部预览服务：`server.py`
- 健康检查：`GET /api/health`，免认证
- 业务 API 鉴权：除 health 外需要 `X-API-Key`
- Journal truth path：`journal_data/preview.jsonl`
- Projection：从 Journal 推导 runs、attempts、route decisions 等视图
- 运维工具：`tools/journal_admin.py`
- 规范资产：
  - `paperclip_darkfactory_v3_0_core_spec.md`
  - `paperclip_darkfactory_v3_0_invariants.md`
  - `paperclip_darkfactory_v3_0_core_enums.yaml`
  - `paperclip_darkfactory_v3_0_core_objects.schema.json`
  - `paperclip_darkfactory_v3_0_event_contracts.yaml`
  - `paperclip_darkfactory_v3_0_state_transition_matrix.csv`
  - `paperclip_darkfactory_v3_0_runtime_config_registry.yaml`
  - `paperclip_darkfactory_v3_0_external_runs.openapi.yaml`
  - `paperclip_darkfactory_v3_0_memory.openapi.yaml`
- 测试入口：
  - `tests/test_validate_v3_bundle.py`
  - `tests/test_v3_runtime.py`
  - `tests/test_v3_http_server_security.py`
  - `tests/test_v3_http_server_load.py`
  - `tests/test_v3_journal_admin.py`
- Paperclip bridge 集成测试：
  - `/home/siyuah/workspace/paperclip_upstream/packages/plugins/integrations/dark-factory-bridge`

### 1.2 当前短板

当前项目偏“协议正确”和“预览服务可用”，但运行时运营层还不够完整：

| 短板 | 表现 | 从 Phoenix 可吸收的经验 |
|---|---|---|
| Provider 状态不够系统 | provider 故障、欠费、超时、429/5xx 没有形成统一 health record | Credit Monitor |
| 路由解释不够产品化 | RouteDecision 有协议价值，但 operator 读起来还不够直接 | 五档路由、reason codes |
| 高风险动作分级不足 | API key 鉴权不能替代操作审批 | P0/P1/P2 审批 |
| 故障恢复偏手工 | journal mismatch、projection drift、bridge timeout 等需要人工判断 | FaultPlaybook / Self-heal |
| 记忆与事实可进一步结构化 | Memory Artifact 已有规范方向，但运行层 facts 抽取可以强化 | Structured Memory |
| 契约漂移检测可更自动化 | YAML/schema/OpenAPI/bridge 之间 drift 需要更明确报告 | Auto-Fusion / compatibility report |

---

## 2. 目标架构

### 2.1 优化后的控制平面流转

```text
外部请求 / Paperclip bridge 调用
  -> API 鉴权 X-API-Key
  -> Guardrail 预检查
  -> RouteDecision 生成
  -> ProviderHealth 检查
  -> Execution / Park / Rehydrate / Repair
  -> Journal 追加 truth event
  -> Projection 重建
  -> FaultPlaybook / RepairLane 按需介入
  -> Operator View / Bridge Response
```

### 2.2 新增概念对象

建议新增或强化以下概念对象，全部必须能落到 Journal 或可回放的派生视图中：

| 对象 | 作用 | 备注 |
|---|---|---|
| `ProviderHealthRecord` | 记录 provider 可用性、错误类别、信用状态 | 借鉴 Phoenix CreditMonitor，但命名更通用 |
| `RouteDecisionReason` | 解释路由为什么发生 | 给 operator 和测试使用 |
| `GuardrailDecision` | 记录操作是否允许、需要确认还是阻断 | 不能只存在内存里 |
| `FaultPlaybookRun` | 记录某个故障剧本被触发、执行、完成或升级 | 先做半自动，不急着全自动 |
| `StructuredJournalFact` | 从 Journal 抽取稳定事实 | 用于 operator view、记忆注入、审计 |
| `ContractDriftReport` | 汇总 schema / OpenAPI / enum / bridge 测试差异 | 作为 release gate 证据 |

---

## 3. 阶段拆分

## 阶段 A: Provider 健康监控与信用兜底

### A.1 目标

把 Phoenix 的 `CreditMonitor` 思路改造成 Dark Factory 的 `ProviderHealthMonitor`。它不只判断欠费，还要判断 provider 是否健康、是否触发降级、是否需要记录恢复车道。

### A.2 具体步骤

1. 在核心规范中加入 provider health 语义。
2. 在 schema 中加入 `ProviderHealthRecord`。
3. 在 event contracts 中加入 provider health 事件。
4. 在 runtime config registry 中注册 provider 健康检查阈值。
5. 在 `server.py` 或 control plane 层暴露 health projection。
6. 在 tests 中加入 provider 失败分类用例。
7. 在 bridge 集成测试中覆盖 provider unavailable / fallback 场景。

### A.3 可执行子任务

| 子任务 ID | 子任务 | 修改位置 | 验收方式 | 中文备注 |
|---|---|---|---|---|
| A-01 | 定义 `ProviderHealthRecord` 字段 | `paperclip_darkfactory_v3_0_core_objects.schema.json` | schema 校验通过 | 字段至少包括 providerId、status、faultClass、lastFailureAt、recoveryLane、fallbackEligible |
| A-02 | 增加 provider health enum | `paperclip_darkfactory_v3_0_core_enums.yaml` | enum parity 测试通过 | status 建议含 healthy、degraded、exhausted、unreachable、unknown |
| A-03 | 增加事件契约 | `paperclip_darkfactory_v3_0_event_contracts.yaml` | bundle validate 通过 | 事件建议为 `provider.health.observed`、`provider.fallback.activated`、`provider.recovered` |
| A-04 | 加入运行配置 | `paperclip_darkfactory_v3_0_runtime_config_registry.yaml` | registry source 可解析 | 阈值包括 timeout、429 次数、402/403 欠费判定、fallback 开关 |
| A-05 | 实现投影视图 | `dark_factory_v3/projection.py` 或相关模块 | health projection 可查询 | 不要把 health 只放日志，必须能重建 |
| A-06 | API 暴露 provider health | `server.py` | `GET /api/provider-health` 返回视图 | 可以先只读，后续再支持 operator 操作 |
| A-07 | 单元测试 | `tests/test_v3_runtime.py` 或新增测试 | pytest 通过 | 覆盖 401/402/403/429/5xx/timeout |
| A-08 | bridge 场景测试 | Paperclip bridge tests | pnpm test 通过 | bridge 需要能识别 fallback 或 degraded 响应 |

### A.4 Definition of Done

- Provider 状态能从 Journal 重放得到。
- 402/403 类欠费能被归类为 `exhausted`。
- 429 能被归类为 `rate_limited` 或 `degraded`。
- fallback 被激活时必须有 truth event。
- operator 可以查看最近一次失败、失败类别和恢复建议。

---

## 阶段 B: 路由决策可解释化

### B.1 目标

吸收 Phoenix 五档路由的解释能力，但不照搬具体模型。Dark Factory 应该增强 `RouteDecision`，让每次路由都能回答：

- 为什么这样路由？
- 风险等级是什么？
- 成本等级是什么？
- 是否需要人工确认？
- 是否允许 fallback？
- 使用了哪些输入信号？

### B.2 具体步骤

1. 给 `RouteDecision` 增加解释字段。
2. 定义 `reason_codes` 字典。
3. 定义风险等级与成本等级。
4. 将 route decision 的输入信号写入 Journal。
5. 更新 projection 与 API response。
6. 更新 bridge 适配字段。
7. 增加测试矩阵。

### B.3 可执行子任务

| 子任务 ID | 子任务 | 修改位置 | 验收方式 | 中文备注 |
|---|---|---|---|---|
| B-01 | 设计 `RouteDecisionReason` | core schema | schema validate | 建议字段：reasonCode、sourceSignal、confidence、humanReadableNote |
| B-02 | 增加风险等级 enum | core enums | enum parity | 建议：low、medium、high、critical |
| B-03 | 增加成本等级 enum | core enums | enum parity | 建议：low_cost、standard、expensive、operator_confirmed |
| B-04 | 更新 event contract | event contracts | validate_v3_bundle 通过 | route decision event 必须携带 reason codes |
| B-05 | 更新 projection | projection module | projection 测试通过 | 投影里保留 reason codes，方便 operator 看 |
| B-06 | 更新 HTTP response | `server.py` / OpenAPI | OpenAPI 与 schema 对齐 | route decision view 不要只返回模型/状态 |
| B-07 | 更新 bridge 映射 | paperclip bridge plugin | bridge tests 通过 | bridge 日志中应展示 route reason |
| B-08 | 增加场景测试 | scenario matrix / tests | release gate 通过 | 覆盖 code、memory、repair、archive、manual gate |

### B.4 推荐 reason_codes

| reason code | 含义 |
|---|---|
| `workload_class_code` | 请求声明为代码类任务 |
| `requires_capability_lease` | 执行前需要 capability lease |
| `provider_degraded` | 首选 provider 降级 |
| `provider_exhausted` | 首选 provider 欠费或不可用 |
| `manual_gate_required` | 需要人工审批 |
| `high_risk_write` | 涉及高风险写路径 |
| `memory_injection_required` | 需要注入记忆 artifact |
| `repair_lane_required` | 需要进入 repair lane |
| `fallback_allowed` | 当前策略允许 fallback |
| `fallback_blocked_by_policy` | 策略禁止 fallback |

### B.5 Definition of Done

- 每条 RouteDecision 至少有一个 reason code。
- 高风险路径必须显式说明是否需要 approval。
- fallback 不是隐式行为，必须有 `fallback_allowed` 或 `fallback_blocked_by_policy`。
- bridge 日志能读出路由原因。

---

## 阶段 C: Guardrail 与审批分级

### C.1 目标

把 Phoenix 的 P0/P1/P2 安全审批改造成 Dark Factory operator action guardrail。

### C.2 分级建议

| 等级 | 操作类型 | 处理方式 | 中文备注 |
|---|---|---|---|
| P0 | 删除 Journal、覆盖配置、清空 projection、密钥变更、绕过 schema fence | 双重确认 + truth event | 这类操作会影响协议真相或安全边界 |
| P1 | journal backup、retain、repair trigger、archive、manual waiver、rehydrate | 单次确认 + 审计事件 | 这类操作可以执行，但必须留痕 |
| P2 | health、read、projection query、普通 run create | 自动通过 | 只读或低风险操作 |

### C.3 具体步骤

1. 定义 `GuardrailDecision` schema。
2. 给 operator API 增加 guardrail precheck。
3. 高风险操作返回 `requires_confirmation`。
4. confirmation request 必须携带 traceId、operationId、确认级别。
5. 所有 guardrail decision 写入 Journal。
6. OpenAPI 标注哪些接口需要审批。

### C.4 可执行子任务

| 子任务 ID | 子任务 | 修改位置 | 验收方式 | 中文备注 |
|---|---|---|---|---|
| C-01 | 增加 approval level enum | core enums | enum parity | P0/P1/P2 用协议枚举，不要写死在 server |
| C-02 | 增加 `GuardrailDecision` | core schema | schema validate | 字段包括 operation、level、decision、reason、confirmationRequired |
| C-03 | 增加 guardrail event | event contracts | validate 通过 | 如 `guardrail.decision.recorded` |
| C-04 | API 中间件或 helper | `server.py` | security tests 通过 | 先覆盖 journal admin 相关 API 或未来 operator API |
| C-05 | OpenAPI 标注审批 | OpenAPI 文件 | OpenAPI lint | 每个高风险接口说明审批需求 |
| C-06 | 测试危险动作 | `tests/test_v3_http_server_security.py` | pytest 通过 | 无确认时必须拒绝 P0/P1 |
| C-07 | 文档 runbook | `docs/internal_preview_runbook.md` | 人工审查 | operator 知道如何确认和回滚 |

### C.5 Definition of Done

- P0/P1/P2 规则写入规范资产。
- Guardrail 决策可回放。
- 未授权或未确认的高风险操作无法执行。
- 所有拒绝响应携带 `protocolReleaseTag`。

---

## 阶段 D: FaultPlaybook 与半自动自愈

### D.1 目标

不要一开始做 Phoenix 那种完整自动进化。先做“故障剧本”：系统遇到常见故障时，可以归类、记录、给出恢复步骤，部分场景允许自动执行低风险恢复。

### D.2 第一批故障剧本

| 故障 | 触发条件 | 恢复建议 |
|---|---|---|
| API key 缺失 | 非 health 请求无 `X-API-Key` 或 key 错误 | 提示设置 `DF_API_KEY` 或 `DF_API_KEY_FILE` |
| Journal sequence mismatch | verify-journal 发现 sequence 不符合预期 | 标记 validator mismatch 或 projection mismatch，输出检查命令 |
| Projection drift | projection 与 journal 重放不一致 | 重新 rebuild projection，生成 drift report |
| Provider exhausted | 401/402/403 或欠费 JSON | fallback 或通知 operator |
| Provider timeout | 超时超过阈值 | retry、降级、记录 degraded |
| Bridge timeout | Paperclip bridge 调用超时 | probe server health、检查 API key、输出 bridge log 指引 |
| Schema write fence violation | 写入对象不符合 schema | 阻断写入，返回 schema path 与字段 |
| Capability lease missing | attempt 未获得 lease | 阻断 high-risk path，要求重新 claim |

### D.3 可执行子任务

| 子任务 ID | 子任务 | 修改位置 | 验收方式 | 中文备注 |
|---|---|---|---|---|
| D-01 | 定义 `FaultClass` | core enums | enum parity | 不要用自由文本散落各处 |
| D-02 | 定义 `FaultPlaybookRun` | core schema | schema validate | 记录 playbookId、faultClass、actions、outcome |
| D-03 | 增加 fault events | event contracts | validate 通过 | `fault.detected`、`fault.playbook.started`、`fault.playbook.completed` |
| D-04 | 实现 playbook registry | `dark_factory_v3/` 新模块 | 单元测试通过 | 先做纯函数，不急着执行真实修复 |
| D-05 | 接入 server 错误响应 | `server.py` | HTTP tests 通过 | 错误响应附带 faultClass 和 operatorHint |
| D-06 | 增加 journal admin 检查 | `tools/journal_admin.py` | journal tests 通过 | backup/retain/verify 可返回故障剧本建议 |
| D-07 | bridge 错误映射 | Paperclip bridge | pnpm test 通过 | bridge 应展示 faultClass，而不是只报网络错误 |

### D.4 Definition of Done

- 常见故障有标准 faultClass。
- 错误响应给 operator 可执行提示。
- 故障剧本运行结果写入 Journal。
- 自动恢复只覆盖低风险动作，高风险动作仍走 Guardrail。

---

## 阶段 E: 结构化 Journal Facts

### E.1 目标

把 Phoenix 的 Structured Memory 改造成 Dark Factory 的 Structured Journal Facts。重点不是“记住聊天”，而是从 truth events 中抽取可审计事实。

### E.2 建议事实类型

| Fact 类型 | 来源 | 用途 |
|---|---|---|
| `run.lifecycle` | run / attempt events | 展示当前生命周期 |
| `provider.health` | provider events | 判断 provider 是否健康 |
| `route.reason` | route decision events | 解释路由原因 |
| `memory.injection` | memory events | 审计 prompt 注入来源 |
| `repair.outcome` | repair events | 评估自愈效果 |
| `operator.action` | guardrail / admin events | 审计人工操作 |
| `projection.integrity` | projection rebuild / verify | 判断视图可信度 |

### E.3 可执行子任务

| 子任务 ID | 子任务 | 修改位置 | 验收方式 | 中文备注 |
|---|---|---|---|---|
| E-01 | 定义 `StructuredJournalFact` | core schema | schema validate | 包含 factId、sourceEventIds、category、confidence、retention |
| E-02 | 定义 fact extraction event | event contracts | validate 通过 | facts 也要可追溯 |
| E-03 | 实现 facts extractor | `dark_factory_v3/` 新模块 | 单元测试通过 | 输入 journal events，输出 facts |
| E-04 | 增加 projection facts 视图 | projection module | projection tests | facts 是派生视图，不要替代 truth event |
| E-05 | 增加 API 查询 | `server.py` | HTTP tests | `GET /api/facts` 可按 category 查询 |
| E-06 | 更新 memory OpenAPI | memory OpenAPI | OpenAPI/schema 对齐 | 和 MemoryArtifact / PromptInjectionReceipt 对齐 |
| E-07 | bridge 消费 facts | Paperclip bridge | pnpm test | bridge 可读取 route/provider facts |

### E.4 Definition of Done

- facts 能从 journal 重建。
- 每条 fact 能追溯 source event。
- facts 有置信度和保留策略。
- facts 不允许绕过核心状态机。

---

## 阶段 F: 契约漂移检测与自动适配报告

### F.1 目标

吸收 Phoenix Auto-Fusion 的“扫描、对比、生成报告”思路，但不要自动乱改协议。Dark Factory 应该做 Contract Drift Report，先报告，再由人决定是否修。

### F.2 检查范围

| 检查对象 | 需要对齐的来源 |
|---|---|
| enum literal | `core_enums.yaml`、state matrix、event contracts、runtime code |
| schema object | core schema、OpenAPI response、server response |
| protocolReleaseTag | create/park/rehydrate/error/event/bundle manifest |
| route decision fields | schema、projection、OpenAPI、bridge logs |
| provider health fields | schema、event、projection、API |
| memory fields | memory OpenAPI、MemoryArtifact schema、PromptInjectionReceipt |
| release blockers | scenario matrix、pytest、bridge tests |

### F.3 可执行子任务

| 子任务 ID | 子任务 | 修改位置 | 验收方式 | 中文备注 |
|---|---|---|---|---|
| F-01 | 扩展 bundle validator | `tools/validate_v3_bundle.py` | validate tests 通过 | 加入新增对象和字段检查 |
| F-02 | 生成 drift report | 新工具 `tools/v3_contract_drift_report.py` | 输出 markdown/json | 报告要有文件、字段、期望、实际 |
| F-03 | 检查 bridge contract | Paperclip bridge tests | pnpm test | bridge 不可硬编码猜测 enum |
| F-04 | 加入 release readiness | `tools/v3_release_readiness.py` | readiness tests | drift 为 blocker 时不得 release |
| F-05 | 更新 docs | `docs/v3_release_readiness.md` | 人工审查 | 明确哪些 drift 是阻断 |
| F-06 | CI 接入 | `.github/workflows` | CI 通过 | 先报告，后续再允许自动修复 |

### F.4 Definition of Done

- drift report 同时有 JSON 和 Markdown。
- 报告能指出具体文件和字段。
- release blocker drift 会阻断发布。
- bridge 测试从权威 YAML/schema 读取值，不硬编码猜测。

---

## 4. 推荐实施顺序

### 4.1 最小可交付版本

优先做这 4 个子任务，能最快产生价值：

1. B-01 到 B-06：RouteDecision 可解释化
2. A-01 到 A-06：ProviderHealthRecord 与 API 视图
3. C-01 到 C-04：GuardrailDecision 与审批分级
4. F-01 到 F-02：ContractDriftReport

### 4.2 4 周拆分

| 周期 | 重点 | 交付物 |
|---|---|---|
| 第 1 周 | 路由解释 + ProviderHealth schema/event/projection | schema、event、projection、API 初版 |
| 第 2 周 | Guardrail + FaultPlaybook 初版 | 审批分级、故障分类、错误响应 operatorHint |
| 第 3 周 | StructuredJournalFacts + bridge 消费 | facts extractor、facts API、bridge 测试 |
| 第 4 周 | ContractDriftReport + release gate | drift 工具、readiness 集成、文档更新 |

### 4.3 不建议优先做的内容

| 内容 | 原因 |
|---|---|
| 完整 Phoenix 模型矩阵 | 当前项目重点不是多模型产品路由 |
| 自动进化抗体库 | 风险高，容易产生不可审计行为 |
| GitHub 自动合并 PR | 当前不应让控制平面直接写 GitHub |
| 任意代码沙箱执行 | 需要更严格安全设计，先不做 |
| 大型 UI 面板 | 先把 REST/operator facts 做稳，再设计 UI |

---

## 5. 测试策略

### 5.1 Python 侧

建议每阶段至少增加以下测试：

```bash
cd /home/siyuah/workspace/123
source .venv/bin/activate
pytest
```

重点测试：

| 测试 | 目的 |
|---|---|
| schema validation | 新对象字段合法 |
| event contract validation | 新事件可被解析 |
| projection replay | Journal 能重建 provider/route/guardrail/facts |
| HTTP security | 未授权、未确认、高风险动作被阻断 |
| load test | 新 projection 不显著拖慢 health/query |

### 5.2 Bridge 侧

```bash
cd /home/siyuah/workspace/paperclip_upstream/packages/plugins/integrations/dark-factory-bridge
pnpm test
```

重点检查：

- bridge 是否识别 route reason codes
- bridge 是否识别 provider health / fallback
- bridge 是否正确处理 faultClass
- bridge 是否仍通过 probe、lease、park、rehydrate、resume

### 5.3 Release gate

发布前必须跑：

```bash
cd /home/siyuah/workspace/123
source .venv/bin/activate
python3 tools/validate_v3_bundle.py
python3 tools/v3_release_readiness.py
python3 tools/v3_contract_drift_report.py --format markdown
pytest
```

中文备注：如果 `v3_contract_drift_report.py` 报告 blocker，不允许通过“运行参数”绕过，只能修正协议资产或实现。

---

## 6. 文档更新清单

每个阶段完成后要同步更新：

| 文档 | 更新内容 |
|---|---|
| `README.md` | 新能力总览 |
| `QUICKSTART.md` | 新 API、新 operator 操作 |
| `docs/internal_preview_runbook.md` | ProviderHealth、Guardrail、FaultPlaybook 运维步骤 |
| `docs/v3_release_readiness.md` | 新 release gate |
| `paperclip_darkfactory_v3_0_core_spec.md` | 新核心语义 |
| `paperclip_darkfactory_v3_0_impl_pack.md` | 参考实现说明 |
| `paperclip_darkfactory_v3_0_agent_assembly_pack.md` | bridge / agent 装配说明 |
| OpenAPI 文件 | 新 API surface |

---

## 7. 风险与控制

| 风险 | 控制方式 |
|---|---|
| 模块膨胀 | 每阶段必须有可运行测试和 API/Projection 证据 |
| 自动恢复越权 | 所有恢复动作经过 Guardrail；P0/P1 不自动执行 |
| facts 污染 truth path | facts 是派生视图，不替代 Journal truth event |
| provider 错误误判 | 保存原始状态码、错误体摘要和 providerFaultClass |
| bridge drift | bridge 测试从权威 YAML/schema 读取协议值 |
| release gate 过重 | 先 report，再逐步把 blocker 接入 gate |

---

## 8. 最终目标图

```text
Paperclip / 外部调用
  |
  v
FastAPI Preview Server
  |
  +--> Auth: X-API-Key
  |
  +--> GuardrailDecision
  |      - P0: 双确认
  |      - P1: 单确认
  |      - P2: 自动通过
  |
  +--> RouteDecision
  |      - reason_codes
  |      - risk_level
  |      - cost_level
  |      - fallback_policy
  |
  +--> ProviderHealthMonitor
  |      - healthy / degraded / exhausted / unreachable
  |      - fallback activation
  |
  +--> Execution / Park / Rehydrate / Repair
  |
  +--> Journal Truth Event
  |
  +--> Projection
  |      - runs
  |      - attempts
  |      - route decisions
  |      - provider health
  |      - guardrail decisions
  |      - structured facts
  |
  +--> FaultPlaybook
  |      - operatorHint
  |      - repair lane
  |
  +--> Bridge / Operator / Release Gate
```

---

## 9. 结论

Phoenix V4.8 最值得借的是“运行时运营层”，不是它的大目录结构。

Dark Factory / Paperclip 最应该保持的是“协议真相层”，不能为了产品化能力牺牲 Journal、schema、OpenAPI、enum、state matrix、projection 和 release gate。

最佳路线是：

```text
第一优先级: 可解释路由 + ProviderHealth + Guardrail
第二优先级: FaultPlaybook + StructuredJournalFacts
第三优先级: ContractDriftReport + release gate
第四优先级: UI / 自动修复 / 更复杂的并行执行
```

这样做的结果是：项目既保留当前 V3.0 的严谨性，又吸收 Phoenix V4.8 的实用运行能力。
