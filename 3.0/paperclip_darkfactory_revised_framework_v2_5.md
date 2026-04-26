# Paperclip × Dark Factory 修订版框架 V2.5

**版本**：2.5  
**日期**：2026-04-21  
**定位**：在 V2.4 基础上，吸收 Gemini 与 GLM5.1 最新一轮评审、并统一此前 V2.2 / V2.3 / V2.4 的关键结论后形成的“可开工且可收场”的运行时约束版。  
**适用范围**：若与 V2.4 冲突，以本稿为准。

---

## 0. V2.5 相对 V2.4 的一句话变化

V2.5 不再继续增加“大而全”的保护机制，而是把 V2.4 中最容易互相打架的部分收敛成四条硬约束：

1. **执行与副作用只能有一个真相源**：Execution Journal 是唯一权威源，Effect Graph 只是可重建的物化视图。  
2. **恢复信息不能未经净化就穿透控制面**：Capsule V4 必须先经过脱敏、最小披露和可反证化处理。  
3. **Resume 不是布尔门，而是带风险等级的排演流程**：所有 `Rebase & Recon` 都必须在隔离克隆工作区中 rehearsal。  
4. **安全机制也必须受物理约束**：Autopsy 可降级、WAL 分层耐久、兄弟子任务不做实时 2PC 借调，UI 必须有视觉合成矩阵。

> **一句话版本**：V2.5 的重点，不是把系统做得更复杂，而是把“谁说了算、谁来收场、什么必须强一致、什么允许物理不完美”写成明确合同。

---

## 1. 结论先行

V2.5 继续坚持方案 B，不推翻三层边界：

- **Paperclip**：控制面，负责协作、预算、审批、人工介入、治理展示与保留要求声明。  
- **Dark Factory**：执行面，负责 runtime、sandbox、verification、artifact、补偿、恢复、取证与执行证据。  
- **Bridge**：集成面，只允许持有最小操作性状态，不升级为新的业务控制面。

但 V2.5 在 V2.4 基础上，再明确九个闭环：

1. **Execution Journal 成为唯一执行真相源**。所有副作用、关键 dispatch、probe、compensation、artifact 原子提交都由 Journal 记录；Effect Graph 只能从 Journal 回放重建，不能与之形成双写真相源。  
2. **Effect Policy 引入显式安全分类**。特别新增 `external_unprobeable_non_idempotent`，对“不可安全探测、又非幂等”的黑盒副作用单独处理。  
3. **WAL 改为按风险分层耐久**。不是所有动作都要求同级别 durable append；只有高风险外部写入才必须 pre-dispatch durable。  
4. **Closure 预算拆为 Cleanup Reserve 与 Postmortem Reserve**。Finalizer、Prober、Autopsy、Recon 不能和普通 Worker 抢最后一口预算。  
5. **Critic / Autopsy 只有“建议权”，没有“绝对权威”**。其结论必须带证据引用与可反证假设；下一个 attempt 启动后必须先做轻量 falsifiability 检查。  
6. **Capsule 升级为 V4**。在 V3 的基础上加入脱敏、披露分层、反证前置、证据引用与作者权威等级。  
7. **Rebase & Recon 升级为 Ephemeral Rehearsal**。所有对齐、探测与 dry-run 都必须先在隔离克隆工作区完成，并输出 `green / amber / red` 风险等级，而不是简单 pass / fail。  
8. **配额调度从“兄弟借调”改为“本地租约 + 父级回收池”**。避免把 Quota Scheduler 做成高并发下的 2PC 锁点。  
9. **前端展示保留 `displayStatus + governanceIntent + blockedBy` 的数据合同，但必须通过视觉合成矩阵渲染为单一复合 UI 组件**，而不是把三个字段平铺给用户。

---

## 2. V2.5 继承什么、修正什么

### 2.1 继续继承的部分

以下判断继续成立：

- 方案 B 不变，Paperclip 管治理，Dark Factory 管执行。  
- run-centric 方向不变，`ExternalRun / RunAttempt / ArtifactRef / TraceRef / ResourceLease` 仍成立。  
- Bridge 允许最小状态化，但仅限去重、验签、顺序控制、对账与投递补偿。  
- Run 继续只有**一个主状态机**；中断、恢复、租约、清理、限流都降为标签或属性。  
- 继续承认**不可中断原子区**存在，不把“实时中断长推理”当成基本假设。  
- 继续坚持：**副作用治理优先于完美状态水合**。  
- 继续坚持：**cleanup reserve 不可被执行阶段侵占**。  
- 继续坚持：**Resume 不能原地热会话恢复，必须 Freeze + Resume**。

### 2.2 相对 V2.4 的修正

V2.4 已经补上了 Finalizer / Reaper / Autopsy、Effect DAG、Quota Lease、Capsule V3、`displayStatus` 与 `governanceIntent`。  
V2.5 进一步把下列问题从“有原则”推进到“有唯一真相源、有风险等级、有降级路径、有数据边界”：

- WAL 与 Effect DAG 不再双写，而是收敛成 **Journal → Materialized Graph**。  
- Critic / Autopsy 结论不再被视为“带官方签名的绝对真理”，而是 **带证据的、可推翻的假设集**。  
- Rebase & Recon 不再直接落在真实 worktree 上，而是先经过 **Sandbox Rehearsal**。  
- Recon 不再是硬阻断布尔门，而是 **`green / amber / red` 风险分级 + tolerance**。  
- 兄弟子任务不再做实时双边借调，而是经过 **父级回收池** 调配。  
- Capsule 不再直接携带可能泄密的上下文，而是先经过 **确定性脱敏 → 结构分类 → 可选残差 LLM 净化**。  
- UI 不再把三个治理字段原样扔给用户，而是通过 **组合矩阵** 产出单一复合展示态。

---

## 3. V2.5 的四条硬约束

### 3.1 唯一主状态

Run 继续只有一个权威主状态：

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

任何标签都不能单独构成终态，也不能反向覆盖终态。

### 3.2 唯一执行真相源

执行与副作用的权威真相只能有一个：

