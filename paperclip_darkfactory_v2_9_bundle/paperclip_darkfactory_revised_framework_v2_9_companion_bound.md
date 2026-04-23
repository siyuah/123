
# Paperclip × Dark Factory 修订版框架 V2.9

**版本**：2.9  
**状态**：Draft for implementation  
**定位**：V2.9 在 V2.8 已经把默认策略、裁决算法、测量口径、兼容规则与异常路径压成实现合同的基础上，继续收口四类仍可能击穿“执行真相”的边界：**任意代码执行的 effect 识别/拦截边界、跨 Run 级联失效、LLM provider 硬上下文上限、以及 runtime profile 自证与混部迁移**。  
**适用范围**：若与 V2.8 冲突，以本稿为准；若本稿未改写相关条款，则继承 V2.8；若本稿内部冲突，以优先级更高的规范层与更保守的安全裁决为准。  

---

## 0. V2.9 相对 V2.8 的一句话变化

V2.9 的重点，不再是继续补一般性的“默认策略”，而是把 V2.8 里仍可能让副作用在事实合同之外逃逸的地方，继续压成**运行时可证明、跨任务可传播、遇到物理硬边界时不会静默崩溃**的协议：

1. **新增 opaque executor（bash / python / 通用代码执行器）合同：外部写不再依赖静态工具标签，而必须穿过 capability lease 与 brokered effect boundary。**  
2. **新增 runtime profile self-proof：声明的 profile 不再只靠配置自报，而必须和运行时观测到的 capability 对账。**  
3. **新增 Artifact Certification + Lineage Invalidation：Run 完成不再等于其产物对所有下游都可直接信任。**  
4. **新增跨 Run 级联失效协议：上游 reopen / revoke 后，下游必须阻断新高风险写、标脏、补偿评估或进入人工裁决。**  
5. **Capsule 从 V7 升级到 V8：语义预算继续保留，但增加 provider hard-token preflight 与 context-poison circuit breaker。**  
6. **新增 Journal / Mailbox 生命周期合同：把“权威真相源”与“热存储期限”解耦，要求可检索归档而不是隐式消失。**  
7. **新增 mixed deployment write-fence：旧 writer 不得在会丢字段或误解释新语义的对象上继续拿写权。**  
8. **新增 Trace / Span 传播与 watermark gap 告警基线，避免状态机正确但线上不可诊断。**  
9. **新增 parked manual mode：人工 SLA 失效时释放计算资源，但不释放真相责任。**  
10. **shadow compare 从“只比结构化决策”升级为“结构化决策 + timing profile + deadline crossing”。**  
11. **新增 JSON 参考样例与形式化验证基线，降低跨团队实现歧义。**  
12. **新增性能退让策略：SLO 打不过一致性时，只能背压、分级准入、manual hold，不能偷降安全语义。**

> **一句话版本**：V2.9 解决的不是“这条规则怎么写更漂亮”，而是“bash/python 这种图灵完备执行器、跨 Run 依赖链、LLM 硬上限与灰度混部，能否仍被拉回到同一套可审计的 execution truth 合同里”。

---

## 1. 结论先行

V2.9 继续坚持方案 B，并保持三层边界：

- **Paperclip**：治理面，负责身份、审批、预算、风险接受、人工裁决入口、产物认证状态展示、证据访问审批与依赖图治理。  
- **Dark Factory**：执行面，负责 runtime、Journal、effects、capability broker、recovery、adjudication、evidence、cleanup、certification 与 execution truth。  
- **Bridge**：集成面，负责输入/输出映射、回调验签、幂等去重、lineage 事件传播与最小操作性状态，不升级为 committed truth source。  

V2.9 的核心立场继续保持，并补充三条新的硬原则：

- 该强一致的地方必须强一致。  
- 该异步的地方必须明示异步。  
- 该不确定的地方必须以 `unknown`、`manual_*`、`tentative`、`reopened` 或更保守路径表达，不得假装精确。  
- **effect 必须尽可能在副作用逃逸前被识别和拦截，而不是在逃逸后才靠 mailbox 收尸。**  
- **“Run 已完成”与“产物已认证”必须分开建模；下游是否可消费，取决于认证状态与依赖策略，而不是只看上游 terminal。**  
- **语义预算与 provider 物理硬上限不是同一回事；前者可以近似，后者必须以 provider/model 绑定的硬预检约束。**  

---

## 2. V2.9 继承什么、修正什么

### 2.1 继续继承的部分

以下判断继续成立：

- 方案 B 不变：Paperclip 管治理，Dark Factory 管执行，Bridge 管最小集成状态。  
- Run 继续只有**一个权威主状态机**。  
- Journal 继续是**唯一权威提交真相源**。  
- `same_attempt_retry / micro_recovery / full_rehearsal` 三条恢复车道继续存在。  
- `primary | compensation | probe` 继续是统一 `effectType`。  
- typed manual gate 继续是强约束。  
- sanitize-by-construction 继续是主路径。  
- feature flags + off-path compare + cutover / rollback gates 继续是上线主路径。  
- 空 mailbox、无 callback、无 probe 继续只表达“未证实”，不能表达“未发生”。  

### 2.2 相对 V2.8 的修正

V2.9 重点把下列内容从“单 Run 内的严谨”推进到“面对任意代码执行、依赖传播和物理边界时仍不分叉”：

- 把 profile 从**静态标签**推进到**运行时 capability 对账**。  
- 把 high-risk reopen 从**单 Run 正确**推进到**跨 Run 不会毒化传播**。  
- 把 `carryOverBudgetUnit` 从**语义预算声明**推进到**provider hard-limit preflight 合同**。  
- 把 retention 从**组件内 TTL**推进到**逻辑保留、可检索归档与 hold 约束**。  
- 把 “实现建议”推进到**trace 传播、gap 告警、参考 schema、模型检查基线**。  
- 把人工介入从**流程停住**推进到**资源可以 park、真相不能丢、恢复必须显式 rehydrate**。  
- 把 schema evolution 从**读时保守解释**推进到**写时版本围栏与混部写权控制**。  
- 把 shadow compare 从**只看结构化裁决**推进到**同时看 timing profile 与 deadline crossing**。  

---

## 3. 规范层级、冲突优先级与默认规则来源

### 3.1 规范层级

V2.9 继续采用四层优先级体系，优先级从高到低：

1. **L1 Safety Invariants**：安全、真相、认证与依赖隔离不变量，任何实现不得违反。  
2. **L2 Protocol Contracts**：claim、mailbox、Journal、callback、lineage、capability broker、schema 等协议合同。  
3. **L3 Default Policy Profiles**：官方默认 profile、capability envelope、默认阈值与默认 fallback。  
4. **L4 Operational Guidance**：推荐 rollout、实现建议、观测建议、形式化验证建议。  

解释规则：

- L1 与 L2 冲突时，以 L1 为准。  
- L3 不得削弱 L1 / L2。  
- L4 不得被实现团队误读为协议。  
- “更严格者为准”只适用于安全边界、访问边界与认证边界；不适用于随意增补流程状态。  

### 3.2 关键词语义

- **MUST**：不满足即视为协议违规。  
- **SHOULD**：默认必须实现；若不实现，必须有审计可见的偏离记录与风险说明。  
- **MAY**：允许实现层选择，但不得破坏上层不变量。  
- **DEFAULT**：官方默认值；实现可更严格但必须保持 schema 与行为兼容。  

### 3.3 全局冲突优先级（V2.9）

当多个条件同时出现时，系统 MUST 按以下优先级裁决：

1. `stale_writer_rejected` / writer 权限违规 / schema write fence 违规  
2. `capability_boundary_breached` / `profile_conformance_violation`  
3. L1 safety red gate  
4. `artifact_certification_reopened` / `lineage_revocation_active`  
5. evidence access policy denial 导致关键裁决不可执行  
6. `manual_adjudication_required` / `manual_risk_acceptance_required`  
7. authorized cancel  
8. fatal closure failure  
9. recovery lane progression  
10. 普通进度推进  

补充约束：

- 任何高风险 `unknown` effect 未闭环时，不得以“无新证据”为由推进 `completed`。  
- 任何 `reopened` 或 `revoked` 依赖未处理时，下游不得继续新的 high-risk primary effect。  
- 一致性语义不足时，允许吞吐下降、允许 admission control、生效 manual hold，但不得静默降级为更弱 durability class。  

---

## 4. V2.9 的十二条硬约束

### 4.1 Run 仍保持单一权威主状态

- Run 只保留一个主状态。  
- Attempt / Child / Control Service / Artifact Certification / Dependency Taint 必须分别建模。  
- UI 允许聚合展示，但不得反向定义主状态。  

### 4.2 Journal 仍是唯一权威提交真相源

- 所有影响恢复、补偿、认证、依赖传播、审计、probe、人工裁决的事实，最终都 MUST 回写 Journal。  
- projection、graph、callback、mailbox、lineage cache 都不是 committed truth source。  

### 4.3 Lease 与 capability 以服务端权威判定为准

- claim 是否仍有效，由 claim store 的权威提交结果决定。  
- capability lease 是否仍有效，由 capability broker / journal 的权威记录决定。  
- 客户端本地时钟只能用于更早自停，不能用于继续写、继续派发 effect 或自认 capability 仍然有效。  

### 4.4 split-brain 条件下优先保守停写

- 无法连通 authoritative claim store 的 writer，不得继续推进主状态或新的 primary effect。  
- 无法连通 capability broker / egress boundary 的 opaque executor，不得继续新的外部写。  
- 网络分区时，活性可以下降，真相不可分叉。  

### 4.5 mailbox 只是证据通道，不是第二真相源

- mailbox entry 只能增加证据，不得直接推进终态或认证态。  
- 空 mailbox 继续不得被解释为“未 dispatch”。  

### 4.6 任意代码执行器必须经过 capability boundary

- `execute_bash`、`run_python`、通用容器执行器等 **opaque executor** 不得再仅靠静态工具 profile 判断风险。  
- 任何可能形成外部写的动作 MUST 通过 `executionCapabilityLease` + `brokered effect boundary` 执行。  
- 对 opaque executor 而言，“先执行、后识别 effect”不是可接受的默认路径。  

### 4.7 产物导出必须携带认证状态与 lineage

- 任何被导出供其他 Run / 系统消费的产物，MUST 绑定 `artifactCertificationState`、`artifactId`、`producerRunId`、`producerAttemptId` 与 lineage 元数据。  
- 仅凭 `Run=completed` 不足以认定其产物可安全触发下游高风险写。  

