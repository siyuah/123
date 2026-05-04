# Dark Factory 工程流水线优化实施文档

文档状态: informative / out-of-bundle  
适用基线: Paperclip x Dark Factory V3.0 `v3.0-agent-control-r1`  
参考项目: `garrytan/gstack`  
目标项目:

- `/home/siyuah/workspace/123`
- `/home/siyuah/workspace/paperclip_upstream/packages/plugins/integrations/dark-factory-bridge`

## 0. 文档目的

本文件不是要把 `gstack` 整套工具直接搬进 Dark Factory，而是吸收它最有价值的工程经验:

1. 把 AI 协作从临时对话变成固定工作流。
2. 把协议合同、测试、真实 HTTP 验证和文档同步串成发布门禁。
3. 把每次开发都拆成可执行、可验收、可交接的子任务。
4. 让后来接手的 AI 或人类工程师能按同一条路线继续推进。

备注:

- 本文档不修改 V3.0 binding artifacts。
- 本文档不改变 `protocolReleaseTag`。
- 本文档不把 Dark Factory 变成第二套 Paperclip control plane。
- 本文档默认当前产品状态仍是 REST-first internal preview，尚无独立 Dark Factory UI 面板。

## 1. 当前基线判断

### 1.1 已具备的优势

当前项目已经具备 `gstack` 类工程流水线的关键前提:

- 有机器可读合同: `core_enums.yaml`、`core_objects.schema.json`、`event_contracts.yaml`、OpenAPI、CSV matrix。
- 有运行预览服务: `/home/siyuah/workspace/123/server.py`。
- 有明确的 API 安全边界: `GET /api/health` 免认证，其他接口要求 `X-API-Key`。
- 有真实 HTTP 集成测试基础: bridge plugin 已有 `tests/http-integration.spec.ts`。
- 有 operator quickstart: `/home/siyuah/workspace/123/QUICKSTART.md`。
- 有下一阶段任务文档区: `/home/siyuah/workspace/123/3.0/future_development/`。

### 1.2 当前短板

当前短板不是“缺文档”或“缺测试”，而是这些资产还没有被编排成一套稳定流水线:

- 协议合同检查、preview smoke、bridge test、journal admin、文档同步仍分散执行。
- 发布前没有一个聚合视图告诉操作者“哪些门禁已过、哪些仍阻塞”。
- AI 接手时需要重新读大量文档，缺少固定入口和固定执行命令。
- 文档更新依赖人工记忆，容易出现代码已变、README/Quickstart/计划文档未同步。
- 安全边界目前适合内网预览，但若未来接远端 provider / agent handoff，需要提前分层。

## 2. 从 gstack 吸收的核心经验

### 2.1 工作流产品化

`gstack` 的重要经验是: 不要只给 AI 一堆原则，要给它命令、角色和停止条件。

Dark Factory 对应做法:

- 建立 `df-plan`、`df-contract-check`、`df-preview-smoke`、`df-bridge-qa`、`df-release-doc` 这一类固定工作流。
- 每个工作流都写清输入、输出、执行步骤、禁止事项、验收命令。
- 每次任务开始先确认工作区和 git 状态，结束时留下 progress / handoff 证据。

备注:

- 这里的命令可以先是文档里的“标准操作步骤”，不必第一天就做成二进制 CLI。
- 等流程稳定后，再把高频步骤沉淀成 `tools/*.py` 或 `scripts/*.mjs`。

### 2.2 Review Readiness Dashboard

`gstack` 的发布前检查不是单一测试命令，而是聚合“审查是否完成”。Dark Factory 应吸收这个做法，做一个发布前状态面板。

建议聚合以下信号:

- V3.0 bundle 文件是否齐全。
- `protocolReleaseTag` 是否在 schema / OpenAPI / event envelope / response 中传播。
- enum / state transition / event contracts 是否对齐。
- release blocker scenario 是否有测试覆盖。
- live preview HTTP smoke 是否通过。
- journal backup / retain 是否可执行。
- bridge plugin `typecheck` 和 `test` 是否通过。
- Quickstart / operator docs 是否与当前命令一致。

备注:

- 第一版可以输出 Markdown 表格。
- 第二版再输出 JSON，供 CI 或 agent 读取。

### 2.3 文档生成和漂移防护

`gstack` 的 `SKILL.md` 由模板和源码元数据生成，避免手工文档漂移。Dark Factory 应用这个思路:

- 机器可读合同继续作为 source of truth。
- 从 YAML / JSON Schema / OpenAPI 生成协议摘要、release checklist、operator command snippet。
- 生成文件明确标注“不要手改，修改 source artifact 后重新生成”。