- **Execution Journal**：唯一权威、append-only、可回放；
- **Effect Graph**：从 Journal 物化出来的索引 / 视图；
- **UI / Callback Projection**：从主状态、标签、Journal、Graph 合成出来的展示投影。

`Effect Graph` 可以损坏、过期、重建，但 **Journal 不可被其反向定义**。

### 3.3 唯一收场边界

任何 Run 的收场能力必须由 **Dark Factory 控制服务**外置提供，而不能由当前 Worker 自己承担：

- Finalizer
- Reaper
- Prober
- Critic
- Autopsy
- Recon / Rehearsal Service
- Quota Scheduler
- Sanitizer

被 Hard Kill 的 Worker 没有资格给自己善后，也没有资格给自己写高可信遗书。

### 3.4 唯一用户心智出口

面向操作员的 UI 不能把内部多字段状态直接摊开。  
用户最终只应看到一个复合组件，例如：

- `running`
- `cancelling`
- `cancel_blocked_by_unknown_effect`
- `manual_intervention_required`
- `recon_amber_continue_with_warning`
- `postmortem_running`

内部仍保留：

- `displayStatus`
- `governanceIntent`
- `blockedBy`
- `uiCompositeKey`

但前端默认渲染 **`uiCompositeKey` 对应的唯一视觉组件**。

---

## 4. 核心架构边界（V2.5）

### 4.1 Paperclip（Control Plane）

继续负责：

- Company / Project / Goal / Task  
- Approval / Budget / Comment / Operator Intervention  
- `ExternalRun` 身份、治理投影与人工接管入口  
- Cancel / Override / Resume / Manual Gate  
- 保留策略、审计要求、法律保留（如适用）的上层声明

新增要求：

- 只接收**脱敏后的 Capsule 投影**与证据摘要，不能直接得到原始敏感工具输出。  
- 默认显示 `uiCompositeKey`，辅助显示 `displayStatus`、`governanceIntent`、`blockedBy`。  
- 可以查看：
  - `capsuleAuthor`
  - `capsuleAuthority`
  - `confidenceScore`
  - `mustValidateFirst[]`
  - `reconGrade`
  - `reconDiffSummary`
  - `residualRiskSummary`
- 对 `manual_required`、`unknown_effect`、`red recon` 必须有明确人工处理入口。

明确不做：

- 不保存 Journal、Trace、Artifact、Restricted Evidence 的原始内容；  
- 不直接管理 sandbox / worktree / container；  
- 不承担补偿、探测、尸检、配额调度职责；  
- 不持有原始 secrets、短效 token、明文环境变量值。

### 4.2 Bridge（Integration Plane）

继续负责：

- 输入映射  
- 输出映射  
- 回调验签  
- 幂等去重  
- 顺序处理  
- 最小对账状态  
- retention / contract ack 透传

允许保存的操作性状态：

- `idempotencyKey`
- `eventId`
- `lastAcceptedSequenceNo`
- `lastLifecycleEventAt`
- `lastProjectionVersion`
- `deliveryRetryState`
- `reconcileCursor`

明确限制：

- Bridge 不保存完整细粒度 progress；  
- Bridge 不保存完整 Journal；  
- Bridge 不做 model routing、verification、调度裁决、审批判断、尸检与净化。

### 4.3 Dark Factory（Execution Plane）

继续负责：

- task spec / acceptance spec  
- runtime / sandbox / orchestration  
- verification / cleanup / compensation  
- artifact / trace / evidence  
- retry / downgrade / self-heal  
- Journal、Effect Graph、Capsule、Retention 落地

新增要求：

- Raw Evidence 只能进入**Restricted Evidence Store**；  
- Capsule、Callback、Paperclip Projection 只能消费**已脱敏投影**；  
- 所有副作用都必须绑定 `effectSafetyClass`、`durabilityClass`、`probePolicy` 与 `pessimisticFallbackPolicy`。

### 4.4 Dark Factory Control Services（明确化）

V2.5 将以下服务显式视为执行面的控制服务，而不是 Worker 的一部分：

- `Finalizer`：收场、回放、补偿、清理  
- `Reaper`：orphan reclaim、Hard Kill 后资源回收  
- `Prober`：已发未确认 effect 的只读确认  
- `Critic`：失败原因复核与假设生成  
- `Autopsy`：异常终止后的旁路尸检  
- `Recon Service`：Ephemeral Rehearsal、风险分级  
- `Quota Scheduler`：租约发放、父级回收池  
- `Sanitizer`：脱敏与披露分层

这些服务消费的是 **Postmortem Reserve / Cleanup Reserve**，不是普通执行预算。

---

## 5. 状态模型与前端展示：继续单主状态，但补足视觉合成矩阵

### 5.1 主状态、标签与调试字段

主状态保持不变；辅助标签继续保留：

- `interruptTag = none | soft_cancel_requested | hard_cancel_requested | override_requested | resume_requested`
- `leaseTag = active | grace | expired | retire_pending`
- `recoveryTag = none | auto_retrying | downgraded_mode | postmortem_running`
- `cleanupTag = none | cleanup_running | cleanup_pending | compensation_running | compensation_partial | manual_required`
- `retentionTag = standard | audit_hold | legal_hold`

调试字段继续允许：

- `phase`
- `reasonCode`
- `lastMilestone`
- `lastHeartbeatAt`
- `progressCursor`
- `journalWatermark`
- `reconGrade`

### 5.2 给前端看的三个语义字段

继续输出：

- `displayStatus`：当前最主要的展示状态  
- `governanceIntent`：系统或用户正在试图做什么  
- `blockedBy`：当前推进被什么阻断

### 5.3 新增：视觉合成矩阵

V2.5 明确要求提供 `uiCompositeKey`，由后端合成，而不是要求前端自行发明规则。

示例：

- `displayStatus=manual_intervention_required` + `governanceIntent=cancel_requested` + `blockedBy=unknown_effect`  
  → `uiCompositeKey=cancel_blocked_by_unknown_effect`
- `displayStatus=executing` + `governanceIntent=none` + `blockedBy=none`  
  → `uiCompositeKey=running`