### 4.8 manual gate 必须是工作流合同，并允许资源 park

- 每类 `manualGateType` 必须定义处理角色、最小证据、允许动作与 SLA。  
- 人工超时后可以释放资源、归档沙箱、停止租约，但不得因此自动把 truth obligation 视为完成。  

### 4.9 context hygiene 必须兼顾调试保真与硬上限预检

- `tail_summary_only` 不得丢失关键调试证据。  
- `carryOverBudget` 继续表示语义预算。  
- **provider hard-token preflight 是独立强约束，不得用 `chars` / `segments` 近似替代。**  

### 4.10 migration 必须受写版本围栏约束

- 旧 writer 若不能 round-trip 未知字段或不能理解新语义，不得 claim 新协议对象。  
- “能读旧数据”不代表“能继续在新协议对象上写入”。  

### 4.11 profile 必须可自证，而不是仅可声明

- tool / adapter / executor 声称自己低风险，不自动成立。  
- 系统 MUST 保存 `declaredCapabilitySet`、`grantedCapabilitySet`、`observedCapabilitySet` 与 `profileConformanceStatus`。  
- 观测到越权能力后，必须进入更保守路径。  

### 4.12 measurement 不只比较裁决，还比较时序风险

- 影子比较不能把 timing drift 当成“虽然结果一样所以没事”。  
- 对 deadline-sensitive 流程，必须把 wall-clock、步骤数、等待分布与 timeout crossing 纳入比较。  

---

## 5. 核心架构边界（V2.9）

### 5.1 Paperclip（Control Plane）

继续负责：

- Company / Project / Goal / Task  
- Approval / Budget / Comment / Operator Intervention  
- `ExternalRun` 身份、治理投影、人工介入入口  
- evidence 访问申请、风险接受、审计查询  

新增职责：

- 展示 `artifactCertificationState` 与 lineage 依赖图。  
- 对 tentative / reopened / revoked 产物执行下游治理策略。  
- 管理 `manual_risk_acceptance_required` 与 `tentative_allowed_with_waiver`。  
- 对 restricted evidence 的访问申请继续要求 `purposeOfUse`、时长与导出范围。  

明确限制：

- 不得自行推导新的主状态、认证态或 effect 裁决。  
- 不得绕过 capability broker 直接发放 opaque executor 的外部写权。  

### 5.2 Bridge（Integration Plane）

继续负责：

- 输入映射  
- 输出映射  
- callback 验签  
- 幂等去重  
- 生命周期事件投递  
- reconcile cursor 与最小投影状态  

新增职责：

- 传播 `artifact.certification.changed`、`lineage.invalidation.started`、`lineage.invalidation.propagated`。  
- 为下游消费者暴露最小可消费认证视图。  
- 保存 callback / provider receipt 与 `artifactId` / `effectId` 的相关性。  

明确限制：

- 不持有 committed 定义权。  
- 不持有恢复裁决权。  
- 不持有 evidence truth。  
- 不得在 lineage cache 中偷偷完成 revoke 决定。  

### 5.3 Dark Factory（Execution Plane）

继续负责：

- runtime / orchestration  
- sandbox / worktree / cleanup  
- Journal / effects / probes / compensation / recovery  
- capsule / recon / sanitization / restricted evidence  
- claim、fencing、mailbox、adjudication  

新增要求：

- 对 opaque executor 提供 capability broker、egress boundary、runtime profile audit 与 `observedCapabilitySet`。  
- 对导出产物输出认证记录与 lineage 依赖。  
- 对 provider/model 执行 hard-token preflight。  
- 所有关键协议事件 MUST 携带 `schemaVersion`、`writerSchemaVersion`、`traceId`。  
- 终态裁决与产物认证裁决 MUST 分别输出结构化 reason。  

---

## 6. 层级状态模型、认证模型与依赖污染模型

### 6.1 Run 主状态（唯一权威）

Run 主状态保持：

- `requested`  
- `validating`  
- `planning`  
- `executing`  
- `waiting_input`  
- `waiting_approval`  
- `finalizing`  
- `completed`  
- `failed`  
- `cancelled`  

终态约束继续保持，并补充：

- `completed` 只表示 Run 闭环完成，不自动等于“所有对外产物都已 certified forever”。  
- 若已 `completed` 的 Run 后续收到高风险矛盾证据，系统必须通过认证态和 incident 反映 reopen，不得静默改写过去 terminal。  

### 6.2 Attempt 状态

Attempt 继续至少具备：

- `created`  
- `booting`  
- `active`  
- `frozen`  
- `handoff_pending`  
- `recon_pending`  
- `recon_running`  
- `resume_ready`  
- `finalizer_owned`  
- `succeeded`  
- `failed`  
- `cancelled`  
- `superseded`  

新增补充状态属性：

- `executionSuspensionState = none | frozen | parked_manual | quarantined_input`  
- `capsuleHealth = healthy | preflight_red | poisoned`  
- `profileConformanceStatus = conformant | exceeded_declared | broker_bypass_attempted | unverifiable`  

规则：

- `parked_manual` 表示资源已释放但 truth obligation 仍在。  
- `capsuleHealth=poisoned` 时，不得 blind retry 相同 capsule hash。  
- `profileConformanceStatus != conformant` 时，不得继续新的 primary dispatch。  

### 6.3 Child Execution 状态

Child / verification worker / auxiliary executor 保持：

- `queued`  
- `running`  
- `waiting_dependency`  
- `blocked`  
- `soft_cancel_pending`  
- `hard_kill_pending`  
- `reaped`  
- `completed`  
- `failed`  
- `cancelled`  

新增要求：

- Child 若消费上游 tentative / reopened / revoked 产物，必须显式记录 `inputDependencyState`。  
- opaque executor child 必须记录 `executorSessionId` 与 capability lease。  

### 6.4 Control Service 状态

Control Service 实例至少具备：

- `idle`  
- `claimed`  
- `running`  
- `degraded`  
- `completed`  
- `timed_out`  
- `aborted`  

新增补充：

- `degraded` 不得被实现为“继续以更弱 consistency 运行”。  
- `degraded` 只能触发背压、收缩能力或 manual hold。  

### 6.5 Artifact Certification 状态机（V2.9 新增）

任何被导出、可被他人或下游 Run 消费的产物 MUST 至少具备：

- `artifactCertificationState = tentative | certified | reopened | revoked | quarantined | superseded`  
- `certificationVersion`  
- `certificationReasonCode`  
- `revocationEpoch`  

规则：

1. 产物首次 materialize 时默认 `tentative`。  
2. 只有满足以下条件时，才允许转为 `certified`：  
   - 生产者 Run 已完成 closure；  
   - 所需 mailbox seal + scan 已完成；  
   - 无未闭环 high-risk unknown effect；  
   - 依赖的上游产物满足本产物声明的最小消费要求。  
3. 若 post-scan 或 post-cert 到达高风险矛盾证据，产物必须转为 `reopened`。  
4. `reopened` 重新裁决后，可以回到 `certified`，也可以进入 `revoked`。  
5. `revoked` 后不得再被新的 high-risk downstream 自动消费。  
6. `quarantined` 表示本产物仍保留，但必须经人工或更高流程解封。  

### 6.6 Dependency / Lineage 污染状态（V2.9 新增）

每个消费他人产物的 Run / Child / effect MUST 至少记录：

- `inputDependencyState = clean | tentative_upstream | reopened_upstream | revoked_upstream | manually_waived`  
- `dependencyConsumptionPolicy = certified_only | tentative_allowed_internal | tentative_allowed_with_waiver`  
- `consumedArtifactIds[]`  

规则：

- `certified_only` 是 high-risk downstream 的默认值。  
- 允许消费 `tentative` 的流程，默认只能是低风险内部探索或人工明确接受风险的流程。  
- 若任一上游依赖变为 `reopened_upstream` 或 `revoked_upstream`，下游必须：  
  - 阻断新的 high-risk primary effect；  
  - 标记 `blockedBy=lineage_reopen` 或 `blockedBy=lineage_revocation`；  
  - 触发补偿评估、人工裁决或自动 quarantine 策略。  

### 6.7 非法状态组合（V2.9 增补）

以下组合 MUST 视为非法并告警：

- `Run=completed` 且存在 `Attempt=active`  
- `Run=completed` 且存在未闭环 `manual_*_required`  
- `ArtifactCertification=certified` 且存在未闭环 high-risk unknown effect  
- `inputDependencyState in {reopened_upstream, revoked_upstream}` 且发生新的 high-risk primary dispatch 且无 waiver  
- `profileConformanceStatus in {exceeded_declared, broker_bypass_attempted}` 且 executor 继续持有外部写 capability  
- `capsuleHealth=poisoned` 且相同 `capsuleHash` 被自动重试  
- 旧 schema writer 在 `minWriterSchemaVersion` 更高的对象上继续成功写入  
- `finalizer_owned` 后还有 `primary effect dispatch` 发生  

---

## 7. Writer Ownership、Claim 协议、时钟与写版本围栏

### 7.1 Writer domain

每个 attempt 继续至少区分两个 writer domain：

- `execution_writer`  
- `closure_writer`  

同一 domain 任意时刻最多一个 owner。默认 `execution_writer=worker`，`closure_writer=none`；接管后 `closure_writer=finalizer`。

### 7.2 正式 claim 字段（V2.9 增补）

每个 attempt MUST 至少具备：

- `attemptId`  
- `attemptEpoch`  
- `executionLeaseId`  
- `closureLeaseId`  
- `fencingToken`  
- `writerRole = worker | finalizer | reaper | prober | recovery_service | operator_override`  
- `claimVersion`  
- `claimIssuedAt`  
- `claimExpiresAt`  
- `authoritativeClockTs`  
- `claimStoreProfile`  
- `claimFailoverEpoch`  
- `writerSchemaVersion`  
- `minWriterSchemaVersion`  
- `traceId`  

### 7.3 claim 基础规则

1. claim 必须通过单点可裁决存储原语完成，至少满足 compare-and-swap 语义。  
2. `attemptEpoch` 只能单调递增，且必须由 claim store 统一发放。  
3. `claimIssuedAt / claimExpiresAt` 以 claim store 的权威时间戳为准。  
4. 新 claim 成功时，旧 claim 立即失效，旧 `fencingToken` 立即 stale。  
5. 续租成功以服务端提交确认为准；未收到确认即视为未续租。  
6. 失去写权限的角色只能读必要状态、停止新 external dispatch、投递晚到证据、释放资源。  
7. 未成功 claim 的角色不得推进 Run terminal、不得发起新的 primary effect。  

