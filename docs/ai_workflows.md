# Dark Factory AI 工作流

本文档定义 Dark Factory V3 项目的 6 个固定 AI 协作工作流。它借鉴 OPC 的角色边界和 GStack 的工作流产品化方式，把常见任务变成可复用、可验收、可归档的流程。

这些工作流不改变 V3 binding artifacts 的事实来源地位。凡是涉及协议事实，仍以 `paperclip_darkfactory_v3_0_*` machine-readable artifacts 和 `3.0/` 中的 binding 文档为准。

## 总览

| 工作流 | 主要用途 | 主要输出 |
|---|---|---|
| df-plan | 拆解任务和确认边界 | 执行计划、风险、验证清单 |
| df-contract-check | 合同一致性检查 | V3 bundle validation / drift 结论 |
| df-preview-smoke | 本地 HTTP 真实验证 | smoke JSON / 终端验证记录 |
| df-bridge-qa | Paperclip bridge plugin QA | typecheck/build/test/evidence |
| df-release-doc | 发布和文档同步 | QUICKSTART、README、progress log |
| df-handoff | 交接包生成 | handoff packet、状态摘要、下一步 |

## 1. df-plan

### 适用场景

- 新任务进入时需要拆成批次。
- 用户要求“自行安排任务计划”但任务边界还需要确认。
- 涉及 `123` 与 `paperclip_upstream` 两个仓库，需要先排顺序。
- 需要判断是否会修改 binding artifacts。

### 执行步骤

```bash
cd /home/siyuah/workspace/123
git status -sb
git log --oneline --decorate --max-count=3
sed -n '1,220p' AGENTS.md
sed -n '1,220p' 3.0/future_development/NEXT_DEVELOPMENT_TASKS.md
```

如任务涉及 Paperclip bridge plugin：

```bash
cd /home/siyuah/workspace/paperclip_upstream
git status --short
git log --oneline --decorate --max-count=5
```

### 验收命令

```bash
cd /home/siyuah/workspace/123
test -f AGENTS.md
test -f 3.0/future_development/NEXT_DEVELOPMENT_TASKS.md
```

### 禁止事项

- df-plan 不直接改代码。
- 不把计划写入 binding artifacts。
- 不把未验证的外部状态写成完成事实。

### 中文备注

df-plan 的价值是“先把路由和边界摆正”。如果计划发现任务会触碰 V3 binding artifacts，必须单独标注风险和验证方式。

## 2. df-contract-check

### 适用场景

- 修改或审查 V3 bundle artifacts 后。
- 需要确认 schema / YAML / OpenAPI / matrix 是否一致。
- 需要为 release readiness 或 bridge parity guard 提供证据。

### 执行步骤

```bash
cd /home/siyuah/workspace/123
python3 tools/validate_v3_bundle.py
```

可补充读取：

```bash
sed -n '1,200p' paperclip_darkfactory_v3_0_bundle_manifest.yaml
sed -n '1,200p' paperclip_darkfactory_v3_0_core_enums.yaml
```

### 验收命令

```bash
cd /home/siyuah/workspace/123
python3 tools/validate_v3_bundle.py 2>&1 | grep '"status"'
```

### 禁止事项

- 只做合同一致性检查，不引入新语义。
- 不硬编码猜测枚举值；枚举必须从 YAML 或 schema 读取。
- 不把 informative 文档当作 source of truth。

### 中文备注

df-contract-check 是“协议地基检查”。如果发现 drift，先报告漂移，再决定是否修改合同或实现。

## 3. df-preview-smoke

### 适用场景

- 验证本地 Dark Factory HTTP preview 是否可运行。
- 验证 `/api/health`、external run、journal projection 等路径。
- 生成真实 HTTP 证据供 readiness dashboard 或 handoff 使用。

### 执行步骤

优先直接启动 Python/FastAPI：

```bash
cd /home/siyuah/workspace/123
source .venv/bin/activate 2>/dev/null || true
python3 -m uvicorn server:app --host 127.0.0.1 --port 9701
```

另一个终端执行：

```bash
cd /home/siyuah/workspace/123
python3 tools/v3_control_plane_smoke.py \
  --base-url http://127.0.0.1:9701 \
  --api-key-file ~/.config/dark-factory/preview-api-key \
  --json
```

### 验收命令

