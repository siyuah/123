# Next Development Tasks

状态: Informative / Non-binding / Out-of-bundle execution plan
适用基线: Paperclip × Dark Factory V3.0 `agent-control-r1`
protocolReleaseTag: `v3.0-agent-control-r1`
所在目录: `3.0/future_development/`
是否进入 V3.0 binding: 否

> **For Hermes:** Use subagent-driven-development skill when executing implementation-heavy phases. Execute task-by-task, verify after each phase, and do not modify V3.0 binding artifacts unless explicitly authorized.

**Goal:** 将 Paperclip × Dark Factory / Phoenix Runtime 的下一阶段工作拆成可执行开发任务，同时保持当前 V3.0 `agent-control-r1` 合同不被干扰。

**Architecture:** 采用四层边界：Paperclip control plane、Bridge / Adapter projection、Dark Factory execution plane、Phoenix Runtime capabilities。123 仓库先沉淀 informative 文档与验收计划；Paperclip upstream 先做 plugin POC，不改 core。

**Tech Stack:** Markdown docs、V3 manifest/validation scripts、Paperclip plugin system、TypeScript/Node/Pnpm（Paperclip 侧）、Python unittest/Makefile（123 侧）。

---

## Phase 0 — 123 文档整理与安全分类

### Task 0.1: 确认仓库与基线

**Objective:** 确认 123 当前分支、远端差异、V3.0 binding baseline 与新增文件不会覆盖用户改动。

**Files:**
- Read: `README.md`
- Read: `3.0/V3_IMPLEMENTATION_ENTRYPOINT.md`
- Read: `paperclip_darkfactory_v3_0_bundle_manifest.yaml`

**Commands:**

```bash
cd /home/siyuah/workspace/123
git status -sb
git log --oneline --decorate --max-count=5
```

**Expected:** 工作树无未解释改动；如果有本地 ahead commit，记录但不 push。

**DoD:** 明确当前 HEAD、origin/main、是否 dirty。

### Task 0.2: 新增 future_development 隔离目录

**Objective:** 将新增/缺失的下一阶段文档放在隔离目录，不干扰 release-gated bundle。

**Files:**
- Create: `3.0/future_development/README.md`
- Create: `3.0/future_development/PAPERCLIP_UPSTREAM_INTEGRATION_PLAN.md`
- Create: `3.0/future_development/NEXT_DEVELOPMENT_TASKS.md`
- Create: `3.0/future_development/HERMES_GPT55_EXECUTION_COMMANDS.md`

**Validation:**

```bash
cd /home/siyuah/workspace/123
git status --short
```

**Expected:** 只出现新增文档与必要的 manifest/README 改动。

### Task 0.3: 更新 informative out-of-bundle 分类

**Objective:** 让 V3 validator 知道新目录是 informative out-of-bundle。

**Files:**
- Modify: `paperclip_darkfactory_v3_0_bundle_manifest.yaml`
- Modify: `README.md`
- Optional Modify: `3.0/V3_IMPLEMENTATION_ENTRYPOINT.md`

**Required manifest entries:**

```yaml
- 3.0/future_development/README.md
- 3.0/future_development/PAPERCLIP_UPSTREAM_INTEGRATION_PLAN.md
- 3.0/future_development/NEXT_DEVELOPMENT_TASKS.md
- 3.0/future_development/HERMES_GPT55_EXECUTION_COMMANDS.md
```

**Validation:**

```bash
cd /home/siyuah/workspace/123
make manifest-v3
make validate-v3
```

**DoD:** validate-v3 通过；新增文件不进入 manifest `files` release-gated 清单。

### Task 0.4: 清理验证副产物

**Objective:** 删除 `__pycache__`，避免提交临时缓存；如果 consistency report 只有 checkedAt 变化，按项目惯例恢复。

**Commands:**

```bash
cd /home/siyuah/workspace/123
find . -type d -name __pycache__ -prune -exec rm -rf {} +
git status -sb
git diff -- paperclip_darkfactory_v3_0_consistency_report.md paperclip_darkfactory_v3_0_consistency_report.json
```

**DoD:** status 中没有 `__pycache__`；报告变更若只是 timestamp，需要恢复。

---

## Phase 1 — Paperclip plugin POC 设计

### Task 1.1: 只读确认 Paperclip plugin 能力

