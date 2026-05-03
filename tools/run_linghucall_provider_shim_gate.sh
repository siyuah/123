#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PAPERCLIP_ROOT="${PAPERCLIP_ROOT:-/home/siyuah/workspace/paperclip_upstream}"
PLUGIN_ROOT="$PAPERCLIP_ROOT/packages/plugins/integrations/dark-factory-bridge"
PYTHON_BIN="${PYTHON_BIN:-$ROOT/.venv312/bin/python}"
PORT="${LINGHUCALL_SHIM_PORT:-9791}"
HOST="${LINGHUCALL_SHIM_HOST:-127.0.0.1}"
JOURNAL="${LINGHUCALL_SHIM_JOURNAL:-$ROOT/.dark_factory_http/linghucall_provider_shim.jsonl}"
BRIDGE_KEY_ENV="${DARK_FACTORY_REMOTE_API_KEY_ENV:-DARK_FACTORY_LINGHUCALL_SHIM_BRIDGE_KEY}"

if [[ -z "${LINGHUCALL_API_KEY:-}" ]]; then
  echo "LINGHUCALL_API_KEY is required in the operator shell." >&2
  exit 2
fi

if [[ -z "${!BRIDGE_KEY_ENV:-}" ]]; then
  export "$BRIDGE_KEY_ENV=bridge-$(date +%s)-$RANDOM"
fi

export DF_API_KEY="${!BRIDGE_KEY_ENV}"
export DARK_FACTORY_REMOTE_INTEGRATION=1
export DARK_FACTORY_REMOTE_ENDPOINT="http://$HOST:$PORT"
export DARK_FACTORY_REMOTE_API_KEY_ENV="$BRIDGE_KEY_ENV"
export LINGHUCALL_MODEL="${LINGHUCALL_MODEL:-gpt-5.5}"
export LINGHUCALL_BASE_URL="${LINGHUCALL_BASE_URL:-https://api.linghucall.net/v1}"

mkdir -p "$(dirname "$JOURNAL")"

"$PYTHON_BIN" "$ROOT/linghucall_provider_shim.py" \
  --host "$HOST" \
  --port "$PORT" \
  --journal "$JOURNAL" \
  > "$ROOT/.dark_factory_http/linghucall_provider_shim.log" 2>&1 &
SERVER_PID=$!

cleanup() {
  kill "$SERVER_PID" >/dev/null 2>&1 || true
  wait "$SERVER_PID" >/dev/null 2>&1 || true
}
trap cleanup EXIT

for _ in $(seq 1 80); do
  if curl -fsS "http://$HOST:$PORT/api/health" >/dev/null; then
    break
  fi
  sleep 0.25
done

curl -fsS "http://$HOST:$PORT/api/health" >/dev/null

cd "$PLUGIN_ROOT"
pnpm gate:provider-status -- --require-ready
pnpm test -- tests/remote-gated-integration.spec.ts

echo "LinghuCall provider shim gated test passed."
