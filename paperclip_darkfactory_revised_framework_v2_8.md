# Paperclip × Dark Factory 修订版框架 V2.8

**版本**：2.8  
**状态**：Draft for implementation  
**定位**：在 V2.7 已经完成边界澄清、协议补全与迁移约束的基础上，继续把高质量规格草案压缩成更少自由发挥空间的实现合同。V2.8 的目标不是再引入新概念，而是把分叉高发点进一步写成默认策略、裁决算法、测量口径、兼容规则与异常路径矩阵。  
**适用范围**：若与 V2.7 冲突，以本稿为准；若与本稿内部冲突，以优先级更高的规范层与更保守的安全裁决为准。  

---

## 0. V2.8 相对 V2.7 的一句话变化

V2.8 的重点，是把 V2.7 里仍然容易在实现中产生分歧的地方，继续从“原则正确”压到“默认策略明确、冲突裁决唯一、测量口径统一、异常路径可执行”：

1. **新增规范层级、冲突优先级与默认规则来源，减少 MUST / SHOULD / MAY 的解释漂移。**  
2. **claim / fencing 从字段与基本协议推进到时钟、failover、split-brain 与 server-authoritative lease 语义。**  
3. **late evidence mailbox 增加 trust model、seal 协议、扫描水位、TTL、大小/速率限制与“空邮箱不代表未发生”约束。**  
4. **Run / Attempt / Child / Control Service 补齐更多 sad path 与全局优先级规则。**  
5. **effect adjudication 不再只讲视图分层，而是增加证据来源优先级、冲突决策表与默认降级路径。**  
6. **新增官方 policy profiles，限制 effect 维度自由组合，避免 per-run 策略爆炸。**  
7. **context hygiene 从“净化”推进到“净化 + 调试保真”，防止 tail_summary_only 抹掉关键堆栈与原始证据坐标。**  
8. **raw stream fallback 增加 oversize / burst fuse，防止恶意或爆炸性输出打挂 sanitization 主路径。**  
9. **新增 schema evolution / backward compatibility 合同，定义 V2.7 历史 Journal 在 V2.8 下的默认裁决。**  
10. **shadow compare 与 SLO 增加 measurement contract，避免对 LLM 非确定性输出做错误的字符级比较。**

> **一句话版本**：V2.8 解决的不是“有没有考虑到坑”，而是“当多个团队分别实现 claim、mailbox、恢复、裁决、迁移与观测时，是否还能对同一条现实世界时间线得出同一个结论”。

---

## 1. 结论先行

V2.8 继续坚持方案 B，并保持三层边界：

- **Paperclip**：治理面，负责身份、审批、预算、访问申请、人工裁决入口、保留要求与 operator surface。  
- **Dark Factory**：执行面，负责 runtime、Journal、effects、recovery、adjudication、evidence、cleanup 与 execution truth。  
- **Bridge**：集成面，负责输入/输出映射、幂等去重、回调投递与最小操作性状态，不升级为 committed truth source。  

V2.8 的核心立场：

- 该强一致的地方必须强一致。  
- 该异步的地方必须明示异步。  
- 该不确定的地方必须以 `unknown`、`manual_*` 或更保守路径表达，不得假装精确。  
- 该可默认的地方必须给出官方默认 profile，不把平台变成无限可配置的策略引擎。  
- 该需要跨团队统一的地方必须有 machine-readable schema、稳定枚举与测量口径。  

---

## 2. V2.8 继承什么、修正什么

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

### 2.2 相对 V2.7 的修正

V2.8 重点把下列内容从“骨架完备”推进到“实现更不容易分叉”：

- 把规范文本增加为**四层优先级体系**。  
- 把 claim store 的权威时间、续租判定、故障转移与失联退化语义写死。  
- 把 late evidence mailbox 的扫描协议从“先扫”推进为“等待、封口、扫描、记录水位、处理迟到”的完整时序。  
- 把状态迁移增加失败路径、拒绝路径、返回路径与全局冲突优先级。  
- 把 effect 裁决增加“证据冲突时谁说了算”的决策表。  
- 把 policy 维度收敛成官方 profile，减少自由组合。  
- 把 context hygiene 增加“关键调试证据不得被摘要吞掉”的保真规则。  
- 把 raw stream fallback 增加体积熔断与采样摘要合同。  
- 把 schema evolution 正式纳入 Journal / callback / capsule / evidence 兼容合同。  
- 把 divergence rate、RTO、lag 等指标增加统一 measurement contract。  

---

## 3. 规范层级、冲突优先级与默认规则来源

### 3.1 规范层级

V2.8 将规范文本分为四层，优先级从高到低：

1. **L1 Safety Invariants**：安全与真相不变量，任何实现不得违反。  
2. **L2 Protocol Contracts**：claim、mailbox、Journal、callback、schema 等协议合同。  
3. **L3 Default Policy Profiles**：官方默认策略与默认阈值，允许更严格，不允许更松。  
4. **L4 Operational Guidance**：推荐 rollout、实现建议、观测建议。  

解释规则：

- L1 与 L2 冲突时，以 L1 为准。  
- L3 不得削弱 L1 / L2。  
- L4 不得被实现团队误读为强制协议。  
- “更严格者为准”只适用于**安全边界与访问边界**；对流程冲突，应按层级与作用域裁决，而不是按语气词强弱裁决。

### 3.2 关键词语义

- **MUST**：不满足即视为规范违规。  
- **SHOULD**：默认必须实现；若不实现，必须有审计可见的偏离记录与风险说明。  
- **MAY**：允许实现层选择，但不得破坏上层不变量。  
- **DEFAULT**：官方默认值；实现可更严格但必须保持 schema 与行为兼容。  

### 3.3 全局冲突优先级

当多个条件同时出现时，系统 MUST 按以下优先级裁决：

1. `stale_writer_rejected` / writer 权限违规  
2. L1 safety red gate  
3. evidence access policy denial 导致关键裁决不可执行  
4. `manual_adjudication_required` / `manual_risk_acceptance_required`  
5. authorized cancel  
6. fatal closure failure  
7. recovery lane progression  
8. 普通进度推进  