- `displayStatus=waiting_approval` + `blockedBy=operator_gate`  
  → `uiCompositeKey=awaiting_operator_approval`
- `displayStatus=planning` + `recoveryTag=postmortem_running`  
  → `uiCompositeKey=postmortem_running`
- `displayStatus=executing` + `reconGrade=amber`  
  → `uiCompositeKey=recon_amber_continue_with_warning`

原则：

- 前端默认只渲染 `uiCompositeKey` 对应组件；  
- `displayStatus / governanceIntent / blockedBy` 作为调试或辅助文字保留；  
- 不允许三个平级 badge 把用户逼成状态机解释器。

---

## 6. 中断模型、外部接管与 Closure 预算

### 6.1 中断分类

继续定义三类治理动作：

1. `soft_cancel`：在安全点消费，优雅退出。  
2. `hard_cancel`：超过宽限时间后强制终止执行单元。  
3. `override_or_resume`：冻结当前 attempt，生成 Capsule V4，以新 attempt 恢复。

### 6.2 不可中断区

继续明确以下场景不可承诺实时中断：

- 单次长模型推理  
- 已发出的外部工具调用  
- 原子 artifact 上传  
- 已进入数据库事务或底层 adapter 不可打断区的工具执行

### 6.3 外部接管协议

当出现 `hard_cancel / worker_crash / lease_expired` 时，流程必须是：

1. 记录 `interruptTag=hard_cancel_requested`；  
2. 强制终止 Worker / Pod / Container；  
3. 由 Finalizer 读取 Journal 水位、Quota Lease、Artifact Session、Restricted Evidence Ref；  
4. 由 Prober / Autopsy / Sanitizer 接管后续流程；  
5. 进入 `finalizing`；  
6. 收束为 `failed` 或 `cancelled`。

### 6.4 Closure 预算拆分（新增明确化）

V2.5 不再只保留一个 cleanup reserve，而是拆为：

- `cleanupReserveUsd / cleanupReserveWallClockSec`：用于 compensation、cleanup、artifact finalize。  
- `postmortemReserveUsd / postmortemReserveWallClockSec`：用于 Prober、Autopsy、Recon、Journal replay、最小诊断。

原则：

- 普通 Worker 不能消费这两个 reserve；  
- Finalizer / Prober / Autopsy 只能消费 reserve，不回头抢运行池；  
- 若 `postmortemReserve` 耗尽，Autopsy 必须降级为模板摘要，而不是无限追求高质量 LLM 尸检；  
- 若 `cleanupReserve` 耗尽，必须显式输出 `cleanup_incomplete` 与剩余风险，而不是假装善后完成。

### 6.5 级联中断树

任何主 agent 派生的子 agent、verification worker、辅助 executor 都必须挂在同一棵中断树下：

- `parentAttemptId`
- `childAttemptIds[]`
- `propagationDeadlineSec`
- `orphanReapDeadlineSec`

要求：

- 父 attempt 收到 cancel / hard_cancel 后，必须广播到所有子执行单元；  
- 子执行单元未按时确认时，由 Reaper 兜底强杀；  
- 不允许出现“父任务已取消，子任务继续烧钱”的孤儿运行。

---

## 7. Watchdog：不仅识别伪推进，也要容纳合法批处理

### 7.1 有效推进证据

续租必须由独立 Watchdog 判定，且至少满足以下一种：

- `progressCursor` 推进  
- `lastMilestone` 更新  
- 关键文件 / worktree diff 发生预期变化  
- 验证基线发生变化  
- 合法批处理的 checkpoint 前进  
- 长推理处于策略允许的宽限区间

### 7.2 伪推进识别

继续保留对以下行为的识别：

- 连续 N 次调用同一工具，参数高度相似；  
- 连续 N 个循环没有产生有效 diff 或验证状态变化；  
- repeated failure signature 重复命中；  
- 围绕同一错误做无边际重试。

### 7.3 `BatchIntent`

为了避免误杀合法批量作业，Agent 在进入相似循环前必须声明：

- `batchIntentId`
- `expectedIterations`
- `expectedTargetSet`
- `expectedCheckpointPattern`
- `loopExpirySec`

Watchdog 规则：

- 有效 `BatchIntent` 覆盖期内，相似性检测降敏；  
- 超出 `expectedIterations`、偏离 `expectedTargetSet`、或连续 checkpoint 不前进时，恢复常规伪推进判定；  
- `BatchIntent` 不能绕过预算、限流与 Hard Kill。

---

## 8. Execution Journal：唯一执行真相源

### 8.1 原则

V2.5 明确：

- **Journal 是唯一权威执行日志**；  
- **Effect Graph 是 Journal 的物化视图，不是独立真相源**；  
- **Finalizer 恢复时先回放 Journal，再重建 Graph，再做补偿 / probe / cleanup 决策**。

### 8.2 推荐 Journal 记录模型

建议 Journal 至少支持以下 `recordType`：

- `tool_intent`
- `tool_dispatch`
- `tool_ack`
- `effect_node_opened`
- `effect_dispatch`
- `effect_ack`
- `effect_probe_started`
- `effect_probe_result`
- `effect_compensation_started`
- `effect_compensation_result`
- `artifact_atomic_start`
- `artifact_atomic_done`
- `batch_checkpoint`
- `recon_started`
- `recon_result`
- `capsule_emitted`

通用字段建议包括：

- `journalSeq`
- `attemptId`
- `timestamp`
- `idempotencyKey`
- `payloadRef`
- `effectRef`
- `riskClass`
- `durabilityClass`
- `evidenceRef`

### 8.3 Journal 与 Effect Graph 的关系

Effect Graph 不再被直接双写，而是通过以下流程形成：

1. Worker / Adapter 写入 `effect_node_opened`；  
2. 后台 materializer 从 Journal 回放构建或更新 Graph；  
3. Graph 记录依赖、状态、补偿策略与 probe 结果；  
4. Finalizer 若发现 Graph 缺失或落后，必须以 Journal 回放出的 `Reconstructed Graph` 为准；  
5. Graph 的持久化值只是缓存与索引，永远可以重建。

