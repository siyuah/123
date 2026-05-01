from __future__ import annotations

import json
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Set

from .protocol import EventEnvelope

try:
    import fcntl  # type: ignore[import-not-found]
except ImportError:  # pragma: no cover - exercised only on non-POSIX runtimes.
    fcntl = None  # type: ignore[assignment]


class JournalAppendError(ValueError):
    """Raised when an append-only journal invariant would be violated."""


class JournalLockTimeoutError(JournalAppendError):
    """Raised when the JSONL journal file lock cannot be acquired in time."""


_FLOCK_WARNING_EMITTED = False


def _warn_unlocked_once() -> None:
    global _FLOCK_WARNING_EMITTED
    if _FLOCK_WARNING_EMITTED:
        return
    print("WARNING: fcntl is unavailable; FileBackedJsonlJournal is running without file locks.", file=sys.stderr)
    _FLOCK_WARNING_EMITTED = True


def _acquire_lock(handle, lock_type: int, *, timeout_seconds: float = 5.0) -> bool:
    if fcntl is None:
        _warn_unlocked_once()
        return False

    deadline = time.monotonic() + timeout_seconds
    while True:
        try:
            fcntl.flock(handle.fileno(), lock_type | fcntl.LOCK_NB)
            return True
        except BlockingIOError as exc:
            if time.monotonic() >= deadline:
                raise JournalLockTimeoutError("timed out acquiring journal file lock") from exc
            time.sleep(0.05)


def _release_lock(handle, locked: bool) -> None:
    if locked and fcntl is not None:
        fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


@dataclass
class InMemoryAppendOnlyJournal:
    """Small append-only journal for V3 event-envelope contract tests.

    The journal only appends; it never exposes mutators for existing records. It
    enforces stable event ids and strictly increasing sequence numbers per
    correlation id so golden timelines can be replayed deterministically.
    """

    _events: List[EventEnvelope] = field(default_factory=list)
    _event_ids: Set[str] = field(default_factory=set)

    def append(self, event: EventEnvelope) -> EventEnvelope:
        if event.eventId in self._event_ids:
            raise JournalAppendError(f"duplicate eventId {event.eventId!r}")
        last_for_correlation = [e.sequenceNo for e in self._events if e.correlationId == event.correlationId]
        if last_for_correlation and event.sequenceNo <= max(last_for_correlation):
            raise JournalAppendError(
                f"sequenceNo must increase within correlationId {event.correlationId!r}: "
                f"got {event.sequenceNo}, last {max(last_for_correlation)}"
            )
        self._events.append(event)
        self._event_ids.add(event.eventId)
        return event

    def read_all(self) -> List[EventEnvelope]:
        return list(self._events)

    def read_by_correlation(self, correlation_id: str) -> List[EventEnvelope]:
        return [event for event in self._events if event.correlationId == correlation_id]

    def get_event(self, event_id: str) -> Optional[EventEnvelope]:
        for event in self._events:
            if event.eventId == event_id:
                return event
        return None

    def to_jsonl(self) -> str:
        return "\n".join(json.dumps(event.to_dict(), ensure_ascii=False, sort_keys=True) for event in self._events)

    @classmethod
    def from_jsonl(cls, jsonl: str) -> "InMemoryAppendOnlyJournal":
        journal = cls()
        for line_number, line in enumerate(jsonl.splitlines(), start=1):
            if not line.strip():
                continue
            try:
                event = EventEnvelope.from_dict(json.loads(line))
            except (TypeError, ValueError, json.JSONDecodeError) as exc:
                raise JournalAppendError(f"invalid journal line {line_number}: {exc}") from exc
            journal.append(event.as_replay())
        return journal


@dataclass(init=False)
class FileBackedJsonlJournal(InMemoryAppendOnlyJournal):
    """Append-only EventEnvelope journal persisted as newline-delimited JSON."""

    path: Path

    def __init__(self, path: Path | str) -> None:
        super().__init__()
        self.path = Path(path)

    def append(self, event: EventEnvelope) -> EventEnvelope:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a+", encoding="utf-8") as handle:
            locked = _acquire_lock(handle, fcntl.LOCK_EX if fcntl is not None else 0)
            try:
                disk_journal = InMemoryAppendOnlyJournal()
                handle.seek(0)
                for line_number, line in enumerate(handle.read().splitlines(), start=1):
                    if not line.strip():
                        continue
                    try:
                        existing = EventEnvelope.from_dict(json.loads(line))
                    except (TypeError, ValueError, json.JSONDecodeError) as exc:
                        raise JournalAppendError(f"invalid journal line {line_number}: {exc}") from exc
                    disk_journal.append(existing.as_replay())
                appended = disk_journal.append(event)
                self._events = disk_journal.read_all()
                self._event_ids = {journal_event.eventId for journal_event in self._events}
                handle.seek(0, 2)
                handle.write(json.dumps(appended.to_dict(), ensure_ascii=False, sort_keys=True))
                handle.write("\n")
                handle.flush()
            finally:
                _release_lock(handle, locked)
        return appended

    @classmethod
    def load(cls, path: Path | str) -> "FileBackedJsonlJournal":
        journal = cls(path)
        if not journal.path.exists():
            return journal
        with journal.path.open("r", encoding="utf-8") as handle:
            locked = _acquire_lock(handle, fcntl.LOCK_SH if fcntl is not None else 0)
            try:
                for line_number, line in enumerate(handle.read().splitlines(), start=1):
                    if not line.strip():
                        continue
                    try:
                        event = EventEnvelope.from_dict(json.loads(line))
                    except (TypeError, ValueError, json.JSONDecodeError) as exc:
                        raise JournalAppendError(f"invalid journal line {line_number}: {exc}") from exc
                    InMemoryAppendOnlyJournal.append(journal, event.as_replay())
            finally:
                _release_lock(handle, locked)
        return journal