### 7.4 写版本围栏（V2.9 新增）

- 对任何带 `minWriterSchemaVersion` 的对象，writer 只有在 `writerSchemaVersion >= minWriterSchemaVersion` 时才允许 claim / mutate。  
- 不能 round-trip 未知字段的 writer，视为 `schema_write_fence_violation`。  
- 旧版本 reader 可以读取新对象的只读投影，但不得在 truth object 上取得写权。  
- mixed deployment 阶段必须显式维护 `schemaFloorEpoch`，禁止“看起来能跑就先写”。  

### 7.5 split-brain / 网络分区语义

- 无法访问 authoritative claim store 的 writer，最多只允许保留只读态与 mailbox 写入能力。  
- 无法访问 capability broker 的 opaque executor，不得继续新的外部写。  
- 不允许在没有全局单调 epoch 发号器的条件下，把多 region active-active claim 伪装成单 writer 语义。  

### 7.6 failover 语义

发生 claim store 或控制平面故障转移时，新的主节点 MUST 满足：

- `attemptEpoch` 不回退  
- stale token 不复活  
- 已 durable 的 revoke / claim 事件不丢失  
- `claimFailoverEpoch` 单调递增并审计可见  

若无法保证以上条件，系统 MUST 阻断自动接管，降级为 `manual_adjudication_required` 或 `manual_recovery_required`。

---

## 8. Opaque Executor 合同：动态 capability、brokered effect boundary 与 runtime self-proof

### 8.1 定义

下列执行器视为 **opaque executor**：

- `execute_bash_command`  
- `run_python_script`  
- 通用容器命令执行器  
- 任意可载入自定义代码、解释脚本或系统调用的执行工具  

这些工具的风险不再由“工具名字”静态决定，而由其**被授予的 capability、运行时观测到的 capability，以及是否越过 brokered effect boundary**共同决定。

### 8.2 `executionCapabilityLease` 最小字段

每次 opaque executor 启动 MUST 至少绑定：

- `executorSessionId`  
- `executionCapabilityLeaseId`  
- `declaredCapabilitySet[]`  
- `grantedCapabilitySet[]`  
- `observedCapabilitySet[]`  
- `sandboxBoundaryProfile`  
- `networkPolicyProfile`  
- `secretAccessProfile`  
- `egressBrokerMode`  
- `capabilityLeaseIssuedAt`  
- `capabilityLeaseExpiresAt`  
- `profileConformanceStatus`  
- `runtimeAuditRef`  

### 8.3 官方 capability 分类（V2.9 新增）

至少支持以下能力维度：

- `fs_read_workspace`  
- `fs_write_workspace`  
- `fs_read_restricted_ref_via_gateway`  
- `process_spawn_local`  
- `network_read_allowlist`  
- `network_write_brokered_only`  
- `secret_read_named`  
- `external_api_via_adapter_only`  
- `package_install_mirror_only`  
- `ipc_local_only`  

默认原则：

- 未声明、未授予的 capability 视为 denied。  
- `network_write_brokered_only` 是 opaque executor 执行外部写的唯一默认合法路径。  
- 沙箱外文件写、任意主机网络写、未授权 secret 读取均视为越权。  

### 8.4 brokered effect boundary

对 opaque executor，任何可能产生外部写的动作 MUST 先经过 broker：

1. executor 发起 capability 或 effect intent 请求；  
2. broker 生成或绑定 `semanticIntentId`；  
3. broker 记录 `effect_intent_preflight` 到 Journal；  
4. 只有在 capability 仍有效且策略允许时，broker 才允许真实出站；  
5. provider receipt / callback / adapter audit 继续走现有 adjudication 体系。  

禁止路径：

- 直接 `curl -X POST ...` 到公网并绕过 broker；  
- 直接由 opaque executor 在未持有 capability lease 的情况下发起不可逆外部写；  
- 通过“先联网后再补 effect 记录”来伪装一致性。  

### 8.5 运行时 profile 自证

系统 MUST 对 opaque executor 执行运行时审计，并产出：

- `declaredCapabilitySet`  
- `grantedCapabilitySet`  
- `observedCapabilitySet`  
- `profileConformanceStatus = conformant | exceeded_declared | broker_bypass_attempted | unverifiable`  
- `observedEffectCandidates[]`  
- `networkFlowDigest`  
- `fileWriteClassDigest`  
- `secretAccessDigest`  
- `subprocessTreeDigest`  

规则：

- `observedCapabilitySet` 可以大于 `declaredCapabilitySet` 吗：**可以被观测到，但不可以被默许继续执行。**  
- 一旦 `observed > granted`，系统 MUST 停止新的外部写、审计并进入 finalizer / manual path。  
- `unverifiable` 只允许在更保守模式下继续，例如 `local_sandbox_only`；不得继续高风险外部写。  

### 8.6 capability 升级语义

V2.9 允许在一个 executor session 内申请更高能力，但必须满足：

- 升级必须显式记录，不得静默“顺手做了”；  
- 升级前默认 freeze 当前步骤；  
- 升级后生成新的 `executionCapabilityLeaseId` 或 capability revision；  
- 若升级目标涉及 high-risk external write，默认进入 `manual_approval_required` 或更严格 profile。  

### 8.7 本地 destructive action 的语义

- 对**沙箱内部**的覆盖、删除、临时工作区写入，若沙箱与外界隔离且可抛弃，可视为 local effect。  
- 对沙箱外宿主机路径、共享卷、秘密挂载路径的写入，视为外部写或越权写。  
- “只是本地命令”不是免责理由；以边界是否可回滚、是否逸出沙箱为准。  

### 8.8 Opaque Executor 的默认 envelope

默认 capability envelope 至少包括：

| Envelope | 默认能力 | 用途 |
|---|---|---|
| `local_sandbox_only` | `fs_read_workspace`, `fs_write_workspace`, `process_spawn_local` | 纯本地计算、编译、测试 |
| `read_heavy_allowlist` | 上述 + `network_read_allowlist`, `package_install_mirror_only` | 需要受控读取外部资源 |
| `brokered_write_candidate` | 上述 + `network_write_brokered_only`, `external_api_via_adapter_only` | 可能触发外部写，但必须过 broker |
| `high_privilege_manual_only` | 按审批单独发放 | 极高风险场景，默认人工审批 |

规则：

- `brokered_write_candidate` 不是“自动允许外部写”，而是“允许在 broker 与 policy 同意后尝试外部写”。  
- 高风险 primary write 默认不应由 opaque executor 直接发起；优先改写为 structured adapter。  

---

## 9. Late Evidence Mailbox、Artifact Certification 与跨 Run 级联失效

### 9.1 mailbox 继续是旁路证据源

`late_evidence_mailbox` 继续用于接收已失去主写权限角色的受限证据投递。它不是第二真相源。

### 9.2 mailbox entry 最小字段（V2.9 继承并增补）

每条 entry MUST 至少携带：

- `attemptId`  
- `mailboxEntryId`  
- `staleFencingToken`  
- `claimVersionAtCapture`  
- `evidenceType`  
- `evidenceDigest`  
- `capturedAt`  
- `restrictedEvidenceRef`  
- `sourceRole`  
- `entrySignature` 或等价真实性证明  
- `entrySchemaVersion`  
- `traceId`  

### 9.3 seal 协议继续有效，并增加认证关联

V2.8 的 seal 协议继续有效，并增加以下要求：

- `mailboxScanWatermark` 必须可关联到 `artifactCertificationVersion`。  
- 产物从 `tentative` 转 `certified` 前，若命中需要 scan 的条件，必须引用对应 `mailboxScanWatermark`。  
- `sealWaitBudgetSec` 必须被纳入 RTO 预算拆分，而不是被实现团队当作“额外白送时间”。  

### 9.4 生命周期与保留（V2.9 新增）

官方默认值：

- `mailboxHotRetentionSec = 604800`（7 天）  
- `mailboxSearchableArchiveMinSec = 7776000`（90 天）  
- `mailboxEntryHoldUntil = max(run_closed, incident_closed, manual_gate_closed, legal_hold_released)`  
- `mailboxEntryTtlSec` 在 V2.9 中不再表示“证据可消失时间”，只表示**热存储优先级边界**  

规则：

- TTL 到期可转冷归档，但不得在 hold 未释放时不可检索。  
- unresolved high-risk / manual / incident 相关 entry 不得无审计删除。  
- “归档”必须保持可检索引用与 restore 路径。  

### 9.5 迟到证据的 reopen 规则继续有效

- 若 post-scan evidence 到达且影响 high-risk unknown effect，系统 MUST 进入 reopen adjudication。  
- 已经 `completed` 的 Run 若收到高风险矛盾证据，不得静默改写历史；必须生成 incident / adjudication record。  

### 9.6 Lineage graph（V2.9 新增）

每个被导出的 artifact MUST 至少记录：

- `artifactId`  
- `producerRunId`  
- `producerAttemptId`  
- `artifactDigest`  
- `artifactCertificationState`  
- `lineageParentArtifactIds[]`  
- `revocationEpoch`  
- `downstreamConsumptionClass`  
- `traceId`  

每个消费者 MUST 记录：

- `consumerRunId`  
- `consumedArtifactIds[]`  
- `dependencyConsumptionPolicy`  
- `inputDependencyState`  
- `consumptionWaiverRef`（若有）  

### 9.7 跨 Run 级联失效协议（V2.9 新增）

当上游 artifact 从 `certified/tentative` 进入 `reopened` 或 `revoked` 时，系统 MUST：

1. 发出 `artifact.certification.changed` 事件；  
2. 建立 `lineage.invalidation.started` 记录；  
3. 查找所有活跃或可恢复的下游 consumer；  
4. 对满足任一条件的下游阻断新的 high-risk primary write：  
   - `dependencyConsumptionPolicy=certified_only`；  
   - `inputDependencyState` 从 `clean` 变为 `reopened_upstream` 或 `revoked_upstream`；  
   - 下游尚未完成针对该依赖的补偿或人工 waiver。  
5. 对已经产生外部写的下游，触发：  
   - compensation evaluation；  
   - incident linkage；  
   - 必要时 `manual_adjudication_required`。  

### 9.8 Tentative 产物的消费规则

默认规则：