### 8.4 Finalizer 的恢复流程

Finalizer 接管时，至少要读取：

- Journal 尾部与 watermarks  
- 当前物化 Effect Graph  
- Resource Lease  
- Quota Lease  
- Artifact Session  
- Tool Adapter 幂等日志（如有）  
- Restricted Evidence 引用

恢复顺序：

1. 校验 Journal 完整性；  
2. 从 Journal 回放生成 `Reconstructed Graph`；  
3. 与持久化 Graph 合并，标出差异；  
4. 再决定 probe、compensation、manual escalation。

---

## 9. Effect Policy：副作用安全分类、依赖补偿与悲观回退

### 9.1 V2.5 的安全分类

所有可写副作用都必须声明 `effectSafetyClass`：

1. `local_ephemeral`  
   - 仅影响当前 sandbox / scratch；  
   - 可随容器销毁而消失；  
   - 不需要外部 probe。  
2. `external_probeable_idempotent`  
   - 可带幂等键；  
   - 可通过只读查询确认；  
   - 允许有限 auto-retry。  
3. `external_probeable_non_idempotent`  
   - 不宜盲重试；  
   - 但可安全只读探测当前状态。  
4. `external_unprobeable_non_idempotent`  
   - 不能安全 probe；  
   - 不可幂等；  
   - 如老旧 webhook、外发邮件、某些黑盒第三方调用。  
5. `irreversible`  
   - 已知不可自动撤销；  
   - 仅在显式审批或预声明策略下允许。

### 9.2 依赖与补偿字段

Effect 物化视图中至少要有：

- `effectId`
- `toolName`
- `effectSafetyClass`
- `dependsOnEffectIds[]`
- `compensationBarrierPolicy = continue_if_safe | block_downstream | manual_gate`
- `effectCommitState = proposed | issued | acked | unknown`
- `probePolicy = safe_read_probe | callback_only | no_probe`
- `pessimisticFallbackPolicy = assume_committed | assume_not_committed | manual_required`
- `compensationStatus = not_needed | pending | running | completed | partial | blocked_by_dependency | probe_required | manual_required | waived`
- `callbackCorrelationKey`

### 9.3 补偿拓扑规则

继续采用依赖感知补偿：

1. 先按 `dependsOnEffectIds[]` 构建 DAG；  
2. 默认按逆拓扑序补偿；  
3. 上游补偿失败时：
   - 若下游 `block_downstream`，则转 `blocked_by_dependency`；  
   - 若 `continue_if_safe`，可继续，但必须写明风险；  
   - 若 `manual_gate`，直接 `manual_required`。  
4. Finalizer 必须产出“已补偿 / 被依赖阻断 / 需人工处理”的显式摘要。

### 9.4 对 `external_unprobeable_non_idempotent` 的特殊规则（新增重点）

这类副作用必须满足以下至少一项，否则禁止发起：

- 操作本身提供**确定性回调**或事后可消费的外部确认事件；  
- 明确声明 `pessimisticFallbackPolicy`；  
- 已通过人工审批并接受状态未知时的人工处理成本。

额外强制规则：

- `probePolicy` 默认必须是 `no_probe` 或 `callback_only`；  
- **禁止盲目 Prober 探测**，避免探测本身引发二次副作用；  
- **禁止 auto-retry**；  
- 若 dispatch 后状态未知，默认升级为 `manual_required`，除非策略明确允许 `assume_committed` 或 `assume_not_committed`。

### 9.5 不可逆副作用

若 `effectSafetyClass=irreversible`：

- 必须在 run 启动前被策略显式允许；  
- 必须记录审批人 / 策略来源；  
- 不允许伪装成“已回滚”；  
- 失败时只能输出 incident / waiver / manual follow-up。

---

## 10. Journal 耐久分层：不是所有动作都值得同级强一致

### 10.1 原则

V2.5 明确反对把所有工具调用都按金融交易系统标准强一致落盘。  
**耐久要求必须按风险分层，而不是一刀切。**

### 10.2 推荐 `durabilityClass`

建议至少分为：

- `local_sync`：写入本地内存 / 本地 NVMe Journal，再异步 flush 到 durable store；  
- `durable_before_dispatch`：必须先 durable append，确认成功后才能 dispatch；  
- `durable_after_atomic_unit`：用于 artifact 等单元性操作，允许原子块完成后再 durable close。

### 10.3 风险到耐久的默认映射

推荐默认映射：

- `local_ephemeral` → `local_sync`  
- `external_probeable_idempotent` → `local_sync` + 异步 durable flush  
- `external_probeable_non_idempotent` → `durable_before_dispatch`  
- `external_unprobeable_non_idempotent` → `durable_before_dispatch`  
- `irreversible` → `durable_before_dispatch`

### 10.4 物理不完美允许范围

V2.5 明确允许：

- 低风险、只读或局部 scratch 相关 Journal 尾部，在进程崩溃时丢最后极少量记录；  
- Autopsy 在预算、RPM 或 provider 不可用时降级为模板；  
- Recon 在 `amber` 风险下继续推进，而不是一律阻断。

V2.5 明确不允许：

- 对 `external_unprobeable_non_idempotent` 和 `irreversible` 在未 durable 记录前直接 dispatch；  
- 对高风险外部写入依赖“也许没发出去”的侥幸推理；  
- 让强一致要求拖垮所有低风险热路径。

---

## 11. 配额与限流：本地租约 + 父级回收池，明确放弃兄弟实时借调

### 11.1 V2.5 的预算判断

V2.5 继续坚持：

- 运行池可以弹性共享；  
- cleanup reserve 与 postmortem reserve 必须硬保留；  
- 子任务不直接共享一个无限热池；  
- 调度器不应位于每一次请求的强依赖热路径。

### 11.2 推荐预算字段

建议 `budgetPolicy` 扩展为：

- `runBudgetUsd`
- `cleanupReserveUsd`
- `postmortemReserveUsd`
- `executionHintUsd`
- `verificationHintUsd`
- `runWallClockSec`
- `cleanupReserveWallClockSec`
- `postmortemReserveWallClockSec`

