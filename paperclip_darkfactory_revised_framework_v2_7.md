# Paperclip × Dark Factory 修订版框架 V2.7

**版本**：2.7  
**状态**：Draft for implementation  
**定位**：在 V2.6 的合同化基础上，继续补齐运行时物理现实、协议闭环、迁移策略与性能边界，把“原则正确、字段齐全”推进到“多团队并行实现也不易分叉”的正式规格版。  
**适用范围**：若与 V2.6 冲突，以本稿为准；若与本稿内部冲突，以更严格者为准。  

---

## 0. V2.7 相对 V2.6 的一句话变化

V2.7 的重点，不是再加一层抽象，而是把 V2.6 还停留在“名词正确、方向正确”的地方，继续压成可执行合同：

1. **Journal 的四阶段事实边界被正式澄清为“语义边界”，不是对所有操作一刀切的同步热路径事务。**  
2. **Takeover / fencing 不再只定义 token，而是补上 claim 协议、writer domain、lease 失效语义与 late evidence mailbox。**  
3. **Run / Attempt / Child / Control Service 不再只有状态集合，还增加最小合法迁移表、非法迁移约束与聚合优先级。**  
4. **Compensation 仍属于统一 effect truth model，但裁决视图拆为 Primary Effect View 与 Compensation Plan View，避免混合 DAG 失控。**  
5. **`manual_required` 被正式拆型，避免审批、取证、恢复、风险承担被前后端实现成一个模糊大桶。**  
6. **`micro_recovery` 不再只谈 worktree 复用，而是加入 prompt/context hygiene、stale hypotheses 隔离与 lane escalation matrix。**  
7. **Sanitize-by-construction 继续是主路径，但新增 legacy / unstructured adapter 兜底合同。**  
8. **Restricted Evidence 不再只有访问控制，还加入 purpose binding、最小用途范围、可导出性与时限约束。**  
9. **迁移不再默认把双轨复杂度压到 Finalizer 主热路径，而改为 feature flags + off-path shadow compare + cutover gates。**  
10. **首次加入最低 SLO、滞后预算、回滚门槛与 failure-injection 通过标准。**

> **一句话版本**：V2.7 要解决的，是“纸面合同已经够强，但真实世界的飞行中请求、非结构化输出、污染上下文、迁移复杂度和热路径性能，会不会把系统拖回语义分叉和运维失控”。

---

## 1. 结论先行

V2.7 继续坚持方案 B，并继续保持三层边界：

- **Paperclip**：治理面，负责身份、审批、预算、人工介入、访问申请、保留要求与 operator surface。
- **Dark Factory**：执行面，负责运行时、Journal、effects、recovery、compensation、evidence、cleanup 与 execution truth。
- **Bridge**：集成面，只保留最小操作性状态，不升级为新的业务控制面或 committed truth source。

V2.7 相比 V2.6，再补十个闭环：

1. **语义事实边界与物理持久语义分离定义**：四阶段事实边界是语义模型；只有高风险 effect 必须使用同步 pre-dispatch durability。  
2. **writer ownership 进入正式仲裁协议**：谁发 epoch、谁续租、谁能 claim、失租后能写什么、旧 writer 的晚到证据去哪儿，必须写死。  
3. **late evidence mailbox 成为一等旁路证据通道**：被 fencing 拒绝的 worker 不能推进主状态，但可以投递受限证据，供 Finalizer 在 recovered_unknown 裁决前读取。  
4. **层级状态转移表正式化**：状态集合、合法迁移、触发者、guard、side effects 必须一起定义。  
5. **manual-required taxonomy 正式化**：人工审批、人工取证、人工恢复、人工风险承担、人工外部跟进，不得再混成同一个 reason。  
6. **effect 统一 truth model + 分层裁决视图**：Journal 仍是一套；但 Primary Effect View 与 Compensation Plan View 分开物化。  
7. **semantic intent contract 正式化**：`semanticIntentId` 的生成、作用域、重试复用、过期和冲突处理必须定义。  
8. **context hygiene 成为恢复合同的一部分**：轻恢复不仅恢复代码与环境，还必须净化模型上下文与失败假设残留。  
9. **legacy adapter fallback 正式化**：结构化、半结构化、原始流三类适配器要分开治理，不再假设所有输出天然可结构化。  
10. **迁移、SLO 与 cutover gates 正式化**：不再只有原则性 migration plan，而是加上开关分期、 shadow compare、 divergence threshold、 rollback threshold 与延迟预算。

---

## 2. V2.7 继承什么、修正什么

### 2.1 继续继承的部分

以下判断继续成立：

- 方案 B 不变：Paperclip 管治理，Dark Factory 管执行，Bridge 管最小集成状态。  
- Run 继续只有**一个权威主状态机**。  
- Attempt / Child / Control Service 必须保有正式层级状态模型。  
- Journal 继续是**唯一权威提交真相源**。  
- V2.6 的 `attemptEpoch / fencingToken / writerRole / watermark / effectType / recoveryLane` 基本方向不变。  
- Capsule 路线继续保留，但升级为更细粒度 merge 与 context hygiene 规则。  
- sanitize-by-construction 继续是主路径。  
- `same_attempt_retry / micro_recovery / full_rehearsal` 三条恢复车道继续存在。  
- `external_unprobeable_non_idempotent` 继续沿 `callback_only / intent_token / provider_idempotency_key / none` 细分。  
- cleanup reserve / postmortem reserve 继续不可被执行阶段侵占。

### 2.2 相对 V2.6 的修正

V2.6 已经补上了 truth boundary、takeover fields、state hierarchy、compensation first-class、sanitization-by-construction、resume lanes、migration 与 failure injection。  
V2.7 进一步把下列问题从“接近工程规格”推进到“更不容易分歧”：