备注:

- 不建议让生成器覆盖现有核心合同文件。
- 生成物应放到 `docs/generated/` 或 `3.0/future_development/generated/`，先作为辅助视图。

### 2.4 真实验证优先

`gstack` 强调真实浏览器 QA。Dark Factory 当前主要是 REST 服务，所以对应原则是“真实 HTTP 优先”。

Dark Factory 对应做法:

- 内部预览默认走真实 FastAPI server，而不是只跑 mock。
- bridge plugin 的关键路径继续打真实临时 HTTP server。
- 每个发现的 bug 都补一个 regression test 或 golden timeline。

备注:

- 当前阶段不用急着引入浏览器自动化。
- 等 standalone UI / operator panel 出现后，再引入浏览器 QA。

### 2.5 安全边界分层

`gstack` 的 browser daemon 把 local listener 和 tunnel listener 分开，远端只暴露极小 allowlist。Dark Factory 后续如果要接远端 provider 或 agent handoff，也应提前采用类似思路。

Dark Factory 对应做法:

- 本地 operator API、远端 provider API、只读 health API 分开定义。
- 远端入口不要复用本地 root key。
- scoped token / route allowlist 优先于“一个 API key 走天下”。

备注:

- V3.0 internal preview 仍可保持简单 `X-API-Key`。
- 分层设计属于 V3.1+ hardening，不应回写 V3.0 binding contract，除非另立协议版本。

### 2.6 上下文保存和交接恢复

`gstack` 的 `context-save/context-restore` 适合多 agent 并行和长周期开发。Dark Factory 文档和仓库跨度更大，也需要固定 handoff packet。

Dark Factory 对应做法:

- 每次阶段性完成后生成一份 handoff packet。
- 内容包括 git 状态、服务端口、API key 文件位置、最近验证命令、验证结果、下一步任务、禁止编辑边界。
- handoff packet 放在 `3.0/future_development/` 或 `docs/progress/`。

备注:

- handoff packet 不应包含真实 API key。
- 可以记录 key 文件路径和生成方式，但不要记录 secret 值。

## 3. 总体实施路线

建议拆成 5 个 PR / 执行批次。

| 批次 | 名称 | 主要目标 | 推荐优先级 |
| --- | --- | --- | --- |
| PR-1 | AI 工作流入口文档 | 先把规则、入口、固定命令写清楚 | P0 |
| PR-2 | Review Readiness Dashboard | 聚合现有合同检查和测试信号 | P0 |
| PR-3 | Live Preview Smoke 固化 | 把直接 Python 预览和 HTTP smoke 变成标准验证路径 | P1 |
| PR-4 | 合同摘要生成与文档漂移防护 | 从 source artifacts 生成辅助文档和 checklist | P1 |
| PR-5 | Handoff Packet 与安全边界升级 | 固化交接包，规划 provider / operator 分层 | P2 |

备注:

- 先做 PR-1 和 PR-2，因为它们改变的是“执行秩序”，风险小、收益大。
- PR-3 开始触碰运行脚本，需要避免影响当前预览服务。
- PR-4 不要一上来重构合同文件，只做生成型辅助视图。
- PR-5 可随远端 provider 接入计划推进。

## 4. 执行前固定检查

每个批次开始前，先运行:

```bash
cd /home/siyuah/workspace/123
git status -sb
git log --oneline --decorate --max-count=3
```

如果要修改 bridge plugin，再运行:

```bash
cd /home/siyuah/workspace/paperclip_upstream
git status -sb
git log --oneline --decorate --max-count=3
```

备注:

- 这一步用于确认没有打开错误工作区。
- 如果发现工作区有他人未提交改动，不要回滚；只在本批次需要的文件内继续工作。
- 如果任务只允许改某个目录，必须先写明 edit boundary。

## 5. PR-1: AI 工作流入口文档

### 5.1 目标

创建 Dark Factory 专用的 AI 执行入口，让后续 Codex / Claude / Hermes / GPT-5.5 接手时不再从零读上下文。

### 5.2 建议新增文件

- `/home/siyuah/workspace/123/AGENTS.md`
- `/home/siyuah/workspace/123/docs/ai_workflows.md`

如果不想在根目录新增 `AGENTS.md`，也可以先只新增:

- `/home/siyuah/workspace/123/3.0/future_development/DARK_FACTORY_AI_WORKFLOWS.md`

### 5.3 子任务拆分

#### Task 1.1: 定义固定工作流名称

步骤:

1. 新增工作流索引。
2. 定义 6 个固定 workflow:
   - `df-plan`
   - `df-contract-check`
   - `df-preview-smoke`
   - `df-bridge-qa`
   - `df-release-doc`
   - `df-handoff`
