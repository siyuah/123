# Dark Factory V3 Internal Preview Runbook

This runbook covers the constrained MVP internal preview deployment. It is not
a full production operating model.

## Transport

Use Caddy as the TLS reverse proxy and keep the FastAPI process on the private
container network. The included `Caddyfile` exposes HTTPS on port `9702` with
Caddy internal certificates for local/private preview.

Start the stack:

```bash
mkdir -p secrets backups
openssl rand -hex 32 > secrets/df_api_key.txt
docker compose up --build
```

Clients should use `https://127.0.0.1:9702` or the private preview hostname.
Health probes may call `GET /api/health` without `X-API-Key`; every other route
must include the configured key.

## Secrets

Preferred order:

1. Docker/Kubernetes secret mounted as a file and passed via `DF_API_KEY_FILE`.
2. Environment variable `DF_API_KEY` for local development only.
3. Generated startup key for temporary manual testing only.

Do not store the API key in plugin namespace state or logs. Bridge production
configuration should carry a secret reference (`apiKeySecretRef`) resolved by
the host environment; inline `apiKey` is limited to local preview.

## Journal Operations

The MVP journal is a single-writer JSONL file on a persistent volume. Back it up
before upgrades and at least daily during preview:

```bash
python3 tools/journal_admin.py backup --journal /data/dark_factory_v3.jsonl --backup-dir /backups
python3 tools/journal_admin.py retain --backup-dir /backups --keep-last 10 --max-age-days 14
```

Restore is explicit and validates JSONL before replacement:

```bash
python3 tools/journal_admin.py restore --backup /backups/dark_factory_v3.20260502T000000Z.jsonl --journal /data/dark_factory_v3.jsonl
```

## Operating Limits

- Run one Dark Factory writer per journal volume.
- Keep the service behind a trusted network boundary or reverse proxy.
- Capture JSON logs from both the server and bridge.
- Treat provider-failure, repair, and archive routes as facade-only in MVP.
