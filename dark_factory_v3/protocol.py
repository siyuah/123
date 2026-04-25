from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, Mapping, Optional

import yaml

PROTOCOL_RELEASE_TAG = "v3.0-agent-control-r1"


def _bundle_root(root: Path | str) -> Path:
    return Path(root).resolve()


def load_protocol_enums(root: Path | str) -> Dict[str, set[str]]:
    data = yaml.safe_load((_bundle_root(root) / "paperclip_darkfactory_v3_0_core_enums.yaml").read_text(encoding="utf-8"))
    if data.get("protocolReleaseTag") != PROTOCOL_RELEASE_TAG:
        raise ValueError("core enum protocolReleaseTag drift")
    return {key: set(values or []) for key, values in data.get("enums", {}).items()}


def load_event_contracts(root: Path | str) -> Dict[str, Dict[str, Any]]:
    data = yaml.safe_load((_bundle_root(root) / "paperclip_darkfactory_v3_0_event_contracts.yaml").read_text(encoding="utf-8"))
    if data.get("protocolReleaseTag") != PROTOCOL_RELEASE_TAG:
        raise ValueError("event contract protocolReleaseTag drift")
    return {event["canonicalName"]: dict(event) for event in data.get("events", [])}


def _validate_literal(field_name: str, value: str, allowed: Iterable[str]) -> None:
    allowed_set = set(allowed)
    if value not in allowed_set:
        raise ValueError(f"{field_name} must be one of {sorted(allowed_set)}, got {value!r}")


_DEFAULT_ENUMS = {
    "runState": {
        "requested",
        "validating",
        "planning",
        "executing",
        "waiting_approval",
        "waiting_input",
        "parked_manual",
        "rehydrating",
        "finalizing",
        "completed",
        "failed",
        "cancelled",
    },
    "attemptState": {
        "created",
        "booting",
        "active",
        "frozen",
        "handoff_pending",
        "parked_manual",
        "rehydrate_pending",
        "superseded",
        "finalizer_owned",
        "succeeded",
        "failed",
        "cancelled",
    },
    "workloadClass": {"chat", "code", "reasoning", "vision", "memory_maintenance", "repair", "operator_adjudication"},
    "routeDecisionState": {"selected_primary", "selected_fallback", "cutover_performed", "degraded", "aborted"},
}


@dataclass(frozen=True)
class Run:
    runId: str
    currentState: str
    protocolReleaseTag: str = PROTOCOL_RELEASE_TAG

    def __post_init__(self) -> None:
        _validate_literal("runState", self.currentState, _DEFAULT_ENUMS["runState"])
        if self.protocolReleaseTag != PROTOCOL_RELEASE_TAG:
            raise ValueError("invalid protocolReleaseTag")

    def to_dict(self) -> Dict[str, Any]:
        return dict(protocolReleaseTag=self.protocolReleaseTag, runId=self.runId, currentState=self.currentState)


@dataclass(frozen=True)
class Attempt:
    attemptId: str
    runId: str
    currentState: str
    protocolReleaseTag: str = PROTOCOL_RELEASE_TAG

    def __post_init__(self) -> None:
        _validate_literal("attemptState", self.currentState, _DEFAULT_ENUMS["attemptState"])
        if self.protocolReleaseTag != PROTOCOL_RELEASE_TAG:
            raise ValueError("invalid protocolReleaseTag")

    def to_dict(self) -> Dict[str, Any]:
        return dict(
            protocolReleaseTag=self.protocolReleaseTag,
            attemptId=self.attemptId,
            runId=self.runId,
            currentState=self.currentState,
        )


@dataclass(frozen=True)
class RouteDecision:
    routeDecisionId: str
    runId: str
    attemptId: str
    workloadClass: str
    routePolicyRef: str
    selectedExecutorClass: str
    fallbackDepth: int
    decisionReason: str
    routeDecisionState: str
    recordedAt: str
    protocolReleaseTag: str = PROTOCOL_RELEASE_TAG

    def __post_init__(self) -> None:
        if self.protocolReleaseTag != PROTOCOL_RELEASE_TAG:
            raise ValueError("invalid protocolReleaseTag")
        _validate_literal("workloadClass", self.workloadClass, _DEFAULT_ENUMS["workloadClass"])
        _validate_literal("routeDecisionState", self.routeDecisionState, _DEFAULT_ENUMS["routeDecisionState"])
        if self.fallbackDepth < 0:
            raise ValueError("fallbackDepth must be non-negative")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "protocolReleaseTag": self.protocolReleaseTag,
            "routeDecisionId": self.routeDecisionId,
            "runId": self.runId,
            "attemptId": self.attemptId,
            "workloadClass": self.workloadClass,
            "routePolicyRef": self.routePolicyRef,
            "selectedExecutorClass": self.selectedExecutorClass,
            "fallbackDepth": self.fallbackDepth,
            "decisionReason": self.decisionReason,
            "routeDecisionState": self.routeDecisionState,
            "recordedAt": self.recordedAt,
        }