### 11.3 Quota Lease

每个 child attempt 获取一段**本地可消费租约**：

- `quotaLeaseId`
- `childSpendCapUsd`
- `childWallClockCapSec`
- `localRpmLease`
- `localTpmLease`
- `leaseRefreshThreshold`
- `leaseExpiresAt`

规则：

- 大多数正常请求在本地租约内完成；  
- child 异步上报消耗；  
- 只有租约将耗尽或需要重平衡时，才访问中央调度器。

### 11.4 父级回收池（新增定稿）

V2.5 明确**不支持兄弟子任务之间的实时点对点借调**。  
取而代之的是：

- 每个父 run 维护 `reclaimPool`；  
- child 在 `waiting_dependency`、`blocked`、`idle`、`completed` 时，未用完的租约在 `leaseReturnAfterSec` 后自动回收到 `reclaimPool`；  
- 关键路径 child 可从 `reclaimPool` 申请 `criticalPathBoost`；  
- 调度器只与父级池交互，不做 A、B 兄弟之间的 2PC 协调。

这样做的目的：

- 避免调度器成为全局锁；  
- 避免兄弟之间的同步确认超时；  
- 保留必要弹性，而不过度引入协调复杂度。

### 11.5 Provider RPM/TPM 限流

除预算外，还必须有供应商速率整形：

- provider / model 级 token bucket  
- repeated 429 触发 backoff / 降并发 / 降级模型  
- runaway child 可被单独限速或熔断

### 11.6 控制服务预算

Finalizer / Prober / Autopsy / Recon 不使用普通 child quota。  
它们消费的是：

- `cleanupReserve`
- `postmortemReserve`

这样可避免“任务正是因为预算耗尽而失败，结果连尸检的钱都没了”的元资源死锁。

---

## 12. Capsule V4：脱敏、分层披露、可反证化

### 12.1 V2.5 的判断

Capsule 的目标不是“记住一切”，而是：

- 不重复犯最昂贵的错；  
- 不把错误尸检当成圣旨；  
- 不把敏感数据抄进控制面与长期存储；  
- 不把上下文做成无限膨胀的垃圾包。

因此，Resume Capsule 升级为 **Capsule V4**。

### 12.2 作者来源与权威等级

`capsuleAuthor` 继续允许：

- `self`  
- `critic`  
- `autopsy`  
- `template_autopsy`

新增 `capsuleAuthority`：

- `advisory_only`  
- `advisory_with_validation`  
- `operator_locked`

默认规则：

- `critic` 与 `autopsy` **默认都只能是 `advisory_with_validation`**；  
- 除非 Operator 显式锁定，否则它们都没有绝对权威；  
- 系统禁止“Critic of Critic”或“Autopsy of Autopsy”的无限套娃，`maxPostmortemDepth=1`。

### 12.3 触发条件

以下场景建议触发旁路作者：

- `hard_kill`  
- `worker_crash`  
- `maxRepeatedFailureSignature` 命中  
- `unknown_effect` / `probe_required` 未闭环  
- `residualRiskSummary` 影响后续决策  
- Operator 明确要求复核

若预算、限流或 provider 健康不允许 LLM 尸检：

- 自动降级为 `template_autopsy`；  
- 直接从 Journal、错误日志、最后里程碑中拼装低配 `nextAttemptBrief`；  
- 不阻塞进入人工处理或恢复链路。

### 12.4 Capsule V4 的结构

#### Head（最高优先级注入区）

Head 必须小而硬，建议强制 token 上限，至少包括：

- `nextAttemptBrief`
- `currentGoal`
- `mustNotRepeat[]`
- `mustValidateFirst[]`
- `refutableHypotheses[]`
- `highestPriorityTodo`
- `stopConditions[]`
- `capsuleAuthor`
- `capsuleAuthority`
- `confidenceScore`

#### Body（结构化恢复区）

- `capsuleId`
- `runId`
- `attemptNo`
- `worktreeRef`
- `patchSetRef`
- `openTodos`
- `decisionCheckpoint`
- `activeHypotheses`
- `knownFailures`
- `rejectedApproaches`
- `failureSignatures`
- `pendingInputs`
- `childTopologySnapshot`
- `remainingBudgetSnapshot`
- `environmentSnapshot`
- `assumptionSet`
- `failureMemoryStoreRef`
- `sanitizationSummary`
- `restrictedEvidenceRefs`

#### Tail（证据与引用区）

- `verificationRefs`
- `journalRefs`
- `incidentRefs`
- `artifactRefs`
- `reconRefs`
- `expiresAt`

### 12.5 可反证化规则（新增重点）

任何来自 Critic / Autopsy 的高影响结论，都必须以假设形式出现，而不是未经验证的命令。  
因此，Capsule V4 必须支持：

- `mustValidateFirst[]`：恢复后第一批必须执行的轻量验证动作  
- `refutableHypotheses[]`：可被下一轮 attempt 推翻的核心判断  
- `evidenceRefs[]`：这些判断所依赖的 Journal / Trace / Error Log 引用

恢复后的第一阶段流程必须是：

1. 先跑 `mustValidateFirst[]`；  
2. 对 `refutableHypotheses[]` 做最小反证；  
3. 若反证成功，可标记 `criticRefuted=true` 并重新生成 Head；  
4. 只有在验证未推翻时，才正式执行 `nextAttemptBrief` 的主体建议。

### 12.6 失败记忆的蒸馏与淘汰

继续禁止 append-only 膨胀：

- `mustNotRepeat[]` 只保留最高价值的少量条目；  
- `failureSignatures` 必须聚类折叠；  
- `rejectedApproaches` 合并同类项；  
- 详细失败历史存入 `failureMemoryStoreRef`，按需检索；  
- `recentToolLedgerTail` 不再内联原始输出，只保存脱敏摘要或 restricted ref。

---

## 13. 脱敏与最小披露：Capsule、Callback、Paperclip 都只能看到“该看到的”

### 13.1 原则