**Objective:** 阅读 Paperclip upstream 的 plugin 示例与 host service，不修改 upstream。

**Files:**
- Read: `/home/siyuah/workspace/paperclip_upstream/packages/plugins/examples/plugin-hello-world-example/src/manifest.ts`
- Read: `/home/siyuah/workspace/paperclip_upstream/packages/plugins/examples/plugin-orchestration-smoke-example/src/manifest.ts`
- Read: `/home/siyuah/workspace/paperclip_upstream/server/src/services/plugin-host-services.ts`
- Read: `/home/siyuah/workspace/paperclip_upstream/ui/src/api/plugins.ts`

**Commands:**

```bash
cd /home/siyuah/workspace/paperclip_upstream
git status -sb
git log --oneline --decorate --max-count=3
```

**DoD:** 输出 plugin manifest、route、dashboard/detail tab、namespace DB 是否可用。

### Task 1.2: 创建 plugin POC 分支或隔离工作区

**Objective:** 避免污染 upstream master；所有实验在分支或 fork 工作区进行。

**Commands:**

```bash
cd /home/siyuah/workspace/paperclip_upstream
git status -sb
git switch -c dark-factory-bridge-plugin-poc
```

**DoD:** 新分支创建成功；无未提交外部改动被覆盖。

### Task 1.3: 最小 plugin manifest

**Objective:** 新增 `paperclip-dark-factory-bridge-plugin` manifest，先注册 UI/API 扩展点，不实现真实 Dark Factory 调用。

**Files:**
- Create under Paperclip plugin examples or packages plugin area, following existing convention.

**Acceptance:**

- manifest 名称清楚表达 bridge/projection，不暗示 truth source；
- capabilities 只声明 dashboard/detail/API/namespace DB；
- 没有修改 Paperclip Task 主模型。

### Task 1.4: Mock projection API

**Objective:** 用 mock data 跑通 projection/cursor/provider-health API。

**Routes:**

```text
GET  /issues/:issueId/dark-factory/projection
GET  /issues/:issueId/dark-factory/journal-cursor
GET  /issues/:issueId/dark-factory/provider-health
POST /issues/:issueId/dark-factory/rehydrate-request
```

**Acceptance:**

- 返回对象含 `source: "projection"` 或等价说明；
- cursor 单调字段存在；
- rehydrate request 只创建请求/意图，不直接改 truth；
- 响应不含 token/secret。

### Task 1.5: UI 最小展示

**Objective:** 在 dashboard widget 与 task detail tab 展示 mock projection。

**UI fields:**

- linked Run id；
- journal cursor；
- projection status；
- callback receipt；
- degraded / blocked / needs approval；
- provider health summary。

**Acceptance:** UI 明确显示 `projection` / `stale` / `lastUpdatedAt`，避免误认为 Paperclip 原生 truth。

---

## Phase 2 — Bridge / Adapter 一致性测试

### Task 2.1: 定义 bridge projection contract proposal

**Objective:** 在 123 informative 文档或 Paperclip POC docs 中定义 projection/cursor/receipt 的最小字段。

**Fields:**

- `projectionId`
- `issueId` / `taskId`
- `runId`
- `journalCursor`
- `lastJournalSequenceNo`
- `projectionVersion`
- `projectionStatus`
- `staleReason`
- `callbackReceiptId`
- `sourceJournalRef`

**Non-goal:** 不把这些字段加入 Paperclip Task 主模型。

### Task 2.2: 写 replay idempotency test

**Objective:** 同一 journal replay 多次，projection 输出一致。

**Expected:** same input journal → same projection hash / state / cursor。

### Task 2.3: 写 duplicate callback receipt test

**Objective:** 同一 callback 重复到达不会重复推进 terminal state。

**Expected:** 第二次 callback 返回 existing receipt / idempotent no-op。

### Task 2.4: 写 out-of-order callback test

**Objective:** 乱序 callback 不得让 cursor 回退或跳过缺失 journal record。

**Expected:** projection 标记 stale / gap，不升级为 success。

### Task 2.5: 写 rebuild from zero test

**Objective:** 删除 projection cache 后能从 journal 重新构建同等 projection。

**Expected:** rebuild result equals cached result except rebuild timestamp。

---

## Phase 3 — Runtime observability proposal

