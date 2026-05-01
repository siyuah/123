#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
# Set DF_API_KEY to pin the server API key. If unset, server.py generates one
# and prints it at startup. DF_PORT defaults to 9701.
exec python3 server.py --port "${DF_PORT:-9701}" "$@"