3. 为每个 workflow 写明适用场景和禁止事项。

验收:

```bash
cd /home/siyuah/workspace/123
test -f docs/ai_workflows.md
grep -n "df-contract-check" docs/ai_workflows.md
grep -n "df-preview-smoke" docs/ai_workflows.md
```

中文备注:

- `df-plan` 用于计划，不直接改代码。
- `df-contract-check` 只做合同一致性，不引入新语义。
- `df-preview-smoke` 优先直接启动 Python/FastAPI 服务。
- `df-bridge-qa` 进入 `paperclip_upstream` 前必须先确认 git 状态。
- `df-release-doc` 负责同步 Quickstart、README、progress log。
- `df-handoff` 负责交接，不存 secret。

#### Task 1.2: 固化 AI 读文件顺序

步骤:

1. 写明进入 `/home/siyuah/workspace/123` 后的推荐阅读顺序:
   - `README.md`
   - `QUICKSTART.md`
   - `3.0/V3_IMPLEMENTATION_ENTRYPOINT.md`
   - `3.0/future_development/NEXT_DEVELOPMENT_TASKS.md`
2. 写明 bridge plugin 的推荐阅读顺序:
   - `package.json`
   - `README.md`
   - `src/`
   - `tests/http-integration.spec.ts`
   - `scripts/run-install-readiness.mjs`
3. 标注哪些文件是 binding，哪些是 informative。

验收:

```bash
cd /home/siyuah/workspace/123
grep -n "推荐阅读顺序" docs/ai_workflows.md
grep -n "binding" docs/ai_workflows.md
grep -n "informative" docs/ai_workflows.md
```

中文备注:

- 读文件顺序本身就是工程资产，能减少 AI 每次重新探索的成本。
- 对协议项目而言，“先读 source of truth”比“先搜实现代码”更安全。

#### Task 1.3: 定义任务结束输出格式

步骤:

1. 为每次执行定义固定收尾格式:
   - 改了哪些文件。
   - 跑了哪些命令。
   - 哪些验证通过。
   - 哪些验证未跑，原因是什么。
   - 下一步建议。
2. 加入“不得声称 UI 已存在，除非实际新增”的说明。

验收:

```bash
cd /home/siyuah/workspace/123
grep -n "任务结束输出格式" docs/ai_workflows.md
grep -n "UI" docs/ai_workflows.md
```

中文备注:

- 这条规则是为了避免后续文档和产品现实脱节。
- 当前 Dark Factory 仍应被描述为 internal preview / REST-first。

## 6. PR-2: Review Readiness Dashboard

### 6.1 目标

新增一个只读检查器，把现有合同检查、测试状态、预览服务状态和 bridge plugin 状态聚合成发布前视图。

### 6.2 建议新增文件

- `/home/siyuah/workspace/123/tools/df_review_readiness.py`
- `/home/siyuah/workspace/123/tests/test_df_review_readiness.py`

### 6.3 第一版输出示例

```text
Dark Factory Review Readiness

[PASS] bundle files present
[PASS] protocolReleaseTag propagated
[PASS] enum/state/event parity
[WARN] live preview smoke not run in this invocation
[PASS] journal admin backup/retain available
[FAIL] release blocker scenario missing evidence: GL-V30-...

Overall: NOT READY
```

### 6.4 子任务拆分

#### Task 2.1: 定义 readiness 数据模型

步骤:

1. 在脚本内定义 `CheckResult`:
   - `id`
   - `status`: `PASS | WARN | FAIL | SKIP`
   - `summary`
   - `details`
   - `evidence`
2. 定义整体状态规则:
   - 任一 `FAIL` -> `NOT_READY`
   - 无 `FAIL` 但有 `WARN` -> `CONDITIONAL_READY`
   - 全部 `PASS` 或允许 `SKIP` -> `READY`

验收:

```bash
cd /home/siyuah/workspace/123
python3 tools/df_review_readiness.py --help
python3 tools/df_review_readiness.py --json
```

中文备注:

- 第一版可以不接 CI，只要本地输出稳定即可。
- `WARN` 用于“没有运行 live smoke”这类缺证据情况，不应伪装成通过。

#### Task 2.2: 接入 V3 bundle 文件完整性检查

步骤:

1. 读取 `paperclip_darkfactory_v3_0_bundle_manifest.yaml`。
2. 检查 manifest 中列出的 binding 文件是否存在。
3. 如果 manifest 无法解析，返回 `FAIL`。
4. 如果 informative 文件缺失，返回 `WARN`，除非 manifest 标记为 release blocker。

验收:

```bash
cd /home/siyuah/workspace/123
python3 tools/df_review_readiness.py --only bundle-files
```

中文备注:

- binding 文件缺失是硬阻塞。
- informative 文件缺失可能是交付质量问题，但不一定阻塞 V3.0 协议。

#### Task 2.3: 接入 `protocolReleaseTag` 传播检查

步骤:

1. 检查以下文件是否包含 `v3.0-agent-control-r1`:
   - `paperclip_darkfactory_v3_0_bundle_manifest.yaml`
   - `paperclip_darkfactory_v3_0_external_runs.openapi.yaml`
   - `paperclip_darkfactory_v3_0_memory.openapi.yaml`
   - `paperclip_darkfactory_v3_0_event_contracts.yaml`
   - `paperclip_darkfactory_v3_0_core_objects.schema.json`
2. 对缺失位置输出具体文件名。
3. 不要用“默认服务端会补”作为通过理由。

验收:

```bash
cd /home/siyuah/workspace/123
python3 tools/df_review_readiness.py --only protocol-tag
```

中文备注:

- `protocolReleaseTag` 是协议完整性证据，不是装饰字段。
- 缺 tag 应被视为合同传播不完整。

#### Task 2.4: 接入 enum / state / event parity 检查

步骤:

1. 从 `paperclip_darkfactory_v3_0_core_enums.yaml` 读取权威枚举。
2. 从 `paperclip_darkfactory_v3_0_state_transition_matrix.csv` 读取状态值。
3. 从 `paperclip_darkfactory_v3_0_event_contracts.yaml` 读取事件名和版本。
4. 检查 matrix / event 中出现的枚举值是否都来自权威 YAML。
5. 输出 drift 详情。

验收:

```bash
cd /home/siyuah/workspace/123
python3 tools/df_review_readiness.py --only contract-parity
```

中文备注:

- 不要硬编码猜测枚举值。
- YAML 是 source of truth。
- 这条原则同样适用于 bridge plugin 的类型级和运行时 parity guard。

#### Task 2.5: 接入 release blocker scenario 检查

步骤:

1. 读取 `paperclip_darkfactory_v3_0_scenario_acceptance_matrix.csv`。
2. 找出 `release_blocker=true` 的场景。
3. 检查是否存在对应 test / golden timeline / evidence。
4. 缺失时返回 `FAIL`。

验收:

```bash
cd /home/siyuah/workspace/123
python3 tools/df_review_readiness.py --only release-blockers
```

中文备注:

- release blocker 的意义是“不能靠口头确认放行”。
- 如果某个 blocker 暂时无法自动验证，应显式记录 waiver，而不是让检查静默通过。

#### Task 2.6: 输出 Markdown 和 JSON 两种格式

步骤:

1. 默认输出人类可读 Markdown / text。
2. `--json` 输出机器可读 JSON。
3. `--fail-on-blocker` 在整体 `NOT_READY` 时返回非 0 exit code。

验收:

```bash
cd /home/siyuah/workspace/123
python3 tools/df_review_readiness.py
python3 tools/df_review_readiness.py --json
python3 tools/df_review_readiness.py --fail-on-blocker
```

中文备注:

- 人类输出用于日常开发。
- JSON 输出用于 CI、后续 agent 读取、progress log 自动生成。

## 7. PR-3: Live Preview Smoke 固化

### 7.1 目标

把“直接 Python 启动内部预览 + 真实 HTTP 验证”变成默认路径，减少临时命令漂移。

### 7.2 建议涉及文件

- `/home/siyuah/workspace/123/tools/v3_control_plane_smoke.py`
- `/home/siyuah/workspace/123/start_server.sh`
- `/home/siyuah/workspace/123/QUICKSTART.md`
- `/home/siyuah/workspace/123/tests/test_v3_http_server_security.py`
- `/home/siyuah/workspace/123/tests/test_v3_http_server_load.py`

备注:

- 当前这些文件已有未提交改动时，执行前必须先阅读 diff。
- 不要为了文档一致性回滚用户改动。

### 7.3 子任务拆分

#### Task 3.1: 标准化本地启动方式

步骤:

1. 保留直接 Python/FastAPI 启动路线。
2. 支持 `DF_API_KEY_FILE`。
3. 默认 journal 路径使用 `./journal_data/preview.jsonl`。
4. 启动前创建 journal 目录。
5. 启动输出只显示 key 文件路径，不打印真实 key。

验收:

```bash
cd /home/siyuah/workspace/123
DF_API_KEY_FILE=/tmp/dark_factory_preview_api_key \
  python3 server.py --port 9701 --journal ./journal_data/preview.jsonl
```