补充约束：

- `cancelled` 高于 `failed` 仅在**取消被授权且未违反更高安全优先级**时成立。  
- 任何高风险 `unknown` effect 未闭环时，不得直接以“无新证据”为由推进 `completed`。  
- 空 mailbox、无 callback、无 probe 都只能表达“未证实”，不能自动表达“未发生”。

---

## 4. V2.8 的九条硬约束

### 4.1 Run 仍保持单一权威主状态

- Run 只保留一个主状态。  
- Attempt / Child / Control Service 必须有正式迁移合同。  
- UI 允许聚合展示，但不得反向定义主状态。  

### 4.2 Journal 仍是唯一权威提交真相源

- 所有影响恢复、补偿、审计、probe、人工裁决的事实，最终都 MUST 回写 Journal。  
- projection、graph、callback、mailbox 都不是 committed truth source。  
- committed 的判定以 `durableWatermark` 与 backend profile 为准。  

### 4.3 Lease 以服务端权威判定为准

- lease 是否仍有效，由 claim store 的权威提交结果决定。  
- 客户端本地时钟只能用于**更早自停**，不能用于继续写。  
- 未拿到续租成功确认的 writer，必须按失权处理。  

### 4.4 split-brain 条件下优先保守停写

- 无法连通 authoritative claim store 的 writer，不得继续推进主状态或新的 primary effect。  
- 网络分区时，活性可以下降，真相不可分叉。  

### 4.5 mailbox 只是证据通道，不是第二真相源

- mailbox entry 只能增加证据，不得直接推进终态。  
- 空 mailbox 不得被解释为“未 dispatch”。  

### 4.6 effect truth model 统一，但 adjudication 必须唯一

- Journal 仍是一套统一事实。  
- `PrimaryEffectView`、`CompensationPlanView`、`ProbeEvidenceView` 必须分层物化。  
- 证据冲突时必须按决策表产生唯一裁决，不得由各团队自行拼 heuristics。  

### 4.7 manual gate 必须是工作流合同，不只是标签

- 每类 `manualGateType` 必须定义处理角色、最小证据、允许动作与 SLA。  
- UI 上不得把六类 gate 再混回模糊 reason。  

### 4.8 context hygiene 必须保留关键调试证据

- `tail_summary_only` 不得丢失可定位错误的原始引用、摘要坐标与 restricted ref。  
- 摘要可以压缩语料，不能抹掉关键证据锚点。  

### 4.9 migration 必须受 measurement contract 约束

- 不允许用字符级比较直接评估 LLM 裁决一致性。  
- divergence 必须比较结构化决策结果，而不是自由文本表述。  

---

## 5. 核心架构边界（V2.8）

### 5.1 Paperclip（Control Plane）

继续负责：

- Company / Project / Goal / Task  
- Approval / Budget / Comment / Operator Intervention  
- `ExternalRun` 身份、治理投影、人工介入入口  
- evidence 访问申请、风险接受、审计查询  

新增约束：

- operator surface 只允许展示 operator-safe 摘要、引用 ID、typed manual gate、风险摘要。  
- 前端不得自行推导新的主状态。  
- 对 restricted evidence 的访问申请必须携带 `purposeOfUse`、时长与导出范围。  

### 5.2 Bridge（Integration Plane）

继续负责：

- 输入映射  
- 输出映射  
- callback 验签  
- 幂等去重  
- 生命周期事件投递  
- reconcile cursor 与最小投影状态  

明确限制：

- Bridge 不持有 committed 定义权。  
- Bridge 不持有恢复裁决权。  
- Bridge 不持有 evidence truth。  

### 5.3 Dark Factory（Execution Plane）

继续负责：

- runtime / orchestration  
- sandbox / worktree / cleanup  
- Journal / effects / probes / compensation / recovery  
- capsule / recon / sanitization / restricted evidence  
- claim、fencing、mailbox、adjudication  

新增要求：

- 所有 writable external effect MUST 绑定官方 profile 或显式声明 profile 偏离。  
- 所有关键协议事件 MUST 带 `schemaVersion`。  
- 所有终态裁决 MUST 输出结构化 adjudication reason，而不是仅输出自然语言摘要。  

---

## 6. 层级状态模型与完整度更高的迁移合同

### 6.1 Run 主状态（唯一权威）

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

- `completed / failed / cancelled` 只能由 `closure_writer` 或 `operator_override` 推进。  
- 存在未闭环 high-risk effect、cleanup 未完成、manual gate 未闭环、incident 未裁决时，不得宣称 `completed`。  

### 6.2 Attempt 状态

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

- `resume_ready` 不是执行态。  
- `finalizer_owned` 后，只有 `closure_writer` 可以推进终态。  
- 同一 Run 默认最多一个 `active` attempt；并行模式必须显式 `parallelBranchMode=true`。  

### 6.3 Child Execution 状态

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

### 6.4 Control Service 状态

Control Service 实例至少具备：

- `idle`  
- `claimed`  
- `running`  
- `degraded`  
- `completed`  
- `timed_out`  
- `aborted`  

### 6.5 Run 最小合法迁移表（V2.8）

