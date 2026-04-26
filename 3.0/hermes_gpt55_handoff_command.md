# Hermes + GPT-5.5 交接命令

你现在接手 /home/siyuah/workspace/123 仓库中的 Paperclip × Dark Factory V3/V3.1 文档收尾工作。

请严格遵守以下边界：

- 使用中文报告。
- 不创建 tag。
- 不创建 GitHub Release。
- 不 push。
- 不读取、打印、保存任何 token / secret / password / API key / connection string。
- 不修改 V3.0 binding protocol contract 的语义。
- 不把 Phoenix Runtime 写成第二套 Paperclip control plane。
- 不把 MemorySidecar 字段塞进 Paperclip Task 主模型。
- 不让 Bridge / Adapter 成为第二 truth source。
- 不把具体模型名写成协议 MUST。
- 不提交 `__pycache__`、timestamp-only consistency report 变化或临时生成物。

当前已知状态：

- 仓库路径：`/home/siyuah/workspace/123`
- 分支：`main`
- 本地 HEAD：`11f9167 Add V3.1 roadmap backlog`
- `origin/main`：`16503a4`
- 本地 `main` 已领先远端 1 个提交。
- 已有提交 `11f9167` 内容：
  - 新增 `3.0/V3_1_BACKLOG_AND_IMPLEMENTATION_ROADMAP.md`
  - 更新 `3.0/V3_IMPLEMENTATION_ENTRYPOINT.md`
  - 更新 `README.md`
  - 更新 `paperclip_darkfactory_v3_0_bundle_manifest.yaml`
- 当前仍有 1 个未提交改动：
  - `3.0/V3_1_BACKLOG_AND_IMPLEMENTATION_ROADMAP.md`

当前未提交改动的意图：

- 给 roadmap 增加边界补强句：
  - Phoenix Runtime 不是第二套 Paperclip control plane；
  - MemorySidecar 字段不得塞进 Paperclip Task 主模型；
  - Bridge / Adapter 不得成为第二 truth source；
  - 具体模型名不得写成协议 MUST。
- 但该改动同时去掉了几处反引号，需要修正格式后再提交。

上一个检查结果：

- `make validate-v3` 已通过：
  - `status: pass`
  - `checks: 12`
  - `errors: 0`
  - `warnings: 0`
- 使用 clean-stash 方式运行 `make test-v3-contracts` 已通过：
  - `Ran 71 tests`
  - `OK`
- 直接在 dirty worktree 下跑完整合同测试可能因 clean-git release/evidence gate 失败，这是预期现象，不要修改 release gate。
- stash 已恢复并清空。
- `__pycache__` 已清理。
- consistency report timestamp-only 变化已还原。
- `git diff --check` 已通过。

你的任务：

1. 检查当前仓库状态。
2. 修正 `3.0/V3_1_BACKLOG_AND_IMPLEMENTATION_ROADMAP.md` 的格式。
3. 保留边界补强句。
4. 如需要，更新 manifest。
5. 运行验证。
6. 清理生成物。
7. 提交边界补强改动。
8. 最终用中文报告结果。
9. 不 push。

---

## 1. 检查当前状态

```bash
cd /home/siyuah/workspace/123

git status -sb
git status --short
git branch --show-current
git rev-parse --short HEAD
git rev-parse --short origin/main
git log --oneline -5 --decorate
git diff --stat
git diff -- 3.0/V3_1_BACKLOG_AND_IMPLEMENTATION_ROADMAP.md
```

预期大致为：

```text
## main...origin/main [ahead 1]
 M 3.0/V3_1_BACKLOG_AND_IMPLEMENTATION_ROADMAP.md
```

如果出现其它未提交文件，尤其是 schema、OpenAPI、event contracts、golden timelines、runtime Python、tests、release report、`__pycache__` 或临时生成物，请停止并报告，不要覆盖。

---

## 2. 修正 roadmap 文档格式并保留边界补强

只允许编辑：

```text
3.0/V3_1_BACKLOG_AND_IMPLEMENTATION_ROADMAP.md
```

请确保文件开头是：