另开终端:

```bash
curl -sf http://127.0.0.1:9701/api/health | python3 -m json.tool
```

中文备注:

- 直接 Python 部署是当前内部预览的主路径。
- Docker / Caddy 可作为补充，不应替代默认 quickstart。

#### Task 3.2: 强化 smoke 脚本

步骤:

1. smoke 脚本读取 base URL 和 API key 文件。
2. 执行以下真实 HTTP 步骤:
   - health check
   - create external run
   - read external run
   - read projection
   - journal backup
   - journal retain
3. 输出每一步 evidence。
4. 支持 `--json` 输出。

验收:

```bash
cd /home/siyuah/workspace/123
python3 tools/v3_control_plane_smoke.py \
  --base-url http://127.0.0.1:9701 \
  --api-key-file /tmp/dark_factory_preview_api_key \
  --json
```

中文备注:

- smoke 脚本不是单纯 ping health。
- 它要证明 create/read/projection/journal 运维链路都能跑通。

#### Task 3.3: 将 smoke 结果接入 readiness dashboard

步骤:

1. `df_review_readiness.py` 增加 `--smoke-evidence <path>`。
2. smoke 脚本可输出 evidence JSON。
3. dashboard 读取 evidence 后将 `live-preview-smoke` 标为 `PASS` 或 `FAIL`。
4. 没有 evidence 时标为 `WARN`。

验收:

```bash
cd /home/siyuah/workspace/123
python3 tools/v3_control_plane_smoke.py \
  --base-url http://127.0.0.1:9701 \
  --api-key-file /tmp/dark_factory_preview_api_key \
  --json > /tmp/df-smoke.json
python3 tools/df_review_readiness.py --smoke-evidence /tmp/df-smoke.json
```

中文备注:

- 这能区分“真的跑过”与“理论上应该可用”。
- 对发布判断来说，缺 evidence 不等于通过。

## 8. PR-4: 合同摘要生成与文档漂移防护

### 8.1 目标

从机器可读 source artifacts 生成辅助文档，减少 README / Quickstart / release checklist 漂移。

### 8.2 建议新增文件

- `/home/siyuah/workspace/123/tools/generate_v3_contract_summary.py`
- `/home/siyuah/workspace/123/3.0/future_development/generated/V3_CONTRACT_SUMMARY.md`
- `/home/siyuah/workspace/123/3.0/future_development/generated/V3_RELEASE_CHECKLIST.md`

### 8.3 子任务拆分

#### Task 4.1: 生成协议摘要

步骤:

1. 读取:
   - `paperclip_darkfactory_v3_0_core_enums.yaml`
   - `paperclip_darkfactory_v3_0_core_objects.schema.json`
   - `paperclip_darkfactory_v3_0_event_contracts.yaml`
2. 输出:
   - enum 列表
   - core object 列表
   - event 列表
   - protocolReleaseTag
3. 在生成文档顶部写明:
   - generated file
   - source files
   - generated time

验收:

```bash
cd /home/siyuah/workspace/123
python3 tools/generate_v3_contract_summary.py
test -f 3.0/future_development/generated/V3_CONTRACT_SUMMARY.md
```

中文备注:

- 生成摘要不是新的合同，只是阅读视图。
- 如摘要和 source artifact 冲突，以 source artifact 为准。

#### Task 4.2: 生成 release checklist

步骤:

1. 从 `scenario_acceptance_matrix.csv` 读取 release blocker。
2. 从 bundle manifest 读取 binding 文件。
3. 从 runtime config registry 读取 release gate 相关配置项。
4. 输出 checklist:
   - 必跑命令
   - 必有 evidence
   - release blocker 状态

验收:

```bash
cd /home/siyuah/workspace/123
python3 tools/generate_v3_contract_summary.py --release-checklist
test -f 3.0/future_development/generated/V3_RELEASE_CHECKLIST.md
```

中文备注:

- release checklist 要服务操作者，不要写成抽象设计说明。
- 每一项都应该能对应到命令、文件或 evidence。

#### Task 4.3: 加入漂移检查测试

步骤:

1. 测试生成器是否能稳定生成相同内容。
2. 在 CI 或本地测试中检测 generated 文件是否过期。
3. 如果 source artifact 变化但 generated 文件未更新，测试失败或 dashboard 给出 `WARN`。

验收:

```bash
cd /home/siyuah/workspace/123
python3 -m pytest tests/test_generated_contract_summary.py
```

中文备注:

- 这一步吸收的是 `gstack` “模板生成 + CI 防漂移”的经验。
- 不要求第一次就接入完整 CI，本地测试先跑通即可。

## 9. PR-5: Handoff Packet 与安全边界升级

