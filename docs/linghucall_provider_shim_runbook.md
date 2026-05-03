# LinghuCall Provider Shim Runbook

Status: operator-gated alpha  
Scope: Dark Factory V3 external-runs shim backed by LinghuCall `gpt-5.5`  
Date: 2026-05-03

## Purpose

`api.linghucall.net` is an OpenAI-compatible model gateway, not a Dark Factory
provider endpoint. The Paperclip bridge expects the Dark Factory external-runs
contract under `/api/*`, so the LinghuCall provider shim exposes:

- `GET /api/health`
- `POST /api/external-runs`
- `GET /api/external-runs/{runId}`
- `POST /api/external-runs/{runId}:park`
- `POST /api/external-runs/{runId}:rehydrate`
- `GET /api/external-runs/{runId}/route-decisions`

The shim calls LinghuCall `/v1/chat/completions` during run creation and records
only redacted provider evidence in its JSONL journal.

## Boundary Rules

- Dark Factory Journal remains truth source.
- The shim never returns or logs resolved credential values.
- `LINGHUCALL_API_KEY` must only exist in the operator shell.
- The bridge-facing API key is separate from the LinghuCall provider key.
- The shim does not mark Paperclip terminal state as advanced.
- This is alpha infrastructure, not a production control plane.

## One-Command Gated Test

From an operator shell with a valid LinghuCall key:

```bash
cd /home/siyuah/workspace/123
export LINGHUCALL_API_KEY="<set in shell only>"
export LINGHUCALL_MODEL="gpt-5.5"
tools/run_linghucall_provider_shim_gate.sh
```

The script:

1. starts `linghucall_provider_shim.py` on `127.0.0.1:9791`,
2. creates a temporary bridge-facing API key if none is set,
3. sets `DARK_FACTORY_REMOTE_ENDPOINT=http://127.0.0.1:9791`,
4. runs `pnpm gate:provider-status -- --require-ready`,
5. runs `pnpm test -- tests/remote-gated-integration.spec.ts`.

It does not print the LinghuCall key.

## Manual Startup

```bash
cd /home/siyuah/workspace/123
export LINGHUCALL_API_KEY="<set in shell only>"
export LINGHUCALL_MODEL="gpt-5.5"
export DF_API_KEY="<bridge-facing temporary key>"
.venv312/bin/python linghucall_provider_shim.py --host 127.0.0.1 --port 9791
```

Then in the Paperclip bridge plugin shell:

```bash
cd /home/siyuah/workspace/paperclip_upstream/packages/plugins/integrations/dark-factory-bridge
export DARK_FACTORY_REMOTE_INTEGRATION=1
export DARK_FACTORY_REMOTE_ENDPOINT="http://127.0.0.1:9791"
export DARK_FACTORY_REMOTE_API_KEY_ENV="DARK_FACTORY_LINGHUCALL_SHIM_BRIDGE_KEY"
export DARK_FACTORY_LINGHUCALL_SHIM_BRIDGE_KEY="<same bridge-facing temporary key>"
pnpm gate:provider-status -- --require-ready
pnpm test -- tests/remote-gated-integration.spec.ts
```

## Local Verification Without LinghuCall Key

The unit tests use a fake LinghuCall client and do not contact the real provider:

```bash
cd /home/siyuah/workspace/123
.venv312/bin/python -m pytest tests/test_linghucall_provider_shim.py -q
python3 tools/validate_v3_bundle.py
```

Expected result:

- shim tests pass,
- V3 bundle validation remains 12/12 pass,
- no V3 binding artifacts are modified.
