# Dark Factory Security Boundaries

Status: informative design note  
Scope: internal preview, Paperclip bridge, LinghuCall provider shim, and future scoped-token planning  
Protocol release tag: `v3.0-agent-control-r1`

This document records the API security boundary used by the current Dark
Factory internal preview and the planned direction for scoped authorization. It
does not change V3 binding artifacts and does not introduce token issuance.

## Goals

- Keep Dark Factory Journal as the truth source.
- Separate public health checks, bridge/provider traffic, and operator-only
  secret/configuration surfaces.
- Preserve projection boundaries: derived views are non-authoritative.
- Avoid turning the provider shim or Paperclip bridge into a second control
  plane.
- Prevent credential values from entering repository files, generated docs,
  logs, handoff packets, or review evidence.

## Three API Layers

| Layer | Audience | Authentication | Mutates Journal | Allowed Surface |
| --- | --- | --- | --- | --- |
| Public health/readiness | local health probes, reverse proxies | none | no | `GET /api/health`, static readiness metadata |
| Bridge/provider shim | Paperclip bridge and internal provider shim clients | bridge-facing API key today; scoped token later | yes, only through contract routes | external runs, route decisions, provider-health projection, journal-derived read views |
| Operator-only local control | human operator on the host | OS account, private files, systemd/user service controls | controlled operational actions only | env files, service files, backup/retain/restore commands, provider credential references |

## Layer 1: Public Health And Readiness

`GET /api/health` remains open so local probes, reverse proxies, and service
managers can check liveness without needing credentials.

Rules:

- It must not expose credential values.
- It must not mutate Journal state.
- It may report coarse readiness, protocol release tag, and redacted provider
  credential presence.
- It must not imply production readiness by itself.

## Layer 2: Bridge And Provider Shim Traffic

All non-health HTTP routes require the bridge-facing API key in `X-API-Key` in
the current implementation. That key is distinct from any provider credential.
The LinghuCall shim follows the same separation: one bridge-facing key protects
the Dark Factory-compatible API, while the provider credential stays operator
managed.

Allowed actions:

- Create and read external runs through the V3 external-runs contract.
- Park and rehydrate runs through explicit contract routes.
- Read route-decision and provider-health projections.
- Run Paperclip gated integration checks against an operator-provided endpoint.

Forbidden actions:

- Printing or returning resolved provider credentials.
- Marking Paperclip terminal state as advanced from a non-authoritative
  projection.
- Treating route decisions, provider health, or structured facts as the Journal
  truth source.
- Adding a second control plane outside the Journal-backed V3 runtime.

## Layer 3: Operator-Only Local Control

Operator-only files and actions stay outside the API surface:

- `~/.config/dark-factory/linghucall-provider-shim.env`
- `~/.config/dark-factory/linghucall-shim-bridge.key`
- local systemd user-service lifecycle commands
- JSONL journal backup, retain, and restore commands
- local reverse-proxy and TLS configuration

Repository rules:

- Example files may describe variable names and file paths.
- Real credential values must not be committed.
- Handoff packets may reference evidence paths, not secret file contents.
- Progress archives may record pass/fail results, not credential material.

## Current Authentication Model

The current implementation uses a single bridge-facing API key for non-health
routes. It is simple and sufficient for the internal alpha boundary, but it is
coarse-grained.

Current guarantees:

- Health is open and non-mutating.
- Non-health routes require `X-API-Key`.
- Provider credentials are separate from bridge credentials.
- Operator service verification checks file permissions without reading file
  contents.
- Remote gated Paperclip tests contact the provider only through the shim.

Current limitations:

- One key cannot express least-privilege scopes.
- Key rotation is operator-managed rather than protocol-managed.
- Audit records can prove a request happened, but not a fine-grained delegated
  authorization decision.

## Scoped Token Design Preview

Scoped tokens are a design preview only. No token issuance, validation, storage,
or migration is implemented in this batch.

Candidate scopes:

| Scope | Purpose |
| --- | --- |
| `health:read` | read health/readiness metadata |
| `runs:create` | create external runs |
| `runs:read` | read run and route-decision projections |
| `runs:park` | park a run at an explicit manual gate |
| `runs:rehydrate` | rehydrate a parked run |
| `journal:read` | read derived Journal projections |
| `journal:backup` | request or verify backup evidence |
| `journal:retain` | request retention evidence |
| `provider:gate` | run gated provider readiness checks |
| `handoff:read` | generate non-authoritative handoff packets |

Candidate token claims:

```json
{
  "aud": "dark-factory-v3",
  "exp": "short-lived timestamp",
  "issuer": "operator-controlled issuer",
  "jti": "opaque request id",
  "scope": ["runs:create", "runs:read"],
  "sub": "paperclip-bridge"
}
```

Open design questions before implementation:

- Whether the issuer is local-only, Paperclip-hosted, or operator-managed.
- Whether tokens should be bearer tokens, signed envelopes, or mTLS-bound
  session capabilities.
- How rotation evidence should be recorded without storing credential values.
- How scope-denied guardrail events should be represented in V3 event contracts.

## Guardrails

High-risk operations stay blocked or operator-only until explicit design review.

- Journal deletion is blocked by guardrail and must not mutate the Journal.
- Backup and retention are local operator workflows, not bridge privileges.
- Restore requires explicit operator action and JSONL validation.
- Provider fallback and recovery decisions remain derived projections unless
  recorded as Journal events.

## Handoff And Evidence Rules

Handoff packets and progress archives are review aids:

- They may include git commit IDs, validation summaries, test counts, and
  evidence file paths.
- They must not include credential values or raw operator env files.
- They must state `authoritative: false` when summarizing projections.
- They must preserve `Dark Factory Journal remains truth source`.

## Verification Commands

```bash
cd /home/siyuah/workspace/123
.venv/bin/python tools/validate_v3_bundle.py
.venv/bin/python tools/df_handoff_packet.py --json --no-paperclip-status
.venv/bin/python -m pytest tests/test_df_handoff_packet.py -v
```

Expected result:

- V3 bundle validation passes.
- Handoff packet generation succeeds without reading credential files.
- Security boundary tests pass.