@dataclass(frozen=True)
class EventEnvelope:
    eventName: str
    eventVersion: str
    eventId: str
    emittedAt: str
    traceId: str
    producer: str
    causationId: str
    correlationId: str
    sequenceNo: int
    isReplay: bool = False
    protocolReleaseTag: str = PROTOCOL_RELEASE_TAG
    partitionKey: Optional[str] = None
    orderingScope: Optional[str] = None
    idempotencyKey: Optional[str] = None
    runId: Optional[str] = None
    attemptId: Optional[str] = None
    artifactId: Optional[str] = None
    memoryArtifactId: Optional[str] = None
    repairAttemptId: Optional[str] = None
    payload: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.protocolReleaseTag != PROTOCOL_RELEASE_TAG:
            raise ValueError("invalid protocolReleaseTag")
        if self.sequenceNo < 1:
            raise ValueError("sequenceNo must be positive")

    @property
    def full_name(self) -> str:
        return f"{self.eventName}.{self.eventVersion}"

    @classmethod
    def from_contract(
        cls,
        contracts: Mapping[str, Mapping[str, Any]],
        *,
        eventName: str,
        eventId: str,
        emittedAt: str,
        traceId: str,
        producer: str,
        causationId: str,
        correlationId: str,
        sequenceNo: int,
        payload: Optional[Dict[str, Any]] = None,
        isReplay: bool = False,
        **optional_fields: Any,
    ) -> "EventEnvelope":
        if eventName not in contracts:
            raise ValueError(f"unknown eventName {eventName!r}")
        contract = contracts[eventName]
        payload = dict(payload or {})
        missing = [name for name in contract.get("requiredPayload", []) if name not in payload and name not in optional_fields]
        if missing:
            raise ValueError(f"event {eventName} missing required payload fields: {', '.join(missing)}")
        return cls(
            eventName=eventName,
            eventVersion=str(contract["version"]),
            eventId=eventId,
            emittedAt=emittedAt,
            traceId=traceId,
            producer=producer,
            causationId=causationId,
            correlationId=correlationId,
            sequenceNo=sequenceNo,
            isReplay=isReplay,
            partitionKey=contract.get("partitionKey"),
            orderingScope=contract.get("orderingScope"),
            idempotencyKey=optional_fields.pop("idempotencyKey", None) or contract.get("idempotencyKey"),
            payload=payload,
            **optional_fields,
        )

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "EventEnvelope":
        known = {
            "eventName",
            "eventVersion",
            "eventId",
            "emittedAt",
            "protocolReleaseTag",
            "traceId",
            "producer",
            "causationId",
            "correlationId",
            "sequenceNo",
            "isReplay",
            "partitionKey",
            "orderingScope",
            "idempotencyKey",
            "runId",
            "attemptId",
            "artifactId",
            "memoryArtifactId",
            "repairAttemptId",
        }
        kwargs = {key: data[key] for key in known if key in data}
        payload = {key: value for key, value in data.items() if key not in known and key != "seq"}
        if "sequenceNo" not in kwargs and "seq" in data:
            kwargs["sequenceNo"] = data["seq"]
        kwargs.setdefault("isReplay", False)
        kwargs["payload"] = payload
        return cls(**kwargs)  # type: ignore[arg-type]

    def to_dict(self) -> Dict[str, Any]:
        base = {
            "eventName": self.eventName,
            "eventVersion": self.eventVersion,
            "eventId": self.eventId,
            "emittedAt": self.emittedAt,
            "protocolReleaseTag": self.protocolReleaseTag,
            "traceId": self.traceId,
            "producer": self.producer,
            "causationId": self.causationId,
            "correlationId": self.correlationId,
            "sequenceNo": self.sequenceNo,
            "isReplay": self.isReplay,
        }
        for key in [
            "partitionKey",
            "orderingScope",
            "idempotencyKey",
            "runId",
            "attemptId",
            "artifactId",
            "memoryArtifactId",
            "repairAttemptId",
        ]:
            value = getattr(self, key)
            if value is not None:
                base[key] = value
        base.update(self.payload)
        return base


def replay_golden_timeline(path: Path | str):
    from .journal import InMemoryAppendOnlyJournal

    journal = InMemoryAppendOnlyJournal()
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        journal.append(EventEnvelope.from_dict(json.loads(line)))
    return journal
