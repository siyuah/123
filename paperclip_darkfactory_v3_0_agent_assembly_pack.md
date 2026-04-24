# Paperclip × Dark Factory V3.0 Agent Assembly Pack

状态: informative  
规范版本: 3.0  
protocolReleaseTag: `v3.0-agent-control-r1`  
agentAssemblyPackVersion: `3.0-assembly.1`

---

## 1. 目的

本文件定义 V3.0 参考装配方式，说明 routing、memory、repair、scenario gate 这些能力如何在不污染核心协议的前提下完成装配。

它是 L2 参考实现包的一部分，不能凌驾于核心规范之上，也不能把具体厂商或模型选择写成协议真义。

---

## 2. 装配原则

- 先有核心对象，再有装配策略
- 先有 truth record，再有 facade 与 UI
- 同一 workload 的 provider/model 选择属于 runtime profile，不属于核心规范
- 默认链路可以给出，但必须能被 registry 替换
- fallback、memory 注入、repair 自动执行都必须受 release gate 与 policy 控制

---

## 3. Workload routing reference profile

### 3.1 workload 分类入口

建议至少支持以下 `workloadClass`：

- `chat`
- `code`
- `reasoning`
- `vision`
- `memory_maintenance`
- `repair`
- `operator_adjudication`

分类输入建议包含：

- 用户输入类型
- 是否包含代码编辑目标
- 是否包含视觉附件
- blast radius 预估
- 是否处于恢复态或人工裁决态

### 3.2 route decision 装配

装配链建议为：

1. classifier 判定 `workloadClass`
2. route policy service 解析 `routePolicyRef`
3. fallback chain resolver 解析可用链路
4. router engine 选出当前执行器
5. append `route.decision.recorded.v1`
6. projection 刷新 route view

### 3.3 provider fault matrix

provider adapter 产生原始错误后，应进入统一 fault classifier，并至少映射到：

- `transient_timeout`
- `transient_5xx`
- `rate_limited`
- `quota_exhausted`
- `auth_invalid`
- `capability_unsupported`
- `context_length_exceeded`
- `response_contract_invalid`
- `provider_unreachable`

随后唯一映射到：

- `retry_same_route`
- `cutover_fallback_route`
- `degrade_low_risk_only`
- `enter_repair_lane`
- `park_manual`
- `fail_terminal`

不得保留未裁决的歧义分支。

---

## 4. Memory artifact pack

### 4.1 最小流水线

建议装配顺序：

1. `MemoryExtractor`
2. `MemorySyncService`
3. `KnowledgeGraphProjector`
4. `DiaryProjectionService`
5. `PromptContextAssembler`
6. `RecoveryBootstrapService`

### 4.2 装配约束

- extractor 只产出候选 artifact，不直接决定跨会话注入资格
- consent、retention、scope 校验必须在注入前执行
- prompt 注入必须留下 `PromptInjectionReceipt`
- recover bootstrap 只能加载仍有效且 scope 合法的 artifact

### 4.3 默认注入策略

默认建议：

- 同 session artifact 可优先注入
- 跨 session artifact 需显式 consent
- 受限 token budget 时优先高 relevance、未过期、未 revoked 的 artifact
- corrected artifact 不应再以旧版本进入 prompt

---

## 5. Repair loop pack

### 5.1 repair lane 装配顺序

建议顺序：

1. recovery lane 判定 `enter_repair_lane`
2. repair policy service 判定是否允许自动修复
3. repair lane service 生成 `RepairAttempt`
4. 在 sandbox 中执行 repair 验证
5. 根据结果推进 `repair_succeeded`、`repair_failed`、`repair_rejected` 或 `repair_needs_manual`
6. 需要时追加 `antibody.pattern.learned.v1`

### 5.2 repair 装配边界

- repair lane 不能直接写最终成功结论
- repair 结果必须经过验证痕迹与主状态机裁决
- 高风险 patch 默认要求 operator approval
- repair lane 不得绕过 capability broker、schema write fence、manual gate 与 lineage block

### 5.3 antibody store

antibody store 应记录：

- 触发 fault class
- 匹配模式摘要
- 验证结果
- 生效范围
- 过期策略

antibody 只能作为复用建议来源，不能取代验证流程。

---

## 6. Scenario acceptance spec

### 6.1 最低场景集合

`paperclip_darkfactory_v3_0_scenario_acceptance_matrix.csv` 至少应覆盖：

1. chat 请求命中 chat route
2. code 修复请求命中 code route
3. vision 输入命中 vision route
4. transient fault 后 fallback 成功
5. quota exhausted 后 route cutover
6. memory extract -> sync -> inject 闭环
7. repair lane 自动修复成功
8. repair lane 失败后进入 manual gate
9. reopened upstream 传播到 consumer block
10. park -> rehydrate -> route re-evaluate 闭环

### 6.2 场景度量

每个场景至少记录：

- expected route
- expected recovery lane
- expected truth objects
- expected blocking behavior
- release blocker 与否
- metrics / threshold key

---

## 7. Operator runbook 约束

runbook 至少应覆盖：

- 如何判定 manual gate 类型
- 如何查看 route、memory、repair 的 truth record
- 如何审批 high-risk repair
- 如何执行 rehydrate
- 如何执行 archive restore
- 如何处理 scenario gate 失败

runbook 不得指导 operator 通过修改 projection 或数据库旁路来“修好”系统。

---

## 8. Source reference keys

本文件为 runtime registry、mapping 和 scenario matrix 提供以下可解析 source key：

- `assembly-pack-routing`: 本文第 3 节 workload routing reference profile
- `assembly-pack-memory`: 本文第 4 节 memory artifact pack
- `assembly-pack-repair`: 本文第 5 节 repair loop pack
- `assembly-pack-scenarios`: 本文第 6 节 scenario acceptance spec
- `assembly-pack-runbook`: 本文第 7 节 operator runbook 约束
- `runtime-design-10.1`: 本文第 3 至第 7 节共同定义的 routing、memory、repair、scenario gate 与 release 参数装配边界
