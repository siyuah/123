#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
exec python3 server.py --port "${DF_PORT:-9701}" "$@"