### Task 3.1: Provider health schema proposal

**Objective:** 编写 V3.1-alpha 候选 schema proposal，先不改 V3.0 binding。

**Fields:** provider role、task type、breaker state、last success/failure、failure_class histogram、open reason、cooldownUntil、probe policy。

### Task 3.2: Degraded mode operator projection proposal

**Objective:** 定义 degraded mode 的 operator-visible projection 和 audit trail。

**Fields:** degraded reason、scope、affected run/attempt、fallback chain、operator acknowledgement、report disclaimer。

---

## Phase 4 — MemorySidecar 独立化

### Task 4.1: MemorySidecar storage profile proposal

**Objective:** 定义 sidecar metadata、KG edge、DiaryStore retention、PromptContextBuilder receipt。

**Hard rules:** revoked/expired/low-confidence/sensitive memory 不得注入；memory 不覆盖 system/developer/user latest instruction；memory 不覆盖 Journal。

### Task 4.2: PhoenixRecover smoke timeline proposal

**Objective:** 描述 runtime restart 后 sidecar reload、journal replay、projection consistency check、安全降级恢复。

**Expected:** 损坏 sidecar 进入 conservative recovery；journal truth 优先。

---

## Runtime Adapter Integration Next Tasks

状态: Informative / Out-of-bundle task list for V3.1+ product-main planning.
是否修改 V3.0 binding artifacts: 否。
是否授权 Paperclip Task/Issue 主模型修改: 否；如需触碰，必须单独架构评审并获得用户授权。
是否授权 push/tag/release: 否。

### P0 — CI visibility / runtime blocker unblock

**Objective:** 先解决 product-main 可验证性，避免把 fork CI 不可见或本机 embedded PostgreSQL blocker 误判为产品完成。

**Tasks:**

- 复核 `siyuah/paperclip` Actions/workflows；当前必须报告：fork 当前 CI 不可见或未触发。
- 明确 root `pnpm run test:run` 的 embedded PostgreSQL/native dependency blocker。
- 让用户二选一授权：安装/provision PostgreSQL native dependencies，或采用 Docker/Compose canonical smoke。

### P0 — adapter contract design doc

**Objective:** 在 fork product-main 内定义 Dark Factory runtime adapter 的最小合同，不直接改 Issue/Task 主模型。

**Required fields:** request ID/idempotency key、Paperclip run ID、Dark Factory run ID、Journal cursor、last sequence、receipt ID、projection status、secret redaction policy。

**DoD:** 明确哪些字段进入 `AdapterExecutionResult.resultJson` / run event metadata，哪些字段只进入 plugin namespace DB，哪些触点需要单独架构评审。

### P1 — mock adapter skeleton

**Objective:** 在 `siyuah/paperclip` fork only 新增 mock Journal-backed runtime adapter skeleton。

**Hard rules:** 不连接真实 Dark Factory；不读取或打印 secrets；不写 Paperclip Task/Issue 主模型；只返回 receipt/cursor/projection metadata。

### P1 — Journal receipt simulator

**Objective:** 提供 fixture simulator，覆盖 normal receipt、duplicate request、out-of-order callback、missing cursor gap、projection rebuild。

**DoD:** same Journal replay → same projection；duplicate callback → idempotent existing receipt；cursor gap → stale/gap，不升级 terminal success。

### P1 — smoke harness

**Objective:** 将 bridge plugin、mock adapter、Journal simulator 串成本地 smoke。

**Validation:** targeted plugin test/typecheck/build；mock adapter unit tests；root typecheck/build；root `test:run` 在 blocker 解除后运行；Docker/Compose smoke 需用户授权。

### P2 — UI operator workflow

**Objective:** 在 projection-only UI 上逐步展示 runtime adapter state。

**Fields:** provider health、degraded/blocked/stale、receipt/cursor、rehydrate request status、operator disclaimer。

**Boundary:** UI 仍显示 `Projection only — Dark Factory Journal remains truth source`，不暗示 Paperclip DB 是 truth source。

### P2 — upstream contribution assessment

**Objective:** 评估哪些通用 adapter/plugin 改进适合 upstream `paperclipai/paperclip`。

**Boundary:** 这是可选上游贡献路径；不作为 `siyuah/paperclip` 产品主线默认阻塞项。

---