- 把 Journal 的四阶段边界从“看起来像同步事务”收敛为**语义边界 + 按风险分层的持久合同**。  
- 把 takeover 从“有 epoch / token”推进为**claim protocol + lease semantics + stale writer evidence path**。  
- 把状态模型从“有状态集合”推进为**最小迁移表、非法组合、聚合优先级与 actor constraints**。  
- 把 `manual_required` 从通用桶推进为**typed manual gate**。  
- 把 effect DAG 从单一混合裁决图推进为**统一 truth model + 分层 view model**。  
- 把 `semanticIntentId`、provider 幂等键与 callback 去重推进为正式规格。  
- 把 Capsule 从 V5 升级为 **V6**：字段级 merge strategy、carry-over budget、stale hypothesis quarantine、context reset policy。  
- 把 Sanitization 从“主路径正确”推进为**legacy raw stream 的最小可接受 fallback**。  
- 把 migration 从“阶段描述”推进为**feature flags、off-path compare、准入阈值与回滚阈值**。  
- 把 Definition of Done 从纯功能闭环推进为**功能 + 性能 + 可回滚 + 演练通过**。

---

## 3. V2.7 的八条硬约束

### 3.1 Run 仍保持单一权威主状态，但下层必须有正式迁移合同

- Run 只保留一个主状态。  
- Attempt / Child / Control Service 必须具备最小状态集合、合法迁移、触发者、guard 与 side effects。  
- UI 可以主展示 Run 状态，但诊断层必须可下钻到其余三层。

### 3.2 Journal 是唯一权威提交真相源，但不是所有操作的同步事务瓶颈

- 所有影响恢复、补偿、probe、审计归因的事实，最终都 MUST 回写 Journal。  
- 四阶段事实边界是语义边界，不要求所有 effect 都同步阻塞式推进全部阶段。  
- 只有 `durabilityClass=durable_pre_dispatch` 的高风险 effect 必须在 dispatch 前跨过 durable commit 门。  
- 低风险、只读或可重建操作 MAY 先执行，再异步补齐低级别 journal append / watermark。

### 3.3 接管必须基于 writer domain、lease 与 fencing，而不是仅靠 token 字段存在

- 同一 attempt 任意时刻，最多只有一个 `execution_writer`。  
- 同一 attempt 任意时刻，最多只有一个 `closure_writer`。  
- claim / renew / revoke / expire 必须可审计。  
- 旧 writer 被 fence 后，不能推进主状态或主 effect，但 MAY 通过 late evidence mailbox 投递只读受限证据。

### 3.4 Effect truth model 统一，但裁决视图分层

- `primary | compensation | probe` 继续是同级 `effectType`。  
- Journal 仍记录统一事实。  
- 裁决时 MUST 至少区分：
  - `PrimaryEffectView`
  - `CompensationPlanView`
  - `ProbeEvidenceView`
- 不允许把所有裁决都压成一张无限增长的混合 DAG。

### 3.5 manual gate 必须 typed，不得继续使用一个笼统的 `manual_required`

系统 MUST 至少支持：

- `manual_approval_required`
- `manual_evidence_access_required`
- `manual_adjudication_required`
- `manual_recovery_required`
- `manual_risk_acceptance_required`
- `manual_external_followup_required`

### 3.6 resume 不仅是资源恢复，也是上下文卫生恢复

- `same_attempt_retry`、`micro_recovery`、`full_rehearsal` 三条车道继续存在。  
- 任何跨 attempt 恢复 MUST 明确 context carry-over 规则。  
- stale hypotheses、错误 tool tail、失效环境快照、污染 prompt head 不能无条件继承。

### 3.7 sanitization 继续以结构化隔离为主，但必须有 raw stream 兜底协议

- 结构化 adapter 是首选。  
- legacy / unstructured 输出不得因为“不好结构化”而直接裸奔到 Paperclip。  
- raw stream 必须至少走 restricted store、最小安全摘要、规则化 redaction 与 excerpt policy。

### 3.8 migration 与上线必须受 cutover gates、rollback gates 与 SLO 约束

- 不允许只靠“原则上可迁移”就切主逻辑。  
- 阴影比较必须尽量离开 Finalizer 主热路径。  
- 新逻辑上线必须满足 divergence threshold、latency budget 与 failure-injection 通过标准。

---

## 4. 核心架构边界（V2.7）

### 4.1 Paperclip（Control Plane）

继续负责：

- Company / Project / Goal / Task
- Approval / Budget / Comment / Operator Intervention
- `ExternalRun` 身份、治理投影、人工介入入口
- 保留要求、访问申请、风险接受与审计查询

新增要求：

- operator surface 继续只允许展示 operator-safe 摘要、引用 ID、脱敏片段与 typed manual gate。  
- 诊断层必须显示：`displayStatus / blockedBy / governanceIntent / reasonCode / manualGateType / residualRiskSummary / sourceVersion / updatedAt`。  
- restricted evidence 访问申请必须带 `purposeOfUse`。  
- front-end 不得将诊断字段反向变成新的主状态源。

明确不做：

- 不保存 raw artifacts / raw traces / restricted evidence body。  
- 不直接管理 sandbox / container / worktree 生命周期。  
- 不持有 Journal committed boundary 定义权。  
- 不保存原始私有 CoT 或内部 KV cache。

### 4.2 Bridge（Integration Plane）

继续负责：

- 输入映射
- 输出映射
- callback 验签
- 幂等去重
- 顺序处理
- 生命周期事件投递与对账补偿

允许保存的最小操作性状态：

- `idempotencyKey`
- `eventId`
- `lastAcceptedSequenceNo`
- `deliveryRetryState`
- `callbackProjectionWatermark`
- `retentionAck`
- `reconcileCursor`
- `callbackSchemaVersion`

明确限制：

- Bridge 不保存完整 progress stream 或完整 trace。  
- Bridge 不做恢复裁决，不做预算仲裁，不做 probe policy 判断。  
- Bridge 不拥有 committed truth 定义权。

### 4.3 Dark Factory（Execution Plane）

继续负责：

- task / acceptance / verification
- runtime / orchestration
- sandbox / worktree / cleanup
- Journal / effects / probes / compensation / recovery
- restricted evidence store / capsule / recon

新增要求：

