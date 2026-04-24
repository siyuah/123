# Paperclip × Dark Factory V3.0 Implementation Pack

状态: informative  
规范版本: 3.0  
protocolReleaseTag: `v3.0-agent-control-r1`  
implPackVersion: `3.0-impl.1`

---

## 1. 目的

本文件定义 V3.0 的参考实现边界，负责把核心规范映射到可施工的 service、storage、API 与 operator surface。

本文件不新增协议真义，只回答三个问题：

1. 核心对象应该落到哪些实现层组件
2. truth path 与 projection 应如何组织
3. API、archive、operator、observability 应如何围绕核心语义装配

---

## 2. 实现边界

V3.0 的实现层必须满足以下边界：

- Journal 仍是唯一 truth path
- Projection 允许重建，不允许反向裁定真相
- HTTP、CLI、operator UI 都只是 facade，不得绕过同一组 domain service
- Route、memory、repair 必须进入可回放的 truth object 与事件链
- Archive / restore 只能恢复 truth-backed 数据，不得恢复无来源的旁路状态

---

## 3. 建议的实现模块

### 3.1 Protocol

- `src/protocol/constants.ts`
- `src/protocol/enums.ts`
- `src/protocol/events.ts`
- `src/protocol/errors.ts`
- `src/protocol/schemas.ts`
- `src/protocol/invariants.ts`

职责：

- 暴露唯一字面量、错误码、事件名与对象 schema
- 为 handler、orchestrator、projection 与 CI 提供统一导入点
- 为 mixed-version writer 拒绝提供 write fence 依据

### 3.2 Journal 与 projection

- `src/journal/journal-service.ts`
- `src/projections/run-view-projection.ts`
- `src/projections/artifact-view-projection.ts`
- `src/projections/lineage-view-projection.ts`
- `src/projections/route-view-projection.ts`
- `src/projections/memory-view-projection.ts`
- `src/projections/repair-view-projection.ts`

职责：

- 先 append truth event，再刷新 projection
- projection 必须可删可重建
- replay 必须能重建 run、artifact、lineage、route、memory、repair 视图

### 3.3 Routing / provider plane

- `src/routing/router-engine.ts`
- `src/routing/route-policy-service.ts`
- `src/routing/fallback-chain-resolver.ts`
- `src/routing/provider-fault-classifier.ts`
- `src/providers/provider-adapter.ts`
- `src/providers/provider-adapter-registry.ts`

职责：

- 计算 `RouteDecision`
- 将 provider 原始故障裁定为 `providerFaultClass`
- 将 fault class 唯一映射到 `recoveryLane`
- 记录 cutover 与 degrade 的 truth record

### 3.4 Memory plane

- `src/memory/memory-extractor.ts`
- `src/memory/memory-sync-service.ts`
- `src/memory/knowledge-graph-service.ts`
- `src/memory/diary-service.ts`
- `src/memory/prompt-context-assembler.ts`
- `src/memory/recovery-bootstrap-service.ts`

职责：

- 提取 `MemoryArtifact`
- 同步 diary / knowledge graph projection
- 生成 `PromptInjectionReceipt`
- 在恢复或新执行前加载允许注入的 artifact

### 3.5 Repair plane

- `src/remediation/repair-lane-service.ts`
- `src/remediation/repair-policy-service.ts`
- `src/remediation/antibody-store.ts`

职责：

- 根据 `recoveryLane=enter_repair_lane` 启动 repair flow
- 产生 `RepairAttempt`
- 在验证通过后再推进主状态
- 记录 `antibody.pattern.learned` 事件，不直接把“学到的经验”当真相

### 3.6 Manual / archive / operator plane

- `src/manual/manual-gate-service.ts`
- `src/archive/archive-catalog-service.ts`
- `src/archive/restore-service.ts`
- `src/api/handlers/*`
- operator CLI / UI facade

职责：

- 处理 park / rehydrate
- 提供 archive search 与 restore
- 暴露 route / memory / repair 的查询与操作面
- 所有 operator 操作必须经过同一组 service 和审计路径

---

## 4. API surface 设计原则

### 4.1 facade 原则

