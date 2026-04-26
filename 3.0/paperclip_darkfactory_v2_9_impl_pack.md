# Paperclip × Dark Factory V2.9 Implementation Pack

**绑定版本**：2.9-impl.1  
**协议绑定**：`v2.9-companion-bound-r1`  
**角色**：本文件是 V2.9 主规范的独立实现 companion；它不新增协议语义，只把实现所需的 API、数据、sidecar、operator、测试与容量要件收口。

---

## 0. 本包解决什么

V2.9 正文已经把“不允许什么”和“必须怎样裁决”写清楚；本 impl 包负责补上这些工程落地点：

1. 把同名字段/状态/事件收口为 machine-readable starter artifacts；  
2. 给出最小 API surface，避免前后端/Bridge/执行面各自发明接口；  
3. 给出 truth / projection / archive 的落库边界，避免不同团队各自建一套“真相源”；  
4. 把 opaque executor 的物理 enforcement 最小要求写实；  
5. 给出 operator surface、park / rehydrate、archive restore 的操作性合同；  
6. 把测试资产、failure injection、golden timeline 的组织形式固化。  

---

## 1. 本包包含的 starter artifacts

| 文件 | 用途 |
|---|---|
| `paperclip_darkfactory_v2_9_core_enums.yaml` | 统一枚举字面量 |
| `paperclip_darkfactory_v2_9_core_objects.schema.json` | 核心对象结构与 required 字段 |
| `paperclip_darkfactory_v2_9_event_contracts.yaml` | 关键事件 envelope 与 payload 最小集合 |
| `paperclip_darkfactory_v2_9_external_runs.openapi.yaml` | 最小 API surface |
| `paperclip_darkfactory_v2_9_runtime_config_registry.yaml` | runtime config registry |
| `paperclip_darkfactory_v2_9_inheritance_matrix.csv` | V2.8/V2.9 继承矩阵 |
| `paperclip_darkfactory_v2_9_responsibility_matrix.csv` | 组件职责边界 |
| `paperclip_darkfactory_v2_9_storage_mapping.csv` | 存储边界与归档路径 |
| `paperclip_darkfactory_v2_9_state_transition_matrix.csv` | 状态迁移 starter matrix |
| `paperclip_darkfactory_v2_9_test_asset_spec.md` | 测试资产说明 |

---

## 2. API surface 最小收口

### 2.1 控制面/外部接口

最小必须具备：

- `POST /api/external-runs`
- `GET /api/external-runs/{runId}`
- `POST /api/external-runs/{runId}:park`
- `POST /api/external-runs/{runId}:rehydrate`
- `GET /api/artifacts/{artifactId}`
- `POST /api/artifacts/{artifactId}:waive-consumption`
- `GET /api/lineage/artifacts/{artifactId}`

要求：

- 所有请求/响应必须带 `protocolReleaseTag` 或可由服务端绑定回写。  
- `park` / `rehydrate` 是工作流合同，不是 UI 标签按钮。  
- `waive-consumption` 只能创建 waiver 记录，不能直接把 artifact 改成 `certified`。  

### 2.2 事件面

最小必须具备以下事件：

- `run.lifecycle.changed.v2`
- `capability.observed.v1`
- `artifact.certification.changed.v1`
- `lineage.invalidation.started.v1`
- `lineage.invalidation.propagated.v1`
- `capsule.preflight.failed.v1`
- `manual_gate.parked.v1`
- `manual_gate.rehydrated.v1`
- `schema.write_fence.rejected.v1`

要求：

- envelope 的 `traceId`、`protocolReleaseTag`、`eventName`、`eventVersion` 必须存在。  
- 同一对象的状态变化必须可被串联成 golden timeline。  

---

## 3. 数据与存储边界

### 3.1 原则

- Journal / artifact certification / waiver record / config registry 属于 truth object。  
- run view / lineage graph view / operator dashboard 属于 projection。  
- archive catalog 是 truth-backed index；冷存储本身不是新真相源。  

### 3.2 建表 / 索引优先级

优先把以下对象落到强约束存储：

1. `journal_events`
2. `artifact_certification`
3. `lineage_edges`
4. `runtime_audit`
5. `waiver_records`
6. `archive_catalog`

这些对象的索引至少要支撑：

- `artifactId -> consumers`
- `consumerRunId -> upstream artifacts`
- `executorSessionId -> observed capabilities`
- `runId -> latest manual gate / park / rehydrate`
- `holdRef -> archive records`

---

## 4. Opaque Executor 的物理 enforcement 最小要求