- Journal truth、writer ownership、late evidence mailbox、effect adjudication、manual gate typing、context hygiene 必须都由 Dark Factory 执行。  
- 任何 writable external effect 都必须声明：
  - `effectSafetyClass`
  - `durabilityClass`
  - `dedupeCapability`
  - `probePolicy`
  - `pessimisticFallbackPolicy`
  - `semanticIntentScope`
  - `confirmationChannel`

### 4.4 Dark Factory Control Roles（逻辑角色，可合并部署）

V2.7 继续将以下视为逻辑角色，而非强制微服务边界：

- `Worker`
- `Finalizer`
- `Reaper`
- `Prober`
- `Critic`
- `Autopsy`
- `Recon`
- `QuotaScheduler`
- `SanitizationPipeline`
- `LateEvidenceCollector`

约束：

- 逻辑角色可以合并部署，但 writer domain、权限边界、审计边界、evidence boundary 不可消失。  
- `LateEvidenceCollector` 可以与 recovery daemon 合并部署，但其 mailbox 不得具备推进主状态权。  
- Minimal Dark Factory 仍允许存在，但必须满足 writer ownership、Journal boundary、evidence access、budget reserve 与 SLO 合同。

---

## 5. 层级状态模型与最小迁移合同

### 5.1 Run 主状态（唯一权威）

Run 保持：

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

终态约束：

- 有效 cancel 且策略允许时，`cancelled` 高于 `failed`。  
- 存在未闭环高风险 effect、cleanup 未完成、incident 未裁决时，不得宣称 `completed`。  
- `completed / failed / cancelled` 只能由 `closure_writer` 或 `operator_override` 推进。

### 5.2 Attempt 状态

Attempt MUST 至少具备：

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

新增约束：

- `resume_ready` 不是执行态；不能直接等价于 `active`。  
- `finalizer_owned` 后，只有 `closure_writer` 可以推进终态。  
- `handoff_pending` 与 `active` 不得长期并存；超过 `handoffMaxSec` 必须进入 `finalizer_owned` 或 `failed`。  
- 同一 Run 默认最多一个 `active` attempt；并行分支模式必须显式声明 `parallelBranchMode=true`。

### 5.3 Child Execution 状态

Child / verification worker / auxiliary executor MUST 至少具备：

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

### 5.4 Control Service 状态

Control Service 实例至少具备：

- `idle`
- `claimed`
- `running`
- `degraded`
- `completed`
- `timed_out`
- `aborted`

### 5.5 最小合法迁移表

#### Run

| Current | Trigger | Actor | Guard | Next | Side effects |
|---|---|---|---|---|---|
| `requested` | request accepted | scheduler | spec valid | `validating` | emit run created |
| `validating` | validation passed | worker/scheduler | budget available | `planning` | write validation summary |
| `planning` | execution starts | execution_writer | approval not required | `executing` | create attempt |
| `executing` | human input required | worker/finalizer | gate typed | `waiting_input` | set manual gate |
| `executing` | approval required | worker/finalizer | gate typed | `waiting_approval` | set manual gate |
| `executing` | takeover starts | finalizer | closure claim granted | `finalizing` | revoke execution writer |
| `finalizing` | closure success | closure_writer | no unresolved high-risk effect | `completed` | emit completion |
| `finalizing` | closure failed | closure_writer | cleanup incomplete or fatal error | `failed` | emit failure |
| `finalizing` | cancel wins | closure_writer/operator | policy allows | `cancelled` | emit cancel |

#### Attempt

| Current | Trigger | Actor | Guard | Next |
|---|---|---|---|---|
| `created` | sandbox/worktree ready | execution_writer | lease granted | `booting` |
| `booting` | first checkpoint | execution_writer | init ok | `active` |
| `active` | override/resume request | operator/finalizer | current step frozen | `frozen` |
| `active` | worker crash or hard cancel | reaper/finalizer | execution lease lost | `handoff_pending` |
| `handoff_pending` | closure claim success | finalizer | fencing advanced | `finalizer_owned` |
| `frozen` | recon required | recon | lane != same_attempt_retry | `recon_pending` |
| `recon_pending` | recon starts | recon | budget reserved | `recon_running` |
| `recon_running` | recon passes | recon/finalizer | lane gate satisfied | `resume_ready` |
| `resume_ready` | new attempt launched | scheduler | previous attempt superseded | `superseded` |
| `finalizer_owned` | closure done | finalizer | outcome determined | `succeeded/failed/cancelled` |

### 5.6 非法状态组合

以下组合 MUST 视为非法并告警：

- `Run=completed` 且存在 `Attempt=active`  
- `Run=completed` 且存在 `manual_*_required` 未闭环  
- 同一 attempt 同时拥有两个 `execution_writer`  
- 同一 attempt 的 `execution_writer` 与 `closure_writer` 同时推进主状态  
- `Attempt=resume_ready` 且仍有 `pendingExternalUnknown=true` 且未打上例外 waiver  
- `Child=reaped` 但父 Attempt 仍无限期 `active` 且无 explanation  
- `finalizer_owned` 后还有 `primary effect dispatch` 发生

### 5.7 聚合规则

- Run 主状态优先级高于 Attempt / Child / Control Service。  
- Attempt 的 `recon_running` 不应直接抬升为 Run 新主状态；只通过 `uiCompositeKey` 反映为 `recovering`。  
- Child 的阻断默认映射到 `blockedBy`，而不是直接改写 Run terminal。  
- `manual_*` 类型必须进入 `blockedBy` 与诊断层，且其类型必须稳定输出。

---

## 6. Writer Ownership、Claim 协议与 Late Evidence Mailbox

### 6.1 Writer domain

每个 attempt MUST 至少区分两个 writer domain：

- `execution_writer`
- `closure_writer`

同一 domain 任意时刻最多一个 owner。  
默认 `execution_writer=worker`，`closure_writer=none`；接管后 `closure_writer=finalizer`。

### 6.2 正式 claim 协议

每个 attempt MUST 具备：

- `attemptId`
- `attemptEpoch`
- `executionLeaseId`
- `closureLeaseId`
- `fencingToken`
- `writerRole = worker | finalizer | reaper | prober | recovery_service | operator_override`
- `claimVersion`
- `claimIssuedAt`
- `claimExpiresAt`