| Current | Trigger | Actor | Guard | Next | Side effects |
|---|---|---|---|---|---|
| `requested` | request accepted | scheduler | spec valid | `validating` | emit run created |
| `validating` | validation passed | worker/scheduler | budget available | `planning` | write validation summary |
| `validating` | validation failed | worker/scheduler | fatal input error | `failed` | emit validation failed |
| `validating` | cancel accepted | operator/scheduler | policy allows | `cancelled` | emit cancel |
| `planning` | approval required | planner/finalizer | gate typed | `waiting_approval` | set manual gate |
| `planning` | planning failed | planner | unrecoverable planning error | `failed` | emit planning failure |
| `planning` | execution starts | execution_writer | approval not required | `executing` | create attempt |
| `waiting_approval` | approval granted | operator/system | approval valid | `planning` or `executing` | clear approval gate |
| `waiting_approval` | approval rejected | operator | final rejection | `cancelled` or `failed` | emit rejection reason |
| `waiting_input` | input received | operator/user | input validated | `executing` | clear input gate |
| `waiting_input` | input timeout / abandoned | policy engine | SLA exceeded | `failed` or `cancelled` | record timeout |
| `executing` | human input required | worker/finalizer | gate typed | `waiting_input` | set manual gate |
| `executing` | approval required | worker/finalizer | gate typed | `waiting_approval` | set manual gate |
| `executing` | takeover starts | finalizer | closure claim granted | `finalizing` | revoke execution writer |
| `executing` | cancel wins | operator/finalizer | no higher safety block | `finalizing` | start safe shutdown |
| `finalizing` | closure success | closure_writer | no unresolved high-risk effect | `completed` | emit completion |
| `finalizing` | closure failed | closure_writer | cleanup incomplete or fatal error | `failed` | emit failure |
| `finalizing` | cancel wins | closure_writer/operator | policy allows and safe | `cancelled` | emit cancel |

### 6.6 Attempt 最小合法迁移表（V2.8）

| Current | Trigger | Actor | Guard | Next |
|---|---|---|---|---|
| `created` | sandbox/worktree allocated | execution_writer | lease granted | `booting` |
| `created` | allocation failed | scheduler | retry not allowed | `failed` |
| `booting` | first checkpoint | execution_writer | init ok | `active` |
| `booting` | init failed | execution_writer/reaper | unrecoverable init error | `failed` |
| `booting` | cancel accepted | operator/finalizer | policy allows | `cancelled` |
| `active` | override / recon request | operator/finalizer | current step frozen | `frozen` |
| `active` | lease lost / worker crash | reaper/finalizer | execution lease lost | `handoff_pending` |
| `active` | local fatal error | worker/finalizer | retry lane unavailable | `failed` |
| `frozen` | recon required | recon | lane != same_attempt_retry | `recon_pending` |
| `frozen` | same attempt retry resumes | execution_writer | lease valid and safe | `active` |
| `recon_pending` | recon starts | recon | budget reserved | `recon_running` |
| `recon_pending` | recon cannot start | recon/finalizer | evidence or budget denied | `finalizer_owned` or `failed` |
| `recon_running` | recon passes | recon/finalizer | lane gate satisfied | `resume_ready` |
| `recon_running` | recon red | recon/finalizer | hard red gate | `finalizer_owned` |
| `handoff_pending` | closure claim success | finalizer | fencing advanced | `finalizer_owned` |
| `handoff_pending` | claim failed terminally | finalizer | authoritative store unavailable too long | `failed` |
| `resume_ready` | new attempt launched | scheduler | previous attempt superseded | `superseded` |
| `resume_ready` | operator refuses resume | operator | policy requires stop | `finalizer_owned` |
| `finalizer_owned` | closure done | finalizer | outcome determined | `succeeded/failed/cancelled` |

### 6.7 Child / Control Service 最小迁移补充

#### Child

| Current | Trigger | Next |
|---|---|---|
| `queued` | worker starts | `running` |
| `running` | dependency missing | `waiting_dependency` |
| `running` | blocked by policy / gate | `blocked` |
| `running` | graceful cancel | `soft_cancel_pending` |
| `running` | hard kill issued | `hard_kill_pending` |
| `soft_cancel_pending` | kill ack | `cancelled` |
| `hard_kill_pending` | process reaped | `reaped` |
| `running` | success | `completed` |
| `running` | failure | `failed` |

#### Control Service

| Current | Trigger | Next |
|---|---|---|
| `idle` | claim acquired | `claimed` |
| `claimed` | task begins | `running` |
| `running` | degraded but serviceable | `degraded` |
| `degraded` | recovered | `running` |
| `running/degraded` | success | `completed` |
| `running/degraded` | timeout | `timed_out` |
| `running/degraded` | aborted by higher authority | `aborted` |

### 6.8 非法状态组合

以下组合 MUST 视为非法并告警：

- `Run=completed` 且存在 `Attempt=active`  
- `Run=completed` 且存在 `manual_*_required` 未闭环  
- 同一 attempt 同时拥有两个 `execution_writer`  
- 同一 attempt 的 `execution_writer` 与 `closure_writer` 同时推进主状态  
- `Attempt=resume_ready` 且 `pendingExternalUnknown=true` 且未打上例外 waiver  
- `finalizer_owned` 后还有 `primary effect dispatch` 发生  
- `waiting_approval` 与未设置 `manualGateType=manual_approval_required` 并存  
- `waiting_input` 与未设置输入来源要求并存  

### 6.9 聚合规则

- Run 主状态优先级高于 Attempt / Child / Control Service。  
- Attempt 的 `recon_running` 只通过 `uiCompositeKey=recovering` 表达，不升级为新的 Run 主状态。  
- Child 的阻断默认进入 `blockedBy`，而不是直接改写 Run terminal。  
- 多个 gate 并存时，UI 必须按全局冲突优先级排序展示。  

---

## 7. Writer Ownership、Claim 协议、时钟与故障转移

### 7.1 Writer domain

每个 attempt MUST 至少区分两个 writer domain：

- `execution_writer`  
- `closure_writer`  

同一 domain 任意时刻最多一个 owner。默认 `execution_writer=worker`，`closure_writer=none`；接管后 `closure_writer=finalizer`。

### 7.2 正式 claim 字段

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
- `authoritativeClockTs`  
- `claimStoreProfile`  
- `claimFailoverEpoch`  

### 7.3 claim 基础规则