### 9.1 目标

让每次阶段性交付都能被可靠接手，同时为未来远端 provider / agent handoff 做安全边界准备。

### 9.2 建议新增文件

- `/home/siyuah/workspace/123/tools/df_handoff_packet.py`
- `/home/siyuah/workspace/123/3.0/future_development/handoffs/`
- `/home/siyuah/workspace/123/docs/security_boundaries.md`

### 9.3 子任务拆分

#### Task 5.1: 生成 handoff packet

步骤:

1. 采集当前 repo 状态:
   - branch
   - short commit
   - dirty files
2. 采集最近验证命令:
   - pytest
   - smoke
   - readiness
   - bridge plugin test
3. 采集运行配置:
   - preview base URL
   - journal path
   - API key file path
4. 输出 Markdown handoff。
5. 自动过滤 secret 值。

验收:

```bash
cd /home/siyuah/workspace/123
python3 tools/df_handoff_packet.py \
  --base-url http://127.0.0.1:9701 \
  --api-key-file /tmp/dark_factory_preview_api_key \
  --out 3.0/future_development/handoffs/HANDOFF_$(date +%Y-%m-%d).md
```

中文备注:

- handoff packet 的目标是“下一位接手者 5 分钟内恢复上下文”。
- 不要把真实 API key 写进去。

#### Task 5.2: 写清 API 边界分层

步骤:

1. 在 `docs/security_boundaries.md` 中定义三类入口:
   - local operator surface
   - remote provider surface
   - read-only health / diagnostics surface
2. 写明每类入口允许的 endpoint。
3. 写明每类入口允许的 token scope。
4. 写明哪些 endpoint 永远不应暴露给公网。

验收:

```bash
cd /home/siyuah/workspace/123
grep -n "local operator surface" docs/security_boundaries.md
grep -n "remote provider surface" docs/security_boundaries.md
grep -n "read-only health" docs/security_boundaries.md
```

中文备注:

- 这是安全设计文档，不必立即改运行代码。
- 一旦后续引入远端 provider，这份文档会变成实现前置条件。

#### Task 5.3: scoped token 设计预研

步骤:

1. 定义 token scope 草案:
   - `operator:admin`
   - `operator:read`
   - `provider:submit`
   - `provider:read-own`
   - `diagnostics:read`
2. 对现有 API 做 endpoint-to-scope 映射。
3. 标注 V3.0 internal preview 继续使用 `X-API-Key`。
4. 标注 scoped token 属于 V3.1+ hardening。

验收:

```bash
cd /home/siyuah/workspace/123
grep -n "operator:admin" docs/security_boundaries.md
grep -n "provider:submit" docs/security_boundaries.md
```

中文备注:

- 不要在 V3.0 协议中偷偷加入新认证语义。
- 先把边界写清楚，再决定是否进入 V3.1 contract。

## 10. Bridge Plugin 专项优化

### 10.1 目标

把 bridge plugin 也纳入 Dark Factory 工程流水线，而不是只作为旁路测试包存在。

### 10.2 推荐检查命令

```bash
cd /home/siyuah/workspace/paperclip_upstream/packages/plugins/integrations/dark-factory-bridge
pnpm typecheck
pnpm test
pnpm install:readiness
pnpm verify:first-provider
```

### 10.3 子任务拆分

#### Task B1: 建立 bridge readiness 输出

步骤:

1. 让 `scripts/run-install-readiness.mjs` 输出稳定 JSON。
2. 包含:
   - manifest identity
   - worker bundle presence
   - UI dist presence
   - HTTP integration availability
   - first-provider handoff evidence
3. 保留人类可读输出。

验收:

```bash
cd /home/siyuah/workspace/paperclip_upstream/packages/plugins/integrations/dark-factory-bridge
pnpm install:readiness -- --json
```

中文备注:

- JSON 输出供 `/home/siyuah/workspace/123/tools/df_review_readiness.py` 读取。
- 不要把 readiness 变成只给人看的日志。

#### Task B2: 合同 parity guard 加强

步骤:

1. 测试从 `/home/siyuah/workspace/123/paperclip_darkfactory_v3_0_core_enums.yaml` 读取权威枚举。
2. 类型级检查覆盖:
   - `ProjectionStatus`
   - `FailureClass`
   - `BreakerState`
   - `ProviderHealthState`
3. 运行时检查覆盖:
   - projection source
   - truth source
   - runtime observation source
   - projection disclaimer
   - `terminalStateAdvanced === false`
4. 如果 drift 出现，测试失败并输出具体 drift。

验收:

```bash
cd /home/siyuah/workspace/paperclip_upstream/packages/plugins/integrations/dark-factory-bridge
pnpm typecheck
pnpm test
```

中文备注:

- 不要硬编码枚举值。
- 不要为了让测试通过而修改 runtime contract，除非任务明确允许。
- 如果只允许改 `tests/`，就保持这个边界并报告实现漂移。

#### Task B3: bridge 结果回传主项目 readiness

步骤:

1. bridge readiness 生成 `/tmp/dark-factory-bridge-readiness.json`。
2. 主项目 `df_review_readiness.py` 支持 `--bridge-evidence`。
3. 主项目 dashboard 展示 bridge 状态:
   - typecheck
   - vitest
   - install readiness
   - first provider handoff

验收:

```bash
cd /home/siyuah/workspace/paperclip_upstream/packages/plugins/integrations/dark-factory-bridge
pnpm install:readiness -- --json > /tmp/dark-factory-bridge-readiness.json

cd /home/siyuah/workspace/123
python3 tools/df_review_readiness.py \
  --bridge-evidence /tmp/dark-factory-bridge-readiness.json
```

中文备注:

- 这样 `123` 可以作为 Dark Factory 总控验收视图。
- bridge plugin 仍保持在 Paperclip upstream 内，不要复制代码到 `123`。

## 11. 推荐目录结构

建议最终形成:

```text
/home/siyuah/workspace/123
├── AGENTS.md
├── docs/
│   ├── ai_workflows.md
│   └── security_boundaries.md
├── tools/
│   ├── df_review_readiness.py
│   ├── df_handoff_packet.py
│   ├── generate_v3_contract_summary.py
│   ├── journal_admin.py
│   └── v3_control_plane_smoke.py
├── tests/
│   ├── test_df_review_readiness.py
│   ├── test_generated_contract_summary.py
│   └── existing tests...
└── 3.0/future_development/
    ├── DARK_FACTORY_GSTACK_WORKFLOW_OPTIMIZATION_PLAN.md
    ├── generated/
    │   ├── V3_CONTRACT_SUMMARY.md
    │   └── V3_RELEASE_CHECKLIST.md
    └── handoffs/
        └── HANDOFF_YYYY-MM-DD.md
```

中文备注:

- `tools/` 放可执行脚本。
- `docs/` 放当前运行和安全说明。
- `3.0/future_development/` 放计划、生成辅助视图和交接包。
- generated / handoffs 可按需要加入 `.gitignore` 或只提交模板，取决于团队是否希望保留历史 evidence。

## 12. 验收总门禁

当 PR-1 到 PR-5 完成后，理想的“一键验收”路径应接近:

```bash
cd /home/siyuah/workspace/123
python3 -m pytest tests
python3 tools/generate_v3_contract_summary.py --check
python3 tools/df_review_readiness.py --fail-on-blocker
python3 tools/v3_control_plane_smoke.py \
  --base-url http://127.0.0.1:9701 \
  --api-key-file /tmp/dark_factory_preview_api_key \
  --json > /tmp/df-smoke.json
python3 tools/df_review_readiness.py \
  --smoke-evidence /tmp/df-smoke.json \
  --bridge-evidence /tmp/dark-factory-bridge-readiness.json \
  --fail-on-blocker
```

Bridge plugin:

```bash
cd /home/siyuah/workspace/paperclip_upstream/packages/plugins/integrations/dark-factory-bridge
pnpm typecheck
pnpm test
pnpm install:readiness -- --json > /tmp/dark-factory-bridge-readiness.json
```

中文备注:

- 第一条 readiness 可以在 smoke 前运行，用于静态合同检查。
- 第二条 readiness 在 smoke 和 bridge evidence 都存在后运行，用于发布前最终判断。
- 如果没有启动 preview server，live smoke 应显示 `WARN` 或 `SKIP`，不能显示 `PASS`。

## 13. 风险与处理

| 风险 | 可能后果 | 处理方式 |
| --- | --- | --- |
| 过早复制 gstack 全套工具 | 项目复杂度暴涨 | 只吸收工作流、门禁、生成文档、交接包思想 |
| 生成文档被误认为新合同 | V3.0 语义被污染 | 生成文件顶部写明 informative / generated |
| readiness dashboard 误报通过 | 发布判断失真 | 缺 evidence 默认 `WARN`，合同 drift 默认 `FAIL` |
| smoke 脚本打印 API key | secret 泄露 | 只打印 key 文件路径，不打印 key 值 |
| bridge 与主项目状态脱节 | 主项目误判集成状态 | bridge 输出 JSON evidence，主项目 dashboard 读取 |
| AI 修改越界文件 | 破坏用户未提交工作 | 每批次先确认 git status 和 edit boundary |
| UI 状态描述不准确 | operator 预期错误 | 明确当前 REST-first，无 standalone UI panel |