V2.5 明确把“敏感数据不应穿透控制面”提升为红线。  
以下内容默认不得直接进入 Capsule Head、Paperclip 或普通 callback：

- secrets / API keys / STS token  
- 明文密码  
- 原始 PII / PHI / 财务敏感数据  
- 原始环境变量值  
- 未经批准的生产数据样本

### 13.2 三段式净化管线

V2.5 推荐固定顺序：

1. **Deterministic Redaction**  
   - 正则、格式规则、secret detectors、repo-specific patterns  
   - 先删再说，不依赖 LLM 判断  
2. **Structured Classifier**  
   - 把证据切分为 `secret / pii / business_sensitive / safe_summary_candidate`  
3. **Optional Residual LLM Sanitizer**  
   - 仅处理前两步无法可靠归类的残差文本  
   - 不能作为第一道屏障

### 13.3 披露分层

建议至少区分三种视图：

- `restricted_internal`：仅 Dark Factory 控制服务可见  
- `worker_internal`：恢复时 Worker 可按最小权限获取  
- `operator_safe`：Paperclip 与人工审批界面可见

规则：

- Paperclip 只看到 `operator_safe`；  
- Capsule Head 必须默认是 `operator_safe` 等级；  
- Body 中若出现 `restrictedEvidenceRefs`，也只能是引用，不能直接内联原文；  
- `environmentSnapshot` 不得包含环境变量原值，只能包含来源、版本、掩码或哈希指纹。

### 13.4 Restricted Evidence Store

Raw logs、原始工具输出、疑似敏感数据必须进入 Restricted Evidence Store：

- 与普通 Artifact / Trace 分离  
- 独立 retention 与 access policy  
- 默认不经 Bridge 回传  
- 审计或事故调查时通过受限代理访问

---

## 14. Resume 链路：Ephemeral Rehearsal + Recon 风险分级

### 14.1 原则

任何 Capsule 恢复都不能直接接管真实 worktree。  
V2.5 规定：**先在隔离克隆工作区 rehearsal，再决定是否把结果应用到目标工作树。**

### 14.2 强制进入点

以下场景启动新 attempt 时，必须先进入 `phase=resume_recon`：

- awaiting_approval / awaiting_input 之后恢复  
- 长时间 freeze 之后恢复  
- override_or_resume  
- handoff  
- watchdog 强制换手  
- Autopsy 之后恢复

### 14.3 Ephemeral Rehearsal 最小流程

1. 在隔离克隆工作区建立 `ephemeralCloneRef`；  
2. 读取 `baseCommit / worktreeRef / patchSetRef / environmentSnapshot`；  
3. 比较当前分支、主干、依赖版本、关键外部契约指纹；  
4. 对 patchSet 做 dry-run rebase / merge；  
5. 验证 `assumptionSet` 中的关键假设；  
6. 执行最小 smoke test 或只读 probe；  
7. 生成 `reconDiffSummary`、`knownReconConflicts[]`、`reconGrade`、`reconRiskScore`；  
8. 仅在策略允许下，才把 rehearsal 结果投到目标工作树。

### 14.4 风险分级与容忍度

Recon 结果必须是风险分级，而不是布尔值：

- `green`：无实质冲突，可继续  
- `amber`：存在可控漂移或小冲突，可在警告下继续  
- `red`：世界线明显偏移，必须回退到 planning 或人工介入

配合 `reconToleranceLevel`：

- `strict`：只允许 `green` 进入执行  
- `balanced`：允许 `amber` 进入受限执行  
- `permissive`：允许更多 `amber`，但必须提升监控与 stop condition

### 14.5 `amber` 的处理方式

当 `reconGrade=amber` 时：

- 必须将 `knownReconConflicts[]` 注入 Capsule Head；  
- 必须提升 `mustValidateFirst[]`；  
- 可限制写能力、限制子任务并发、或缩小任务范围；  
- 必须在 UI 上以警告态呈现，而不是伪装成正常恢复。

---

## 15. 观测、回调、保留与受限证据

### 15.1 Bridge 处理的生命周期事件

建议 Bridge 仅处理：

- `run_state_changed`
- `ui_composite_changed`
- `display_status_changed`
- `governance_intent_changed`
- `blocked_by_changed`
- `interrupt_acknowledged`
- `quota_rebalanced`
- `recon_completed`
- `postmortem_started / downgraded / completed`
- `compensation_started / completed / partial / manual_required`
- `cleanup_started / completed / manual_required`
- `capsule_available`
- `lease_expired`
- `journal_replay_required`

### 15.2 Observability 专线

细粒度内容仍走 OTLP / PubSub / logs：

- token / model call 统计  
- sub-agent span  
- repeated failure signature  
- provider 429 / backoff  
- BatchIntent checkpoint  
- Journal append / flush / replay 指标  
- Sanitizer 命中统计  
- Recon rehearsal 细节

### 15.3 RetentionPolicy

V2.5 要求保留策略至少覆盖：

- `TraceRef`
- `ArtifactRef`
- `JournalRef`
- `CapsuleRef`
- `IncidentRef`
- `RestrictedEvidenceRef`

并继续要求：

- Paperclip 只声明最低保留要求；  
- Dark Factory 可以保留更久，不能更短；  
- `operator_safe` 与 `restricted_internal` 可有不同存储层，但不得早于审计对象过期。

---

## 16. 合同增量（V2.5）

### 16.1 `POST /api/external-runs` 建议字段（更新）