claim 规则：

1. claim 必须通过单点可裁决存储原语完成，至少满足 compare-and-swap 语义。  
2. `attemptEpoch` 只能单调递增，且由 claim store 统一发放。  
3. 新 claim 成功时，旧 claim 立即失效，旧 `fencingToken` 立即进入 stale。  
4. lease 续约失败不等于瞬间 kill，但等于**失去写权限**。  
5. 失去写权限的角色只能：
   - 读取必要状态  
   - 停止新 external dispatch  
   - 将晚到证据投递到 late evidence mailbox  
6. 未成功 claim 的角色不得推进 Run terminal 或发起新的 primary effect。

### 6.3 Fencing 规则

- Journal、state projection、artifact finalize、effect dispatch、compensation dispatch、Run terminal transition 全部 MUST 携带当前 `fencingToken`。  
- 带旧 token 的写入 MUST 被拒绝，并审计为 `stale_writer_rejected`。  
- `stale_writer_rejected` 不得被视为普通重试噪音；高风险场景必须进入 recovery note。

### 6.4 Reaper / Finalizer / Prober 权限矩阵

| 角色 | 可写主状态 | 可写 Journal | 可发起 primary effect | 可写 compensation | 可投递 late evidence |
|---|---:|---:|---:|---:|---:|
| Worker | 是 | 是 | 是 | 否 | 是 |
| Finalizer | 是 | 是 | 否 | 是 | 是 |
| Reaper | 否 | 是 | 否 | 否 | 是 |
| Prober | 否 | 是 | 否 | 否 | 是 |
| Recovery Service | 受限 | 是 | 否 | 受策略限制 | 是 |
| Operator Override | 是 | 是 | 受策略限制 | 受策略限制 | 否 |

### 6.5 Late Evidence Mailbox

#### 定义

`late_evidence_mailbox` 是专门用于接收**已失去主写权限角色**的受限证据投递通道。

#### 能写什么

- provider receipt / callback correlation key
- 外部系统 ACK/NAK 片段
- stdout/stderr digest
- dispatch request fingerprint
- artifact upload receipt
- external reference ID

#### 不能写什么

- Run 主状态推进
- effect commit 裁决
- compensation 裁决
- 终态宣告

#### 使用规则

- 被 fencing 拒绝的 worker MAY 在有限时间窗口内写 mailbox。  
- mailbox entry 必须带：
  - `attemptId`
  - `staleFencingToken`
  - `mailboxEntryId`
  - `evidenceType`
  - `evidenceDigest`
  - `capturedAt`
  - `restrictedEvidenceRef`
- Finalizer 在裁决 `recovered_unknown` 且满足任一条件时 MUST 先扫描 mailbox：
  - `effectSafetyClass=irreversible`  
  - `blastRadiusClass>=medium`  
  - `confirmationChannel=callback | adapter_audit`  
  - `dispatch_visible=true && journal_committed=false`

### 6.6 优雅退让协议

被 fence 的 worker MUST：

1. 停止新 primary dispatch。  
2. 尝试 flush 本地只读证据到 mailbox。  
3. 释放本地资源并退出。  
4. 不得继续争抢 claim。  
5. 若 mailbox 写失败，只能记录 `late_evidence_drop_risk`，不得重新夺回写权。

---

## 7. Execution Journal：语义边界、物理持久与 committed 定义

### 7.1 正式定义

V2.7 将 Journal 定义收敛为：

- Journal 是唯一**权威提交真相源**。  
- 四阶段边界是**语义边界**，不是所有 effect 必须同步串行完成的热路径事务。  
- committed 的判断以 `durableWatermark` 为准，而不是以 projection 或 callback 为准。  
- committed 的物理语义必须由底层存储合同显式定义，而不能只停留在“某种 durable”描述上。

### 7.2 四阶段语义边界

每个关键 effect 或执行动作至少区分：

1. `intent_recorded`
2. `dispatch_visible`
3. `journal_committed`
4. `recovered_unknown`

解释：

- `intent_recorded`：系统已记录语义意图。  
- `dispatch_visible`：adapter 已尝试把请求发向外部世界。  
- `journal_committed`：相关事实已经跨过 authoritative durable boundary。  
- `recovered_unknown`：由于崩溃、切换或外部系统不透明，真实世界状态仍需额外裁决。

### 7.3 Watermark 规范

每个 attempt MUST 至少维护：

- `appendWatermark`
- `durableWatermark`
- `projectionWatermark`
- `graphMaterializeWatermark`
- `mailboxScanWatermark`

规则：

- 权威恢复起点是 `durableWatermark`。  
- `appendWatermark > durableWatermark` 的尾部区间视为不确定尾部。  
- `mailboxScanWatermark` 用于证明 Finalizer 已扫描晚到证据范围。  
- projection 与 graph 永远不得反向定义 `durableWatermark`。

### 7.4 Committed 的最低物理语义

实现 MUST 明确定义 committed 的最低条件；至少需要一张类似下表的实现绑定：

| Journal backend profile | `journal_committed` 最低条件 |
|---|---|
| single-node durable DB | 本地事务提交且 fsync 成功 |
| quorum log / replicated DB | 达到配置的写仲裁确认 |
| object store + index | 索引事务提交成功且 object pointer 持久可读 |
| hybrid WAL + DB | WAL durable 且 DB pointer 可重放 |

约束：

- 不允许把“进程内 buffer 已写入”声称为 committed。  
- 多副本 / 多 region 部署必须明确 authoritative write quorum。  
- 发生故障转移时，新的 writer/claim store MUST 保持 epoch 单调递增，不得回退 committed 边界。

### 7.5 Graph 与 reconcile records

- Effect Graph 仍是裁决视图，不是第二真相源。  
- reconcile、callback、probe、operator adjudication 想成为权威事实，必须回写 Journal。  
- 允许存在多个 materialized views，但只有 Journal committed 事实具有最终裁决权。

---

## 8. Effect Model：统一 truth model、分层视图与 semantic intent