## 14. AI 执行提示模板

### 14.1 PR-1 执行提示

```text
请在 /home/siyuah/workspace/123 中实现 PR-1: AI 工作流入口文档。
先运行 git status -sb 和 git log --oneline --decorate --max-count=3。
只新增或修改文档文件，不改 server.py、tools/、tests/。
目标是新增 docs/ai_workflows.md，定义 df-plan、df-contract-check、df-preview-smoke、df-bridge-qa、df-release-doc、df-handoff。
每个 workflow 必须包含适用场景、步骤、验收命令、禁止事项、中文备注。
完成后汇报文件路径、验证命令和未处理事项。
```

### 14.2 PR-2 执行提示

```text
请在 /home/siyuah/workspace/123 中实现 PR-2: Review Readiness Dashboard。
先运行 git status -sb 和 git log --oneline --decorate --max-count=3。
新增 tools/df_review_readiness.py 和 tests/test_df_review_readiness.py。
第一版必须支持 --json、--only、--fail-on-blocker。
检查范围包括 bundle files、protocol tag、contract parity、release blockers。
不要修改 V3.0 binding artifacts。
完成后运行 python3 -m pytest tests/test_df_review_readiness.py，并运行 python3 tools/df_review_readiness.py --json。
```

### 14.3 PR-3 执行提示

```text
请在 /home/siyuah/workspace/123 中实现 PR-3: Live Preview Smoke 固化。
先运行 git status -sb 和 git log --oneline --decorate --max-count=3，并阅读 start_server.sh 与 tools/v3_control_plane_smoke.py 当前 diff。
保留直接 Python/FastAPI 预览路线，支持 DF_API_KEY_FILE，避免打印真实 key。
smoke 覆盖 health、create run、read run、projection、journal backup、journal retain。
完成后运行相关 pytest，并给出手动启动 server 与 smoke 的验证命令。
```

### 14.4 Bridge 执行提示

```text
请在 /home/siyuah/workspace/paperclip_upstream/packages/plugins/integrations/dark-factory-bridge 中执行 bridge readiness 优化。
先在 /home/siyuah/workspace/paperclip_upstream 运行 git status -sb 和 git log --oneline --decorate --max-count=3。
不要回滚用户已有改动。
如果任务限定 tests/，只改 tests/。
readiness 输出需要有人类可读和 JSON 两种格式。
完成后运行 pnpm typecheck 和 pnpm test。
```

## 15. 最小可行版本

如果只能先做最小版本，建议只做三件事:

1. 新增 `docs/ai_workflows.md`。
2. 新增 `tools/df_review_readiness.py`，先覆盖静态合同检查。
3. 让 bridge readiness 输出 JSON，并由主项目 readiness 读取。

执行顺序:

1. 先做 `docs/ai_workflows.md`，让后续 AI 执行有固定入口。
2. 再做静态 `df_review_readiness.py`，先覆盖不需要启动服务的合同检查。
3. 最后接入 bridge JSON evidence，让主项目能看见 upstream 插件状态。
4. live smoke、生成文档、handoff packet 放到下一轮，不阻塞最小版本。

最小版本验收:

```bash
cd /home/siyuah/workspace/123
python3 tools/df_review_readiness.py --json

cd /home/siyuah/workspace/paperclip_upstream/packages/plugins/integrations/dark-factory-bridge
pnpm typecheck
pnpm test
```

中文备注:

- 这三件事完成后，Dark Factory 就从“有很多好资产”前进到“有可重复工程流水线”。
- 后续再补 smoke、生成文档、handoff packet、安全边界，会更自然。

## 16. Definition of Done

整体优化完成时，应满足:

- 任意 AI 接手时，能从固定入口理解项目状态和执行边界。
- 发布前能运行一个 readiness dashboard，看见所有关键门禁。
- 合同 source artifacts 与生成摘要之间有漂移检查。
- preview smoke 能证明真实 HTTP 主链路可用。
- bridge plugin 状态能回传主项目 dashboard。
- 每次阶段交付都有 handoff packet。
- 文档明确区分 binding / informative / generated。
- 没有把 secret 写入仓库。
- 没有声称 standalone UI 已存在。

最终备注:

`gstack` 的最大价值不是某个脚本，而是它把 AI 开发变成了一条可重复流水线。Dark Factory 当前已经有强合同、强测试和真实 HTTP 验证基础，下一步应该补的正是这层“工程编排壳”: 让计划、验证、发布、文档和交接都能被稳定重复。