```json
{
  "externalRunId": "pc_run_1201",
  "requestedMode": "execute",
  "contextBoundary": {
    "toolAllowlist": ["git", "npm", "playwright"],
    "networkAccessLevel": "repo-default",
    "secretMountPolicy": "repo-default",
    "capabilityDelegationPolicy": "subagents-must-downgrade"
  },
  "budgetPolicy": {
    "runBudgetUsd": 16,
    "cleanupReserveUsd": 3,
    "postmortemReserveUsd": 1,
    "executionHintUsd": 8,
    "verificationHintUsd": 4,
    "runWallClockSec": 1800,
    "cleanupReserveWallClockSec": 240,
    "postmortemReserveWallClockSec": 120
  },
  "quotaPolicy": {
    "maxConcurrentChildren": 4,
    "maxChildrenPerBranch": 2,
    "defaultQuotaLease": {
      "childSpendCapUsd": 0.5,
      "childWallClockCapSec": 120,
      "localRpmLease": 20,
      "localTpmLease": 40000,
      "leaseRefreshThreshold": 0.2
    },
    "reclaimPoolEnabled": true,
    "directSiblingBorrow": false,
    "leaseReturnAfterSec": 5,
    "criticalPathBoost": true,
    "asyncUsageReportSec": 10
  },
  "interruptPolicy": {
    "softCancelGraceSec": 60,
    "hardKillAfterSec": 180,
    "cascadeToSubagents": true
  },
  "leasePolicy": {
    "ttlSec": 3600,
    "renewBeforeSec": 300,
    "stuckThresholdSec": 240,
    "watchdogRequired": true,
    "pseudoProgressWindow": 6,
    "maxRepeatedFailureSignature": 3,
    "maxNoDiffToolCycles": 5,
    "batchIntentRequiredForLoopExemption": true
  },
  "effectPolicy": {
    "journalAsSourceOfTruth": true,
    "materializeEffectGraph": true,
    "requireEffectDependencies": true,
    "allowIrreversibleEffects": false,
    "defaultSafetyClasses": {
      "localEphemeral": "local_ephemeral",
      "probeableIdempotent": "external_probeable_idempotent",
      "probeableNonIdempotent": "external_probeable_non_idempotent",
      "unprobeableNonIdempotent": "external_unprobeable_non_idempotent"
    },
    "requireDeterministicCallbackForUnprobeableNonIdempotent": true,
    "defaultPessimisticFallback": "manual_required",
    "durabilityBySafetyClass": {
      "local_ephemeral": "local_sync",
      "external_probeable_idempotent": "local_sync",
      "external_probeable_non_idempotent": "durable_before_dispatch",
      "external_unprobeable_non_idempotent": "durable_before_dispatch",
      "irreversible": "durable_before_dispatch"
    }
  },
  "resumePolicy": {
    "emitResumeCapsule": true,
    "capsuleVersion": "v4",
    "requireFalsifiabilityGate": true,
    "reconMode": "ephemeral_rehearsal",
    "reconToleranceLevel": "balanced",
    "validationBudget": {
      "maxToolCalls": 3,
      "maxWallClockSec": 45
    },
    "fullMemorySnapshotRequired": false
  },
  "sanitizationPolicy": {
    "deterministicRedactionRequired": true,
    "structuredClassifierRequired": true,
    "allowResidualLlmSanitizer": true,
    "operatorSurface": "sanitized_projection_only",
    "forbidEnvValueInlining": true,
    "restrictedEvidenceStoreRequired": true
  },
  "autopsyPolicy": {
    "maxDepth": 1,
    "defaultAuthority": "advisory_with_validation",
    "allowTemplateFallback": true,
    "consumeReserve": "postmortemReserve",
    "llmAutopsyWhen": "provider_healthy_and_budget_available"
  },
  "uiPolicy": {
    "emitDisplayStatus": true,
    "emitGovernanceIntent": true,
    "emitBlockedBy": true,
    "emitUiCompositeKey": true,
    "compositionMatrixVersion": "v1"
  },
  "observabilityPolicy": {
    "lifecycleViaBridge": true,
    "fineTelemetryVia": "otlp"
  },
  "retentionPolicy": {
    "retentionClass": "audit_1y",
    "allowEarlyPurge": false
  }
}
```

### 16.2 回调建议新增字段

- `runStatus`
- `displayStatus`
- `governanceIntent`
- `blockedBy`
- `uiCompositeKey`
- `phase`
- `reasonCode`
- `tags[]`
- `lastMilestone`
- `journalWatermark`
- `guardrailUsage`
- `quotaState`
- `reconGrade`
- `reconRiskScore`
- `knownReconConflicts[]`
- `compensationSummary`
- `cleanupSummary`
- `residualRiskSummary`
- `capsuleAuthor`
- `capsuleAuthority`
- `mustValidateFirst[]`
- `sanitizationSummary`
- `retentionAck`

### 16.3 Journal / Effect 记录建议新增字段

- `journalSeq`
- `recordType`
- `durabilityClass`
- `effectSafetyClass`
- `dependsOnEffectIds[]`
- `compensationBarrierPolicy`
- `effectCommitState`
- `probePolicy`
- `pessimisticFallbackPolicy`
- `callbackCorrelationKey`
- `manualInterventionTicketRef`
- `reconstructedFromJournal = true | false`

---

## 17. V2.5 的路线图

### Phase 0：先把硬约束写死

必须产出：

1. `runtime-truth-model.md`
2. `effect-journal-and-materialized-graph.md`
3. `effect-safety-classes-and-pessimistic-fallback.md`
4. `interrupt-closure-budget-and-external-takeover.md`
5. `quota-lease-and-reclaim-pool.md`
6. `capsule-v4-sanitization-and-falsifiability.md`
7. `rebase-recon-rehearsal-and-risk.md`
8. `ui-composition-matrix.md`
9. `retention-and-restricted-evidence-store.md`
10. `bridge-contract.md`

必须决定：

- 唯一主 Run 状态集合  
- Journal 的最小记录模型  
- Effect Graph 的重建策略  
- `external_unprobeable_non_idempotent` 的默认策略  
- reserve 拆分规则  
- Critic / Autopsy 的 authority 与模板降级边界  
- Capsule V4 的脱敏与披露级别  
- Recon risk grade 与 tolerance  
- UI 组合矩阵  
- Restricted Evidence 的 retention 与访问策略

### Phase 1：零副作用模式先跑通

目标：

- 打通 `validate-only / print-plan`  
- 打通 `uiCompositeKey` 展示  
- 打通 Journal 最小 append 与 projection  
- 打通 Sanitizer 与 operator-safe 投影

成功标准：

