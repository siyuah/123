#!/usr/bin/env python3
"""Healthcheck for the LinghuCall-backed Dark Factory provider shim."""
from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import UTC, datetime
from typing import Any


def utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def check_health(endpoint: str, timeout: float) -> dict[str, Any]:
    normalized = endpoint.rstrip("/")
    health_url = f"{normalized}/api/health"
    result: dict[str, Any] = {
        "schemaVersion": 1,
        "reportType": "linghucall-provider-shim-health",
        "checkedAt": utc_now(),
        "endpointHost": urllib.parse.urlparse(normalized).netloc,
        "ok": False,
        "credentialValuesRedacted": True,
    }
    try:
        with urllib.request.urlopen(health_url, timeout=timeout) as response:
            body = json.loads(response.read().decode("utf-8"))
        result.update(
            {
                "ok": bool(body.get("ok")),
                "status": "ready" if body.get("ok") else "not_ready",
                "httpStatus": response.status,
                "protocolReleaseTag": body.get("protocolReleaseTag"),
                "providerKind": (body.get("provider") or {}).get("kind"),
                "providerCredentialValueRedacted": (body.get("provider") or {}).get("credentialValueRedacted") is True,
                "journal": body.get("journal"),
                "events": body.get("events"),
            }
        )
    except urllib.error.HTTPError as exc:
        result.update({"status": "http_error", "httpStatus": exc.code, "message": exc.reason})
    except Exception as exc:  # pragma: no cover - exact platform errors differ
        result.update({"status": "unreachable", "message": str(exc)})
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Check LinghuCall provider shim health")
    parser.add_argument("--endpoint", default="http://127.0.0.1:9791", help="Shim base endpoint.")
    parser.add_argument("--timeout", default=3.0, type=float, help="Healthcheck timeout in seconds.")
    parser.add_argument("--require-ready", action="store_true", help="Exit non-zero unless shim is ready.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    report = check_health(args.endpoint, args.timeout)
    print(json.dumps(report, indent=2, sort_keys=True))
    if args.require_ready and not report.get("ok"):
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