- **高风险 downstream**：`certified_only`。  
- **低风险内部探索**：可 `tentative_allowed_internal`，但必须带 `taintedInput=true`，并默认禁止高风险 primary write。  
- **人工接受风险**：`tentative_allowed_with_waiver`，必须有 `manual_risk_acceptance_required` 的审计记录。  

### 9.9 Reopen 的全局语义

- Reopen 不是“把过去悄悄改写成另一个历史”，而是“在既有历史上新增一个更高版本的裁决与认证事实”。  
- 对外暴露时，必须能同时回答：  
  - 旧的 terminal 是什么；  
  - 何时进入 reopen；  
  - 当前认证态是什么；  
  - 哪些下游受影响、是否已 quarantine、是否已补偿。  

---

## 10. Execution Journal：语义边界、生命周期、归档与 mixed deployment

### 10.1 正式定义

V2.9 继续定义：

- Journal 是唯一权威提交真相源。  
- 四阶段边界是语义边界，不代表所有 effect 都走同步热路径事务。  
- committed 的判断继续以 `durableWatermark` 与 backend profile 为准。  

### 10.2 Watermark 规范（V2.9 增补）

每个 attempt / run / artifact domain MUST 至少维护：

- `appendWatermark`  
- `durableWatermark`  
- `projectionWatermark`  
- `graphMaterializeWatermark`  
- `mailboxScanWatermark`  
- `schemaCompatWatermark`  
- `archiveWatermark`  
- `restoreCursor`  

规则：

- 权威恢复起点是 `durableWatermark`。  
- `appendWatermark > durableWatermark` 的区间视为不确定尾部。  
- `archiveWatermark` 用于证明哪些 committed 事实已从热存储迁往冷存储。  
- 归档后必须仍能通过 `restoreCursor` 或等价索引取回原始 truth 记录。  

### 10.3 Journal 生命周期合同（V2.9 新增）

官方默认值：

- `journalHotRetentionDays = 30`  
- `journalSearchableArchiveMinDays = 365`  
- `journalHoldUntil = max(run_closed, incident_closed, legal_hold_released, retention_policy_floor)`  

规则：

- “Journal 是唯一权威真相源”指逻辑权威，不要求永远放在热路径数据库。  
- 归档后的 Journal 仍必须：  
  - 可按 `runId / attemptId / effectId / artifactId / traceId` 检索；  
  - 可恢复最小审计时间线；  
  - 不得因冷热迁移改变 committed 语义。  
- 任何 unresolved high-risk / incident / legal hold 相关段落不得物理删除。  

### 10.4 Committed 的最低物理语义

实现 MUST 明确定义 committed 的最低条件；至少需要与 backend profile 绑定。V2.8 的表格继续成立，并补充：

- 若 committed 依赖 quorum / replicated store，则 failover 后 committed 边界不得回退。  
- 不得把仅存在于进程内缓存、sidecar buffer 或 broker 临时日志中的记录声称为 committed。  

### 10.5 Schema evolution / mixed deployment（V2.9 增补）

所有 Journal event、callback event、capsule、mailbox entry、artifact certification、evidence access request 都 MUST 带：

- `schemaVersion`  
- `writerSchemaVersion`  
- `minReaderCompatVersion`（若需要）  

混部期规则：

1. reader 必须 preserve unknown fields；不能 preserve 的 reader 只能读投影，不得写 truth object。  
2. legacy writer 只有在能 round-trip 未知字段且 `writerSchemaVersion >= minWriterSchemaVersion` 时，才允许写回。  
3. down-conversion 只允许发生在 projection / callback contract / operator view，不允许在 Journal truth object 上丢字段。  
4. `schemaFloorEpoch` 提升前，必须完成 unknown-field round-trip 验证。  
5. 对新增强语义字段（如 `artifactCertificationState`、`executionCapabilityLeaseId`、`capsuleHealth`），旧 writer 读到后不得默认成功或忽略。  

---

## 11. Effect Model：统一 truth model、唯一裁决、capability lease 与依赖语义

### 11.1 统一 effect 结构（V2.9 增补）

每个 effect 节点至少具备：

- `effectId`  
- `effectType = primary | compensation | probe`  
- `effectSafetyClass`  
- `originEffectId`  
- `compensatesEffectId`  
- `dependsOnEffectIds[]`  
- `durabilityClass`  
- `probePolicy`  
- `pessimisticFallbackPolicy`  
- `effectCommitState`  
- `semanticIntentId`  
- `semanticIntentScope`  
- `dedupeCapability`  
- `confirmationChannel`  
- `blastRadiusClass`  
- `policyProfileId`  
- `effectBoundaryType = structured_adapter | brokered_opaque_executor | local_only`  
- `executionCapabilityLeaseId`  
- `inputArtifactDependencyPolicy`  
- `profileConformanceStatusAtDispatch`  

### 11.2 统一事实，不统一混合大图

系统 SHOULD 物化至少四个视图：

- `PrimaryEffectView`：主 effect 与正向依赖  
- `CompensationPlanView`：补偿动作与顺序  
- `ProbeEvidenceView`：probe、callback、mailbox、operator adjudication 等证据  
- `ArtifactCertificationView`：产物认证、lineage、reopen / revoke 传播状态  

### 11.3 semantic intent contract 继续有效

V2.8 关于 `semanticIntentId` 的规则继续成立，并补充：

- 对 opaque executor 经过 broker 的外部写，`semanticIntentId` 由 broker 生成或最终裁决绑定，不得由 shell script 自行字符串拼接伪造。  
- capability 升级或 child handoff 时，`semanticIntentId` 不得被重置成新的业务动作，除非业务语义真的变化。  

### 11.4 `dedupeCapability` 规则继续有效，并新增对 opaque executor 的约束

- `none`：默认 `manual_adjudication_required` 或 `manual_external_followup_required`。  
- `callback_only`：不得 blind retry。  
- `intent_token`：允许有限次重试，但必须复用相同 `semanticIntentId`。  
- `provider_idempotency_key`：允许在 provider 保证时间窗内重试，但必须记录 provider contract version。  
- **对 `brokered_opaque_executor`：若未成功取得 broker receipt，则不得假装获得 dedupe 保证。**  

### 11.5 证据来源与权重（V2.9 增补）

V2.9 将证据来源细化为：

1. `journal_committed_fact`  
2. `broker_receipt_verified`  
3. `provider_callback_verified`  
4. `provider_receipt_or_mailbox_verified`  
5. `probe_result`  
6. `operator_adjudication`  
7. `heuristic_inference`  

规则：

- 没有任何来源可以否定已 committed 的 Journal 历史事实。  
- `broker_receipt_verified` 可以证明 effect 已穿过受控边界，但不自动证明外部系统最终成功。  
- `heuristic_inference` 不能单独关闭 high-risk unknown。  
- 弱证据可以提高风险等级，不能单独降低风险等级。  

### 11.6 裁决决策表（V2.9 简化增补）

| 场景 | 默认裁决 |
|---|---|
| opaque executor 直接尝试未 broker 的外部写且被拦截 | `capability_boundary_breached`，不得视为已 dispatch |
| opaque executor 通过 broker 成功拿到 receipt，但 provider callback 未回 | `recovered_unknown` 或等待 callback，按 profile 保守处理 |
| 上游 artifact=`tentative` 且下游 policy=`certified_only` | 阻断高风险下游写，进入 `blocked_unknown_effect` 或 manual gate |
| 上游 artifact=`revoked` 且下游已有外部写 | 触发 incident + compensation evaluation + lineage quarantine |
| provider 返回 `ContextLengthExceeded` 且 capsule hash 未变化 | 标记 `capsule_poisoned`，不得 blind retry |
| callback 与 probe / lineage 状态冲突 | 保持 unknown / reopened，进入更保守路径 |

---

## 12. 官方 Policy Profiles 与 Capability Envelopes（V2.9）

### 12.1 V2.8 的 effect policy profiles 继续保留

下列 profile 继续有效：

- `irreversible_external_write`  
- `compensable_external_write`  
- `callback_only_legacy_write`  
- `read_only_low_risk_tool`  
- `legacy_raw_stream_tool`  

### 12.2 新增 capability envelope（V2.9）

对 opaque executor，effect policy profile 不足以单独约束运行时行为；必须再绑定一个 `capabilityEnvelopeId`：

- `local_sandbox_only`  
- `read_heavy_allowlist`  
- `brokered_write_candidate`  
- `high_privilege_manual_only`  

规则：

- profile 管**业务 effect 的裁决语义**。  
- envelope 管**运行时能做什么**。  
- 两者必须同时满足，缺一不可。  

### 12.3 `brokered_write_candidate` 的默认规则

适用：bash/python 可能在局部流程里触发外部写，但不能提前静态定性为已获准写。

默认：

- `durabilityClass` 不能弱于相关 effect profile 要求；  
- `egressBrokerMode = required`  
- `networkWriteWithoutBroker = denied`  
- `capabilityEscalationOnFirstWrite = true`  
- 对 high-risk write 默认要求 `manual_approval_required` 或强策略豁免。  

### 12.4 `read_only_low_risk_tool` 的运行时自证

- 只有当 `observedCapabilitySet` 仍落在低风险 envelope 内，才可以继续被视为低风险。  
- 一旦观测到越界网络写、越权 secret 读或越权宿主机写，必须立即失去低风险资格。  

---

## 13. Capsule V8：context hygiene、debug fidelity 与 provider hard limit

### 13.1 升级目标

V2.9 将 Capsule 从 V7 升级为 **V8**，新增三个目标：

1. 继续保留上下文卫生与调试保真；  
2. 继续允许语义预算使用 `token_estimate | chars | segments`；  
3. **新增 provider/model 绑定的 hard-token preflight，防止 ContextLengthExceeded 变成死循环。**  

### 13.2 Capsule V8 关键新增字段

- `carryOverBudget`  
- `carryOverBudgetUnit = token_estimate | chars | segments`  
- `criticalDebugRefs[]`  
- `droppedContextRefs[]`  
- `providerModelId`  
- `providerTokenizerVersion`  
- `hardTokenLimit`  
- `reservedCompletionTokens`  
- `estimatedPromptTokens`  
- `upperBoundPromptTokens`  
- `hardLimitPreflightMethod = exact_tokenizer | validated_upper_bound_estimator`  
- `hardLimitSafetyMarginTokens`  
- `capsuleHash`  
- `capsuleHealth = healthy | preflight_red | poisoned`  
- `capsulePoisonReason`  
- `lastContextLengthErrorAt`  

