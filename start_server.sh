#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
# Set DF_API_KEY_FILE for Docker/Kubernetes secrets, or DF_API_KEY for local
# development. If neither is set, server.py generates a temporary key and
# prints it at startup. DF_PORT defaults to 9701.
exec python3 server.py --port "${DF_PORT:-9701}" "$@"
