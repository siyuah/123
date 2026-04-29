# Paperclip × Dark Factory Runtime Adapter Integration Plan

Status: Informative / Non-binding / Out-of-bundle for V3.0
This document does not modify V3.0 binding artifacts.
Dark Factory Journal remains truth source.
Paperclip bridge/plugin DB is projection/cache/cursor/receipt/request only.
No Paperclip Task/Issue main model mutation is authorized by this document.
No GitHub Release/tag/push is authorized by this document.

适用范围: `/home/siyuah/workspace/123/3.0/future_development/` future-development planning only
产品目标仓库: `siyuah/paperclip` fork, branch `dark-factory-product-main`
产品代码本地仓库: `/home/siyuah/workspace/paperclip_upstream`

---

## 1. Scope and Non-Scope

### Scope

- product-main fork planning for V3.1+ runtime adapter integration.
- 将已经存在的 Paperclip Dark Factory bridge plugin POC 从“projection-only UI/API baseline”推进到 V3.1+ runtime adapter integration 的设计输入。
- 对齐 Paperclip 产品主线中的 adapter registry、agent run lifecycle、plugin capability model、issue/run/approval/operator workflow 与 Dark Factory Journal-backed execution plane 的边界。
- 给出 fork 内可执行的阶段路线：先保持 plugin projection baseline，再设计 external/runtime adapter contract，再用 mock Journal-backed adapter 验证 request/receipt/cursor/replay 语义。

### Non-Scope

- 不修改 V3.0 binding artifacts，不改变 `v3.0-agent-control-r1`。
- 不创建、不修改 GitHub Release；不 push；不 tag。
- 不连接真实 Dark Factory 服务；不读取、打印、提交 token/password/API key/connection string。
- 不把 bridge plugin namespace DB 变成 truth source。
- 不直接修改 Paperclip Task/Issue 主模型。
- 如果未来设计需要触碰 Paperclip Task/Issue 主模型、core issue schema、run lifecycle 或 approval state，必须列为“需单独架构评审/需用户授权”，不能由本文档直接授权实施。
- upstream `paperclipai/paperclip` PR/maintainer review 仅是可选上游贡献路径，不是 `siyuah/paperclip` 产品主线默认阻塞项。

---

## 2. Current Baseline

### 2.1 `siyuah/123` repo current stable state

当前稳定输入来自本轮开始前的状态说明与只读复核：

- local repo: `/home/siyuah/workspace/123`
- branch: `main`
- tracking: `origin/main`
- HEAD: `cbcf25c Add AI execution handoff for product mainline`
- pre-change status: `## main...origin/main`
- baseline validation: `python3 tools/validate_v3_bundle.py` reported `status pass, checks 12, errors 0, warnings 0` before this future-development doc task.
- allowed write scope for this task: only `3.0/future_development/` informative planning docs.

### 2.2 `paperclip_upstream` product branch / PR state

当前产品主线输入来自本轮状态说明与只读复核：

- local repo: `/home/siyuah/workspace/paperclip_upstream`
- branch: `dark-factory-product-main`
- tracking: `fork/dark-factory-product-main`
- fork remote: `https://github.com/siyuah/paperclip.git`
- origin remote: `https://github.com/paperclipai/paperclip.git` as optional upstream source, not default product-main blocker.
- HEAD: `74d52265d79db1bcf59467820ca94cbe09b8acbb`
- latest commit: `fix: complete Dark Factory bridge review hardening`
- local HEAD matches `fork/dark-factory-product-main` at the stated baseline.
- PR: `https://github.com/siyuah/paperclip/pull/1`
- PR state: `OPEN`
- mergeStateStatus: `CLEAN`
- statusCheckRollup: `[]`

### 2.3 Bridge plugin projection-only status

The fork already contains a projection-only bridge plugin example at:

```text
packages/plugins/examples/paperclip-dark-factory-bridge-plugin/
```

Observed characteristics:

- package name: `@paperclipai/plugin-dark-factory-bridge-example`
- manifest id: `paperclipai.dark-factory-bridge-example`
- capabilities are intentionally narrow: API route registration, plugin namespace DB migrate/read/write, `issues.read`, dashboard/detail/settings UI slots.
- forbidden write capabilities such as issue creation, issue wakeup, relation writes, document writes, subtree writes, and orchestration writes are intentionally not part of the manifest.
- namespace DB migration stores projection/cache/cursor/receipt/request records, including `projection_cache`, `journal_cursors`, `callback_receipts`, and `rehydrate_requests`.
- route/API responses and UI copy include the boundary: `Projection only — Dark Factory Journal remains truth source`.
- mock routes include:
  - `GET /issues/:issueId/dark-factory/projection`
  - `GET /issues/:issueId/dark-factory/journal-cursor`
  - `GET /issues/:issueId/dark-factory/provider-health`
  - `POST /issues/:issueId/dark-factory/rehydrate-request`