### 13.3 语义预算与硬上限的分离

规则：

- `carryOverBudget` 继续表示语义预算，不强制要求所有实现都对语义预算做昂贵的精确 tokenizer 计算。  
- **但 hard-token preflight MUST 不依赖纯 `chars` / `segments` 近似。**  
- 若无法使用 exact tokenizer，则必须使用经验证的上界估算器，并带安全余量。  
- 不允许用 `chars / 4` 这类未经验证的粗糙估算去承诺 provider hard limit。  

### 13.4 hard-token preflight 合同（V2.9 新增）

在每次真正调用 LLM provider 前，系统 MUST：

1. 绑定 `providerModelId`；  
2. 计算 `estimatedPromptTokens` 与 `upperBoundPromptTokens`；  
3. 预留 `reservedCompletionTokens`；  
4. 扣除 `hardLimitSafetyMarginTokens`；  
5. 若 `upperBoundPromptTokens + reservedCompletionTokens + margin > hardTokenLimit`：  
   - 不得继续调用；  
   - 必须先 shrink / summarize / drop refs / full_rehearsal / manual_recovery。  

### 13.5 `ContextLengthExceeded` 的 deterministic 处理

- provider 返回 `ContextLengthExceeded` 时，默认视为 deterministic non-transient error。  
- 同一 `capsuleHash` 若未发生内容变更，不得 blind retry。  
- 重复命中时必须标记 `capsuleHealth=poisoned`，并进入：  
  - `full_rehearsal`；或  
  - `manual_recovery_required`；或  
  - 更强 shrink policy。  
- Watchdog 不得把这类错误误判为普通 worker crash。  

### 13.6 非自然语言 payload 的默认处理

对于 base64、hex dump、二进制摘要、多语言混杂长日志等 payload：

- 默认进入 `binary_heavy_context_class`；  
- 不应优先 inline 到上下文；  
- 仅保留 digest、索引、excerpt 或 restricted ref。  

---

## 14. Sanitization、Legacy Adapter、Restricted Evidence 与 Oversize Fuse

V2.8 在此处的基本设计继续成立，V2.9 仅补充以下约束：

### 14.1 Adapter 分类增补

V2.9 保持：

1. `structured_adapter`  
2. `semi_structured_adapter`  
3. `raw_stream_adapter`  

并新增：

4. `opaque_executor_adapter`  

### 14.2 `opaque_executor_adapter` 的特殊约束

- 默认必须绑定 capability envelope。  
- 原始 stdout/stderr 继续落 restricted store。  
- 若输出包含可疑凭据、未脱敏 URL、provider receipt、secret material，必须走更严格 redaction。  
- 任何越权 capability 审计结果都必须可被 operator 在 operator-safe 摘要中看到。  

### 14.3 Oversize / Burst Fuse 继续有效

默认阈值维持 V2.8，并补充：

- 对 `opaque_executor_adapter` 的原始输出，若检测到 `binary_heavy_context_class`，应更早触发采样与截断，而不是尝试全量在线 redaction。  
- Burst 自保限流不得影响 Journal 写入与 capability breach 审计。  

### 14.4 Restricted Evidence 访问控制继续有效

继续要求：

- `subjectId`  
- `objectRef`  
- `purposeOfUse`  
- `requestedScope`  
- `approvedScope`  
- `requestedDuration`  
- `approvedDuration`  
- `redactionLevel`  
- `exportability`  
- `schemaVersion`  

新增要求：

- 若 evidence 关联 `profile_conformance_violation`、`lineage_revocation_active` 或 `capsule_poisoned`，operator surface 默认应优先展示受限摘要与引用，而不是长文本噪声。  

---

## 15. Resume 链路、lane escalation 与 parked manual mode

### 15.1 三条恢复车道继续存在

保留：

1. `same_attempt_retry`  
2. `micro_recovery`  
3. `full_rehearsal`  

### 15.2 新增 lane 选择红线

以下情况不得走 `same_attempt_retry`：

- `capsuleHealth in {preflight_red, poisoned}`  
- `inputDependencyState in {reopened_upstream, revoked_upstream}`  
- `profileConformanceStatus != conformant`  
- `capability_boundary_breached`  
- high-risk external write unknown  

### 15.3 lane escalation matrix（V2.9 增补）

| 当前车道 | 失败类型 | 次数阈值 | 下一车道 |
|---|---|---:|---|
| `same_attempt_retry` | 同类瞬态失败重复 | 2 | `micro_recovery` |
| `same_attempt_retry` | 发现外部 unknown / lease 风险 / capability breach | 1 | `full_rehearsal` 或 `finalizer_owned` |
| `micro_recovery` | 同因失败重复 | 2 | `full_rehearsal` |
| `micro_recovery` | context hard-limit preflight red | 1 | `full_rehearsal` |
| `micro_recovery` | lineage reopened / revoked | 1 | `finalizer_owned` 或 `manual_recovery_required` |
| `full_rehearsal` | recon 为 `red` | 1 | `manual_recovery_required` |
| 任意车道 | 相同 `capsuleHash` 命中 `ContextLengthExceeded` | 1 | `capsule_poisoned` + `manual_recovery_required` 或强 shrink |

### 15.4 typed manual gate 作为工作流合同

系统继续 MUST 输出稳定的 `manualGateType`：

- `manual_approval_required`  
- `manual_evidence_access_required`  
- `manual_adjudication_required`  
- `manual_recovery_required`  
- `manual_risk_acceptance_required`  
- `manual_external_followup_required`  

新增要求：

- 每类 gate 除了 `ownerRole`、`minimumEvidenceSet`、`allowedActions[]`、`defaultSlaSec`、`escalationTarget` 外，还应定义：  
  - `parkResourcesAfterSec`  
  - `rehydrationRequirements[]`  
  - `consumesTentativeInputAllowed`（若相关）  

`manualGateType` 的 canonical literal 由 `paperclip_darkfactory_v2_9_core_enums.yaml` 唯一定义。  
OpenAPI、事件 contract、状态机矩阵、测试 fixture 仅可复用该字面量，不得派生同义替代值。  
历史文稿中的别名字面量若存在，必须显式登记为 legacy alias，不得继续作为新实现输出。  

### 15.5 parked manual mode（V2.9 新增）

当人工 SLA 失效但系统又不能自动完成终态时，系统 MUST 支持：

- 释放 compute / lease / sandbox 活跃资源；  
- 保留 Journal、restricted refs、capsule refs、lineage refs；  
- 记录 `executionSuspensionState=parked_manual`；  
- 记录 `rehydrationRequirements[]`；  
- 禁止把 parked 理解成 completed / failed。  

恢复 parked run 时：

- 必须显式 rehydrate；  
- 必须重新 claim；  
- 必须重新校验依赖、schema floor、capability 与 capsule preflight。  

---

## 16. 回调、事件模型、shadow compare 与 Measurement Contract V2

### 16.1 生命周期事件（V2.9 增补）

Bridge / Dark Factory 处理的生命周期事件至少包括：

- `run.lifecycle.changed`  
- `interrupt.acknowledged`  
- `guardrail.exhausted`  
- `compensation.started` / `compensation.completed` / `compensation.failed`  
- `cleanup.started` / `cleanup.completed` / `cleanup.failed`  
- `resume_capsule.available`  
- `lease.expired`  
- `recon.started` / `recon.completed`  
- `takeover.started` / `takeover.completed`  
- `manual_gate.parked` / `manual_gate.rehydrated`  
- `adjudication.reopened`  
- `artifact.certification.changed`  
- `lineage.invalidation.started`  
- `lineage.invalidation.propagated`  
- `profile.conformance.changed`  
- `capsule.health.changed`  

绑定型 machine-readable canonical 事件集合还包括：

- `capability.observed`  
- `capsule.preflight.failed`  
- `schema.write_fence.rejected`  

本规范中的事件 canonical name 统一使用 dotted.case。  
主文档中的 snake_case 历史写法仅作为迁移期别名，不构成新的事件命名标准。  
CI 必须校验事件 canonical name 在主文档、event contracts、测试时间线中的一致性。  

### 16.2 callback 排序与幂等

每个 callback event MUST 带：

- `eventId`  
- `sequenceNo`  
- `projectionWatermark`  
- `schemaVersion`  
- `isReplay`  
- `measurementProfile`  
- `traceId`  

规则继续保持：

- 按 `sequenceNo` 或 watermark 去重与乱序容忍。  
- replay event 必须显式标识。  
- out-of-order delivery 不得覆盖更高序号状态。  

### 16.3 divergence 的比较对象（V2.9 升级）

V2.9 明确区分两类 divergence：

1. **Decision Divergence**：  
   - recovery lane  
   - `manualGateType`  
   - terminal decision  
   - effect adjudication class  
   - certification state  
   - 是否触发 compensation / reopen / lineage quarantine / manual followup  

2. **Timing Divergence**：  
   - wall-clock latency bucket  
   - step count drift  
   - external dispatch latency bucket  
   - wait-phase distribution  
   - deadline crossing / timeout threshold crossing  

### 16.4 deadline-sensitive shadow compare（V2.9 新增）

若某流程声明 `deadlineSensitive=true`，则以下任一情况都不能被算作“虽然结构化裁决一致，所以通过”：

- 新逻辑跨过外部系统 timeout 阈值  
- 新逻辑使 takeover / callback projection / mailbox scan 超过保护阈值  
- 新逻辑导致 step count 或 tool chain 显著膨胀，并触发锁竞争 / 资源排队风险  

### 16.5 Measurement Contract V2 默认口径

默认测量口径：

- `shadow decision divergence rate`：继续以进入 shadow compare 的样本 run 为分母。  
- `timing divergence rate`：以具备 timing profile 的 shadow 样本为分母。  
- `deadline crossing count`：新旧版本比较后跨过配置 deadline 的样本数。  
- `Finalizer takeover RTO`：起点继续取 authoritative lease expiry 或 revoke committed 的更早可审计点；终点为 closure claim 成功并进入可观测接管状态。  
- `callback projection lag`：外部 callback 被 Bridge 验收时间到 projection 可见时间。  
- `mailbox evidence processing lag`：entry durable accepted 到其反映进 adjudication log 的时间。  
- `lineage invalidation propagation lag`：上游认证态变化到所有受影响活跃下游被标脏/阻断的时间。  

---

## 17. 可观测性基线、Trace 传播与 watermark gap 告警

