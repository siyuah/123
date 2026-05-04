from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable

from .protocol import EventEnvelope, PROTOCOL_RELEASE_TAG

TRUTH_SOURCE = "dark-factory-journal"


@dataclass(frozen=True)
class StructuredJournalFact:
    factId: str
    factType: str
    subjectRef: str
    sourceEventId: str
    sourceEventName: str
    sourceCorrelationId: str
    confidence: float
    extractedAt: str
    factPayload: dict[str, Any] = field(default_factory=dict)
    protocolReleaseTag: str = PROTOCOL_RELEASE_TAG
    authoritative: bool = False
    truthSource: str = TRUTH_SOURCE

    def to_dict(self) -> dict[str, Any]:
        return {
            "protocolReleaseTag": self.protocolReleaseTag,
            "factId": self.factId,
            "factType": self.factType,
            "subjectRef": self.subjectRef,
            "sourceEventId": self.sourceEventId,
            "sourceEventName": self.sourceEventName,
            "sourceCorrelationId": self.sourceCorrelationId,
            "confidence": self.confidence,
            "extractedAt": self.extractedAt,
            "factPayload": dict(self.factPayload),
            "authoritative": self.authoritative,
            "truthSource": self.truthSource,
        }


def extract_structured_facts(events: Iterable[EventEnvelope]) -> tuple[StructuredJournalFact, ...]:
    facts: list[StructuredJournalFact] = []
    for event in events:
        fact = fact_from_event(event)
        if fact is not None:
            facts.append(fact)
    return tuple(facts)


def fact_from_event(event: EventEnvelope) -> StructuredJournalFact | None:
    if event.eventName == "route.decision.recorded":
        return _make_fact(
            event,
            fact_type="route_decision_fact",
            subject_ref=_payload_ref(event, "routeDecisionId", event.runId or event.correlationId),
            payload_keys=(
                "routeDecisionId",
                "workloadClass",
                "routePolicyRef",
                "selectedExecutorClass",
                "fallbackDepth",
                "decisionReason",
                "routeDecisionState",
            ),
        )
    if event.eventName == "provider.failure.recorded":
        return _make_fact(
            event,
            fact_type="provider_failure_fact",
            subject_ref=_payload_ref(event, "failureId", event.runId or event.correlationId),
            payload_keys=("failureId", "providerFaultClass", "providerRef", "routeDecisionId", "recoveryLane", "cutoverPerformed"),
        )
    if event.eventName == "provider.health.observed":
        return _make_fact(
            event,
            fact_type="provider_health_fact",
            subject_ref=_payload_ref(event, "providerId", event.correlationId),
            payload_keys=("providerId", "status", "observedAt", "fallbackEligible", "recoveryLane"),
        )
    if event.eventName == "guardrail.decision.recorded":
        return _make_fact(
            event,
            fact_type="guardrail_decision_fact",
            subject_ref=_payload_ref(event, "traceId", event.traceId),
            payload_keys=("operation", "level", "decision", "reason", "confirmationRequired", "traceId"),
        )
    if event.eventName in {"memory.artifact.created", "memory.artifact.corrected"}:
        return _make_fact(
            event,
            fact_type="memory_artifact_fact",
            subject_ref=_payload_ref(event, "memoryArtifactId", event.memoryArtifactId or event.correlationId),
            payload_keys=(
                "memoryArtifactId",
                "memoryArtifactType",
                "subjectRef",
                "confidence",
                "consentScope",
                "currentState",
                "correctedFromState",
                "correctedToState",
                "correctionReason",
            ),
        )
    if event.eventName in {"repair.attempt.started", "repair.attempt.completed"}:
        return _make_fact(
            event,
            fact_type="repair_attempt_fact",
            subject_ref=_payload_ref(event, "repairAttemptId", event.repairAttemptId or event.runId or event.correlationId),
            payload_keys=("repairAttemptId", "triggeredBy", "triggerFaultClass", "repairPlanRef", "outcome", "operatorApprovalRequired"),
        )
    if event.eventName in {"run.lifecycle.transitioned", "run.lifecycle.changed"}:
        return _make_fact(
            event,
            fact_type="run_state_fact",
            subject_ref=event.runId or _payload_ref(event, "runId", event.correlationId),
            payload_keys=("runState", "oldState", "newState", "transitionTrigger", "actor", "reasonCode"),
        )
    if event.eventName == "attempt.lifecycle.transitioned":
        return _make_fact(
            event,
            fact_type="attempt_state_fact",
            subject_ref=event.attemptId or _payload_ref(event, "attemptId", event.correlationId),
            payload_keys=("oldState", "newState", "transitionTrigger", "attemptId"),
        )
    return None


def _make_fact(
    event: EventEnvelope,
    *,
    fact_type: str,
    subject_ref: str,
    payload_keys: tuple[str, ...],
) -> StructuredJournalFact:
    payload = {key: event.payload[key] for key in payload_keys if key in event.payload}
    return StructuredJournalFact(
        factId=f"fact-{event.eventId}-{fact_type}",
        factType=fact_type,
        subjectRef=subject_ref,
        sourceEventId=event.eventId,
        sourceEventName=event.eventName,
        sourceCorrelationId=event.correlationId,
        confidence=float(payload.get("confidence", 1.0)),
        extractedAt=event.emittedAt,
        factPayload=payload,
    )


def _payload_ref(event: EventEnvelope, key: str, fallback: str | None) -> str:
    value = event.payload.get(key)
    if isinstance(value, str) and value:
        return value
    return fallback or event.eventId
