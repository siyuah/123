# V3 Runtime Policy

状态: informative runtime policy  
适用基线: Paperclip × Dark Factory V3.0 `agent-control-r1`  
protocolReleaseTag: `v3.0-agent-control-r1`

---

## 1. 目的与边界

本文将 Phoenix V2 / 不死鸟材料中的模型路由、provider fallback、重试、熔断、降级策略收敛为 V3 Agent Runtime 的运行层策略。它不改写 Paperclip Control Plane、Dark Factory Journal、core schema、OpenAPI 或 event contracts。

本文只定义抽象角色、失败分类、重试/降级原则和建议观测字段。**具体模型名只能出现在配置示例中，不应成为协议合同。**

---

## 2. task_type 分类

Runtime router 至少应识别以下 `task_type`，用于选择 provider role、retry budget、fallback 链和是否允许 delegate：

| task_type | 说明 | 运行层关注点 |
| --- | --- | --- |
| `chat` | 普通对话、解释、状态整理 | 低延迟、上下文安全注入、稳定 fallback |
| `code` | 代码编辑、测试、仓库操作 | 工具调用安全、工作区隔离、测试回执、可升级 escalation |
| `reasoning` | 复杂推理、规划、审查、设计权衡 | 高可靠推理、证据引用、可回退到保守输出 |
| `vision` | 图像理解、截图分析、视觉资产解释 | 多模态能力、输入 redaction、不可用时明确降级 |
| `routing` | 路由决策、任务分解、provider 选择 | 不应递归失控；必须记录选择依据 |
| `delegate/subtask` | 子任务代理、并行审查、隔离执行 | 边界清晰、结果汇总、失败隔离、不可越权写入 |

---

## 3. provider role 抽象

运行配置应使用 provider role，而不是把具体供应商或模型名写进协议合同。推荐 role 集合：

| provider role | 用途 |
| --- | --- |
| `router.primary` | 默认路由决策入口 |
| `chat.primary` | chat 任务主执行角色 |
| `chat.fallback` | chat 任务备用角色 |
| `code.primary` | code 任务主执行角色 |
| `code.escalation` | code 任务升级角色，用于疑难实现或高风险变更审查 |
| `reasoning.primary` | reasoning 任务主执行角色 |
| `reasoning.fallback` | reasoning 任务备用角色 |
| `vision.primary` | vision 任务主执行角色 |
| `vision.fallback` | vision 任务备用角色 |
| `global.degraded` | 主链、备用链或常规接口不可用时的降级角色 |

配置文件可以把 role 绑定到具体 provider/model，但代码、journal 和 operator 报告应优先记录 role 与 attempt，而不是把具体模型名当成协议必填语义。

---

## 4. failure_class 分类表

| failure_class | 典型信号 | retryable | 策略 |
| --- | --- | --- | --- |
| `transient_network` | timeout、connection reset、网络抖动 | yes, limited | 可有限重试；若持续失败则 fallback |
| `transient_provider` | 临时 5xx、provider 短暂错误 | yes, limited | 可有限重试；若重复失败则 fallback 或 open circuit |
| `provider_auth` | 401、403、key 失效 | no | 不重试；熔断/告警/切备用；不得打印凭据 |
| `quota_exceeded` | 402、quota exceeded、欠费/额度不足 | no | 不重试；切备用；需要 billing / quota 告警 |
| `rate_limited` | 429、显式 rate limit | conditional | 可等待或切备用；不得无限等待 |
| `invalid_request` | 参数错误、schema 错误、上下文超限且未裁剪 | no | 不重试，不盲目换模型；修正请求或失败返回 |
| `provider_unavailable` | provider 持续不可用、健康检查失败 | no direct retry while open | 熔断并切备用；进入 half_open 探测恢复 |
| `global_outage` | 主链、备用链、常规接口均不可用 | no | 进入 degraded mode；输出保守结果或排队等待恢复 |

分类原则：如果失败来自请求自身不合法或权限/额度问题，不应靠盲目换模型掩盖；如果失败来自短暂网络或 provider 抖动，可以有限重试。

---

## 5. Retry policy

只允许 `transient_network` / `transient_provider` 默认进入有限 retry。推荐节奏：

1. immediate retry；
2. 300-500ms jitter backoff；
3. 1-2s jitter backoff；
4. fallback 或失败返回。