1. claim 必须通过单点可裁决存储原语完成，至少满足 compare-and-swap 语义。  
2. `attemptEpoch` 只能单调递增，且必须由 claim store 统一发放。  
3. `claimIssuedAt / claimExpiresAt` 以 claim store 的权威时间戳为准，不以客户端本地时间为准。  
4. 新 claim 成功时，旧 claim 立即失效，旧 `fencingToken` 立即进入 stale。  
5. 续租成功以**服务端提交确认**为准；未收到确认即视为未续租。  
6. 失去写权限的角色只能：读必要状态、停止新 external dispatch、投递晚到证据、释放资源。  
7. 未成功 claim 的角色不得推进 Run terminal、不得发起新的 primary effect。  

### 7.4 本地时钟与权威时间的关系

- 客户端本地时钟 MAY 用于“提前怀疑 lease 将过期”，从而更早停止写入。  
- 客户端本地时钟 MUST NOT 用于“自行认定 lease 仍有效”。  
- 任何“本地判断 lease 还没过期，所以继续写”的实现都视为协议违规。  

### 7.5 split-brain / 网络分区语义

- 无法访问 authoritative claim store 的 writer，最多只允许保留只读态与 mailbox 写入能力。  
- 网络分区期间，系统 MAY 牺牲可用性，但 MUST 防止双写。  
- 不允许在没有全局单调 epoch 发号器的条件下，把多 region active-active claim 伪装成单 writer 语义。  

### 7.6 failover 语义

发生 claim store 或控制平面故障转移时，新的主节点 MUST 满足：

- `attemptEpoch` 不回退  
- stale token 不复活  
- 已 durable 的 revoke / claim 事件不丢失  
- `claimFailoverEpoch` 单调递增并审计可见  

若无法保证以上条件，系统 MUST 阻断自动接管，降级为 `manual_adjudication_required` 或 `manual_recovery_required`。

### 7.7 Recovery Service 与 Finalizer 边界

- `Recovery Service` 负责 recon、车道选择与恢复准备，不拥有默认终态宣告权。  
- `Finalizer` 负责 closure、effect adjudication、terminal decision。  
- `resume_ready` 只能表示“已准备好由 scheduler 发起新 attempt 或由 finalizer 决定停止”，不能自动恢复为 `active`。  
- 当 `Recovery Service` 与 `Finalizer` 冲突时，以 `closure_writer` 的权威裁决为准。  

---

## 8. Late Evidence Mailbox：trust model、seal 协议与扫描合同

### 8.1 定义

`late_evidence_mailbox` 是用于接收**已失去主写权限角色**的受限证据投递通道。它是旁路证据源，不是第二真相源。

### 8.2 mailbox entry 最小字段

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
- `entrySignature` or equivalent authenticity proof  
- `entrySchemaVersion`  

### 8.3 能写什么 / 不能写什么

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

### 8.4 trust model

- mailbox entry 必须具备来源真实性证明，至少能绑定到 stale token、attemptId 与 capture 时间。  
- mailbox entry 的真实性不自动代表语义正确性；它只是证据输入，仍需进入 adjudication。  
- Finalizer MUST 对 entry 进行签名校验、schemaVersion 校验、大小校验与重复校验。  

### 8.5 大小、速率、TTL 与去重

官方默认值：

- `maxMailboxEntryBytes = 256KB`  
- `maxMailboxEntriesPerAttempt = 1000`  
- `maxMailboxWriteRate = 20 entries / min / attempt`  
- `mailboxEntryTtlSec = 86400`  
- `dedupeKey = mailboxEntryId || (evidenceDigest + sourceRole + capturedAt bucket)`  

超限规则：

- 超大小 entry MUST 截断为 digest + restricted ref，不得把超大正文挤入 mailbox 主路径。  
- 速率超限 MUST 审计为 `mailbox_rate_limited`。  
- TTL 到期可归档，但不得无审计删除。  

### 8.6 seal 协议

V2.8 新增 mailbox seal 协议：

1. Finalizer 获得 closure claim 后，写入 `mailboxSealRequestedAt`。  
2. stale writer 若仍存活，SHOULD 在 `maxMailboxGraceSec` 内完成最后 flush 并发送 `mailbox_sealed_by_writer`。  
3. Finalizer 必须等待以下两者之一后开始正式扫描：  
   - 收到 `mailbox_sealed_by_writer`  
   - `maxMailboxGraceSec` 超时  
4. Finalizer 扫描到 `sealScanUpperBound`，并将结果持久化为 `mailboxScanWatermark`。  
5. `mailboxScanWatermark` 之后再到达的新 entry 视为**迟到证据**，不得悄悄覆盖已有裁决，只能触发 reopen 或人工裁决策略。  

默认值：

- `maxMailboxGraceSec = 5`  
- `reopenOnPostScanHighRiskEvidence = true`  

### 8.7 使用规则

- 被 fencing 拒绝的 writer MAY 在有限时间窗口内写 mailbox。  
- Finalizer 在裁决 `recovered_unknown` 且满足任一条件时 MUST 先执行 seal + scan：  
  - `effectSafetyClass=irreversible`  
  - `blastRadiusClass>=medium`  
  - `confirmationChannel=callback | adapter_audit`  
  - `dispatch_visible=true && journal_committed=false`  
- mailbox 写失败时，只能记录 `late_evidence_drop_risk`，不得重新夺回写权。  
- **空 mailbox 不得被解释为“没有发出去”**。  

### 8.8 迟到证据的 reopen 规则

- 若 post-scan evidence 到达且影响 high-risk unknown effect，系统 MUST 进入 reopen adjudication。  
- 已经 `completed` 的 Run 若收到高风险矛盾证据，不得静默改写历史；必须生成 incident / adjudication record。  

---

## 9. Execution Journal：语义边界、物理持久与兼容语义

### 9.1 正式定义

V2.8 继续定义：

- Journal 是唯一权威提交真相源。  
- 四阶段边界是语义边界，不代表所有 effect 都走同步热路径事务。  
- committed 的判断以 `durableWatermark` 与 backend profile 为准。  

### 9.2 Watermark 规范

每个 attempt MUST 至少维护：

- `appendWatermark`  
- `durableWatermark`  
- `projectionWatermark`  
- `graphMaterializeWatermark`  
- `mailboxScanWatermark`  
- `schemaCompatWatermark`  