### 8.1 统一 effect 结构

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

### 8.2 统一事实，不统一混合大图

V2.7 明确：

- Journal 保持统一 truth model。  
- 但 Finalizer / recovery / UI 不应一律消费同一张无限增长的混合 DAG。  
- 系统 SHOULD 物化至少三个视图：
  - `PrimaryEffectView`：只看主 effect 及其正向依赖  
  - `CompensationPlanView`：只看补偿动作与补偿顺序  
  - `ProbeEvidenceView`：只看 probe、callback、mailbox、operator adjudication 等证据

### 8.3 补偿原则

- 补偿不是历史抹除，而是后续纠正动作。  
- 原始 effect 一旦 committed，不得伪装为“从未发生”。  
- `compensation_completed` 不代表主 effect 不存在。  
- 补偿链默认 `maxCompensationDepth=1`；超出后默认人工裁决。

### 8.4 semantic intent contract

#### 定义

`semanticIntentId` 表示“同一业务语义动作”的稳定标识，不等于请求 UUID，也不等于 attemptId。

#### 作用域

`semanticIntentScope` MUST 至少区分：

- `per_effect`
- `per_run`
- `per_external_system_business_key`

#### 规则

- 同一语义动作在 `same_attempt_retry / micro_recovery / takeover retry` 中必须复用同一 `semanticIntentId`。  
- 不同业务动作不得复用同一 `semanticIntentId`。  
- `provider_idempotency_key` 若存在，应由 `semanticIntentId` 稳定映射产生。  
- 冲突、碰撞、过期必须显式记录，不得静默替换。

### 8.5 `dedupeCapability` 规则

- `none`：默认 `manual_adjudication_required` 或 `manual_external_followup_required`。  
- `callback_only`：不得 blind retry，只能等待 callback / adapter audit / mailbox evidence。  
- `intent_token`：允许有限次重试，但必须复用相同 `semanticIntentId`。  
- `provider_idempotency_key`：允许在 provider 文档保证的时间窗内重试，但必须记录 provider contract version。

### 8.6 composite effect 与 partial commit

每个 effect MAY 挂接：

- `compositeEffectId`
- `subEffectIds[]`
- `partialCommitState = none | partial_visible | partial_committed | unknown_partial`
- `reentrantRecoveryPolicy`

规则：

- 复合 effect 不要求成为单一数据库事务，但必须能拆成可审计子 effect。  
- 出现部分提交时，不得把整个 effect 简化成“成功”或“失败”二元。  
- `partial_*` 状态默认提高裁决等级，至少进入 `manual_adjudication_required` 或更严格策略。

---

## 9. Durability 分层与热路径预算

### 9.1 `durabilityClass`

保留并强化：

- `ephemeral_local`
- `local_append`
- `local_sync`
- `durable_async`
- `durable_pre_dispatch`

### 9.2 语义与热路径合同

| durabilityClass | 最低要求 | 允许丢失窗口 | 典型用途 |
|---|---|---|---|
| `ephemeral_local` | 仅进程内临时 | 进程崩溃可全部丢失 | 临时 scratch |
| `local_append` | 本地 append log | 节点丢失可丢尾部 | 低风险读工具、可重建中间态 |
| `local_sync` | 本地 durable sync | 节点级 durable，不保证多副本 | 本地关键 checkpoint |
| `durable_async` | 提交到 authoritative durable store，但可异步在主流程后确认 | 有限未确认窗口 | probe、可补偿外部写 |
| `durable_pre_dispatch` | dispatch 前必须跨过 authoritative durable commit | 不允许先发后记 | 高风险、不可逆、不可安全探测外部写 |

### 9.3 热路径要求

- 四阶段事实边界是语义模型，不得自动实现为所有操作都同步等待 `durable_pre_dispatch`。  
- 只有高风险 effect 必须阻塞等待 pre-dispatch commit。  
- 只读、低风险、可重建操作 SHOULD 尽量留在 `local_append/local_sync/durable_async`。  
- 若 `durable_pre_dispatch` 使用率超过预算阈值，系统 MUST 触发架构告警，防止热路径退化成串行事务执行器。

---

## 10. 配额、限流、公平性与 closure reserve

### 10.1 预算字段

保留：

- `executionBudgetUsd`
- `verificationBudgetUsd`
- `reservedCleanupBudgetUsd`
- `postmortemReserveBudgetUsd`
- `executionWallClockSec`
- `reservedCleanupWallClockSec`
- `tenantFairnessPolicy`
- `projectFairnessPolicy`

新增：

- `recoveryLaneBudgetUsd`
- `lateEvidenceProcessingBudgetUsd`
- `maxDurablePreDispatchRate`

### 10.2 子执行配额

继续使用本地预分配额度：

- `childSpendLeaseUsd`
- `childTokenLease`
- `childRpmLease`
- `childLeaseExpiresAt`

### 10.3 closure reserve

- Finalizer / Prober / Recon / Autopsy / LateEvidenceCollector 必须优先使用 reserve 预算。  
- reserve 耗尽时不得静默失败；必须写：
  - `cleanup_incomplete`
  - `postmortem_degraded`
  - `late_evidence_unprocessed`

---

## 11. Capsule V6：字段级 merge、context hygiene 与 carry-over budget

### 11.1 升级目标

V2.7 将 Capsule 从 V5 升级为 **V6**，新增三个目标：

1. 字段级 merge strategy 正式化  
2. context carry-over budget 正式化  
3. stale hypothesis quarantine 正式化

### 11.2 Capsule V6 结构

#### Head

- `currentGoal`
- `highestPriorityTodo`
- `mustValidateFirst[]`
- `mustNotRepeat[]`
- `refutableHypotheses[]`
- `nextAttemptBrief`
- `validationBudgetUsd`
- `maxValidationSteps`
- `maxValidationWallClockSec`
- `staleFieldSet[]`
- `carryOverTokenBudget`
- `contextResetPolicy`

#### Body

