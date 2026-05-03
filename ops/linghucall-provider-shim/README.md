# LinghuCall Provider Shim Operations

Status: alpha operationalization assets  
Scope: supervised local service for `linghucall_provider_shim.py`  
Date: 2026-05-03

## Purpose

These files turn the LinghuCall-backed Dark Factory external-runs shim from a
manual one-shot command into a repeatable operator-managed service.

The shim still keeps these boundaries:

- Dark Factory Journal remains truth source.
- LinghuCall is an OpenAI-compatible chat backend behind the shim, not a direct
  Dark Factory `/api/*` provider endpoint.
- Credential values stay in the operator environment or secret files only.
- The service does not modify Paperclip Task/Issue main models.

## Files

- `linghucall-provider-shim.service`: systemd user service template.
- `linghucall-provider-shim.env.example`: environment template with placeholders
  only.
- `tools/check_linghucall_provider_shim_health.py`: healthcheck helper.
- `tools/verify_linghucall_provider_shim_ops.py`: offline operations verifier.

## User Service Install

From the `123` repository:

```bash
mkdir -p ~/.config/systemd/user ~/.config/dark-factory
cp ops/linghucall-provider-shim/linghucall-provider-shim.service ~/.config/systemd/user/
cp ops/linghucall-provider-shim/linghucall-provider-shim.env.example ~/.config/dark-factory/linghucall-provider-shim.env
chmod 600 ~/.config/dark-factory/linghucall-provider-shim.env
```

Edit `~/.config/dark-factory/linghucall-provider-shim.env` in the operator
shell or secret manager. Keep credential values out of git, docs, screenshots,
and logs.

Create the bridge-facing key file referenced by `DF_API_KEY_FILE`:

```bash
printf '%s\n' '<bridge-facing random key>' > ~/.config/dark-factory/linghucall-shim-bridge.key
chmod 600 ~/.config/dark-factory/linghucall-shim-bridge.key
```

Start the service:

```bash
systemctl --user daemon-reload
systemctl --user enable --now linghucall-provider-shim.service
systemctl --user status linghucall-provider-shim.service
```

## Healthcheck

```bash
cd /home/siyuah/workspace/123
.venv312/bin/python tools/check_linghucall_provider_shim_health.py \
  --endpoint http://127.0.0.1:9791 \
  --require-ready
```

The healthcheck does not send credentials. It reads only `/api/health`.

## Paperclip Bridge Gate Against Service

Use the bridge-facing key from `DF_API_KEY_FILE`, not the LinghuCall provider
credential:

```bash
cd /home/siyuah/workspace/paperclip_upstream/packages/plugins/integrations/dark-factory-bridge
export DARK_FACTORY_REMOTE_INTEGRATION=1
export DARK_FACTORY_REMOTE_ENDPOINT=http://127.0.0.1:9791
export DARK_FACTORY_REMOTE_API_KEY_ENV=DARK_FACTORY_LINGHUCALL_SHIM_BRIDGE_KEY
export DARK_FACTORY_LINGHUCALL_SHIM_BRIDGE_KEY='<same bridge-facing key>'
pnpm gate:provider-status -- --require-ready
pnpm test -- tests/remote-gated-integration.spec.ts
```

## Rollback

```bash
systemctl --user stop linghucall-provider-shim.service
systemctl --user disable linghucall-provider-shim.service
unset DARK_FACTORY_REMOTE_INTEGRATION
unset DARK_FACTORY_REMOTE_ENDPOINT
unset DARK_FACTORY_REMOTE_API_KEY_ENV
unset DARK_FACTORY_LINGHUCALL_SHIM_BRIDGE_KEY
```

Do not mutate Paperclip Task/Issue state during rollback. Reconcile against the
Dark Factory Journal before retrying failed runs.

## Offline Verification

```bash
cd /home/siyuah/workspace/123
.venv312/bin/python tools/verify_linghucall_provider_shim_ops.py
```

Expected result: all checks pass, with no credential values printed.