```markdown
# V3.1 Backlog and Implementation Roadmap

状态: informative roadmap / backlog
适用基线: Paperclip × Dark Factory V3.0 `agent-control-r1`
protocolReleaseTag: `v3.0-agent-control-r1`
```

请确保第 1 节边界段落包含：

```markdown
V3.0 `agent-control-r1` **保持不变**。任何进入 V3.1 的候选事项，必须先明确是否触及 binding artifacts；如果触及，需要在独立 V3.1 设计、测试和 release gate 中同步推进，不能在 V3.0 文档中暗改合同。

额外边界：Phoenix Runtime 不是第二套 Paperclip control plane；MemorySidecar 字段不得塞进 Paperclip Task 主模型；Bridge / Adapter 不得成为第二 truth source；具体模型名不得写成协议 MUST。
```

也就是说：

- 恢复 `agent-control-r1` 的反引号；
- 恢复 `v3.0-agent-control-r1` 的反引号；
- 保留新增的“额外边界”一句；
- 不改其它 V3.0 binding artifacts；
- 不新增 schema / OpenAPI / event contracts / tests / golden timelines。

---

## 3. 检查 roadmap 内容边界

确认 `3.0/V3_1_BACKLOG_AND_IMPLEMENTATION_ROADMAP.md` 仍满足：

- 状态是 `informative roadmap / backlog`；
- 适用基线是 Paperclip × Dark Factory V3.0 `agent-control-r1`；
- 包含 `protocolReleaseTag: v3.0-agent-control-r1` 或带反引号形式；
- 明确 V3.0 `agent-control-r1` 保持不变；
- 明确本文不是 V3.0 binding spec，不替代 release-gated artifacts；
- Phoenix Runtime 不是第二套 Paperclip control plane；
- MemorySidecar 字段不进入 Paperclip Task 主模型；
- Bridge / Adapter 不是第二 truth source；
- 具体模型名不是协议 MUST。

确认 P0/P1/P2 backlog 均包含：背景、不做的风险、建议变更范围、是否触及 binding artifacts、需要同步更新的文件类型、验收方式、推荐阶段。

确认 backlog 至少覆盖：provider health 与 circuit breaker observability schema；RunAttempt `provider_role` / `model_role` / `failure_class` / `retryable` / `fallback_triggered` 字段边界；MemorySidecar metadata schema、storage profile、KG edge schema、DiaryStore retention policy；PhoenixRecover 重启恢复 smoke test / golden timeline；degraded mode operator UI 与 audit trail；Bridge reconciliation cursor 跨系统一致性测试；历史 V2.9 companion-bound 资料归档为带 normativity metadata 的 reference bundle。

---

## 4. 更新 manifest 并验证

```bash
make manifest-v3
make validate-v3
```

要求：

- `make validate-v3` 必须通过；
- 预期为 12 checks / 0 errors / 0 warnings；
- 如果 `make manifest-v3` 更新了 `paperclip_darkfactory_v3_0_bundle_manifest.yaml`，请保留该 manifest 更新；
- 如果只产生 timestamp-only consistency report 变化，后续清理时还原。

---

## 5. 审查 diff

```bash
git diff --stat
git diff -- 3.0/V3_1_BACKLOG_AND_IMPLEMENTATION_ROADMAP.md paperclip_darkfactory_v3_0_bundle_manifest.yaml
git diff --check
```

确认：

- roadmap 只恢复反引号格式并保留“额外边界”一句；
- manifest 如变化，仅为 roadmap 的 sha256 / bytes 跟随更新；
- roadmap 仍位于 `informativeOutOfBundle`；
- 没有把 roadmap 加入 release-gated binding files；
- 没有修改 V3.0 core spec、schema、OpenAPI、event contracts、golden timelines 或 tests；
- `git diff --check` 通过。

---

## 6. 运行合同测试

由于当前有未提交文档 diff，直接运行 `make test-v3-contracts` 可能受 clean-git release/evidence gate 影响。请用临时 stash 验证 clean committed baseline，同时保证 stash 被恢复。