- HTTP handler 不直接改 projection store
- CLI 与 HTTP 共用 domain service
- 错误响应必须显式携带 `protocolReleaseTag`
- 同名对象字段以 `paperclip_darkfactory_v3_0_core_objects.schema.json` 为准

### 4.2 external runs API

`paperclip_darkfactory_v3_0_external_runs.openapi.yaml` 至少应覆盖：

- `POST /api/external-runs`
- `GET /api/external-runs/{runId}`
- `POST /api/external-runs/{runId}:park`
- `POST /api/external-runs/{runId}:rehydrate`
- `GET /api/external-runs/{runId}/route-decisions`
- `GET /api/external-runs/{runId}/provider-failures`
- `GET /api/external-runs/{runId}/repair-attempts`
- `POST /api/external-runs/{runId}:repair`
- `GET /api/archive/search`
- `POST /api/archive/restore`

### 4.3 memory API

`paperclip_darkfactory_v3_0_memory.openapi.yaml` 至少应覆盖：

- `GET /api/memory/artifacts/{memoryArtifactId}`
- `POST /api/memory/artifacts:search`
- `POST /api/memory/artifacts/{memoryArtifactId}:correct`
- `GET /api/external-runs/{runId}/memory-injections`

---

## 5. Storage mapping 原则

V3.0 存储必须拆成至少四类：

1. journal store: 权威 truth log
2. projection store: 面向查询的重建视图
3. policy / registry store: 运行参数与 profile
4. archive store: 冷存与恢复对象目录

约束：

- truth object 只能先写 journal，再异步或同步刷新 projection
- archive catalog 只能索引 truth-backed 对象
- restore 必须带恢复来源与恢复时间戳，不能无来源覆写现有 truth
- memory、route、repair 的 projection 与 run view 一样属于可重建派生层

---

## 6. Operator surface

operator surface 必须覆盖以下能力：

- 查看 run 主状态、attempt 状态与 active blocker
- 查看 route decision、provider failure 与 cutover 历史
- 查看 memory artifact、consent scope、retention、correction 历史
- 查看 repair attempt、验证证据、approval 状态与 antibody 学习历史
- 查看 archive 命中、restore 请求与恢复结果
- 对 manual gate、rehydrate、repair approval 做显式审计

operator surface 不得提供：

- 直接改 projection 的后门
- 绕过 capability broker 的“管理员执行”
- 绕过 schema write fence 的“强制写入”
- 把 revoked 或 out-of-scope memory 标成可注入

---

## 7. Runtime audit 与 observability

至少记录以下指标与审计对象：

### 7.1 Routing

- route decision count by workload
- provider fault count by `providerFaultClass`
- fallback depth distribution
- cutover success rate
- unverifiable degrade invocations

### 7.2 Memory

- extraction acceptance rate
- injection hit / miss rate
- cross-session consent denial count
- retention expiration count
- correction / revocation count

### 7.3 Repair

- repair attempts per run
- repair verification failure rate
- operator approval waits
- antibody reuse rate
- repair regression rate

### 7.4 Release gate

- scenario decision divergence
- scenario fallback rate
- scenario memory injection miss rate
- scenario repair regression rate
- manifest mismatch count

### 7.5 Shadow compare

- weighted high-risk decision divergence
- protected flow deadline crossing divergence
- shadow compare sample coverage
- cutover recommendation threshold breach count

---

## 8. Archive / restore 约束

archive / restore 必须遵守：

1. archive catalog 只收录可追溯 truth-backed 对象
2. restore 必须产生审计记录
3. restore 不得绕过 write fence
4. restore 后的 projection 应可由 journal 或 restore event 重建
5. restore 不得把已 revoked 的对象伪装成 clean 当前值

---

## 9. Source reference keys

本文件为 runtime registry、mapping 和 responsibility matrix 提供以下可解析 source key：

- `impl-pack-api`: 本文第 4 节 API surface 设计原则
- `impl-pack-storage`: 本文第 5 节 Storage mapping 原则
- `impl-pack-operator`: 本文第 6 节 Operator surface
- `impl-pack-observability`: 本文第 7 节 Runtime audit 与 observability
- `impl-pack-shadow`: 本文第 7.5 节 shadow compare 指标与 cutover threshold 观测边界
- `impl-pack-archive`: 本文第 8 节 Archive / restore 约束