规则：

- 权威恢复起点是 `durableWatermark`。  
- `appendWatermark > durableWatermark` 的区间视为不确定尾部。  
- `mailboxScanWatermark` 用于证明 Finalizer 已扫描到的晚到证据范围。  
- `schemaCompatWatermark` 用于证明旧 schema 事件已完成兼容解释或回填。  

### 9.3 Committed 的最低物理语义

实现 MUST 明确定义 committed 的最低条件；至少需要如下 backend profile 绑定：

| Journal backend profile | `journal_committed` 最低条件 |
|---|---|
| single-node durable DB | 本地事务提交且 fsync 成功 |
| quorum log / replicated DB | 达到配置写仲裁确认 |
| object store + index | 索引事务提交成功且 object pointer 持久可读 |
| hybrid WAL + DB | WAL durable 且 DB pointer 可重放 |

约束：

- 不允许把进程内 buffer 写入声称为 committed。  
- 多副本 / 多 region 部署必须明确定义 authoritative write quorum。  
- 故障转移后 epoch 与 committed 边界不得回退。  

### 9.4 Schema evolution / backward compatibility

V2.8 新增兼容合同：

- Journal event、callback event、capsule、mailbox entry、evidence access request 都 MUST 带 `schemaVersion`。  
- V2.7 历史 Journal 若缺少 V2.8 新字段，必须按“保守默认值”解释，不得以缺字段默认成功。  

V2.7 -> V2.8 默认解释规则：

| 缺失字段 | V2.8 默认解释 |
|---|---|
| `semanticIntentId` | `unknown_semantic_intent`，禁止自动高风险重试 |
| `claimStoreProfile` | `legacy_unspecified_claim_store`，禁止多 region 自动接管 |
| `entrySignature` | `legacy_unverified_mailbox_entry`，仅作弱证据 |
| `carryOverBudgetUnit` | `token_estimate` |
| `criticalDebugRefs[]` | 视为未知，禁止把摘要当作完整调试证据 |
| `measurementProfile` | `legacy_unspecified_measurement`，不得纳入正式 cutover 分母 |

补充约束：

- 旧字段缺失时，允许继续读取，但默认进入更保守策略。  
- 不允许为了兼容旧数据而弱化新协议的不变量。  

---

## 10. Effect Model：统一 truth model、唯一裁决与 semantic intent

### 10.1 统一 effect 结构

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

### 10.2 统一事实，不统一混合大图

系统 SHOULD 物化至少三个视图：

- `PrimaryEffectView`：主 effect 与正向依赖  
- `CompensationPlanView`：补偿动作与顺序  
- `ProbeEvidenceView`：probe、callback、mailbox、operator adjudication 等证据  

### 10.3 semantic intent contract

`semanticIntentId` 表示“同一业务语义动作”的稳定标识，不等于请求 UUID，也不等于 attemptId。

`semanticIntentScope` MUST 至少区分：

- `per_effect`  
- `per_run`  
- `per_external_system_business_key`  

规则：

- 同一语义动作在 `same_attempt_retry / micro_recovery / takeover retry` 中必须复用同一 `semanticIntentId`。  
- 不同业务动作不得复用同一 `semanticIntentId`。  
- `provider_idempotency_key` 若存在，应由 `semanticIntentId` 稳定映射产生。  
- 冲突、碰撞、过期必须显式记录，不得静默替换。  
- 外部系统不识别该 key 时，不得假装已获得外部幂等保证。  

### 10.4 `dedupeCapability` 规则

- `none`：默认 `manual_adjudication_required` 或 `manual_external_followup_required`。  
- `callback_only`：不得 blind retry，只能等待 callback / adapter audit / mailbox evidence。  
- `intent_token`：允许有限次重试，但必须复用相同 `semanticIntentId`。  
- `provider_idempotency_key`：允许在 provider 文档保证的时间窗内重试，但必须记录 provider contract version。  

### 10.5 证据来源与权重

V2.8 将证据来源分为：

1. `journal_committed_fact`  
2. `provider_callback_verified`  
3. `provider_receipt_or_mailbox_verified`  
4. `probe_result`  
5. `operator_adjudication`  
6. `heuristic_inference`  

规则：

- 没有任何来源可以否定已 committed 的 Journal 历史事实。  
- `operator_adjudication` 可以决定最终操作结论，但不得篡改历史事件。  
- `heuristic_inference` 不能单独关闭 high-risk unknown。  
- 弱证据可以提高风险等级，不能单独降低风险等级。  

### 10.6 裁决决策表（简化版）

| 场景 | 默认裁决 |
|---|---|
| `dispatch_visible=false` 且 `journal_committed=true` | 未出站，可安全按未发出处理 |
| `dispatch_visible=true` 且 `journal_committed=true` 且 callback success | 成功已确认 |
| `dispatch_visible=true` 且 `journal_committed=false` 且 mailbox 有 receipt | `recovered_unknown`，按证据闭环或人工裁决 |
| `dispatch_visible=true` 且 `journal_committed=false` 且 mailbox 空且无 callback | 仍为 `recovered_unknown`，不得推断未发生 |
| `partialCommitState=unknown_partial` | 至少 `manual_adjudication_required` |
| `dedupeCapability=none` 且 high-risk external write unknown | `manual_adjudication_required` 或 `manual_external_followup_required` |
| callback 与 probe 冲突 | 保持 unknown，进入 operator adjudication 或更保守 fallback |
| post-scan mailbox evidence 与既有 completed 结论冲突 | reopen + incident，不可静默覆盖 |

### 10.7 composite effect 与 partial commit

每个 effect MAY 挂接：

- `compositeEffectId`  
- `subEffectIds[]`  
- `partialCommitState = none | partial_visible | partial_committed | unknown_partial`  
- `reentrantRecoveryPolicy`  

规则：

- `partial_*` 状态默认提高裁决等级。  
- `unknown_partial` 默认直接进入 `manual_adjudication_required`，除非 profile 明确给出更严格自动保守路径。  