### 17.1 Trace 传播（V2.9 新增）

V2.9 将以下要求提升为 L2 合同：

- Paperclip、Bridge、Dark Factory、callback consumer、child worker、opaque executor sidecar 之间 MUST 传播 `traceId`。  
- 若有 span 体系，至少传播：  
  - `traceId`  
  - `spanId`  
  - `parentSpanId`  
  - `spanLinks[]`（用于 callback / reopen / lineage 链接）  

### 17.2 最小相关性集合

任何关键事实应至少可通过以下维度任意联查：

- `runId`  
- `attemptId`  
- `effectId`  
- `artifactId`  
- `semanticIntentId`  
- `executionCapabilityLeaseId`  
- `traceId`  

### 17.3 watermark gap 告警基线（V2.9 新增）

默认告警建议：

| Gap | 建议告警条件 |
|---|---|
| `appendWatermark - durableWatermark` | 持续超过 60 秒或事件差超阈值 |
| `durableWatermark - projectionWatermark` | 持续超过 30 秒或影响 operator view |
| `mailbox accepted - mailboxScanWatermark` | 高风险样本超过 60 秒 p95 或 300 秒 max |
| `artifact certification change - downstream taint applied` | 高风险活跃下游超过 60 秒未被阻断 |
| `archiveWatermark - restoreCursor health` | 无法按 SLA 恢复 truth 片段 |

实现可以更严格，但不得完全不设告警基线。

### 17.4 operator surface 的最低可诊断性

operator-safe 视图至少应展示：

- 主状态  
- `manualGateType`  
- `artifactCertificationState`  
- `inputDependencyState`  
- `profileConformanceStatus`  
- `capsuleHealth`  
- `traceId`  
- 关键 restricted ref 引用  
- 最新 adjudication / incident reason code  

---

## 18. 合同增量与参考 JSON（V2.9）

### 18.1 `POST /api/external-runs` 建议新增字段

```json
{
  "resumePolicy": {
    "defaultRecoveryLane": "micro_recovery",
    "sameAttemptRetryLimit": 2,
    "microRecoveryLimit": 2,
    "carryOverBudget": 4000,
    "carryOverBudgetUnit": "token_estimate",
    "defaultContextResetPolicy": "tail_summary_only",
    "providerHardTokenPreflightRequired": true,
    "hardLimitSafetyMarginTokens": 2048
  },
  "takeoverPolicy": {
    "claimStoreRequired": true,
    "claimStoreProfile": "single_authoritative_cas",
    "lateEvidenceMailboxEnabled": true,
    "maxMailboxGraceSec": 5,
    "mailboxHotRetentionSec": 604800,
    "mailboxSearchableArchiveMinSec": 7776000,
    "reopenOnPostScanHighRiskEvidence": true,
    "lineageInvalidationEnabled": true
  },
  "effectPolicy": {
    "defaultPolicyProfileId": "compensable_external_write",
    "semanticIntentRequiredForWritableEffects": true,
    "highRiskDownstreamConsumptionPolicy": "certified_only"
  },
  "opaqueExecutorPolicy": {
    "capabilityBrokerRequiredForExternalWrite": true,
    "defaultCapabilityEnvelopeId": "local_sandbox_only",
    "runtimeProfileAuditRequired": true
  },
  "measurementPolicy": {
    "shadowCompareMode": "structured_decision_plus_timing_v2",
    "weightedDivergenceEnabled": true,
    "deadlineSensitiveMeasurement": true
  }
}
```

### 18.2 Mailbox Entry 参考样例

```json
{
  "mailboxEntryId": "mbe_01JXYZ...",
  "attemptId": "att_42",
  "staleFencingToken": "ft_18",
  "claimVersionAtCapture": 9,
  "evidenceType": "provider_receipt",
  "evidenceDigest": "sha256:abc...",
  "capturedAt": "2026-04-22T18:01:23Z",
  "restrictedEvidenceRef": "ref://restricted/mailbox/mbe_01JXYZ",
  "sourceRole": "worker",
  "entrySignature": "sig:base64...",
  "entrySchemaVersion": "2.9",
  "traceId": "trace_7f..."
}
```

### 18.3 Brokered Opaque Executor Effect 参考样例

```json
{
  "effectId": "eff_901",
  "effectType": "primary",
  "effectBoundaryType": "brokered_opaque_executor",
  "executionCapabilityLeaseId": "lease_cap_77",
  "semanticIntentId": "intent_charge_123",
  "policyProfileId": "irreversible_external_write",
  "capabilityEnvelopeId": "brokered_write_candidate",
  "profileConformanceStatusAtDispatch": "conformant",
  "brokerReceiptRef": "ref://broker/receipt/901",
  "confirmationChannel": "provider_callback",
  "blastRadiusClass": "high"
}
```

### 18.4 Artifact Certification 参考样例

```json
{
  "artifactId": "art_551",
  "producerRunId": "run_A",
  "producerAttemptId": "att_42",
  "artifactDigest": "sha256:def...",
  "artifactCertificationState": "reopened",
  "certificationVersion": 3,
  "certificationReasonCode": "post_scan_high_risk_evidence_conflict",
  "revocationEpoch": 1,
  "lineageParentArtifactIds": ["art_src_1"],
  "traceId": "trace_7f..."
}
```

### 18.5 Capsule V8 参考样例

```json
{
  "capsuleHash": "cap_abc123",
  "carryOverBudget": 4000,
  "carryOverBudgetUnit": "token_estimate",
  "providerModelId": "gpt-x",
  "providerTokenizerVersion": "2026-04",
  "hardTokenLimit": 128000,
  "reservedCompletionTokens": 4000,
  "estimatedPromptTokens": 97200,
  "upperBoundPromptTokens": 109800,
  "hardLimitPreflightMethod": "validated_upper_bound_estimator",
  "hardLimitSafetyMarginTokens": 2048,
  "capsuleHealth": "healthy",
  "criticalDebugRefs": [
    "ref://stderr/build/17",
    "ref://stacktrace/python/9"
  ]
}
```

---

## 19. Failure Injection、形式化验证与验收标准

### 19.1 最小新增测试矩阵（V2.9）

V2.9 至少新增覆盖：

1. opaque executor 直接尝试公网 POST，被 broker 前拦截并审计  
2. opaque executor 合法申请 capability 升级，broker 成功生成 `semanticIntentId`  
3. 观测到 `observedCapabilitySet > grantedCapabilitySet` 后，新的 primary write 被阻断  
4. 高风险产物在未 certified 前不会触发下游 `certified_only` 流程  
5. 上游 artifact `reopened` 后，活跃下游被标脏并停止新的高风险写  
6. 已完成下游在上游 `revoked` 后触发 incident linkage 与 compensation evaluation  
7. `chars` 预算看似足够但 hard-token preflight 拦截了真实超限 capsule  
8. provider 返回 `ContextLengthExceeded` 后，相同 `capsuleHash` 不会进入盲重试死循环  
9. mailbox 热 TTL 到期后，证据仍可从 searchable archive 检索  
10. 旧 writer 因 schema write fence 被拒绝拿到新对象写权  
11. parked manual mode 会释放资源，但不会丢失 rehydration 所需 truth  
12. shadow compare 会把 deadline crossing 记为 timing divergence，而不是误算通过  
13. traceId 在 Paperclip → Bridge → Dark Factory → callback → reopen 全链完整传播  
14. watermark gap 超阈值时触发自保告警而非静默积压  

### 19.2 形式化验证基线（V2.9 新增）

以下域 SHOULD 具备模型检查、穷举状态测试或等价强度的形式化验证：

- claim / finalizer 接管与 split-brain  
- capability lease 与 brokered effect boundary  
- artifact certification 与 lineage invalidation  
- capsule poisoned 与 retry loop breaker  
- schema write fence 与 mixed deployment  

至少需要验证的不变量：

- 不会出现两个有效 writer 同时推进主状态  
- 不会在依赖 revoked 时继续新的高风险 primary dispatch  
- 不会在 capability 越权后继续持有外部写权限  
- 不会在相同 poisoned capsule 上自动重试  
- 不会由旧 writer 静默覆盖新字段  

### 19.3 每个用例的期望输出

每个用例至少产出：

- 事件时间线  
- Journal 片段  
- 期望状态转移  
- 期望 `uiCompositeKey`  
- 期望 callback / lineage 事件  
- 期望 evidence 访问记录  
- 期望 mailbox / archive 检索结果  
- 期望 adjudication decision  
- 期望 certification / dependency taint  
- 通过 / 失败判定  

---

## 20. Migration、Feature Flags、Cutover Gates 与 Rollback Gates

### 20.1 功能开关分期（V2.9 建议）

推荐按功能开关渐进上线：

1. `flag.schema_write_fence_v29`  
2. `flag.opaque_executor_capability_broker`  
3. `flag.runtime_profile_self_proof`  
4. `flag.artifact_certification_lineage`  
5. `flag.capsule_v8_hard_token_preflight`  
6. `flag.parked_manual_mode`  
7. `flag.journal_archive_policy_v29`  
8. `flag.trace_propagation_l2`  
9. `flag.timing_shadow_measurement_v2`  
10. `flag.mixed_deployment_roundtrip_check`  

### 20.2 cutover gates（V2.9 增补）

进入主裁决前，至少满足：

- sampled opaque executor 中 **0 个** unbrokered external write escape  
- high-risk downstream 的 `certified_only` 覆盖率达到目标阈值  
- 相同 `capsuleHash` 的 context-length blind retry = 0  
- trace propagation 覆盖率达到目标阈值  
- unknown-field round-trip 成功率 = 100%  
- weighted high-risk decision divergence = 0  
- deadline crossing divergence = 0（对 protected flows）  
- lineage invalidation propagation lag p95 达标  
- mailbox searchable archive restore path 可用  

### 20.3 rollback gates（V2.9 增补）

出现以下任一情况 MUST 支持快速回滚：

- 发现 unbrokered external write escape  
- high-risk downstream 在依赖 `reopened/revoked` 后仍继续高风险写  
- context-length blind retry loop 出现  
- trace propagation 缺失导致 incident 无法串联  
- legacy writer 成功覆盖新字段  
- archive restore path 失效导致 truth 不可检索  
- weighted high-risk divergence > 0  
- protected flow 的 deadline crossing divergence > 0  

---

## 21. 最低 SLO、退让策略与运行预算（V2.9）

### 21.1 最低建议 SLO