This is a strong Phase 1 baseline, but it is not yet a runtime adapter. It does not execute Dark Factory work, does not connect to real Journal APIs, and does not mutate Paperclip Task/Issue main model.

### 2.4 CI invisible / untriggered status

Fork CI is currently not available as a release/product-main confidence signal:

- `gh run list --repo siyuah/paperclip --branch dark-factory-product-main` returned `[]`.
- `gh api repos/siyuah/paperclip/actions/workflows` returned `total_count: 0`.
- Required status text for reporting: **fork 当前 CI 不可见或未触发**.

### 2.5 Embedded PostgreSQL local blocker

Paperclip product dev/runtime validation can depend on embedded PostgreSQL or native PostgreSQL runtime dependencies. Current planning assumes an unresolved local blocker around embedded PostgreSQL/native provisioning until explicitly verified or user-authorized remediation is performed.

Implications:

- Do not install system packages or use `sudo` without user authorization.
- Prefer targeted plugin validation first.
- For end-to-end smoke, either provision PostgreSQL native dependencies with authorization or use Docker/Compose as the canonical smoke path after checking Docker availability.

---

## 3. Boundary Model

### Dark Factory Journal = truth source

Dark Factory Journal is the authoritative execution record for run facts, attempt facts, callback receipts, journal sequence, replay, and recovery decisions. Runtime adapter and bridge surfaces may reference Journal cursors and receipt IDs, but must not replace Journal facts.

### Paperclip Issue/Task = product workflow/control-plane surface

Paperclip Issue/Task remains the product-visible workflow and operator control-plane surface. It may show derived execution state, approvals, activity, comments, and operator actions, but it should not absorb Dark Factory Journal internals or MemorySidecar internals as first-class Task/Issue truth without separate architecture review.

### Bridge plugin DB = projection/cache/cursor/receipt/request only

The bridge/plugin namespace DB may store:

- projection cache;
- cursor metadata;
- callback receipt metadata;
- request/intention records such as rehydrate request receipts;
- stale/degraded/blocked projection metadata;
- source Journal reference/cursor identifiers.

It must not store:

- real provider credentials;
- token/password/API key/connection string;
- authoritative Journal contents as a competing truth record;
- Paperclip Task/Issue main model overrides;
- unbounded raw execution logs or secret-bearing payloads.

### Runtime adapter = execution/request translation layer, not truth source

A Dark Factory runtime adapter translates Paperclip wake/run/request semantics into Dark Factory execution requests and maps Journal-backed receipts back to Paperclip run/result surfaces. It can enforce idempotency, serialize request envelopes, attach correlation IDs, emit status/log metadata, and reconcile cursors. It is not a truth source; all terminal execution claims must be backed by Journal receipt/cursor evidence.

### Hermes/GPT-5.5 = execution provider/agent runtime, not authoritative record

Hermes/GPT-5.5 can be one execution provider or agent runtime behind the Dark Factory execution plane. It is not the authoritative product record. Paperclip should treat it as runtime/provider capability surfaced through adapter outputs, receipts, status events, and logs, not as a direct source of Task/Issue truth.

---

## 4. Target Architecture Options

### A. Plugin-only projection + manual operator actions

**Ownership boundary**

- Paperclip plugin owns projection UI/API and namespace DB.
- Dark Factory Journal remains external truth.
- Operators perform manual decisions based on projection status.

**Implementation touchpoints**

- Existing `packages/plugins/examples/paperclip-dark-factory-bridge-plugin/` manifest, worker, UI, migration, tests.
- Plugin host services: plugin API routes, UI slots, plugin namespace DB.
- No adapter registry or heartbeat run execution changes.

**Data persisted**

- `projection_cache`
- `journal_cursors`
- `callback_receipts`
- `rehydrate_requests`
- derived provider health/projection status payloads

**What remains read-only/projection**