```bash
STASH_BEFORE=$(git stash list | wc -l)

git stash push --include-untracked -m v3_roadmap_boundary_tmp

make test-v3-contracts
TEST_RC=$?

rm -rf dark_factory_v3/__pycache__ tests/__pycache__ tools/__pycache__

git checkout -- \
  paperclip_darkfactory_v3_0_consistency_report.json \
  paperclip_darkfactory_v3_0_consistency_report.md

git stash pop
POP_RC=$?

STASH_AFTER=$(git stash list | wc -l)

printf 'TEST_RC=%s\nPOP_RC=%s\nSTASH_BEFORE=%s\nSTASH_AFTER=%s\n' \
  "$TEST_RC" "$POP_RC" "$STASH_BEFORE" "$STASH_AFTER"

test "$TEST_RC" = "0"
test "$POP_RC" = "0"
test "$STASH_BEFORE" = "$STASH_AFTER"
```

预期：

- `make test-v3-contracts` 通过；
- 71 tests OK；
- `TEST_RC=0`；
- `POP_RC=0`；
- `STASH_BEFORE == STASH_AFTER`。

如果 `git stash pop` 因 consistency report 变化冲突，请执行：

```bash
git checkout -- \
  paperclip_darkfactory_v3_0_consistency_report.json \
  paperclip_darkfactory_v3_0_consistency_report.md

git stash pop
```

然后重新确认：

```bash
git stash list
git status -sb
```

不要留下 stash 残留。

---

## 7. 清理生成物并最终检查

```bash
rm -rf dark_factory_v3/__pycache__ tests/__pycache__ tools/__pycache__

git checkout -- \
  paperclip_darkfactory_v3_0_consistency_report.json \
  paperclip_darkfactory_v3_0_consistency_report.md

git status -sb
git status --short
git diff --stat
git diff --check
```

预期只剩：

```text
 M 3.0/V3_1_BACKLOG_AND_IMPLEMENTATION_ROADMAP.md
```

如果 `make manifest-v3` 更新了 manifest，则预期可以是：

```text
 M 3.0/V3_1_BACKLOG_AND_IMPLEMENTATION_ROADMAP.md
 M paperclip_darkfactory_v3_0_bundle_manifest.yaml
```

不要留下 `__pycache__`、release report timestamp-only 变化、临时文件或 stash 残留。

---

## 8. 提交边界补强

如果以上全部通过，请提交当前未提交改动。

如果只改了 roadmap：

```bash
git add 3.0/V3_1_BACKLOG_AND_IMPLEMENTATION_ROADMAP.md
git commit -m "Clarify V3.1 roadmap protocol boundaries"
```

如果 manifest 也因 hash/bytes 更新而变化：

```bash
git add \
  3.0/V3_1_BACKLOG_AND_IMPLEMENTATION_ROADMAP.md \
  paperclip_darkfactory_v3_0_bundle_manifest.yaml

git commit -m "Clarify V3.1 roadmap protocol boundaries"
```

提交后检查：

```bash
git status -sb
git log --oneline -5 --decorate
```

预期：

- `main` 领先 `origin/main` 2 个提交；
- 工作区干净；
- 不 push。

---

## 9. 最终报告

请用中文报告：

- 是否已提交；
- 新提交 hash；
- 当前 HEAD；
- 当前 `origin/main`；
- `make validate-v3` 是否通过；
- clean-stash 方式的 `make test-v3-contracts` 是否通过；
- 最终 `git status -sb`；
- 是否还有 stash 残留；
- 确认没有创建 tag；
- 确认没有创建 GitHub Release；
- 确认没有 push。

最终报告格式建议：

```text
已完成检查与提交。

提交：
- 新提交：<hash> Clarify V3.1 roadmap protocol boundaries
- 当前 HEAD：<hash>
- origin/main：16503a4
- main 状态：ahead 2

验证：
- make validate-v3：通过，12 checks / 0 errors / 0 warnings
- make test-v3-contracts：通过，71 tests OK，使用 clean-stash 方式验证
- git diff --check：通过

最终状态：
- git status -sb：<输出>
- stash 残留：无
- __pycache__：已清理
- consistency report timestamp-only 变化：已还原

确认：
- 没有创建 tag
- 没有创建 GitHub Release
- 没有 push
- 没有修改 V3.0 binding protocol contract 语义
```