## Phase 5 — 提交与汇报

### Task 5.1: 123 文档提交

**Commands:**

```bash
cd /home/siyuah/workspace/123
git status -sb
git diff --stat
git add README.md paperclip_darkfactory_v3_0_bundle_manifest.yaml 3.0/future_development/
git commit -m "docs: add future development integration workspace"
```

**DoD:** commit 后 `git status -sb` 显示 ahead，工作树干净。

### Task 5.2: Paperclip POC 提交

**Commands:**

```bash
cd /home/siyuah/workspace/paperclip_upstream
pnpm -r typecheck
pnpm test:run
pnpm build
git status -sb
git diff --stat
git add <plugin files>
git commit -m "feat: add dark factory bridge plugin poc"
```

**DoD:** typecheck/test/build 通过；POC 不改 core Task model。

---

## Progress Log

### 2026-05-02 - Architecture improvements + Environment lifecycle hooks

Completed in `siyuah/paperclip` fork `fork-master-product` branch:

1. **V3 parity guard tests** - Added runtime contract V3 parity guard test suite (7 assertions) to lock TypeScript `runtime-contract.ts` types against V3 `core_enums.yaml`. 4 runtime-level types (`ProjectionStatus`, `FailureClass`, `BreakerState`, `ProviderHealthState`) confirmed as not yet in V3.0 binding enums; marked as runtime stability assertions with V3.1 upgrade path comments.

2. **Plugin directory migration** - Moved bridge plugin from `packages/plugins/examples/` to `packages/plugins/integrations/dark-factory-bridge/`. Package renamed to `@paperclipai/plugin-dark-factory-bridge`. `pnpm-workspace.yaml` updated with `integrations/*` glob.

3. **Environment adapter design document** - Created `docs/dark-factory/DARK_FACTORY_ENVIRONMENT_ADAPTER_DESIGN.md` (239 lines, 9 sections) covering Plugin-hosted environment driver approach, SDK interface mapping, mock implementation, manifest changes, AdapterExecutionResult mapping, boundary constraints, verification plan, and step-by-step implementation guide.

4. **Environment lifecycle hooks Step 1-4** - Implemented `onEnvironmentValidateConfig`, `onEnvironmentProbe`, `onEnvironmentAcquireLease`, `onEnvironmentExecute` in `worker.ts` (+129 LOC). Added `environment-lifecycle.spec.ts` (+162 LOC, 5 tests). All 36 tests pass.

5. **Environment lifecycle hooks Step 5-6** - Implemented `onEnvironmentResumeLease`, `onEnvironmentReleaseLease`, `onEnvironmentDestroyLease`. Added resume, release, destroy, and full lifecycle smoke tests. All 40 tests pass.

Commits:

- `f90562fa` docs: add Dark Factory environment adapter design document
- `ccdfec5d` refactor: move dark-factory bridge plugin to integrations
- `d705bb16` feat: add environment lifecycle hooks Step 1-4
- `71c417f6` feat: add environment lifecycle hooks Step 5-6

Boundary compliance:

- Dark Factory Journal remains truth source: yes
- `authoritative: false` on all outputs: yes
- `terminalStateAdvanced: false` on all outputs: yes
- No Paperclip Task/Issue main model changes: yes
- No real Dark Factory connection: yes
- No secrets read/printed/committed: yes
- Plugin DB limited to projection/cache/cursor/receipt/request metadata: yes

Next candidate tasks:

- P0: adapter contract design doc (fork-internal mapping of `AdapterExecutionContext` to Dark Factory request envelope)
- P1: Journal receipt simulator fixtures
- P1: smoke harness connecting bridge plugin + mock adapter + Journal simulator

### 2026-05-02 - Adapter contract + Journal simulator + smoke harness

Completed in `siyuah/paperclip` fork `fork-master-product` branch:

1. **P0 adapter contract design doc** - Created `docs/dark-factory/DARK_FACTORY_ADAPTER_CONTRACT_DESIGN.md` (289 lines) defining field-level mapping between Paperclip `PluginEnvironmentExecuteParams` / `AdapterExecutionContext` and Dark Factory request/response envelopes. Covers idempotency, error mapping, resultJson/run event metadata allocation, and boundary constraints.