- Paperclip Issue/Task main model remains unchanged.
- Journal facts remain outside plugin DB.
- Rehydrate is a request/receipt/intention, not a terminal state transition.

**Validation strategy**

- Targeted plugin test/typecheck/build.
- Manifest capability assertions that no issue-write capabilities are declared.
- API route tests requiring `authoritative: false`, `truthSource: dark-factory-journal`, and disclaimer text.
- Migration scan for no secrets and no authoritative Journal tables.

**Risks**

- Manual operator flow may not provide enough automation for V3.1+ runtime execution.
- Projection-only plugin can drift from future adapter semantics if no contract is written.
- Without CI visibility, fork validation remains local-only unless Actions are enabled.

### B. External adapter integration using Paperclip adapter manager

**Ownership boundary**

- Paperclip adapter registry owns adapter discovery, configuration, environment checks, and invocation.
- Dark Factory adapter package owns request translation and Journal-backed result mapping.
- Journal remains authoritative; adapter result is a receipt/projection into Paperclip run lifecycle.

**Implementation touchpoints**

- `packages/adapter-utils/src/types.ts` `ServerAdapterModule`, `AdapterExecutionContext`, `AdapterExecutionResult`, `testEnvironment`, optional capabilities.
- `server/src/adapters/registry.ts` and external adapter plugin loader / adapter management routes.
- Agent config fields: `agents.adapterType`, `agents.adapterConfig`, `agents.runtimeConfig`.
- Heartbeat/run executor in `server/src/services/heartbeat.ts`.
- Adapter UI/management routes in `server/src/routes/adapters.ts`.

**Data persisted**

- Existing Paperclip `heartbeat_runs`, `heartbeat_run_events`, agent runtime state, activity log, cost/log metadata where appropriate.
- Adapter config should only store references to configured secret paths, not raw secrets.
- Dark Factory correlation IDs, idempotency keys, Journal cursor references, and receipt IDs may be persisted in adapter result metadata if bounded and non-secret.

**What remains read-only/projection**

- Bridge/plugin DB remains projection/cache/cursor/receipt/request only.
- Paperclip Issue/Task main model should not be extended for Dark Factory internal fields in this phase.
- Terminal execution truth remains Journal-backed.

**Validation strategy**

- Adapter contract unit tests with mock Journal client.
- Environment check tests for missing credentials/dependencies without printing secret values.
- Heartbeat/run lifecycle tests with a fake adapter returning Journal-backed receipts.
- Existing plugin projection tests continue to pass.

**Risks**

- `AdapterExecutionResult` may be too narrow for full Journal receipt semantics unless extension fields are agreed.
- Existing heartbeat service can persist result/log/cost/run status; mapping terminal Journal states to Paperclip run status requires careful review.
- Credential flow and local-agent JWT handling need security review.

### C. Dedicated Dark Factory runtime adapter with Journal-backed receipts

**Ownership boundary**

- Dedicated fork-internal adapter owns Dark Factory request envelope, idempotency, cursor reconciliation, receipt verification, mock Journal replay, and future real connector boundary.
- Paperclip owns agent/run lifecycle and operator visibility.
- Bridge plugin owns projection and operator UI.
- Dark Factory Journal remains authoritative.

**Implementation touchpoints**

- New fork-internal adapter package, likely under `packages/adapters/` or as an external adapter package loaded by adapter manager.
- `ServerAdapterModule.execute(ctx)` translates Paperclip run context to Dark Factory request envelope.
- `ServerAdapterModule.testEnvironment(ctx)` validates configured paths/URLs without touching real secrets.
- Optional adapter config schema for endpoint/secret reference/mock mode.
- Bridge plugin can read adapter result metadata or a mock Journal simulator to display projection state.
- Smoke harness can run adapter execute against a mock Journal service or fixture.

**Data persisted**

- Paperclip run rows and events for run lifecycle.
- Adapter result metadata containing non-secret correlation IDs, idempotency key hash/ref, receipt ID, Journal cursor, projection status, and reconciliation outcome.
- Plugin namespace DB projection/cache/cursor/receipt/request metadata only.

**What remains read-only/projection**

- Journal contents are not copied as truth into Paperclip.
- Provider/model internals remain runtime/provider facts, not protocol MUSTs.
- Paperclip Issue/Task main model is not mutated by this document.

**Validation strategy**