| 指标 | 建议目标 |
|---|---|
| Journal append p95 | <= 50 ms |
| durable pre-dispatch commit p95 | <= 200 ms |
| capability broker preflight p95 | <= 150 ms |
| callback projection lag p95 | <= 15 s |
| Finalizer takeover RTO p95 | <= 120 s |
| mailbox evidence processing lag p95 | <= 60 s |
| lineage invalidation propagation lag p95 | <= 60 s |
| sanitization main-path added latency p95 | <= 100 ms |
| hard-token preflight p95 | <= 300 ms |
| recon gate decision p95 | <= 30 s |

### 21.2 性能退让策略（V2.9 新增）

若系统无法同时满足强一致与目标吞吐，允许的退让顺序是：

1. admission control / queue backpressure  
2. 降低低风险并发、保住高风险一致性  
3. 将 write-candidate 流量转入 `manual_hold` 或串行化 lane  
4. 暂停 tentative downstream 自动启动  
5. 暂停 timing shadow compare 或低风险附加观测  

禁止的退让方式：

- 把 `durable_pre_dispatch` 偷降为更弱 durability class  
- 在 capability broker 不可用时默许 opaque executor 直连外部系统  
- 在 hard-token preflight 不可用时继续盲调大模型  
- 在 lineage invalidation 不可用时继续自动启动高风险 downstream  

### 21.3 报告要求

所有 SLO 报告必须绑定：

- `measurementContractVersion`  
- `schemaVersion`  
- `writerSchemaVersion`  
- `providerModelId`（若相关）  
- `deadlineSensitive`（若相关）  

---

## 22. V2.9 Definition of Done

达到以下条件，可认为 V2.9 最小闭环成立：

1. opaque executor 已具备 capability broker 与外部写边界拦截  
2. runtime profile self-proof 已保存 declared / granted / observed capability 对账  
3. Artifact Certification + Lineage Invalidation 协议已生效  
4. high-risk downstream 已默认使用 `certified_only`  
5. Capsule V8 已执行 provider hard-token preflight 与 poisoned breaker  
6. mailbox / Journal 生命周期已具备 searchable archive 与 hold 语义  
7. mixed deployment write-fence 已阻断旧 writer 覆盖新字段  
8. trace propagation 与 watermark gap 告警已生效  
9. parked manual mode 已能释放资源并支持 rehydrate  
10. shadow compare 已纳入 timing profile 与 deadline crossing  
11. failure injection 最小新增矩阵已通过  
12. 相关形式化验证或等价强度状态机测试已落地  
13. cutover gates 达标且 rollback path 演练通过  

---

## 23. 实施优先级

V2.9 的优先级顺序建议为：

1. `opaque executor capability broker + runtime profile self-proof`  
2. `artifact certification + lineage invalidation`  
3. `Capsule V8 hard-token preflight + poisoned breaker`  
4. `schema write fence + mixed deployment roundtrip guard`  
5. `trace propagation + watermark gap alerting`  
6. `mailbox / journal archive & hold semantics`  
7. `parked manual mode`  
8. `timing shadow measurement v2`  
9. `参考 JSON、模型检查与长期优化`  

---

## 24. 收尾判断

V2.9 的目标，不是把 V2.8 推翻重写，而是承认这样一个事实：

1. **对于 bash / python 这类任意代码执行器，profile 不能只靠静态声明；必须把“能做什么”与“实际做了什么”重新拉回到 capability lease 与 brokered effect boundary 上。**  
2. **对于 reopen，单 Run 内政治正确不够；必须再补一个跨 Run 的认证/撤销传播协议，否则“完成”会沿依赖图把污染继续放大。**  
3. **对于 Capsule，语义预算有价值，但 provider hard limit 是不可协商的物理边界，必须独立预检。**  
4. **对于 mixed deployment 与 incident 处理，文档正确不等于系统可实现；必须提供写围栏、可检索归档、trace 穿透、park/re-hydrate 与模型检查基线。**

> **一句话收尾**：V2.9 的意义，是把“谁能真正触发外部写、一个完成的产物何时才算可被下游信任、Context 上限何时必须硬停、旧 writer 何时必须失去写权、以及 reopen 如何沿依赖图传播”统一写成更少自由发挥空间的执行规格。

---

## 25. Implementation Companion Contract（V2.9 内置短附录）

### 25.1 文档集组成与 source-of-truth 规则

自本版起，V2.9 文档集分为三层：

1. **V2.9 主文档**：负责 L1/L2 级语义、状态机、不变量、协议边界与默认裁决。  
2. **本内置短附录**：负责继承/覆盖索引、版本绑定、关键算法唯一口径、runtime config registry 摘要，以及 machine-readable canonical bundle 的索引。  
3. **V2.9-impl 包**：负责 API/IDL、事件 contract、DDL/storage mapping、sidecar/SDK、operator surface、测试资产与容量/归档实现说明。  

优先级规则：

- L1/L2 协议语义以**主文档正文**为准。  
- 同名字段、同名状态、同名 reason code 的**唯一枚举字面量、required 字段集合与事件名**，以 canonical bundle 为准。  
- V2.9-impl 中的样例、DDL、OpenAPI、事件样例、测试 fixture 都是**派生产物**，不得反向覆盖主文档或本附录。  
- 若较低层文档与较高层文档冲突，CI MUST 阻断发布，不得用“实现更方便”为由静默漂移。  

### 25.2 并行开发准入规则

以下条件满足前，不得进入多团队并行实现：

1. 该域已有 machine-readable artifact；  
2. 该 artifact 已绑定 `protocolReleaseTag`；  
3. 该域的 source-of-truth 已在继承/覆盖索引中指明；  
4. 该域关键算法已从“规则 + 原则”收口为“输入 / 计算 / 输出 / 缺失数据时的保守行为”；  
5. 该域 unknown-field round-trip 与 write-fence 规则已明确。  

---

## 26. 继承/覆盖索引与 canonical bundle 索引

### 26.1 继承 / 覆盖索引（规范绑定件）

| Topic | Source of truth | 说明 |
|---|---|---|
| Run / Attempt / Child / Control Service 主状态机 | V2.8 + V2.9 merged | V2.8 提供主框架；V2.9 增补 `parked_manual`、`capsuleHealth`、`profileConformanceStatus` 与依赖污染语义。 |
| Claim / Fencing / authoritative clock | V2.8 + V2.9 merged | V2.8 负责 claim/epoch/failover；V2.9 增补 `minWriterSchemaVersion` 与 write-fence。 |
| Mailbox seal / scan / reopen | V2.8 + V2.9 merged | V2.8 负责 seal/scan/reopen；V2.9 增补 searchable archive / hold / certification coupling。 |
| Journal durable truth / watermarks | V2.8 + V2.9 merged | V2.8 定义权威边界；V2.9 增补 retention profile、restore cursor、mixed deployment。 |
| Effect model / semantic intent / dedupe capability | V2.8 + V2.9 merged | V2.8 提供基本 effect truth model；V2.9 增补 capability lease、依赖污染与 dispatch gate。 |
| Opaque executor / capability broker / runtime self-proof | V2.9 | 新增于 V2.9。 |
| Artifact Certification / Lineage Invalidation | V2.9 | 新增于 V2.9。 |
| Capsule V8 / hard-token preflight / poisoned breaker | V2.9 | 新增于 V2.9。 |
| Trace propagation / watermark gap alerting | V2.9 | 新增于 V2.9。 |
| Measurement Contract / shadow compare 基线 | V2.8 + V2.9 merged | V2.8 定义结构化比较；V2.9 增补 timing profile / deadline crossing / weighted divergence。 |
| Policy Profiles / Capability Envelopes | V2.8 + V2.9 merged | V2.8 提供官方 profile；V2.9 将 opaque executor 拉回 capability envelope。 |
| Restricted evidence / sanitization / debug fidelity | V2.8 + V2.9 merged | V2.8 提供主约束；V2.9 增补 oversize/legacy adapter/runtime audit 关联。 |
| parked manual / rehydrate | V2.9 | 新增于 V2.9。 |
| mixed deployment / unknown-field preservation / write fence | V2.8 + V2.9 merged | V2.8 定义读时保守解释；V2.9 增补写时围栏。 |

### 26.2 canonical bundle 索引（最小必备）

V2.9-impl 包 MUST 至少包含以下 machine-readable or machine-checkable 资产：

| Artifact | 作用 | 缺失时的影响 |
|---|---|---|
| `core_enums.yaml` | 统一枚举与字面量 | 禁止多团队并行开发 API / UI / storage。 |
| `core_objects.schema.json` | 核心对象 required 字段与结构 | 禁止生成 SDK、DDL 与事件 envelope。 |
| `event_contracts.yaml` | 生命周期/认证/能力/级联事件 contract | 禁止并行开发 producer / consumer。 |
| `external_runs.openapi.yaml` | 控制面 / 外部接口 surface | 禁止前后端 / Bridge / operator surface 并行联调。 |
| `runtime_config_registry.yaml` | 阈值、默认值、scope、owner | 禁止把阈值写死到业务代码。 |
| `inheritance_matrix.csv` | V2.8/V2.9 继承与覆盖关系 | 禁止混部升级实现。 |
| `responsibility_matrix.csv` | source-of-truth / write roles / read roles | 禁止组件分工定稿。 |
| `storage_mapping.csv` | Journal / projection / index / archive 映射 | 禁止独立建库后再汇合。 |
| `state_transition_matrix.csv` | 状态迁移与非法组合输入 | 禁止测试与实现各写一套状态机。 |
| `test_asset_spec.md` | 测试资产、fixture、golden timeline 组织方式 | 禁止 QA/开发各自发明验收资产。 |

---

## 27. 关键算法唯一口径（V2.9 附录）

### 27.1 `weightedHighRiskDecisionDivergence`

用途：作为 shadow compare、cutover gate 与 rollback gate 的统一统计口径。

输入：

- 样本集合 `S`，每个样本至少包含：  
  - `blastRadiusClass ∈ {low, medium, high, irreversible}`  
  - `protectedFlow ∈ {true, false}`  
  - `structuredDecisionDiverged ∈ {true, false}`  
  - `deadlineCrossed ∈ {true, false}`  
  - `timingBucketShift ∈ {0, 1, 2plus}`  

基础权重：

- `low = 0.25`  
- `medium = 1`  
- `high = 3`  
- `irreversible = 5`  

样本权重：

`weight_i = baseWeight(blastRadiusClass_i) × (protectedFlow_i ? 2 : 1)`