- `openTodos`
- `knownFailures`
- `rejectedApproaches`
- `activeHypotheses`
- `quarantinedHypotheses`
- `decisionCheckpoint`
- `environmentSnapshot`
- `assumptionSet`
- `batchIntentSnapshot`
- `recoveryLaneRecommendation`
- `promptTailDigest`

#### Tail

- `recentToolLedgerTail`
- `artifactRefs`
- `traceRefs`
- `restrictedEvidenceRefs`
- `probeRefs`
- `mailboxEvidenceRefs`
- `capsuleMergeConflicts[]`

### 11.3 字段级 merge strategy

关键字段 SHOULD 明确 merge 策略：

| 字段 | mergeStrategy |
|---|---|
| `currentGoal` | `authority_wins` |
| `highestPriorityTodo` | `latest_valid_authority_wins` |
| `mustValidateFirst[]` | `ranked_union_with_budget_cap` |
| `mustNotRepeat[]` | `union_dedup` |
| `refutableHypotheses[]` | `ranked_union_dedup` |
| `environmentSnapshot` | `field_level_latest_with_expiry` |
| `artifactRefs` | `append_ref_only` |
| `restrictedEvidenceRefs` | `append_ref_only` |
| `quarantinedHypotheses` | `append_with_reason` |

### 11.4 context hygiene 规则

- `micro_recovery` 默认不继承完整 prompt tail。  
- 只允许在 `carryOverTokenBudget` 范围内带入压缩后的 tool ledger tail。  
- 连续失败后被判定为 stale 的 hypothesis MUST 进入 `quarantinedHypotheses`，不得直接进入下次 prompt head。  
- `contextResetPolicy` 至少支持：
  - `full_reset`
  - `head_only`
  - `tail_summary_only`
  - `carry_selected_refs`

### 11.5 有界验证

- `mustValidateFirst[]` 只允许验证最高风险且最可判定的 1~N 项。  
- 不允许“critic of critic”递归套娃。  
- 验证预算耗尽时，必须降级为 `manual_*` 或 `resume_with_warning`，不得无限递归。

---

## 12. Sanitization、Legacy Adapter 与 Restricted Evidence

### 12.1 三类 adapter

V2.7 把 adapter 分成：

1. `structured_adapter`  
2. `semi_structured_adapter`  
3. `raw_stream_adapter`

### 12.2 structured / semi-structured 主路径

继续优先输出：

- `operatorSafeSummary`
- `restrictedRawRef`
- `safeExcerpt[]`
- `semanticSurrogates[]`

### 12.3 raw stream fallback

对于 `raw_stream_adapter`，MUST 至少执行：

1. 原始输出直接落 restricted store  
2. 生成摘要时使用规则化 redaction / allowlist excerpt，而不是原样透传  
3. 记录：
   - `rawStreamClass`
   - `excerptPolicyVersion`
   - `redactionRuleSetVersion`
   - `safeSummaryHeuristicVersion`
4. 若无法在在线主路径内安全摘要，则只允许输出：
   - 固定模板告警  
   - digest  
   - restricted reference  
   - 访问申请入口

### 12.4 residual LLM sanitizer

`residual LLM sanitizer` 继续默认 `off`。  
只能用于：

- incident replay
- offline re-sanitize
- 人工授权的专项路径

### 12.5 漏检处置

发现 false negative 时，系统 MUST 支持：

- 生成 `sanitizationIncidentId`
- 回溯受影响对象
- re-sanitize
- purge / tombstone
- 不可改写审计
- 对下游索引、缓存、副本做可验证失效

### 12.6 Restricted Evidence：访问控制 + 用途绑定

每次 evidence 访问必须至少带：

- `subjectId`
- `objectRef`
- `purposeOfUse`
- `requestedScope`
- `approvedScope`
- `requestedDuration`
- `approvedDuration`
- `redactionLevel`
- `exportability`

`purposeOfUse` SHOULD 至少支持：

- `operator_recovery`
- `incident_response`
- `security_forensics`
- `customer_impact_review`
- `legal_hold_review`

规则：

- 普通 operator 默认只能 `view_metadata` 或 `view_excerpt`。  
- `request_full_access` SHOULD 需要双人审批或等价策略门。  
- `break_glass_access` MUST 带原因、时长、审批链、自动过期时间与导出限制。  
- evidence 导出应默认 `reference_only`，而不是明文下载。

---

## 13. Resume 链路：三条恢复车道、三层 Recon 与 lane escalation

### 13.1 三条恢复车道

保留：

1. `same_attempt_retry`
2. `micro_recovery`
3. `full_rehearsal`

### 13.2 车道选择原则

#### `same_attempt_retry`

仅适用于：

- 瞬态网络失败
- 可确认未产生外部副作用的本地错误
- 当前 `execution_writer` 仍然持有有效 lease

#### `micro_recovery`

仅适用于：

- 无高风险 `pendingExternalUnknown`
- 无 approval wait 后恢复
- 无严重 drift
- 上下文可以在预算内净化

#### `full_rehearsal`

必须用于：

- 存在未闭环 unknown high-risk effect
- 长时间冻结
- callback contract drift
- environment / secret / branch 明显漂移
- 连续轻恢复失败超过阈值

### 13.3 lane escalation matrix

| 当前车道 | 失败类型 | 次数阈值 | 下一车道 |
|---|---|---:|---|
| `same_attempt_retry` | 同类瞬态失败重复 | 2 | `micro_recovery` |
| `same_attempt_retry` | 发现外部 unknown 或 lease 风险 | 1 | `full_rehearsal` 或 `finalizer_owned` |
| `micro_recovery` | 同因失败重复 | 2 | `full_rehearsal` |
| `micro_recovery` | context hygiene 无法满足预算 | 1 | `full_rehearsal` |
| `full_rehearsal` | recon 为 `red` | 1 | `manual_recovery_required` |

### 13.4 三层 Recon

继续至少区分：

1. `code_artifact_recon`
2. `env_dependency_recon`
3. `external_state_recon`

### 13.5 partial evidence 与 hard red gate

允许 `amber + partial_evidence`，但以下场景 MUST 直接 `red`：