- Mock Journal-backed adapter tests covering request creation, duplicate request idempotency, out-of-order callback, missing Journal gap, cursor monotonicity, stale projection, and replay rebuild.
- Plugin + adapter integration smoke using fixtures only.
- Root typecheck/build once local blockers are resolved.
- Docker/Compose smoke to avoid native PostgreSQL blocker if Docker is approved and available.

**Risks**

- More implementation surface than plugin-only option.
- Requires careful architecture review for run status mapping and activity log semantics.
- Real Dark Factory connector must be postponed until credential/secret path and network policy are reviewed.

### D. Optional future webhook/event ingestion path

**Ownership boundary**

- Dark Factory emits webhook/events.
- Paperclip receives events through a dedicated ingestion endpoint, plugin route, or external service.
- Journal remains truth; webhook is a delivery channel, not truth.

**Implementation touchpoints**

- Plugin API routes or server route for webhook ingestion.
- Signature verification and replay protection.
- Namespace DB for delivery receipts/cursors, not authoritative execution facts.
- Live-event/activity/log projection into Paperclip UI.

**Data persisted**

- Delivery receipt metadata.
- Event cursor/high-water mark.
- Idempotency/deduplication keys.
- Projection update payloads after validation.

**What remains read-only/projection**

- Raw webhook payloads should not become truth if they are not Journal-verified.
- Paperclip Issue/Task main model changes require separate authorization.
- Secrets/signing keys must live in configured secret path only.

**Validation strategy**

- Signature verification tests with fake keys.
- Replay/deduplication tests.
- Out-of-order delivery and cursor gap tests.
- Projection rebuild from Journal fixtures.

**Risks**

- Webhook ingress expands attack surface.
- Signature, replay, and payload retention policy require security review.
- If implemented too early, it can bypass the cleaner adapter contract and create a second truth path.

---

## 5. Recommended Path

Recommended product-main path for `siyuah/paperclip`:

1. **Phase 1: keep bridge PR as projection baseline**
   - Preserve the existing projection-only bridge plugin as the UI/API baseline.
   - Keep namespace DB limited to projection/cache/cursor/receipt/request.
   - Continue to avoid Paperclip Task/Issue main model mutation.

2. **Phase 2: design external adapter contract**
   - Write a fork-local adapter contract proposal that maps Paperclip `AdapterExecutionContext` / `AdapterExecutionResult` to Dark Factory request/receipt/cursor semantics.
   - Identify whether existing `AdapterExecutionResult.resultJson`, `runtimeServices`, `errorFamily`, `summary`, and log hooks are sufficient or need reviewed extension points.
   - Treat any extension to `ServerAdapterModule`, run status, issue lifecycle, approval gates, or activity log as architecture-review-required.

3. **Phase 3: implement mock Journal-backed adapter in fork only**
   - Add a mock `dark_factory_runtime` adapter behind the fork product branch, not upstream first.
   - Use fixture Journal client/simulator; do not connect to real Dark Factory.
   - Return only non-secret receipt/cursor/projection metadata.

4. **Phase 4: add smoke harness / Docker validation**
   - Add direct unit tests and integration smoke with mock Journal.
   - Run targeted plugin validation, adapter tests, root typecheck/build, and Docker/Compose smoke if Docker is authorized and available.
   - Use Docker/Compose as canonical smoke if embedded PostgreSQL native dependencies remain blocked.

5. **Phase 5: evaluate upstream contribution separately**
   - Only after fork product-main behavior is stable, decide whether parts should be contributed upstream.
   - Mark this as **可选上游贡献路径**; do not block fork product-main on upstream maintainer review unless the user explicitly asks.

---

## 6. Paperclip Touchpoints Requiring Review

The following touchpoints are high-risk and require architecture review before implementation if the runtime adapter integration needs them:

- **adapter interface extension**
  - `ServerAdapterModule`, `AdapterExecutionContext`, `AdapterExecutionResult`, environment checks, model/quota hooks, and config schema.
  - Any new receipt/cursor/status hook must preserve runtime agnosticism.

- **issue/run lifecycle integration**
  - Mapping Dark Factory request/receipt/cursor states into `heartbeat_runs`, `heartbeat_run_events`, liveness fields, continuation/retry behavior, and issue execution state.
  - Avoid direct Issue/Task main model mutation without user authorization.

- **approval gates**
  - Any adapter-triggered approval, rehydrate, retry, or terminal-state transition must respect Paperclip issue execution policy and approval services.