---

## 11. 官方 Policy Profiles（V2.8 新增）

V2.8 要求所有 writable effect 默认绑定官方 profile 之一。若偏离，必须记录 `customPolicyDeviationReason`。

### 11.1 `irreversible_external_write`

适用：扣费、发信、下单、不可安全回滚的外部写。

默认：

- `durabilityClass = durable_pre_dispatch`  
- `dedupeCapability = provider_idempotency_key | intent_token | none`  
- `probePolicy = conservative`  
- `pessimisticFallbackPolicy = manual_hold`  
- `confirmationChannel = callback | provider_receipt | adapter_audit`  
- `blastRadiusClass >= medium`  

### 11.2 `compensable_external_write`

适用：可补偿但仍有真实外部副作用的写操作。

默认：

- `durabilityClass = durable_async`  
- `dedupeCapability = intent_token | provider_idempotency_key`  
- `probePolicy = allowed_if_safe`  
- `pessimisticFallbackPolicy = compensation_then_review`  

### 11.3 `callback_only_legacy_write`

适用：老系统、无幂等键、无法安全探测，只能等 callback 或人工外部确认。

默认：

- `durabilityClass = durable_pre_dispatch`  
- `dedupeCapability = callback_only | none`  
- `probePolicy = disabled`  
- `pessimisticFallbackPolicy = wait_or_manual_followup`  
- blind retry 默认禁止  

### 11.4 `read_only_low_risk_tool`

适用：只读工具、可重建中间态。

默认：

- `durabilityClass = local_append | durable_async`  
- `dedupeCapability = not_required`  
- `probePolicy = optional`  
- `blastRadiusClass = low`  

### 11.5 `legacy_raw_stream_tool`

适用：只能输出原始流、无法可靠结构化的工具。

默认：

- `durabilityClass = durable_async`  
- `dedupeCapability = not_applicable`  
- 输出必须走 restricted store + safe summary  
- oversize fuse 必开  

---

## 12. Capsule V7：context hygiene + debug fidelity

### 12.1 升级目标

V2.8 将 Capsule 从 V6 升级为 **V7**，新增三个目标：

1. 在保持上下文卫生的同时保留关键调试证据  
2. 把预算从“仅 token 数”推进到“预算语义 + 计量单位”  
3. 让恢复选择可审计、可重放、可解释  

### 12.2 Capsule V7 关键新增字段

- `carryOverBudgetUnit = token_estimate | chars | segments`  
- `criticalDebugRefs[]`  
- `toolTailCarryOverDigest`  
- `droppedContextRefs[]`  
- `selectionPolicyVersion`  
- `summaryHeuristicVersion`  

### 12.3 context hygiene 合同

- `micro_recovery` 默认不继承完整 prompt tail。  
- 只允许在 `carryOverBudget` 范围内带入压缩后的 tool ledger tail。  
- stale hypotheses MUST 进入 `quarantinedHypotheses[]`。  
- `contextResetPolicy` 至少支持：  
  - `full_reset`  
  - `head_only`  
  - `tail_summary_only`  
  - `carry_selected_refs`  

### 12.4 debug fidelity 规则

`tail_summary_only` 或任何摘要策略 MUST 保留：

- 原始 stack trace / compiler error / stderr 的 restricted ref  
- 至少一个可定位坐标：文件名、行号、异常类名或 error code  
- 失败工具调用的 digest 与时间顺序  
- 关键 environment drift 的引用  

不允许把长错误压缩成“发生异常”这一类无定位摘要后，再丢弃原始 ref。

### 12.5 预算计量规则

- `carryOverBudget` 是语义预算，不强制要求所有实现做昂贵的精确 token 计量。  
- 实现可用 `token_estimate`、字符预算或段落预算，但必须在 schema 中声明 `carryOverBudgetUnit`。  
- 同一部署内不得对同一 policy 同时混用不可审计的预算算法。  

---

## 13. Sanitization、Legacy Adapter、Restricted Evidence 与 Oversize Fuse

### 13.1 三类 adapter

V2.8 保持：

1. `structured_adapter`  
2. `semi_structured_adapter`  
3. `raw_stream_adapter`  

### 13.2 raw stream fallback

对于 `raw_stream_adapter`，MUST 至少执行：

1. 原始输出直接落 restricted store  
2. 摘要使用规则化 redaction / allowlist excerpt  
3. 记录：  
   - `rawStreamClass`  
   - `excerptPolicyVersion`  
   - `redactionRuleSetVersion`  
   - `safeSummaryHeuristicVersion`  
4. 若无法在线安全摘要，则只允许输出：固定模板告警、digest、restricted ref、访问申请入口  

### 13.3 Oversize / Burst Fuse（V2.8 新增）

默认阈值：

- `rawStreamSoftLimitBytes = 1MB`  
- `rawStreamHardLimitBytes = 10MB`  
- `rawStreamMaxLinesForInlineExcerpt = 200`  
- `rawStreamBurstRateLimit = 5MB / 10s / run`  

规则：

- 超过 soft limit 时，仅允许采样摘要与 restricted ref。  
- 超过 hard limit 时，不得尝试全量在线 redaction；必须直接截断、采样并标记 `output_truncated_due_to_oversize=true`。  
- Burst 超阈值时，SanitizationPipeline MUST 自保限流，不得因异常输出拖垮主系统。  

### 13.4 Restricted Evidence：访问控制 + 用途绑定

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
- `schemaVersion`  

规则：

- 普通 operator 默认只能 `view_metadata` 或 `view_excerpt`。  
- `request_full_access` SHOULD 需要双人审批或等价策略门。  
- `break_glass_access` MUST 带原因、时长、审批链、自动过期时间与导出限制。  
- evidence 导出默认 `reference_only`，而不是明文下载。  

---

## 14. Resume 链路、lane escalation 与 manual gate workflow

### 14.1 三条恢复车道

保留：

1. `same_attempt_retry`  
2. `micro_recovery`  
3. `full_rehearsal`  

