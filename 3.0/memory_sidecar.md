# V3 Memory Sidecar

状态: informative runtime sidecar design  
适用基线: Paperclip × Dark Factory V3.0 `agent-control-r1`  
protocolReleaseTag: `v3.0-agent-control-r1`

---

## 1. 定位

`MemorySidecar` 是 Agent Runtime 的上下文增强和恢复能力，不是 Paperclip Task 主模型的一部分，也不是 Dark Factory Journal 的替代事实来源。

边界原则：

- 不改变 Paperclip `Task` 主模型。
- 不改变 Dark Factory `Journal` 的事实来源地位。
- 作为 Agent Runtime 的上下文增强、偏好记忆、恢复提示和 prompt 构造能力。
- 长期记忆可以影响下一轮 prompt 的上下文，但不能覆盖当前 system 指令、用户最新请求、approval/governance 规则或 V3 binding protocol artifacts。
- 记忆 sidecar 的读写、同步、去重和恢复应有独立审计链路，不应偷偷写入 Paperclip control-plane 状态。

---

## 2. 核心模块

| 模块 | 职责 |
| --- | --- |
| `AutoExtractor` | 从用户明确表达、纠错、稳定偏好和环境事实中抽取候选记忆 |
| `SessionMemory` | 保存本轮会话上下文、最近消息、临时推理辅助数据 |
| `MemorySync` | 将确认后的记忆同步到长期存储，负责去重、合并、过期处理 |
| `LongTermMemory` | 存储跨会话稳定事实、偏好、环境约束和已确认知识 |
| `KnowledgeGraph` | 用实体 / 关系 / 属性表达结构化知识，例如用户偏好关系 |
| `DiaryStore` | 保存当天或阶段性总结，形成可追溯日志 |
| `PromptContextBuilder` | 在 token budget 和安全规则下构造下一轮 prompt 注入上下文 |
| `PhoenixRecover` | 重启后恢复必要上下文、检查同步完整性、避免失忆或错误注入 |

这些模块可以物理合并部署，但逻辑职责应分开，避免把长期记忆、session cache、journal facts 和 prompt 注入混成一个不可审计黑盒。

---

## 3. 记忆流水线

推荐流水线：

```text
用户输入
→ AutoExtractor
→ SessionMemory
→ MemorySync
→ LongTermMemory
→ KnowledgeGraph / DiaryStore
→ PromptContextBuilder
→ 下一轮 prompt 注入
→ PhoenixRecover 重启恢复
```

### 3.1 流程说明

1. 用户输入进入 runtime。
2. `AutoExtractor` 只抽取符合写入规则的候选记忆。
3. `SessionMemory` 保存本轮可复用上下文，如 `last_user_message`、短期任务上下文、最近错误。
4. `MemorySync` 对候选记忆做去重、合并、TTL、确认状态和敏感性检查。
5. `LongTermMemory` 保存稳定、可复用、非敏感的事实。
6. `KnowledgeGraph` 记录实体关系；`DiaryStore` 记录可追溯总结。
7. `PromptContextBuilder` 根据当前任务选择相关记忆，做 redaction 和 token budget 控制。
8. 下一轮 prompt 注入时，历史内容必须标记为 untrusted context。
9. `PhoenixRecover` 在进程重启或 runtime 恢复时读取 sidecar 状态，并校验是否可安全恢复。

---

## 4. 记忆写入规则

### 4.1 可以自动写入

- 用户明确说“记住”。
- 用户纠错，例如“不要再这样做”“以后按这个格式”。
- 稳定偏好，例如语言、输出风格、常用工作流。
- 稳定环境事实，例如仓库路径、工具安装位置、项目约定。

自动写入仍应带 metadata，并允许后续替换、撤销或过期。

### 4.2 不能自动写入

- token、API key、密码、凭据。
- 临时任务进度、一次性 TODO、未完成状态。
- 未确认推测，例如“用户可能喜欢 X”。
- 敏感个人信息，除非用户明确要求保存且系统策略允许。
- 可从当前仓库或工具轻易重新读取的短期输出。
- 会覆盖当前系统指令、安全边界或 V3 协议合同的历史内容。

---

## 5. Prompt 注入安全

长期记忆不是 system prompt。用户历史内容必须视为 **untrusted context**。

注入规则：