```bash
curl -sS http://127.0.0.1:9701/api/health
python3 tools/v3_control_plane_smoke.py --base-url http://127.0.0.1:9701 --json
```

### 禁止事项

- 不连接真实 Dark Factory 服务，除非任务明确是 operator-gated real provider attempt。
- 不打印 API key。
- 不把 preview projection 说成权威事实。

### 中文备注

preview smoke 的目标是“本地真实链路”，不是 mock-only。失败时要区分服务未启动、认证缺失、协议不一致和实现 bug。

## 4. df-bridge-qa

### 适用场景

- 修改 Paperclip bridge plugin 后。
- 需要确认插件与 Paperclip upstream 最新代码兼容。
- 需要验证 remote provider shim / gated integration / UI smoke harness。

### 执行步骤

进入 `paperclip_upstream` 前必须确认状态：

```bash
cd /home/siyuah/workspace/paperclip_upstream
git status --short
git log --oneline --decorate --max-count=5
```

执行插件验证：

```bash
cd /home/siyuah/workspace/paperclip_upstream/packages/plugins/integrations/dark-factory-bridge
pnpm typecheck
pnpm build
pnpm test
```

如需 root 验证：

```bash
cd /home/siyuah/workspace/paperclip_upstream
pnpm -r typecheck
```

### 验收命令

```bash
cd /home/siyuah/workspace/paperclip_upstream/packages/plugins/integrations/dark-factory-bridge
pnpm test 2>&1 | tail -12
```

### 禁止事项

- 不修改 Paperclip core/server/ui，除非任务明确要求。
- 不把 mock adapter 输出标为 authoritative。
- 不连接真实 provider，除非 gated inputs 存在且用户明确执行。
- 不读取、打印、提交 token/password/API key/secret。

### 中文备注

df-bridge-qa 是 bridge plugin 的主验收线。UI 修改后必须 `pnpm build`，否则浏览器仍可能加载旧的 `dist/ui/index.css`。

## 5. df-release-doc

### 适用场景

- 完成一个开发批次后同步 operator 文档。
- 修改运行方式、验证命令、部署边界后。
- 需要更新 progress log 或 release readiness 说明。

### 执行步骤

```bash
cd /home/siyuah/workspace/123
git status --short
sed -n '1,220p' QUICKSTART.md
sed -n '1,220p' README.md
sed -n '1,260p' 3.0/future_development/NEXT_DEVELOPMENT_TASKS.md
```

根据实际变更更新：

- `QUICKSTART.md`
- `README.md`
- `docs/`
- `3.0/future_development/NEXT_DEVELOPMENT_TASKS.md`
- `docs/progress/`

### 验收命令

```bash
cd /home/siyuah/workspace/123
python3 tools/validate_v3_bundle.py
git diff --check
```

### 禁止事项

- 不伪造验证结果。
- 不写入 secret。
- 不把尚未完成的功能写成 production-ready。
- 不把 progress log 写入 binding artifacts。

### 中文备注

df-release-doc 是“记录事实”的流程，不是润色宣传。文档必须能让下一位接手者复现状态。

## 6. df-handoff

### 适用场景

- 一个批次完成，需要交给其他 AI 或人工审查。
- 准备长任务中断恢复。
- 需要形成审查包、证据包或下一步命令。

### 执行步骤

当前推荐先收集状态：

```bash
cd /home/siyuah/workspace/123
git status --short
git log --oneline --decorate --max-count=8
python3 tools/validate_v3_bundle.py
```

如涉及 Paperclip：

```bash
cd /home/siyuah/workspace/paperclip_upstream
git status --short
git log --oneline --decorate --max-count=8
```

未来 `tools/df_handoff_packet.py` 落地后，入口为：

```bash
cd /home/siyuah/workspace/123
python3 tools/df_handoff_packet.py --output docs/progress/HANDOFF_PACKET.json
```

### 验收命令

```bash
cd /home/siyuah/workspace/123
test -d docs/progress
test -f docs/progress/README.md
```

### 禁止事项

- 不存 secret。
- 不复制 token/password/API key/API 响应中的敏感字段。
- 不把临时浏览器状态当作可复现事实。
- 不省略失败项。

### 中文备注

handoff 的质量取决于可复现证据。好的交接包应该让 Claude / GPT / 人工审查者不用猜当前状态。