### 14.2 车道选择原则

- `same_attempt_retry`：仅适用于瞬态失败、确认未产生外部副作用、且当前 writer 仍持有效 lease。  
- `micro_recovery`：仅适用于无 high-risk `pendingExternalUnknown`、上下文可在预算内净化、无重大 drift。  
- `full_rehearsal`：用于 high-risk unknown、长冻结、callback contract drift、环境漂移、连续轻恢复失败。  

### 14.3 lane escalation matrix

| 当前车道 | 失败类型 | 次数阈值 | 下一车道 |
|---|---|---:|---|
| `same_attempt_retry` | 同类瞬态失败重复 | 2 | `micro_recovery` |
| `same_attempt_retry` | 发现外部 unknown 或 lease 风险 | 1 | `full_rehearsal` 或 `finalizer_owned` |
| `micro_recovery` | 同因失败重复 | 2 | `full_rehearsal` |
| `micro_recovery` | context hygiene 无法满足预算 | 1 | `full_rehearsal` |
| `full_rehearsal` | recon 为 `red` | 1 | `manual_recovery_required` |

### 14.4 typed manual gate 作为工作流合同

系统 MUST 输出稳定的 `manualGateType`：

- `manual_approval_required`  
- `manual_evidence_access_required`  
- `manual_adjudication_required`  
- `manual_recovery_required`  
- `manual_risk_acceptance_required`  
- `manual_external_followup_required`  

每类 gate MUST 定义：

- `ownerRole`  
- `minimumEvidenceSet`  
- `allowedActions[]`  
- `defaultSlaSec`  
- `escalationTarget`  

### 14.5 UI 展示规则

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

## 15. 回调、事件模型、shadow compare 与 measurement contract

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
- `adjudication_reopened`  

### 15.2 callback 排序与幂等

每个 callback event MUST 带：

- `eventId`  
- `sequenceNo`  
- `projectionWatermark`  
- `schemaVersion`  
- `isReplay`  
- `measurementProfile`  

规则：

- 消费方必须按 `sequenceNo` 或 watermark 去重与乱序容忍。  
- replay event 必须显式标识。  
- out-of-order delivery 不得覆盖更高序号状态。  

### 15.3 shadow compare 规则

允许 shadow compare，但 SHOULD 满足：

- 尽量离开 Finalizer 主热路径  
- 只读消费 Journal / projections  
- 输出 divergence report，不直接执行新裁决  
- 高风险流量按采样或白名单运行  

### 15.4 divergence 的比较对象

V2.8 明确：

- 不比较自由文本 `nextAttemptBrief` 的字面一致性。  
- 应比较结构化结果：  
  - 选择的 recovery lane  
  - `manualGateType`  
  - terminal decision  
  - effect adjudication class  
  - 是否触发 compensation / reopen / manual followup  

可以附加比较摘要质量，但不得把语言表述差异直接记为主分歧。

### 15.5 measurement contract

默认测量口径：

- `shadow divergence rate` 分母：进入 shadow compare 的样本 run 数，而不是全部平台流量。  
- `weighted divergence rate` SHOULD 按 `blastRadiusClass` 与 `effectSafetyClass` 加权。  
- `Finalizer takeover RTO` 起点：authoritative lease expiry 或 revoke committed 时间，两者取更早可审计点；终点：closure claim 成功并推进到可观测接管状态。  
- `callback projection lag`：外部 callback 被 Bridge 验收时间到相关 projection 可见时间。  
- `mailbox evidence processing lag`：entry durable accepted 到其被扫描并反映到 adjudication log 的时间。  

---

## 16. 合同增量（V2.8）

### 16.1 `POST /api/external-runs` 建议新增字段

```json
{
  "resumePolicy": {
    "defaultRecoveryLane": "micro_recovery",
    "sameAttemptRetryLimit": 2,
    "microRecoveryLimit": 2,
    "carryOverBudget": 4000,
    "carryOverBudgetUnit": "token_estimate",
    "defaultContextResetPolicy": "tail_summary_only"
  },
  "takeoverPolicy": {
    "claimStoreRequired": true,
    "claimStoreProfile": "single_authoritative_cas",
    "lateEvidenceMailboxEnabled": true,
    "maxMailboxGraceSec": 5,
    "lateEvidenceRetentionSec": 86400,
    "reopenOnPostScanHighRiskEvidence": true
  },
  "effectPolicy": {
    "defaultPolicyProfileId": "compensable_external_write",
    "semanticIntentRequiredForWritableEffects": true,
    "maxDurablePreDispatchRate": 0.15
  },
  "sanitizationPolicy": {
    "legacyRawStreamFallback": "restricted_store_plus_safe_summary",
    "rawStreamHardLimitBytes": 10485760,
    "oversizeFuseEnabled": true
  },
  "measurementPolicy": {
    "shadowCompareMode": "structured_decision_only",
    "weightedDivergenceEnabled": true
  }
}
```

### 16.2 新增/强化字段摘要

#### Attempt / Claim

- `claimStoreProfile`  
- `authoritativeClockTs`  
- `claimFailoverEpoch`  
- `claimVersion`  
- `claimIssuedAt`  
- `claimExpiresAt`  

#### Journal

- `mailboxScanWatermark`  
- `schemaCompatWatermark`  
- `authoritativeStoreProfile`  
- `commitQuorumClass`  

#### Effect

- `policyProfileId`  
- `semanticIntentId`  
- `semanticIntentScope`  
- `partialCommitState`  
- `reentrantRecoveryPolicy`  

#### Capsule

- `carryOverBudget`  
- `carryOverBudgetUnit`  
- `criticalDebugRefs[]`  
- `quarantinedHypotheses[]`  
- `droppedContextRefs[]`  

#### Mailbox

- `entrySignature`  
- `claimVersionAtCapture`  
- `entrySchemaVersion`  

#### Measurement

- `measurementProfile`  
- `weightedRiskScore`  
- `divergenceClass`  