V2.9 正文已经要求“外部写必须经过 broker”；impl 层至少还要满足以下任一物理强制路径，并产出等价审计：

1. **sidecar forward proxy + no-direct-egress**  
2. **node / pod 级 egress proxy + sandbox deny-all**  
3. **microVM / gVisor / sandbox 网络默认无路由，仅 broker 放行**  

统一要求：

- executor 进程**默认不得**拥有直连公网的路径；  
- 任何 `network_write_brokered_only` 都必须留下 broker receipt 或 broker deny 记录；  
- sidecar / proxy / sandbox 审计流必须能折算为 `observedCapabilitySet`；  
- 若审计流断裂，高风险模式必须退化为 `unverifiable -> manual_hold`，而不是“继续跑但少记点日志”。  

### 4.1 建议的 sidecar/SDK 最小接口

- `AcquireCapabilityLease(session, requestedCapabilities)`
- `RequestEffectIntent(session, semanticIntentId, effectClass, targetRef)`
- `CommitBrokeredDispatch(intentId, providerReceipt)`
- `ReportObservedCapability(session, observedCapability, evidenceRef)`
- `SealAndFlushMailbox(session)`

这些接口的调用结果都必须可回写 Journal 或其 truth-backed audit。

---

## 5. Lineage Graph 与级联失效查询模型

### 5.1 最小查询能力

系统必须能在目标 SLO 内回答：

- 某 artifact 当前认证态是什么？  
- 它有哪些活跃 consumer？  
- 哪些 consumer 是 `certified_only`？  
- 哪些 consumer 已经进入 `reopened_upstream` / `revoked_upstream`？  
- 哪些 consumer 已经产生外部写，需要补偿评估？  

### 5.2 查询实现建议

本 impl 包不强制具体数据库，但要求实现具备：

- `parentArtifactId -> active consumers` 的索引  
- `consumerRunId -> upstream artifacts` 的索引  
- `artifactId + revocationEpoch` 的版本化查询  
- 对 `lineage_invalidation_started` 的幂等传播  
- 对 propagation lag 的监控与重试

---

## 6. Operator Surface 与人工介入

### 6.1 operator UI 最小要素

- run 主状态与 manual gate
- artifactCertificationState
- inputDependencyState
- profileConformanceStatus
- capsuleHealth
- traceId / runId / attemptId / artifactId 串联视图
- restricted evidence 的受限摘要与 access request 入口
- park / rehydrate / approve waiver / incident linkage

### 6.2 rehydrate 合同

rehydrate 必须显式产生：

- 新的 `attemptId`
- 与旧 attempt 的 lineage/trace 关联
- rehydrate 原因与操作人
- 旧资源释放证明
- 当前 manual gate 是否已解除

---

## 7. Runtime Config Registry 治理

- 所有 release gate 使用的阈值必须来自 registry。  
- 任何 tenant / workflow override 必须携带 owner、scope、expiry、审计记录。  
- 默认值可更严格，不可更松到破坏正文语义。  

---

## 8. 测试与形式化验证

### 8.1 测试资产

执行团队应先使用 `paperclip_darkfactory_v2_9_test_asset_spec.md` 固定：

- case id
- fixture layout
- golden timeline 格式
- failure injection hook
- mock broker / fake callback / fake archive restore

### 8.2 形式化验证最低边界

至少对以下不变量做模型级验证或等价强度 property-based testing：

1. 单 writer / stale token 不复活  
2. reopen / revoke 不改写既有历史，只增加更高版本事实  
3. revoked upstream 不放行新的 high-risk primary write  
4. poisoned capsule hash 不出现 blind retry 环  
5. write-fence 阻止旧 writer 覆盖新语义对象  

---

## 9. Archive / Restore / Hold

最小要求：

- mailbox/Journal/artifact/runtime audit 都要有 searchable archive；  
- 归档不等于删除；  
- hold record 存在时不得物理清除；  
- restore SLA 必须被测量；  
- operator 必须能基于 object id / run id / artifact id 检索冷数据。  

---

## 10. Walking Skeleton 开工顺序

最推荐的启动路径不是全量铺开，而是按以下骨架顺序：

1. `createExternalRun -> claim -> attempt boot -> journal append`
2. `opaque executor capability lease -> brokered dispatch -> runtime audit`
3. `artifact tentative -> certified`
4. `artifact certified -> reopened -> lineage invalidation -> downstream block`
5. `capsule hard-token preflight -> poisoned breaker`
6. `park -> rehydrate`
7. `archive -> restore -> operator query`

任何阶段都不应跳过 machine-readable bundle 与 golden timeline 更新。