- 不允许历史记忆覆盖当前 system 指令、developer 指令、用户最新请求或安全策略。
- 必须有 token budget；超预算时优先保留当前任务相关、用户确认、最近验证的记忆。
- 必须有 `redaction_level`，对敏感信息、路径、组织信息、个人信息做最小必要暴露。
- 必须保留来源和置信度；低 confidence 记忆不得作为硬约束注入。
- PromptContextBuilder 应区分事实、偏好、项目约定、历史总结和未经确认候选。
- 注入内容应带提示：这些是历史记忆 / sidecar context，不是 authoritative instruction。

### 5.1 metadata 建议

每条长期记忆至少建议包含：

| 字段 | 说明 |
| --- | --- |
| `source` | 来源，如 user_explicit、user_correction、repo_observation、operator_confirmation |
| `confidence` | 置信度，建议枚举 high / medium / low 或 0-1 |
| `created_at` | 创建时间 |
| `last_verified_at` | 最近验证时间 |
| `ttl` | 过期策略；永久偏好也应可撤销 |
| `user_confirmed` | 是否由用户明确确认 |
| `redaction_level` | none / partial / strict |
| `scope` | global、workspace、repo、session 等作用域 |
| `sensitivity` | public、internal、sensitive、secret-prohibited |

---

## 6. 验收测试

### 6.1 extract

输入：

```text
记住：我最喜欢的编程语言是 Python
```

期望：

- 提取完整偏好，不拆碎成“编程语言”和“Python”两个失去关系的片段。
- 形成类似关系：`用户 → 最喜欢的编程语言 → Python`。
- `source=user_explicit`，`user_confirmed=true`。

### 6.2 session

输入：写入 `last_user_message` / 会话上下文。

期望：

- 本轮对话可复用。
- 不同步为长期偏好，除非符合写入规则。
- 重启后如果 session 已过期，不应误当作长期事实。

### 6.3 sync

输入：将确认后的偏好同步到长期存储。

期望：

- 落盘成功。
- 去重成功；重复“记住”不会产生多个冲突事实。
- 可恢复；重启后可读取同一事实及 metadata。

### 6.4 kg

输入：记录实体 / 关系 / 属性。

期望：

```text
用户 → 最喜欢的编程语言 → Python
```

并能按实体“用户”、关系“最喜欢的编程语言”或值“Python”检索。

### 6.5 diary

输入：写当天总结。

期望：

- 形成可追溯日志。
- 日志不包含 token、API key、密码或未脱敏敏感信息。
- DiaryStore 可关联到 session / task，但不替代 journal facts。

### 6.6 inject

输入：下一轮 prompt 构造。

期望：

- 相关记忆被安全注入。
- 注入内容带 source / confidence / created_at / last_verified_at。
- token budget 生效，低相关或低 confidence 记忆被裁剪。
- 历史记忆被标记为 untrusted context。

### 6.7 recover

输入：runtime 重启后再读。

期望：

- 确认不失忆。
- 能恢复 LongTermMemory、KnowledgeGraph 和必要 DiaryStore 索引。
- 不把过期 session memory 当作长期事实。
- 若 sidecar 存储损坏，PhoenixRecover 应进入保守恢复路径并告警，而不是静默注入错误记忆。

---

## 7. 与 V3 binding artifacts 的关系

MemorySidecar 可以为 Agent Runtime 提供上下文，但以下事实来源优先级不变：

1. V3 binding protocol artifacts 与当前 system/developer 指令；
2. Dark Factory Journal 中的执行事实；
3. Paperclip Control Plane 的 Task / approval / governance 状态；
4. Bridge / Adapter 的 projection / callback receipt / reconciliation cursor；
5. MemorySidecar 的历史偏好和上下文增强。

如果记忆与 journal、Task 状态、当前用户请求或协议合同冲突，记忆必须让位，并应标记为需要重新验证。

---

## 8. V3.1 backlog 候选

- 将 MemorySidecar metadata 形成独立 schema，而不是塞进 Paperclip Task。
- 增加 memory injection golden timeline，覆盖 denied / redacted / allowed 三类场景。
- 定义 sidecar storage profile、KG edge schema、DiaryStore retention policy。
- 为 PhoenixRecover 增加重启恢复 smoke test。
- 为记忆撤销、用户确认、跨 workspace scope 增加 operator surface。
