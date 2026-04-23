# Paperclip × Dark Factory V2.9 Companion-bound Bundle

本 bundle 采用 **“主文档 + 内置短附录 + 独立 impl 包 + machine-readable starter artifacts”** 的组织方式。

## 建议阅读顺序

1. `paperclip_darkfactory_revised_framework_v2_9_companion_bound.md`
2. `paperclip_darkfactory_v2_9_impl_pack.md`
3. `paperclip_darkfactory_v2_9_external_runs.openapi.yaml`
4. `paperclip_darkfactory_v2_9_core_objects.schema.json`
5. `paperclip_darkfactory_v2_9_runtime_config_registry.yaml`
6. `paperclip_darkfactory_v2_9_test_asset_spec.md`
7. `paperclip_darkfactory_v2_9_contract_consistency_check.py`
8. `golden_timelines/*.jsonl`

## 文件清单

| 文件 | 角色 | 规范地位 | 是否进入 CI 一致性校验 |
|---|---|---|---|
| `paperclip_darkfactory_revised_framework_v2_9_companion_bound.md` | 主规范 + 内置短附录 | binding | yes |
| `paperclip_darkfactory_v2_9_impl_pack.md` | 独立 impl 包总览 | informative-with-binding-references | partial |
| `paperclip_darkfactory_v2_9_external_runs.openapi.yaml` | 控制面/外部接口 contract | binding-on-covered-fields | yes |
| `paperclip_darkfactory_v2_9_event_contracts.yaml` | 生命周期/能力/认证/级联事件 contract | binding-on-covered-fields | yes |
| `paperclip_darkfactory_v2_9_core_enums.yaml` | 统一枚举字面量 | binding | yes |
| `paperclip_darkfactory_v2_9_core_objects.schema.json` | 核心对象 JSON Schema | binding-on-covered-fields | yes |
| `paperclip_darkfactory_v2_9_runtime_config_registry.yaml` | runtime config registry | binding | yes |
| `paperclip_darkfactory_v2_9_inheritance_matrix.csv` | V2.8/V2.9 继承覆盖矩阵 | informative legacy mapping | no |
| `paperclip_darkfactory_v2_9_responsibility_matrix.csv` | 组件职责矩阵 | informative | partial |
| `paperclip_darkfactory_v2_9_storage_mapping.csv` | truth/projection/archive 存储映射 | informative | partial |
| `paperclip_darkfactory_v2_9_state_transition_matrix.csv` | 状态迁移矩阵 | binding-on-covered-transitions | yes |
| `paperclip_darkfactory_v2_9_test_asset_spec.md` | 测试资产与 fixture 组织说明 | binding-on-covered-obligations | yes |
| `paperclip_darkfactory_v2_9_contract_consistency_check.py` | contract consistency 自动校验脚本 | release-gate tool | yes |
| `golden_timelines/*.jsonl` | golden timeline 示例资产 | binding-on-covered-obligations | yes |

## 版本绑定

- `protocolReleaseTag = v2.9-companion-bound-r1`
- `normativeVersion = 2.9`
- `companionAppendixVersion = 2.9-companion.1`
- `implPackVersion = 2.9-impl.1`

同名字段/枚举/状态若出现冲突，按主文档正文与其内置附录优先，machine-readable 资产和 impl 文档必须随之更新并通过 CI 一致性校验。

## 规范解释规则

- `binding`：该文件中的同名状态、枚举、字段、规则具有直接规范约束力。
- `binding-on-covered-fields`：文件中已经声明的字段、枚举、状态具有约束力；未声明部分不得被视为协议默认值。
- `binding-on-covered-transitions`：矩阵中已经列出的合法/非法迁移具有约束力，缺失迁移不得被默认解释为允许。
- `binding-on-covered-obligations`：测试资产规范中已经声明的 release-blocking 用例与一致性义务具有约束力。
- `informative`：用于实现参考、职责说明或设计辅助，不单独构成协议语义来源。
- `informative legacy mapping`：仅用于说明 V2.8/V2.9 继承关系，不构成新的 canonical 语义来源，冲突时必须让位于主规范与 machine-readable 资产。
- `release-gate tool`：用于自动校验 binding 资产之间的一致性，本身不定义协议语义，但其失败应阻断发布。

若同名字段/枚举/状态出现冲突，按以下优先级处理：
1. 主文档正文与内置附录
2. `paperclip_darkfactory_v2_9_core_enums.yaml`
3. `paperclip_darkfactory_v2_9_core_objects.schema.json` / `paperclip_darkfactory_v2_9_event_contracts.yaml` / `paperclip_darkfactory_v2_9_external_runs.openapi.yaml`
4. `paperclip_darkfactory_v2_9_impl_pack.md`
5. CSV 矩阵、golden timeline 示例与测试资产说明
6. `paperclip_darkfactory_v2_9_inheritance_matrix.csv`

## 自动校验与示例资产

执行一致性检查：

```bash
python3 paperclip_darkfactory_v2_9_contract_consistency_check.py
```

当前提供的 golden timeline 示例：

- `golden_timelines/GL-V29-manual-park-rehydrate.jsonl`
- `golden_timelines/GL-V29-lineage-reopen-propagation.jsonl`
- `golden_timelines/GL-V29-lineage-certified-clean.jsonl`
- `golden_timelines/GL-V29-lineage-waiver-scoped-consumer-only.jsonl`
- `golden_timelines/GL-V29-lineage-revoked-waiver-does-not-allow-write.jsonl`
- `golden_timelines/GL-V29-capability-exceeded-declared.jsonl`
- `golden_timelines/GL-V29-capability-broker-bypass-attempted.jsonl`
- `golden_timelines/GL-V29-capability-unverifiable-blocked.jsonl`
- `golden_timelines/GL-V29-capsule-preflight-poisoned.jsonl`
- `golden_timelines/GL-V29-capsule-poisoned-retry-blocked.jsonl`
- `golden_timelines/GL-V29-schema-write-fence-reject.jsonl`