- **agent key / auth**
  - Adapter credentials and local-agent JWT handling must be reviewed.
  - Future real Dark Factory credentials must come only from configured secret path, never inline docs or committed config.

- **activity logs**
  - Activity entries should distinguish projection/receipt/request from authoritative execution facts.
  - Avoid logging secret-bearing payloads.

- **DB schema or plugin capability changes**
  - Plugin namespace migrations can add projection/cursor/receipt/request metadata only.
  - Core DB schema changes, issue schema changes, plugin capability expansion, or issue-write capabilities require separate review.

- **UI navigation/settings**
  - Runtime adapter settings, provider health, degraded state, and rehydrate request UI must show projection-only disclaimers until Journal-backed terminal verification is implemented.

- **worktree/embedded PostgreSQL assumptions**
  - Local runtime and smoke tests may require embedded PostgreSQL/native dependencies or Docker.
  - Do not assume host provisioning exists; require explicit verification/authorization.

---

## 7. Validation and CI Plan

### 7.1 Targeted plugin direct validation

Run from `/home/siyuah/workspace/paperclip_upstream` when dependencies are available:

```sh
pnpm --filter @paperclipai/plugin-dark-factory-bridge-example test
pnpm --filter @paperclipai/plugin-dark-factory-bridge-example typecheck
pnpm --filter @paperclipai/plugin-dark-factory-bridge-example build
```

Expected assertions:

- manifest parses;
- no Issue/Task mutation capabilities;
- API route dispatch returns `authoritative: false`;
- `truthSource` remains `dark-factory-journal`;
- rehydrate returns request/receipt semantics only.

### 7.2 Root typecheck/build

After targeted validation and dependency readiness:

```sh
pnpm run typecheck
pnpm run build
```

These should be treated as product-main validation gates before merge/commit decisions in the fork.

### 7.3 Root `test:run` blocker and remediation options

Run when local runtime dependencies are ready:

```sh
pnpm run test:run
```

Known blocker class:

- embedded PostgreSQL/native dependency readiness may block root test/dev smoke.

Remediation options:

1. User authorizes native dependency provisioning without printing secrets and without `sudo` unless explicitly approved.
2. Use Docker/Compose smoke path as canonical local runtime validation if Docker is available and user approves.
3. Keep targeted plugin/adapter tests as short-term confidence until root runtime blocker is removed.

### 7.4 Docker/Compose smoke path

Before running smoke, read and confirm:

- `doc/DEVELOPING.md`
- `doc/DOCKER.md`
- `.env.example`
- `Dockerfile`
- `docker/docker-compose.yml`
- `docker/docker-compose.quickstart.yml`

Then, if authorized and Docker is available, perform product smoke without committing generated artifacts:

- start Paperclip dev/server or compose service;
- check `http://localhost:3100/api/health`;
- check `http://localhost:3100`;
- preserve logs with secrets redacted.

### 7.5 GitHub Actions visibility issue

The fork currently has no visible workflow runs/workflows:

> fork 当前 CI 不可见或未触发

Required next validation work:

- enable or add fork CI only with user authorization;
- report Actions visibility explicitly instead of guessing success;
- do not treat upstream `paperclipai/paperclip` CI or maintainer review as a fork product-main blocker by default.

### 7.6 No-release/no-tag verification

For this document and the runtime adapter design phase:

- no push;
- no tag push;
- no GitHub Release creation/modification;
- no merge PR.

Before finalizing implementation tasks, verify with git status/diff and, if needed, read-only GitHub API queries.

### 7.7 Secret scan

Before any commit/push authorization:

- scan changed files for token/password/API key/connection string patterns;
- expected benign hits may include policy text saying not to print secrets;
- no actual secret values should appear;
- redact any accidental secret-like value in reports.

### 7.8 Git cleanliness

For `/home/siyuah/workspace/123` future-development docs:

```sh
test -f 3.0/future_development/PAPERCLIP_DARK_FACTORY_RUNTIME_ADAPTER_INTEGRATION_PLAN.md
python3 tools/validate_v3_bundle.py
git diff --check
find . -type d -name __pycache__ -prune -print
find . -type d -name __pycache__ -prune -exec rm -rf {} +
git status -sb
git diff --stat
git diff --name-status
```

Expected result for this planning task:

- new document exists;
- git diff includes the new document and index/task doc updates;
- validation passes or failure cause is explicitly reported;
- no cache/dist/node_modules/DB/secret artifacts are introduced.

---

## 8. Security / Secrets / Data Handling

