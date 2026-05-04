# Dark Factory V3 — AI 协作规则

本文件是 Dark Factory V3 项目的 AI 协作入口。它定义角色边界、文件写入边界、固定工作流、交付输出格式和禁止事项。它是协作规则，不是协议合同；协议事实仍以 V3 binding artifacts 为 source of truth。

## 1. 角色定义

本项目在 AI 协作中使用四个角色：

| 角色 | 职责 | 不做什么 |
|---|---|---|
| Coordinator | 拆任务、路由、汇总、控边界、维护 dashboard | 不直接写代码、不做研究 |
| Researcher | 验证 schema、YAML、contract、API 行为 | 不写最终实现 |
| Builder | 实现 server、bridge plugin、tests | 不重新定义需求 |
| Writer | 整理 QUICKSTART、operator docs、progress | 不伪造事实 |

角色是工作边界，不是必须由四个独立模型执行。单个执行者也必须按这些边界切换职责，避免在同一步里同时改合同、改实现、改结论。

## 2. 文件边界

| 目录 | 职责 | 谁可以写 |
|---|---|---|
| `3.0/` binding artifacts | 协议合同，source of truth | 仅 Coordinator 批准后 Builder 修改 |
| `server.py` | 内部预览服务 | Builder |
| `dark_factory_v3/` | V3 runtime / journal / projection 实现 | Builder |
| `tools/` | 运维和检查工具 | Builder |
| `tests/` | 测试 | Builder + Researcher |
| `docs/` | 运维、安全、工作流和交接文档 | Writer |
| `3.0/future_development/` | 计划和交接 | Coordinator + Writer |
| `QUICKSTART.md` | Operator 快速启动 | Writer |
| `paperclip_upstream/` | Paperclip fork 与 bridge plugin | Builder + Researcher，进入前必须检查 git 状态 |

## 3. 信息写入路由

| 信息类型 | 写入位置 | 不写入 |
|---|---|---|
| 协议事实 | binding artifacts | future_development |
| 项目状态 | dashboard / progress log | AGENTS.md |
| 临时材料 | inbox 或 PR 描述 | 正式文档 |
| 可复用经验 | `docs/` 中的 runbook | 项目 context |
| 旧版本 | archive | 当前工作区 |
| 机器生成辅助视图 | `docs/generated/` | binding artifacts |
| 交接记录 | `docs/progress/` 或 `3.0/future_development/` | 运行日志散文 |

## 4. 固定工作流

| 工作流 | 用途 | 入口命令 |
|---|---|---|
| df-plan | 计划任务，不改代码 | 读取 `3.0/future_development/NEXT_DEVELOPMENT_TASKS.md` |
| df-contract-check | 合同一致性检查 | `python3 tools/validate_v3_bundle.py` |
| df-preview-smoke | HTTP 真实验证 | `python3 tools/v3_control_plane_smoke.py` |
| df-bridge-qa | Bridge plugin 测试 | `cd /home/siyuah/workspace/paperclip_upstream && git status --short` |
| df-release-doc | 文档同步 | 更新 `QUICKSTART.md`、`README.md`、progress log |
| df-handoff | 生成交接包 | `python3 tools/df_handoff_packet.py` |

固定工作流的目的是减少临时决策。执行者可以扩展步骤，但不能绕过边界检查、验证和归档。

## 5. 任务结束输出格式

每次执行结束必须输出：

1. 改了哪些文件
2. 跑了哪些命令
3. 哪些验证通过
4. 哪些验证未跑及原因
5. 下一步建议

如果有失败项，先说明真实失败原因，再说明是否属于环境依赖、外部服务、合同漂移或本次改动引入。

## 6. 推荐阅读顺序

进入 `/home/siyuah/workspace/123`：

1. `README.md`
2. `QUICKSTART.md`
3. `AGENTS.md`（本文件）
4. `3.0/V3_IMPLEMENTATION_ENTRYPOINT.md`
5. `3.0/future_development/NEXT_DEVELOPMENT_TASKS.md`

进入 bridge plugin：

1. `package.json`
2. `src/manifest.ts`
3. `src/runtime-contract.ts`
4. `tests/http-integration.spec.ts`
5. `tests/remote-gated-integration.spec.ts`

## 7. 禁止事项

- 不修改 binding artifacts，除非 Coordinator 明确批准。
- 不存储 secret 到仓库。
- 不读取、打印、归档 token/password/API key/secret 的值。
- 不声称 standalone UI 已存在，除非已经有真实可访问 UI。
- 不用自由文本散落枚举值；需要枚举时从 YAML 或 schema 读取。
- `authoritative: false` 在所有 projection 中固定。
- `terminalStateAdvanced: false` 在非权威 projection / simulator 输出中固定。
- Dark Factory Journal remains truth source。
- 不把 Phoenix Runtime 或任何 provider shim 做成第二 control plane。
- 不用生成文档覆盖 source-of-truth 合同。