---

## 17. Migration、Feature Flags、Cutover Gates 与 Rollback Gates

### 17.1 功能开关分期

推荐按功能开关渐进上线：

1. `flag.writer_claim_protocol_v28`  
2. `flag.mailbox_seal_protocol`  
3. `flag.adjudication_decision_table`  
4. `flag.policy_profiles_enforced`  
5. `flag.capsule_v7_debug_fidelity`  
6. `flag.raw_stream_oversize_fuse`  
7. `flag.schema_evolution_v28`  
8. `flag.structured_shadow_measurement`  

### 17.2 cutover gates

进入主裁决前，至少满足：

- shadow divergence rate < 0.5%  
- weighted high-risk divergence = 0  
- takeover RTO p95 不劣化超过 15%  
- callback projection lag p95 不超过 15 秒  
- mailbox evidence processing lag p95 不超过 60 秒  
- failure-injection 必测集全通过  
- 无 `stale_writer_rejected` 漏审计  
- raw stream oversize fuse 覆盖率达到目标阈值  

### 17.3 rollback gates

出现以下任一情况 MUST 支持快速回滚：

- divergence rate 连续超阈值  
- weighted high-risk divergence > 0  
- takeover RTO 或 cleanup lag 明显超预算  
- typed manual gate 丢失或回退成模糊文本  
- mailbox 积压超过处理上限  
- high-risk effect 发生未经授权的 blind retry  
- schema evolution 使旧 Journal 被错误解释为低风险成功  

---

## 18. Failure Injection 与验收标准

### 18.1 最小测试矩阵

V2.8 至少新增覆盖：

1. stale writer 被 fence 后写入 mailbox，并通过 seal 协议被 Finalizer 消费  
2. mailbox 为空时 high-risk unknown 不会被误判为未发生  
3. post-scan high-risk evidence 到达后会 reopen，而不是静默覆盖  
4. split-brain / claim store failover 下不会出现双写  
5. `callback_only_legacy_write` 在 unknown 下不会 blind retry  
6. `provider_idempotency_key` effect 在时间窗内受控重试且不重复记账  
7. `tail_summary_only` 不会丢失关键 stack trace ref  
8. raw stream oversize fuse 在 2GB 爆炸输出下仍能自保  
9. schemaVersion 缺失的 V2.7 Journal 会进入保守解释而非成功捷径  
10. shadow compare 只比较结构化决策，不把自由文本差异误算为主分歧  

### 18.2 每个用例的期望输出

每个用例至少产出：

- 事件时间线  
- Journal 片段  
- 期望状态转移  
- 期望 `uiCompositeKey`  
- 期望 callback  
- 期望 evidence 访问记录  
- 期望 mailbox 扫描结果  
- 期望 adjudication decision  
- 通过/失败判定  

### 18.3 通过标准

- 必须验证状态正确，也必须验证**不发生错误副作用**。  
- `stale_writer_rejected` 必须 100% 可观测。  
- 高风险 unknown effect 不得盲重试。  
- raw stream 输出不得未脱敏直达 operator surface。  
- typed manual gate 不得退化成模糊文本。  
- split-brain 测试中不得出现两个有效 writer 同时推进主状态。  

---

## 19. 最低 SLO 与运行预算（V2.8）

V2.8 保持以下最低建议 SLO；实现可更严格，但不应更松：

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

- 若系统无法满足 SLO，必须在 rollout decision 中显式阻断。  
- 高风险 effect 的安全优先级高于吞吐。  
- 低风险热路径吞吐优先级高于形式上的强一致幻觉。  
- 所有 SLO 报告必须绑定 measurement contract 版本。  

---

## 20. V2.8 Definition of Done

达到以下条件，可认为 V2.8 最小闭环成立：

1. claim 协议已具备 authoritative clock、failover 与 split-brain 语义。  
2. late evidence mailbox 已具备 trust model、seal 协议、扫描水位与迟到证据 reopen 合同。  
3. Run / Attempt / Child / Control Service 的 sad path 迁移矩阵已落实。  
4. effect adjudication 已有证据来源优先级与决策表。  
5. 官方 policy profiles 已启用，禁止无约束自由组合。  
6. Capsule V7 已支持 debug fidelity、预算计量单位与 dropped refs 审计。  
7. raw stream oversize fuse 已上线。  
8. schema evolution / backward compatibility 合同已生效。  
9. shadow compare 已按结构化决策与 measurement contract 运行。  
10. failure injection 必测集全通过。  
11. 最低 SLO 已被观测并纳入上线准入。  

---

## 21. 实施优先级

V2.8 的优先级顺序建议为：

1. `writer claim protocol + authoritative lease semantics + failover`  
2. `late evidence mailbox trust model + seal protocol`  
3. `effect adjudication decision table`  
4. `policy profiles enforced`  
5. `schema evolution + backward compatibility`  
6. `Capsule V7 debug fidelity + budget semantics`  
7. `raw stream oversize fuse`  
8. `structured shadow compare + measurement contract`  
9. `full sad-path state transition enforcement`  
10. `更复杂的 UI、深度运维视图与长期优化`  

---

## 22. 收尾判断

V2.8 的目标，不是把系统继续写成更厚的架构小说，而是把 V2.7 尚存的几类实现分叉点继续写成正式合同：

1. **失去写权的旧 writer 仍可能掌握事实，但不再掌握状态推进权**  
2. **上下文净化不能以牺牲关键调试证据为代价**  
3. **非结构化和爆炸性输出不会因为文档希望整洁就自动变整洁**  
4. **迁移比较必须比较结构化裁决，而不是拿 LLM 自由文本做伪精确一致性**  
5. **旧数据兼容必须走保守解释，而不是用缺字段默认成功**

> **一句话收尾**：V2.8 的意义，是把“谁说了算、什么时候失权、邮箱为空能否下结论、证据冲突谁赢、恢复时哪些上下文能带、历史数据怎么解释、影子比较到底比什么”继续统一写成更少自由发挥空间的执行规格。