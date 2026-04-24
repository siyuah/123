#!/usr/bin/env python3
"""Refresh V3.0 bundle manifest file sizes and SHA-256 digests."""
from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any, Dict

import yaml  # type: ignore

MANIFEST_PATH = Path("paperclip_darkfactory_v3_0_bundle_manifest.yaml")
SELF_HASH_MODE = "excluded-from-own-digest"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    manifest: Dict[str, Any] = yaml.safe_load(MANIFEST_PATH.read_text(encoding="utf-8"))
    manifest["selfHashMode"] = SELF_HASH_MODE
    generated = ["paperclip_darkfactory_v3_0_consistency_report.md", "paperclip_darkfactory_v3_0_consistency_report.json"]
    excluded = list(dict.fromkeys(manifest.get("excludedFromDigest", []) + [str(MANIFEST_PATH)] + generated))
    manifest["excludedFromDigest"] = excluded
    manifest.setdefault("informativeOutOfBundle", [])

    for entry in manifest.get("files", []):
        rel = entry["path"]
        path = Path(rel)
        if rel in excluded:
            entry["sha256"] = "SELF_HASH_EXCLUDED"
            entry["bytes"] = path.stat().st_size if path.exists() else 0
            continue
        if not path.exists():
            raise FileNotFoundError(rel)
        entry["sha256"] = sha256(path)
        entry["bytes"] = path.stat().st_size

    MANIFEST_PATH.write_text(yaml.safe_dump(manifest, allow_unicode=True, sort_keys=False), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
