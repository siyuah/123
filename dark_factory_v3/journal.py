from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Set

from .protocol import EventEnvelope


class JournalAppendError(ValueError):
    """Raised when an append-only journal invariant would be violated."""


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
        appended = super().append(event)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(appended.to_dict(), ensure_ascii=False, sort_keys=True))
            handle.write("\n")
        return appended

    @classmethod
    def load(cls, path: Path | str) -> "FileBackedJsonlJournal":
        journal = cls(path)
        if not journal.path.exists():
            return journal
        for line_number, line in enumerate(journal.path.read_text(encoding="utf-8").splitlines(), start=1):
            if not line.strip():
                continue
            try:
                event = EventEnvelope.from_dict(json.loads(line))
            except (TypeError, ValueError, json.JSONDecodeError) as exc:
                raise JournalAppendError(f"invalid journal line {line_number}: {exc}") from exc
            InMemoryAppendOnlyJournal.append(journal, event.as_replay())
        return journal
