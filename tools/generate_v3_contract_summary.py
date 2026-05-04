#!/usr/bin/env python3
"""Generate a deterministic summary of the Dark Factory V3 contract bundle."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import yaml  # type: ignore

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL_RELEASE_TAG = "v3.0-agent-control-r1"

CORE_ENUMS = "paperclip_darkfactory_v3_0_core_enums.yaml"
CORE_OBJECTS_SCHEMA = "paperclip_darkfactory_v3_0_core_objects.schema.json"
EVENT_CONTRACTS = "paperclip_darkfactory_v3_0_event_contracts.yaml"
RUNTIME_CONFIG = "paperclip_darkfactory_v3_0_runtime_config_registry.yaml"
MANIFEST = "paperclip_darkfactory_v3_0_bundle_manifest.yaml"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_sources(root: Path) -> dict[str, Any]:
    return {
        "enums": yaml.safe_load((root / CORE_ENUMS).read_text(encoding="utf-8")),
        "schema": json.loads((root / CORE_OBJECTS_SCHEMA).read_text(encoding="utf-8")),
        "events": yaml.safe_load((root / EVENT_CONTRACTS).read_text(encoding="utf-8")),
        "runtimeConfig": yaml.safe_load((root / RUNTIME_CONFIG).read_text(encoding="utf-8")),
        "manifest": yaml.safe_load((root / MANIFEST).read_text(encoding="utf-8")),
    }


def render_summary(root: Path | str = ROOT) -> str:
    root = Path(root)
    sources = load_sources(root)
    enum_map = sources["enums"].get("enums", {})
    schema_defs = sources["schema"].get("$defs", {})
    events = sources["events"].get("events", [])
    runtime_entries = sources["runtimeConfig"].get("registry", [])
    manifest_files = sources["manifest"].get("files", [])
    source_files = [CORE_ENUMS, CORE_OBJECTS_SCHEMA, EVENT_CONTRACTS, RUNTIME_CONFIG, MANIFEST]

    lines = [
        "# Dark Factory V3 Contract Summary",
        "",
        f"protocolReleaseTag: `{PROTOCOL_RELEASE_TAG}`",
        "",
        "## Source Digests",
        "",
    ]
    for rel_path in source_files:
        path = root / rel_path
        lines.append(f"- `{rel_path}`: `{sha256(path)}` ({path.stat().st_size} bytes)")

    lines.extend(
        [
            "",
            "## Counts",
            "",
            f"- Enum groups: {len(enum_map)}",
            f"- Enum literals: {sum(len(values or []) for values in enum_map.values())}",
            f"- Core object definitions: {len(schema_defs)}",
            f"- Event contracts: {len(events)}",
            f"- Runtime config entries: {len(runtime_entries)}",
            f"- Manifest file entries: {len(manifest_files)}",
            "",
            "## Core Object Definitions",
            "",
        ]
    )
    for name in sorted(schema_defs):
        if name[:1].isupper():
            lines.append(f"- `{name}`")

    lines.extend(["", "## Event Contracts", ""])
    for event in sorted(events, key=lambda item: item["canonicalName"]):
        lines.append(f"- `{event['canonicalName']}` `{event['version']}`")

    lines.extend(["", "## Batch 4 Surfaces", ""])
    for name in ("FaultPlaybook", "StructuredJournalFact", "ContractDriftReport"):
        lines.append(f"- `{name}`: {'present' if name in schema_defs else 'missing'}")
    for enum_name in ("structuredJournalFactType", "contractDriftStatus"):
        lines.append(f"- `{enum_name}` enum: {len(enum_map.get(enum_name, []))} values")

    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=str(ROOT), help="repository root")
    parser.add_argument("--output", help="write summary markdown to this path")
    parser.add_argument("--check", action="store_true", help="fail if --output exists and differs")
    args = parser.parse_args()

    root = Path(args.root)
    summary = render_summary(root)
    if args.output:
        output = (root / args.output).resolve()
        output.relative_to(root.resolve())
        if args.check and output.exists() and output.read_text(encoding="utf-8") != summary:
            print(json.dumps({"ok": False, "status": "drift_detected", "path": str(output)}, sort_keys=True))
            return 1
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(summary, encoding="utf-8")
        print(json.dumps({"ok": True, "path": str(output)}, sort_keys=True))
        return 0
    print(summary, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