- 未闭环的 `irreversible` effect 且确认缺失  
- `blastRadiusClass=high` 且 `confirmationChannel` 不可用  
- callback contract drift 且无替代 probe  
- approval boundary 变化且需重新授权  
- evidence access 被策略拒绝导致关键裁决不可执行

### 13.6 context hygiene 合同

任何 `micro_recovery` / `full_rehearsal` MUST 记录：

- `contextResetPolicy`
- `carryOverTokenBudget`
- `toolTailCarryOverDigest`
- `quarantinedHypotheses[]`
- `droppedContextRefs[]`

---

## 14. `manual_required` 拆型与 UI 合同

### 14.1 typed manual gate

系统 MUST 输出稳定的 `manualGateType`：

- `manual_approval_required`
- `manual_evidence_access_required`
- `manual_adjudication_required`
- `manual_recovery_required`
- `manual_risk_acceptance_required`
- `manual_external_followup_required`

### 14.2 UI 展示规则

默认操作视图只展示有限主视觉态：

- `healthy_executing`
- `waiting_on_human`
- `cancelling`
- `recovering`
- `blocked_manual`
- `blocked_unknown_effect`
- `finalizing_cleanup`
- `done_completed`
- `done_failed`
- `done_cancelled`

同时附带：

- `manualGateType`
- `displayStatus`
- `blockedBy`
- `phase`
- `reasonCode`
- `reconGrade`
- `residualRiskSummary`
- `sourceVersion`

前端不得自行推导新的主状态；只能消费已定义枚举。

---

## 15. 回调、事件模型与投影合同

### 15.1 生命周期事件

Bridge 处理的生命周期事件至少包括：

- `run_state_changed`
- `interrupt_acknowledged`
- `guardrail_exhausted`
- `compensation_started/completed/failed`
- `cleanup_started/completed/failed`
- `resume_capsule_available`
- `lease_expired`
- `recon_started/completed`
- `takeover_started/completed`
- `manual_gate_changed`

### 15.2 回调排序与幂等

每个 callback event MUST 带：

- `eventId`
- `sequenceNo`
- `projectionWatermark`
- `schemaVersion`
- `isReplay`

规则：

- 消费方必须按 `sequenceNo` 或 watermark 进行去重与乱序容忍。  
- out-of-order delivery 允许发生，但不得覆盖更高序号状态。  
- replay event 必须显式标识，不得伪装成首次投递。

### 15.3 观测专线

细粒度 telemetry 继续走 OTLP / logs / PubSub，不走 Bridge 生命周期通道。

---

## 16. 合同增量（V2.7）

### 16.1 `POST /api/external-runs` 新增建议字段

```json
{
  "resumePolicy": {
    "defaultRecoveryLane": "micro_recovery",
    "fullRehearsalRequiredAfterApprovalWait": true,
    "sameAttemptRetryLimit": 2,
    "microRecoveryLimit": 2,
    "contextCarryOverBudget": 4000,
    "defaultContextResetPolicy": "tail_summary_only"
  },
  "effectPolicy": {
    "recordSideEffects": true,
    "requireCompensationForWritableTools": true,
    "allowIrreversibleEffects": false,
    "defaultDedupeCapability": "none",
    "semanticIntentRequiredForWritableEffects": true,
    "maxDurablePreDispatchRate": 0.15
  },
  "takeoverPolicy": {
    "claimStoreRequired": true,
    "lateEvidenceMailboxEnabled": true,
    "lateEvidenceRetentionSec": 86400
  },
  "sanitizationPolicy": {
    "sanitizeByConstructionRequired": true,
    "legacyRawStreamFallback": "restricted_store_plus_safe_summary",
    "residualLlMSanitizerDefault": "off"
  },
  "sloPolicy": {
    "maxProjectionLagSec": 15,
    "maxTakeoverRtoSec": 120,
    "maxCleanupLagSec": 300
  }
}
```

### 16.2 新增回调字段

- `manualGateType`
- `mailboxScanWatermark`
- `pendingExternalUnknown`
- `semanticIntentSummary`
- `contextResetPolicy`
- `carryOverTokenBudget`
- `takeoverClaimVersion`
- `schemaVersion`
- `isReplay`

### 16.3 Schema 字段摘要

#### Attempt / Claim

- `claimVersion`
- `claimIssuedAt`
- `claimExpiresAt`
- `writerDomain`
- `closureLeaseId`

#### Journal

- `mailboxScanWatermark`
- `authoritativeStoreProfile`
- `commitQuorumClass`

#### Effect

- `semanticIntentId`
- `semanticIntentScope`
- `compositeEffectId`
- `partialCommitState`
- `reentrantRecoveryPolicy`

#### Capsule

- `carryOverTokenBudget`
- `contextResetPolicy`
- `quarantinedHypotheses[]`
- `mailboxEvidenceRefs`

#### Evidence Access

- `purposeOfUse`
- `approvedDuration`
- `redactionLevel`
- `exportability`

---

## 17. Migration、Feature Flags 与 Cutover Gates

### 17.1 功能开关分期

V2.7 推荐按功能开关渐进上线，而不是让 Finalizer 主热路径长期承受双轨复杂度：

1. `flag.writer_claim_protocol`
2. `flag.late_evidence_mailbox`
3. `flag.semantic_intent_contract`
4. `flag.manual_gate_typing`
5. `flag.raw_stream_sanitization_fallback`
6. `flag.resume_context_hygiene`
7. `flag.v27_state_transition_enforcement`

### 17.2 off-path shadow compare

允许 shadow compare，但 SHOULD 满足：

- 尽量离开 Finalizer 主热路径  
- 只读消费 Journal / projections  
- 输出 divergence report，不直接执行新裁决  
- 高风险流量可按采样或白名单运行

### 17.3 cutover gates

进入主裁决前，至少满足：

- shadow divergence rate < 0.5%  
- takeover RTO p95 不劣化超过 15%  
- callback projection lag p95 不超过 15 秒  
- failure-injection 必测集全通过  
- 无 `stale_writer_rejected` 漏审计  
- raw stream fallback 覆盖率达到目标阈值

