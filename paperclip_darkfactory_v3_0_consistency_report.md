# V3.0 Bundle Consistency Check

protocolReleaseTag: `v3.0-agent-control-r1`
checkedAt: `2026-04-25T12:34:10Z`
status: `pass`

errors: 0
warnings: 0
checks: 12

## Checks

- `manifest-path-exists`: **pass** — all manifest paths exist
  - details: `{"checkedFiles": 42}`
- `manifest-unique-paths`: **pass** — manifest paths are unique
- `manifest-sha256-match`: **pass** — manifest sha256 values match disk
- `tracked-files-classified-by-manifest`: **pass** — tracked files are listed or explicitly excluded
- `event-enum-contract-parity`: **pass** — event canonical names match between enum and event contracts
- `state-matrix-enum-parity`: **pass** — state transition matrix values are declared in core enums
- `release-blocker-scenario-traceability`: **pass** — every release-blocker scenario is mapped in traceability
- `golden-timeline-exists`: **pass** — all referenced golden timelines exist
  - details: `{"goldenTimelineRefs": ["tests/golden_timelines/v3_0/GL-V30-lineage-reopen-blocks-consumer.jsonl", "tests/golden_timelines/v3_0/GL-V30-manual-park-rehydrate.jsonl", "tests/golden_timelines/v3_0/GL-V30-memory-injection-denied.jsonl", "tests/golden_timelines/v3_0/GL-V30-repair-verified-success.jsonl", "tests/golden_timelines/v3_0/GL-V30-routing-chat.jsonl", "tests/golden_timelines/v3_0/GL-V30-routing-code.jsonl", "tests/golden_timelines/v3_0/GL-V30-routing-vision.jsonl"]}`
- `golden-timeline-event-contract-parity`: **pass** — golden timelines use canonical event names, event versions, and protocol tags
- `openapi-parse-and-protocol-tag:paperclip_darkfactory_v3_0_external_runs.openapi.yaml`: **pass** — OpenAPI parses and contains protocol release tag
  - details: `{"protocolReleaseTagOccurrences": 14}`
- `openapi-parse-and-protocol-tag:paperclip_darkfactory_v3_0_memory.openapi.yaml`: **pass** — OpenAPI parses and contains protocol release tag
  - details: `{"protocolReleaseTagOccurrences": 8}`
- `json-schema-parse`: **pass** — core object JSON Schema parses

No blocking consistency issues detected by the automated lightweight checker.
