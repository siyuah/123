import json
from pathlib import Path

import yaml

from dark_factory_v3.protocol import EventEnvelope
from dark_factory_v3.structured_facts import extract_structured_facts, fact_from_event

ROOT = Path(__file__).resolve().parents[1]


def make_event(event_name: str, *, event_id: str = "evt-001", payload: dict | None = None, **extra):
    return EventEnvelope(
        eventName=event_name,
        eventVersion="v1",
        eventId=event_id,
        emittedAt="2026-05-05T00:00:00Z",
        traceId="trace-001",
        producer="test",
        causationId="run-001",
        correlationId="corr-001",
        sequenceNo=1,
        runId=extra.pop("runId", "run-001"),
        attemptId=extra.pop("attemptId", "attempt-001"),
        payload=payload or {},
        **extra,
    )


def test_structured_fact_extractor_derives_non_authoritative_route_fact():
    event = make_event(
        "route.decision.recorded",
        payload={
            "routeDecisionId": "rd-001",
            "workloadClass": "code",
            "routePolicyRef": "policy://routing/v3/default",
            "selectedExecutorClass": "code_executor",
            "fallbackDepth": 0,
            "decisionReason": "primary_policy_match",
        },
    )

    fact = fact_from_event(event)

    assert fact is not None
    assert fact.factType == "route_decision_fact"
    assert fact.subjectRef == "rd-001"
    assert fact.sourceEventId == "evt-001"
    assert fact.authoritative is False
    assert fact.truthSource == "dark-factory-journal"
    assert fact.factPayload["selectedExecutorClass"] == "code_executor"


def test_structured_fact_extractor_covers_provider_guardrail_memory_repair_and_state_events():
    events = [
        make_event("provider.failure.recorded", event_id="evt-failure", payload={"failureId": "failure-001", "providerFaultClass": "transient_5xx"}),
        make_event("provider.health.observed", event_id="evt-health", payload={"providerId": "provider-001", "status": "healthy", "fallbackEligible": False}),
        make_event("guardrail.decision.recorded", event_id="evt-guardrail", payload={"operation": "projection.read", "level": "P2_auto", "decision": "allowed", "reason": "read"}),
        make_event("memory.artifact.created", event_id="evt-memory", payload={"memoryArtifactId": "mem-001", "memoryArtifactType": "memory_fact", "confidence": 0.9}),
        make_event("repair.attempt.completed", event_id="evt-repair", payload={"repairAttemptId": "repair-001", "outcome": "repair_succeeded"}),
        make_event("run.lifecycle.transitioned", event_id="evt-run", payload={"oldState": "planning", "newState": "executing", "transitionTrigger": "execution_starts"}),
        make_event("attempt.lifecycle.transitioned", event_id="evt-attempt", payload={"oldState": "created", "newState": "booting", "transitionTrigger": "sandbox_allocated"}),
    ]

    facts = extract_structured_facts(events)

    assert [fact.factType for fact in facts] == [
        "provider_failure_fact",
        "provider_health_fact",
        "guardrail_decision_fact",
        "memory_artifact_fact",
        "repair_attempt_fact",
        "run_state_fact",
        "attempt_state_fact",
    ]
    assert all(fact.authoritative is False for fact in facts)
    assert all(fact.truthSource == "dark-factory-journal" for fact in facts)


def test_unknown_event_does_not_emit_fact():
    event = make_event("unknown.event", payload={"value": "ignored"})

    assert fact_from_event(event) is None
    assert extract_structured_facts([event]) == ()


def test_structured_fact_schema_and_event_contract_are_declared():
    enums = yaml.safe_load((ROOT / "paperclip_darkfactory_v3_0_core_enums.yaml").read_text(encoding="utf-8"))["enums"]
    schema = json.loads((ROOT / "paperclip_darkfactory_v3_0_core_objects.schema.json").read_text(encoding="utf-8"))
    events = yaml.safe_load((ROOT / "paperclip_darkfactory_v3_0_event_contracts.yaml").read_text(encoding="utf-8"))["events"]

    assert enums["structuredJournalFactType"] == [
        "route_decision_fact",
        "provider_failure_fact",
        "provider_health_fact",
        "guardrail_decision_fact",
        "memory_artifact_fact",
        "repair_attempt_fact",
        "run_state_fact",
        "attempt_state_fact",
    ]
    assert "StructuredJournalFact" in schema["$defs"]
    assert schema["$defs"]["StructuredJournalFact"]["properties"]["factType"]["$ref"] == "#/$defs/StructuredJournalFactType"
    assert "journal.fact.extracted" in {event["canonicalName"] for event in events}