样本惩罚：

- 若 `structuredDecisionDiverged=true`，则 `penalty_i = 1.0`  
- 否则若 `deadlineCrossed=true`，则 `penalty_i = 0.5`  
- 否则若 `timingBucketShift=2plus`，则 `penalty_i = 0.25`  
- 否则 `penalty_i = 0.0`  

聚合：

`weightedHighRiskDecisionDivergence = Σ(weight_i × penalty_i) / Σ(weight_i)`

保守默认：

- `blastRadiusClass` 缺失时，按 `irreversible` 处理。  
- `protectedFlow` 缺失但存在任何外部写 candidate 时，按 `true` 处理。  
- cutover gate 与 rollback gate 的判定仍以正文为准：**对 high-risk gate，允许阈值默认是 0。**

### 27.2 `protectedFlow`

下列任一条件满足时，流程 MUST 被视为 `protectedFlow=true`：

1. 流程消费的上游 artifact 将驱动新的 primary external write；  
2. 任一 downstream effect 满足 `effectSafetyClass=irreversible` 或 `blastRadiusClass>=medium`；  
3. 流程跨 tenant / project / human-visible / compliance boundary 暴露状态；  
4. 流程涉及权限、身份、secret、支付、审批、对账、通知发送、配置变更或其他不可低成本回滚的对象；  
5. operator 明确打上 protected 标记。  

保守默认：

- 只要“是否会驱动外部写”无法被证明为否，且流程消费上游 artifact，默认 `protectedFlow=true`。  
- `protectedFlow` 的默认消费策略是 `dependencyConsumptionPolicy=certified_only`。  

### 27.3 `deadlineSensitive`

下列任一条件满足时，`deadlineSensitive=true`：

1. 存在显式 `absoluteDeadlineAt`、`timeoutSec` 或 provider/tool 的硬超时合同；  
2. 当前步骤参与 claim / lease / lock / callback projection / mailbox scan / finalization 等带时限的关键路径，且剩余裕量 `< 2 ×` 最近稳定窗口的 p95 历史延迟；  
3. 当前步骤属于 `protectedFlow` 且其结果会直接决定是否允许新的 high-risk write；  
4. operator / workflow config 明确声明 `deadlineSensitive=true`。  

保守默认：

- 对 `protectedFlow`，若 deadline 信息缺失但存在外部系统 timeout 风险，按 `deadlineSensitive=true` 处理。  
- `deadlineSensitive=true` 时，**结构化决策一致并不足以判定 shadow pass**；deadline crossing 仍算 divergence。  

### 27.4 `observedCapabilitySet`

`observedCapabilitySet` MUST 由以下证据源按统一规则折算，不得由各服务自由解释：

优先证据源（从高到低）：

1. broker 许可/拒绝/receipt 记录；  
2. sidecar / sandbox 审计：网络出站尝试、secret 读取、文件写分类、子进程树、包安装、受限 ref 访问；  
3. adapter audit / callback correlation；  
4. Journal 中的 `observedEffectCandidates`；  
5. 仅用于补充解释的 heuristic inference。  

折算规则：

- 任何被 broker 明确放行或拒绝的 capability，均计入 `observedCapabilitySet`。  
- 对 `network_write_brokered_only`、`secret_read_named`、沙箱外写、未授权出站等敏感能力，**单次被阻断尝试**就足以计入 observed。  
- 对非敏感能力，若没有 broker 证据，则必须至少有一个高可信 sidecar 证据；仅 heuristic 不得单独把能力记为“已安全使用”。  
- 证据缺失不代表能力未使用；只表示 runtime 可能 `unverifiable`。  

### 27.5 `profileConformanceStatus`

输入：

- `declaredCapabilitySet = D`  
- `grantedCapabilitySet = G`  
- `observedCapabilitySet = O`  
- `runtimeAuditCoverage`（包含 sidecar、broker、adapter、Journal 的覆盖完整度）  

输出枚举继续固定为：

- `conformant`  
- `exceeded_declared`  
- `broker_bypass_attempted`  
- `unverifiable`  

判定算法：

1. 若缺少必要 runtime audit、关键审计流断裂，或 `runtimeAuditCoverage < minRequiredCoverage`，输出 `unverifiable`。  
2. 否则若存在任一 `unbrokered external write attempt`、`egress boundary bypass attempt`、或观察到 broker 明确 denied 的能力仍被尝试执行，输出 `broker_bypass_attempted`。  
3. 否则若 `O ⊄ D` 或 `O ⊄ G`，输出 `exceeded_declared`。  
4. 否则输出 `conformant`。  

强制动作：

- `conformant`：可按 profile 继续。  
- `exceeded_declared` / `broker_bypass_attempted`：MUST 阻断新的 primary external write，进入 finalizer / manual 路径。  
- `unverifiable`：只允许继续 `local_sandbox_only` 或同等更保守模式；不得继续 high-risk external write。  

### 27.6 `consumptionWaiverRef`

`consumptionWaiverRef` 是对“在上游未 fully certified 时，某个明确 consumer 范围内允许继续消费”的**人工风险接受引用**，而不是上游认证状态的覆盖物。

一个有效 waiver 至少 MUST 绑定：

- `waiverId`  
- `artifactId`  
- `approvedBy`  
- `approvedAt`  
- `expiresAt`  
- `allowedConsumerScope`  
- `allowedConsumptionPolicy`  
- `allowedEffectSafetyCeiling`  
- `maxFanOut`  
- `reasonCode`  

规则：

- 有效 waiver 只能改变**指定 consumer** 的消费 gate，不得改写上游 `artifactCertificationState`。  
- waiver 不得抑制 `artifact.certification.changed` / `lineage.invalidation.*` 事件。  
- `inputDependencyState=revoked_upstream` 时，waiver 不得授权新的 high-risk primary write。  
- `inputDependencyState=reopened_upstream` 时，只有在 scope 匹配、未过期且 `allowedEffectSafetyCeiling` 允许的情况下，才可转为 `manually_waived`。  
- 过期、缺失、找不到审批记录的 waiver，等同于不存在。  

---

## 28. Runtime Config Registry 摘要（规范绑定件）

下表给出必须统一管理、不得写死在业务代码中的最小配置键：

| Key | Type | Default | Scope | Reload | Owner |
|---|---|---|---|---|---|
| `lineage.protectedFlow.defaultConsumptionPolicy` | enum | `certified_only` | workflow / tenant | hot | control-plane |
| `lineage.propagation.maxLagSec` | integer | `60` | env / workflow-tier | hot | control-plane |
| `lineage.waiver.defaultMaxFanOut` | integer | `1` | workflow | cold | governance |
| `broker.capabilityLease.defaultTtlSec` | integer | `60` | executor profile | hot | execution-plane |
| `broker.runtimeAudit.minRequiredCoverage` | float | `0.95` | env | hot | execution-plane |
| `broker.unverifiable.highRiskMode` | enum | `manual_hold` | env | hot | execution-plane |
| `tokenPreflight.defaultSafetyMarginRatio` | float | `0.90` | provider/model | hot | model-runtime |
| `tokenPreflight.hardStop.enabled` | boolean | `true` | provider/model | hot | model-runtime |
| `tokenPreflight.poisonedRetryPolicy` | enum | `block_same_capsule_hash` | env | hot | model-runtime |
| `shadow.weightedHighRiskDecisionDivergence.cutoverThreshold` | float | `0.0` | env | hot | release-governor |
| `shadow.deadlineCrossing.protectedFlowThreshold` | float | `0.0` | env | hot | release-governor |
| `archive.restore.defaultTargetSec` | integer | `300` | storage tier | cold | platform-storage |
| `schema.minWriterVersion.v2_9_objects` | string | `2.9.0` | env | cold | platform-architecture |

约束：

- 任一默认值被 override 时，override 也必须进入审计。  
- 任何 feature flag 或运行阈值若未在 registry 中登记，不得作为 release gate 输入。  
- registry 是“默认值与 scope 的权威表”，不是独立协议源；它不得削弱正文或本附录约束。  

---

## 29. Companion 绑定、变更纪律与一致性校验

### 29.1 版本绑定

V2.9 的 companion 绑定版本如下：

- `normativeVersion = 2.9`  
- `companionAppendixVersion = 2.9-companion.1`  
- `implPackVersion = 2.9-impl.1`  
- `protocolReleaseTag = v2.9-companion-bound-r1`  

所有 machine-readable 资产、OpenAPI、事件 contract、DDL 映射、测试 fixture 与 archive/restore 工具链，MUST 带 `protocolReleaseTag`。  

### 29.2 变更纪律

- 变更 **正文 L1/L2 语义**：需要升 `normativeVersion`。  
- 只新增/修订 **本附录的算法定义、registry 摘要、继承索引**：至少升 `companionAppendixVersion`。  
- 只修订 **实现包中的派生契约、样例、DDL、SDK、测试资产**：升 `implPackVersion` 即可，但不得改变同名协议语义。  

### 29.3 一致性校验

CI / 发布闸门 MUST 至少校验：

1. `core_enums.yaml` 与 `core_objects.schema.json` 中的同名字段/枚举，与正文/附录一致；  
2. `external_runs.openapi.yaml` / `event_contracts.yaml` 不得出现正文未定义且会影响协议语义的新增状态；  
3. `manualGateType`、`artifactCertificationState`、`inputDependencyState`、`profileConformanceStatus`、`capsuleHealth` 的字面量在主文档与 machine-readable 资产间完全一致；  
4. event canonical name 在主文档、`event_contracts.yaml` 与 golden timeline 中一致；  
5. OpenAPI 所有 mutation operation 声明 `X-Protocol-Release-Tag`，所有响应与错误响应可回写 `protocolReleaseTag`；  
6. unknown-field round-trip 与 write-fence 测试通过；  
7. `state_transition_matrix.csv` 覆盖正文要求的关键迁移与非法组合，且显式覆盖 `parked_manual` 与 `tentative_upstream`；  
8. 任何 impl 包中的示例，不得把 `reopened`、`revoked`、`unverifiable`、`broker_bypass_attempted`、`manual_*` 等状态弱化为“warning only”。  

### 29.4 收尾规则

V2.9 正文继续保持“稳定主规范”的角色；本附录只负责把**最容易导致多团队实现分叉的规范绑定件**贴近主文档固定下来。其余 API、DDL、sidecar、operator UX、测试与容量说明，统一放入 V2.9-impl 包维护。
