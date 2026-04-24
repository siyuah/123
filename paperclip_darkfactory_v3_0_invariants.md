# Paperclip × Dark Factory V3.0 Invariants

状态: normative  
规范版本: 3.0  
protocolReleaseTag: `v3.0-agent-control-r1`

---

## 1. 目的

本文件承载无法仅靠 OpenAPI、JSON Schema 或枚举清单表达的硬不变量。
任何实现、配置、operator 操作或应急手工流程都不得削弱这些约束。

---

## 2. Truth path 与写入边界

1. Journal 是唯一 truth path。
2. Projection、cache、operator view、search index、archive catalog 都只能派生，不能反向定义真相。
3. 任何状态推进、route decision、provider failure、memory artifact、repair attempt、park / rehydrate 结果，都必须先有 Journal truth record，再允许派生视图变化。
4. 不允许通过直接改 projection、直接改 view store、直接写 operator side table 的方式伪造主状态。

---

## 3. Run / Attempt 主状态机不变量

1. 同一 `runId` 任一时刻最多只能有一个 active attempt。
2. Run 主状态只能由单一 closure authority 推进到终态。
3. `parked_manual` 不是成功终态，也不是 cleanup 完成态。
4. `rehydrating` 必须建立在已验证的 `RehydrationToken` 之上。
5. rehydrate 必须产生新的 `attemptId`，旧 attempt 必须转为 `superseded` 或其他非活跃状态。
6. 不允许在 parked 的旧 attempt 上继续追加高风险执行效果并将其视为合法主流程。

---

## 4. Capability 与执行边界不变量

1. 所有 attempt 在实际执行前必须先获得 `ExecutionCapabilityLease`。
2. `observedCapabilitySet` 超出 `grantedCapabilitySet` 时，必须记录审计事实并触发阻断、降级或人工介入，不能静默继续。
3. 不允许绕过 capability broker 直接声明“等效授权”。
4. `profileConformanceStatus=unverifiable` 时，不得进入新的 high-risk write 路径。
5. repair lane、recovery lane、manual 恢复流程同样受 capability broker 约束，不是例外通道。

---

## 5. Schema write fence 不变量

1. 旧 writer 不得覆盖新 schema 对象。
2. write fence 拒绝必须形成可审计事件或错误响应，不得静默吞掉。
3. 不允许通过 repair lane、archive restore、manual override 绕过 write fence。
4. mixed-version 兼容只能更保守，不能更宽松。

---

## 6. Artifact / lineage 不变量

1. Artifact 的认证状态是消费资格的唯一协议来源。
2. `revoked_upstream` 不得放行新的 high-risk primary write。
3. `tentative_upstream` 必须是正式状态，不能被 UI 注释或实现私有标签替代。
4. reopened / revoked 的上游变化必须向所有受影响 consumer 传播。
5. waiver 只能改变其授权范围内的消费约束，不能改写上游 artifact 的认证历史。
6. waiver 不得把 `revoked_upstream` 重新解释成可安全放行的 high-risk primary write。

---

## 7. Park / rehydrate 不变量

1. `park` 必须同时满足两件事：
   - 产生 `ParkRecord`
   - 释放执行资源并保留 truth obligation
2. `RehydrationToken` 必须单次成功消费。
3. rehydrate 前必须重新 claim、重新 preflight、重新 route decision。
4. rehydrate 不得继承一个已经 poisoned 且仍违反 preflight 约束的执行上下文。
5. park / rehydrate 不得造成 trace、lineage、attempt linkage 断裂。

---

## 8. Routing / provider failure 不变量

1. 路由决策必须可审计、可重放、可关联到 `attemptId`。
2. provider 故障必须先进入 `providerFaultClass`，再映射到唯一 `recoveryLane`。
3. 不允许保留未裁决的 `A or B` 恢复分支。
4. cutover 必须留下正式 truth record。
5. route degrade 只能在策略允许且 blast radius 满足条件时发生。

---

## 9. Memory 不变量

1. memory artifact 必须可追溯到 source trace、source run、consent scope 与 retention policy。
2. out-of-scope memory artifact 不得注入 prompt。
3. 过期、撤销、被更正后不再可用的 memory artifact，不得继续被当作 active 输入。
4. prompt injection 必须形成 `PromptInjectionReceipt`。
5. cross-session memory 注入若要求 consent，则缺失 consent 必须阻断，而不是降级为隐式允许。

---

## 10. Repair 不变量

1. repair lane 是正式恢复车道，不是后门写入通道。
2. repair attempt 必须有触发原因、计划引用、结果与验证痕迹。
3. repair 成功不等于自动可信，仍需通过验证与主状态推进规则。
4. repair lane 不得绕过 capability broker、schema write fence、lineage block 与 manual gate。
5. 需要 operator 审批的 repair 不得由自动流程假装完成。

---

## 11. 发布 gate 不变量

1. 协议正确与场景正确都必须进入 CI gate。
2. machine-readable 资产与 prose 冲突时，发布必须阻断。
3. 缺失 `protocolReleaseTag` 传播闭环时，发布必须阻断。
4. `scenario_acceptance_matrix` 中 `release_blocker=true` 的场景未通过时，发布必须阻断。
5. bundle manifest 与实际产物不一致时，发布必须阻断。