- No real secrets in repo.
- Do not read, print, log, commit, or submit token/password/API key/connection string values.
- Adapter credentials must come only through configured secret path in future implementation.
- Do not place real Dark Factory credentials in Paperclip plugin DB, adapter config examples, docs, tests, fixtures, or logs.
- Projection DB cannot store real Journal contents as truth.
- Receipts/cursors must not contain secret payloads.
- Use correlation IDs, receipt IDs, cursor IDs, and redacted references rather than raw credential-bearing payloads.
- Plugin HTTP/fetch and future webhook/event paths require SSRF, signature, replay, timeout, and retention review before real network integration.
- Any future user-facing logs must distinguish:
  - authoritative Journal-backed receipt;
  - projection/cache view;
  - operator request/intention;
  - adapter runtime status;
  - non-authoritative UI summary.

---

## 9. Open Questions

1. fork CI 如何启用？
   - Current status: fork 当前 CI 不可见或未触发.
   - Need user authorization to add/enable workflows or configure fork Actions.

2. 是否授权安装/provision PostgreSQL native dependencies？
   - Needed if local root tests/dev smoke remain blocked by embedded PostgreSQL/native dependencies.
   - No `sudo` or system package install without explicit authorization.

3. 是否采用 Docker 作为 canonical smoke？
   - Docker/Compose may avoid host native PostgreSQL blockers.
   - Need Docker availability check and user authorization before relying on it as canonical smoke.

4. runtime adapter 是否作为 external adapter plugin 还是 fork-internal adapter？
   - External adapter path improves product extensibility and aligns with Paperclip adapter manager.
   - Fork-internal adapter path may reduce initial integration friction.
   - Recommendation: start fork-internal/mock if faster, but keep contract compatible with external adapter manager.

5. Journal cursor/receipt schema 的最小稳定契约是什么？
   - Need to define required fields: run ID, issue ID, request ID/idempotency key, receipt ID, cursor, sequence number, Journal ref, status, timestamp, replay/rebuild marker, and redaction rules.

6. 是否需要用户授权创建 issue/roadmap task？
   - This document does not authorize creating GitHub Issues, Paperclip Issues, roadmap tasks, PR merges, or release artifacts.
   - If the next step needs issue creation, ask for explicit authorization.

---

## 10. Concrete Next Tasks

### P0: CI visibility / runtime blocker unblock

- Confirm fork Actions/workflows visibility for `siyuah/paperclip`.
- If user authorizes, add/enable minimal CI on fork product-main.
- Document current blocker as: fork 当前 CI 不可见或未触发.
- Decide whether to unblock local root tests through native PostgreSQL provisioning or Docker/Compose smoke.

### P0: adapter contract design doc

- Draft a fork-local adapter contract mapping:
  - Paperclip `AdapterExecutionContext`;
  - Dark Factory request envelope;
  - idempotency key;
  - Journal cursor;
  - receipt;
  - `AdapterExecutionResult.resultJson` and run event metadata.
- Mark all Issue/Task model or lifecycle changes as architecture-review-required.

### P1: mock adapter skeleton

- Implement a mock Dark Factory runtime adapter in `siyuah/paperclip` fork only.
- Do not connect to real Dark Factory.
- Do not store or print secrets.
- Return Journal-backed mock receipts/cursors through bounded metadata.

### P1: Journal receipt simulator

- Create fixture-based simulator for:
  - normal request/receipt;
  - duplicate request idempotency;
  - out-of-order callback;
  - missing cursor gap;
  - stale projection;
  - replay/rebuild.

### P1: smoke harness

- Build direct adapter tests and plugin+adapter smoke harness.
- Validate targeted plugin test/typecheck/build.
- Run root typecheck/build/test when runtime blockers are resolved.
- Add Docker/Compose smoke if authorized.

### P2: UI operator workflow

- Extend projection UI only after adapter contract stabilizes.
- Show provider health, degraded/blocked/stale state, receipt/cursor, and rehydrate request status.
- Keep disclaimer visible: projection-only; Dark Factory Journal remains truth source.
- Do not add Task/Issue main model fields without separate review.

### P2: upstream contribution assessment

- Evaluate whether projection plugin, adapter contract, or generic runtime adapter improvements should be proposed upstream.
- Mark this as **可选上游贡献路径**.
- Do not block fork product-main on `paperclipai/paperclip` maintainer review unless user explicitly requests it.