- Paperclip 不会接收到原始敏感上下文  
- 主状态、治理意图与复合 UI 组件可稳定展示  
- 高频 telemetry 不进入 Bridge 主库

### Phase 2：真实执行，但先把真相源与安全分类补齐

目标：

- 接通真实执行  
- 接通 Execution Journal  
- 接通 Effect Graph materializer  
- 接通 Effect Safety Classes  
- 接通 Finalizer / Prober / Reaper

成功标准：

- 取消或失败后，副作用可补偿、可悲观回退、或显式进入人工介入  
- `external_unprobeable_non_idempotent` 不会被盲探或盲重试  
- Journal 能重建 Effect Graph

### Phase 3：接通恢复、尸检与排演

目标：

- Capsule V4  
- Critic / Autopsy / Template Autopsy  
- Falsifiability Gate  
- Rebase & Recon Ephemeral Rehearsal

成功标准：

- Hard Kill 后仍能输出可信但可推翻的交接摘要  
- Capsule 不泄露 secrets / PII 到控制面  
- Resume 一定先经过 rehearsal 与风险分级

### Phase 4：接通配额、速率与批处理治理

目标：

- Quota Lease  
- Reclaim Pool  
- provider RPM/TPM shaping  
- Watchdog 伪推进  
- BatchIntent

成功标准：

- Scheduler 不在热路径上成为瓶颈  
- 兄弟子任务不需要实时借调  
- 合法批处理不会被误杀  
- runaway child 不会拖垮整棵执行树

### Phase 5：有限动态提权与审计治理

目标：

- 窄白名单 requestEscalation  
- retention policy handshake  
- Restricted Evidence 审计访问链路

成功标准：

- 审批等待不再持有热会话  
- 审计保留期间的 Journal / Capsule / Restricted Evidence 不会失效

### Phase 6：后续增强

后放内容：

- full memory snapshot  
- 更复杂的 retrieval / RAG memory  
- 更复杂的 sub-agent 可视化  
- 更细的执行 drill-down UI  
- 更复杂的跨 executor 抽象

---

## 18. V2.5 的 Definition of Done

达到以下条件，可认为 V2.5 的最小闭环成立：

1. Run 在系统中只有一个主状态可见。  
2. 前端得到的是 `uiCompositeKey` 对应的单一复合组件，而不是三字段平铺。  
3. Execution Journal 是唯一执行真相源。  
4. Effect Graph 可由 Journal 回放重建，不与 Journal 构成双写裂脑。  
5. 所有外部写入都声明 `effectSafetyClass`。  
6. `external_unprobeable_non_idempotent` 默认不允许盲 probe、盲 retry。  
7. 高风险外部写入必须 `durable_before_dispatch`。  
8. cleanup reserve 与 postmortem reserve 已拆分并生效。  
9. Hard Kill 后由外部 Finalizer / Prober / Autopsy 接管。  
10. Autopsy 在预算或 provider 不可用时能自动降级为模板摘要。  
11. Capsule V4 必须经过脱敏，且 Paperclip 只能看到 operator-safe 投影。  
12. Critic / Autopsy 结论默认是 `advisory_with_validation`，而不是绝对权威。  
13. Resume 一定先经过 Ephemeral Rehearsal 与 Recon 风险分级。  
14. `amber` Recon 可在策略允许下继续执行，避免恢复活锁。  
15. 配额采用本地租约 + 父级回收池，不做兄弟实时 2PC 借调。  
16. Watchdog 能识别伪推进，并支持 BatchIntent。  
17. 高频 telemetry 不经过 Bridge 主库。  
18. JournalRef / CapsuleRef / RestrictedEvidenceRef 已与 retention policy 强绑定。

---

## 19. 最终决策与优先级

### 19.1 最终决策

继续坚持方案 B，但对实现方式做以下最终解释：

- **Paperclip** 拥有 run 身份、治理投影与 operator-safe 视图。  
- **Dark Factory** 拥有执行真相、Journal 真相、Effect 真相、资源真相、尸检真相与 restricted evidence 真相。  
- **Bridge** 只拥有最小操作性状态，不拥有业务控制权。  
- **Finalizer / Reaper / Prober / Critic / Autopsy / Recon / Sanitizer / Quota Scheduler** 均属于 Dark Factory 控制服务，而不是 agent 自身。

### 19.2 实施优先级（更新）

V2.5 的优先级顺序应为：

1. **Execution Journal 单一真相源 + Effect Safety Classes + 悲观回退规则**  
2. **cleanupReserve / postmortemReserve + Finalizer / Prober / Autopsy 模板降级**  
3. **Capsule V4 脱敏与最小披露**  
4. **Falsifiability Gate + Critic / Autopsy advisory authority**  
5. **Ephemeral Rehearsal + Recon 风险分级与 tolerance**  
6. **Quota Lease + Reclaim Pool + provider 限流**  
7. **Watchdog 伪推进 + BatchIntent**  
8. **UI Composition Matrix**  
9. **窄白名单 requestEscalation**  
10. **full memory snapshot / 高级 retrieval（后放）**

---

## 20. 收尾判断

V2.2 把框架从“理论正确”拉回到“可以开工”。  
V2.3 把“谁来收尸、谁来限流、怎样不死循环”补成了工程骨架。  
V2.4 把“失败者不可靠、世界线会漂移、强杀会留下半截状态”写进了合同。  
V2.5 继续做的，是把这些保护机制之间最危险的摩擦再压实：

- 不再允许 WAL 与 Effect Graph 双写裂脑；  
- 不再允许尸检结论带着高置信度却不可反证；  
- 不再允许 Capsule 把 secrets / PII 带进控制面；  
- 不再允许 Recon 只会硬拦截、不允许带伤执行；  
- 不再允许调度器为了“聪明借调”把自己做成全局锁；  
- 不再让用户面对一堆内部字段自己猜当前到底发生了什么。

> **一句话收尾**：V2.5 的目标，不是让系统显得更聪明，而是让它在“执行真相、失败真相、恢复真相、展示真相”这四件事上，各自只有一个说法，而且都能经得起物理世界的折腾。