### 17.4 rollback gates

出现以下任一情况 MUST 支持快速回滚：

- divergence rate 连续超阈值  
- takeover RTO 或 cleanup lag 明显超预算  
- typed manual gate 丢失或回退成模糊文本  
- mailbox evidence 积压超过处理上限  
- high-risk effect 发生未经授权的 blind retry

---

## 18. Failure Injection 与验收标准

### 18.1 最小测试矩阵

在 V2.6 基础上，V2.7 至少新增覆盖：

1. stale worker 被 fence 后将 provider receipt 写入 mailbox，Finalizer 能消费  
2. `callback_only` effect 在 unknown 状态下不会 blind retry  
3. `provider_idempotency_key` effect 在时间窗内受控重试成功且不重复记账  
4. raw stream adapter 输出不会直接泄露到 Paperclip  
5. `micro_recovery` 会清理 stale hypotheses，不复用完整污染 tail  
6. `manual_required` 被稳定拆型输出到 UI 与 callback  
7. `partialCommitState` 能触发正确 adjudication  
8. feature flag 回滚后旧逻辑仍可安全读取新字段

### 18.2 每个用例的期望输出

每个用例至少产出：

- 事件时间线
- Journal 片段
- 期望状态转移
- 期望 `uiCompositeKey`
- 期望 callback
- 期望 evidence 访问记录
- 期望 mailbox 扫描结果
- 通过/失败判定

### 18.3 通过标准

- 必须验证状态正确，也必须验证**不发生错误副作用**。  
- `stale_writer_rejected` 必须 100% 可观测。  
- 高风险 unknown effect 不得盲重试。  
- raw stream 输出不得未脱敏直达 operator surface。  
- typed manual gate 不得退化成模糊 reason 文本。

---

## 19. 最低 SLO 与运行预算

V2.7 首次引入最低建议 SLO；实现可更严格，但不应更松：

| 指标 | 建议目标 |
|---|---|
| Journal append p95 | <= 50 ms |
| durable pre-dispatch commit p95 | <= 200 ms |
| callback projection lag p95 | <= 15 s |
| Finalizer takeover RTO p95 | <= 120 s |
| cleanup completion lag p95 | <= 300 s |
| mailbox evidence processing lag p95 | <= 60 s |
| sanitization main-path added latency p95 | <= 100 ms |
| recon gate decision p95 | <= 30 s |

约束：

- 若系统无法满足 SLO，必须在 rollout decision 中显式阻断，而不是仅记录已知问题。  
- 高风险 effect 的安全优先级高于吞吐；低风险热路径吞吐优先级高于形式上的强一致幻觉。

---

## 20. Phase 0 文档清单（V2.7）

建议至少补齐以下文档：

1. `writer-claim-protocol-and-late-evidence-mailbox.md`
2. `journal-authoritative-commit-semantics.md`
3. `hierarchical-state-transition-matrix.md`
4. `semantic-intent-and-dedupe-contract.md`
5. `manual-gate-typing-and-operator-surface.md`
6. `capsule-v6-context-hygiene-and-merge-strategy.md`
7. `raw-stream-sanitization-fallback.md`
8. `v27-cutover-gates-and-slo.md`

---

## 21. V2.7 Definition of Done

达到以下条件，可认为 V2.7 最小闭环成立：

1. writer ownership 已具备 claim 协议、lease 语义、epoch 单调性与 stale reject。  
2. late evidence mailbox 已可处理高风险 unknown effect 的晚到证据。  
3. Journal committed 的最低物理语义已按具体 backend profile 定义。  
4. Run / Attempt / Child / Control Service 的最小迁移表已落实。  
5. `manual_required` 已拆成稳定 typed manual gate。  
6. effect model 已具备 semantic intent contract、partial commit 与分层裁决视图。  
7. Capsule V6 已支持字段级 merge、context reset、carry-over budget 与 hypothesis quarantine。  
8. legacy raw stream adapter 已有安全 fallback。  
9. resume 车道已具备 escalation matrix 与 context hygiene 合同。  
10. migration 已支持 feature flags、off-path compare、cutover/rollback gates。  
11. failure injection 必测集全通过。  
12. 最低 SLO 已被观测并纳入上线准入。

---

## 22. 最终决策与实施优先级

### 22.1 最终决策

继续坚持方案 B，并将 V2.7 解释为：

- **Paperclip** 拥有治理投影、审批、访问申请与 operator surface。  
- **Dark Factory** 拥有 committed execution truth、effect truth、evidence truth 与 closure truth。  
- **Bridge** 只拥有最小操作性状态，不拥有业务控制权与 committed 定义权。  
- **V2.7 的核心立场**：该强一致的地方必须强一致；该异步的地方必须明示异步；该模糊的地方不得假装精确；该危险的地方不得省掉人工 gate。

### 22.2 实施优先级

V2.7 的优先级顺序建议为：

1. `writer claim protocol + fencing semantics`
2. `late evidence mailbox`
3. `journal authoritative commit semantics`
4. `manual gate typing`
5. `semantic intent + dedupe contract`
6. `resume context hygiene + lane escalation`
7. `raw stream sanitization fallback`
8. `state transition enforcement`
9. `feature flags + cutover gates + SLO`
10. `更复杂的 UI、深度运维视图与长期优化`

---

## 23. 收尾判断

V2.7 的目标，不是把系统继续写成更厚的架构小说，而是把 V2.6 尚未彻底闭环的几个现实问题写成正式合同：

1. **旧 writer 被 fence 之后，外部世界并不会自动回到“未发生”**  
2. **轻恢复如果不处理上下文卫生，只会把错误更快地重复一次**  
3. **非结构化现实不会因为文档希望结构化就自动变整洁**  
4. **迁移和上线不只需要正确性，还需要性能边界和回滚门槛**

> **一句话收尾**：V2.7 的意义，是把“谁说了算、谁能接管、什么时候必须强一致、什么时候允许异步、飞出去的副作用如何追回、污染上下文如何净化、人工介入到底是哪一种、迁移什么时候能切主”统一写成可执行规格。