约束：

- 每个 RunAttempt 必须有明确 retry budget。
- 不允许对 `provider_auth`、`quota_exceeded`、`invalid_request` 盲目重试。
- `rate_limited` 可按 provider 返回的 retry-after 等待；没有明确等待窗口时优先切备用，不得无限阻塞。
- retry 不能改变任务语义、用户授权范围、workspace 边界或输出格式承诺。
- retry 必须记录 attempt index、failure_class、retryable 判断和最终 outcome。

---

## 6. Fallback policy

推荐链路：`primary → fallback → degraded`。

Fallback 规则：

- fallback 必须有日志，至少记录 provider role、model role、failure_class、attempt_index、fallback_triggered。
- fallback 不应改变任务语义；如果能力缺失导致语义无法保持，应返回 degraded / partial，并明确说明限制。
- fallback 后产物必须记录 provider role 和 attempt，便于审计与回放。
- fallback 不得放宽安全策略、文件访问边界、secret redaction 或用户审批要求。
- 对 code / delegate/subtask 类任务，fallback 前后必须保持工作区状态可追踪，必要时先做 status / diff 检查。

Degraded mode 只能作为运行可用性策略，不能伪装为完整成功。进入 degraded mode 时应暴露给 operator，并在 journal / report 中留下可追踪证据。

---

## 7. Circuit breaker policy

Circuit breaker 维护 provider health state，建议状态：

| state | 含义 | 允许行为 |
| --- | --- | --- |
| `closed` | provider 健康，请求正常进入 | 正常调用，可按 failure_class retry |
| `open` | 连续失败超过阈值，provider 被临时熔断 | 不再向该 provider 发送普通请求；直接 fallback |
| `half_open` | 冷却结束后的探测恢复状态 | 允许少量探测请求；成功后 closed，失败后 open |

建议字段：

- 连续失败阈值：按 provider role 与 task_type 分开配置；
- 冷却时间：短链路可 30-120 秒，长链路按运维配置；
- 探测恢复：half_open 只允许低风险探测，不得承载不可重复副作用；
- provider health state：记录最近成功时间、最近失败时间、failure_class 分布、open reason。

Circuit breaker 不应成为第二套业务状态机；它只描述 provider 可用性，不改变 Run / Task 的协议语义。

---

## 8. RunAttempt 建议字段

如未来把运行策略正式合同化，可优先考虑在 RunAttempt / attempt metadata / journal event 中增加以下字段。V3.0 当前文档仅将其作为 runtime policy 建议，不自动进入 Paperclip Task 主模型：

| 字段 | 说明 |
| --- | --- |
| `provider_id` | 运行配置中的 provider 实例标识；不得包含 secret |
| `provider_role` | 如 `code.primary`、`reasoning.fallback` |
| `model_role` | 模型能力抽象，如 fast、balanced、deep、vision；不是具体模型名 |
| `failure_class` | 本文定义的失败分类 |
| `retryable` | 本次失败是否允许 retry |
| `fallback_triggered` | 是否触发 fallback |
| `attempt_index` | 同一任务/Run 内的尝试序号 |
| `circuit_breaker_state` | closed / open / half_open |
| `degraded_mode` | 是否处于降级模式 |

---

## 9. 配置示例边界

允许在部署配置中出现具体模型名，例如：

```yaml
providerRoles:
  code.primary:
    provider_id: provider-a
    model: example-code-model
  code.escalation:
    provider_id: provider-b
    model: example-deep-code-model
```

但上述具体值是部署配置，不是 V3 protocol contract。协议、测试和 release gate 应校验 role、failure_class、attempt 记录与行为边界，而不是校验某个固定供应商或模型名。

---

## 10. 验收建议

- 对 `transient_network` / `transient_provider` 注入故障，确认 retry 次数有限且最终可 fallback。
- 对 `provider_auth` / `quota_exceeded` / `invalid_request` 注入故障，确认不盲目重试。
- 对连续 `provider_unavailable` 注入故障，确认 breaker 从 closed → open → half_open → closed/open 转换。
- 对 fallback 产物检查 provider role、attempt_index、failure_class 是否可追踪。
- 对 global outage 检查 degraded mode 是否明确暴露，且不宣称完整成功。