2. **P1 Journal receipt simulator fixtures** - Added `journal-receipt-simulator.ts` with deterministic normal, gap, out-of-order, duplicate, and empty Journal sequences. Added `simulateCallbackSequence` and `JournalReceiptSimulator` class API. Added 9 simulator tests; all 49 plugin tests passed after this step.

3. **P1 smoke harness** - Added `smoke-harness.spec.ts` connecting bridge plugin API routes, environment lifecycle hooks, and Journal receipt simulator in process. Covers happy path, deterministic execution, Journal anomaly fixtures, lease resume/release/destroy, projection-only API state, non-mock config rejection, and unknown route handling. No network, database, Docker, or real Paperclip instance required. All 54 plugin tests pass.

Commits:

- `bffa1aa6` docs: add adapter contract design for Dark Factory request/response mapping
- `32c4609d` feat: add journal receipt simulator fixtures and tests
- `cb8e834a` test: add Dark Factory bridge smoke harness

Boundary compliance:

- Dark Factory Journal remains truth source: yes
- `authoritative: false` on all outputs: yes
- `terminalStateAdvanced: false` on all outputs: yes
- No Paperclip Task/Issue main model changes: yes
- No Plugin SDK or Paperclip core/server/ui changes: yes
- No real Dark Factory connection: yes
- No secrets read/printed/committed: yes

Next candidate tasks:

- P1: projection-only UI operator workflow for provider health, stale/degraded/blocked, receipt/cursor, and rehydrate request status
- P2: upstream contribution assessment

### 2026-05-02 - Upstream sync + root validation + contribution assessment

1. **Upstream sync** - Rebased `fork-master-product` onto latest `origin/master` (`685ee84e`). Zero conflicts. Actual replay set was 8 commits on top of master because fork baseline commit `f53a8f51` was also not present upstream.

2. **Root validation** - `pnpm -r typecheck` passed for all packages (server, ui, cli, all plugins including dark-factory-bridge). `pnpm build` passed. 54/54 bridge plugin tests pass after rebase. Root `pnpm test:run` failed in upstream/environment-dependent cursor-local and live SSH tests, not in Dark Factory bridge code.

3. **Contribution assessment** - Created `docs/dark-factory/DARK_FACTORY_CONTRIBUTION_ASSESSMENT.md` analyzing which commits are suitable for upstream PR. Recommendation: do not open one large upstream PR directly; discuss in upstream Discord first and, if accepted, split into smaller generalized plugin-environment-driver PRs.

4. **Push to fork** - Pushed `fork-master-product` to the fork remote. `git push fork master:master` was rejected as non-fast-forward, so `fork/master` remains on the old fork baseline and was not force-updated.

Current branch state:

- `fork-master-product`: pushed to fork remote, 9 commits ahead of `master` after adding the contribution assessment document
- `master`: synced with `origin/master` at `685ee84e`
- `fork/master`: not synced with `master`; normal push rejected as non-fast-forward

Project status: **All development tasks complete. Ready for contribution decision.**

### 2026-05-02 - Internal preview deployment validated

1. **MVP hardening Batch 1** - API key auth, journal file locking, structured logging, HTTP retry with backoff, Docker packaging, security tests.

2. **MVP hardening Batch 2** - TLS reverse proxy (Caddy), Docker secrets, secret management docs, journal admin tool (backup/restore/retain), load and concurrency tests.

3. **Production readiness updated** - Assessment upgraded from NO to CONDITIONAL YES for MVP internal preview.

4. **Internal preview deployed and validated**:
   - Dark Factory HTTP server started on localhost:9701
   - createRun returned valid runId with journal persistence
   - API key authentication working (401 on missing/wrong key)
   - Journal persisted to JSONL file (4.8KB, entries validated)
   - journal_admin.py tools (backup/retain) working
   - Bridge plugin 58/58 tests pass including real HTTP integration
   - QUICKSTART.md created with one-click startup guide

Final project metrics:
- paperclip_upstream: 15 commits on fork-master-product
- 123 repo: synced with origin/main after deployment commits
- Bridge plugin: 58 tests, 7 test files, ~2,800 LOC source + tests
- Dark Factory server: ~850 LOC Python
- Design docs + assessment: ~1,200 LOC
- Total project: ~7,000+ LOC across both repos

**Status: MVP INTERNAL PREVIEW READY. CONDITIONAL YES for deployment.**

