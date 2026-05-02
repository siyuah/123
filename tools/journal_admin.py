#!/usr/bin/env python3
"""Operational helpers for Dark Factory JSONL journals.

The tool is intentionally small and file-system based for MVP internal preview:
backup creates immutable timestamped copies, restore validates JSONL before
replacement, and retain prunes old backups by age/count.
"""
from __future__ import annotations

import argparse
import json
import shutil
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Iterable


def timestamp() -> str:
    return datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")


def validate_jsonl(path: Path) -> int:
    count = 0
    if not path.exists():
        raise FileNotFoundError(path)
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"invalid JSONL at line {line_number}: {exc}") from exc
            count += 1
    return count


def backup(journal: Path, backup_dir: Path) -> Path:
    validate_jsonl(journal)
    backup_dir.mkdir(parents=True, exist_ok=True)
    destination = backup_dir / f"{journal.stem}.{timestamp()}.jsonl"
    shutil.copy2(journal, destination)
    return destination


def restore(backup_path: Path, journal: Path) -> int:
    event_count = validate_jsonl(backup_path)
    journal.parent.mkdir(parents=True, exist_ok=True)
    temp_path = journal.with_suffix(journal.suffix + ".restore-tmp")
    shutil.copy2(backup_path, temp_path)
    temp_path.replace(journal)
    return event_count


def iter_backups(backup_dir: Path) -> Iterable[Path]:
    if not backup_dir.exists():
        return []
    return sorted((path for path in backup_dir.glob("*.jsonl") if path.is_file()), key=lambda path: path.stat().st_mtime, reverse=True)


def retain(backup_dir: Path, *, keep_last: int, max_age_days: int) -> list[Path]:
    backups = list(iter_backups(backup_dir))
    cutoff = datetime.now(UTC) - timedelta(days=max_age_days)
    removed: list[Path] = []
    for index, path in enumerate(backups):
        modified = datetime.fromtimestamp(path.stat().st_mtime, UTC)
        if index >= keep_last or modified < cutoff:
            path.unlink()
            removed.append(path)
    return removed


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Manage Dark Factory JSONL journal backups")
    subcommands = parser.add_subparsers(dest="command", required=True)

    backup_parser = subcommands.add_parser("backup", help="Create a timestamped JSONL backup")
    backup_parser.add_argument("--journal", required=True)
    backup_parser.add_argument("--backup-dir", required=True)

    restore_parser = subcommands.add_parser("restore", help="Validate and restore a JSONL backup")
    restore_parser.add_argument("--backup", required=True)
    restore_parser.add_argument("--journal", required=True)

    retain_parser = subcommands.add_parser("retain", help="Prune old JSONL backups")
    retain_parser.add_argument("--backup-dir", required=True)
    retain_parser.add_argument("--keep-last", type=int, default=10)
    retain_parser.add_argument("--max-age-days", type=int, default=14)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.command == "backup":
        destination = backup(Path(args.journal), Path(args.backup_dir))
        print(json.dumps({"ok": True, "backup": str(destination), "events": validate_jsonl(destination)}, sort_keys=True))
        return 0
    if args.command == "restore":
        events = restore(Path(args.backup), Path(args.journal))
        print(json.dumps({"ok": True, "journal": args.journal, "events": events}, sort_keys=True))
        return 0
    if args.command == "retain":
        removed = retain(Path(args.backup_dir), keep_last=args.keep_last, max_age_days=args.max_age_days)
        print(json.dumps({"ok": True, "removed": [str(path) for path in removed]}, sort_keys=True))
        return 0
    raise AssertionError(args.command)


if __name__ == "__main__":
    raise SystemExit(main())
