import json
import unittest
from pathlib import Path

from dark_factory_v3.journal import InMemoryAppendOnlyJournal, JournalAppendError
from dark_factory_v3.protocol import (
    PROTOCOL_RELEASE_TAG,
    Attempt,
    EventEnvelope,
    RouteDecision,
    Run,
    load_event_contracts,
    load_protocol_enums,
    replay_golden_timeline,
)

ROOT = Path(__file__).resolve().parents[1]


class V3RuntimeContractTests(unittest.TestCase):
    def test_protocol_enums_are_loaded_from_v3_bundle_assets(self):
        enums = load_protocol_enums(ROOT)

        self.assertTrue({"chat", "code", "vision", "repair"}.issubset(enums["workloadClass"]))
        self.assertIn("route.decision.recorded", enums["eventCanonicalName"])
        self.assertIn("parked_manual", enums["runState"])

    def test_core_runtime_types_carry_protocol_release_tag_and_validate_enum_literals(self):
        run = Run(runId="run-001", currentState="requested")
        attempt = Attempt(attemptId="attempt-001", runId=run.runId, currentState="created")
        decision = RouteDecision(
            routeDecisionId="rd-001",
            runId=run.runId,
            attemptId=attempt.attemptId,
            workloadClass="chat",
            routePolicyRef="policy://routing/v3/default",
            selectedExecutorClass="general_chat_executor",
            fallbackDepth=0,
            decisionReason="primary_policy_match",
            routeDecisionState="selected_primary",
            recordedAt="2026-04-24T00:00:00Z",
        )

        self.assertEqual(run.protocolReleaseTag, PROTOCOL_RELEASE_TAG)
        self.assertEqual(attempt.protocolReleaseTag, PROTOCOL_RELEASE_TAG)
        self.assertEqual(decision.to_dict()["protocolReleaseTag"], PROTOCOL_RELEASE_TAG)

        with self.assertRaisesRegex(ValueError, "workloadClass"):
            RouteDecision(
                routeDecisionId="rd-bad",
                runId=run.runId,
                attemptId=attempt.attemptId,
                workloadClass="legacy_chat",
                routePolicyRef="policy://routing/v3/default",
                selectedExecutorClass="general_chat_executor",
                fallbackDepth=0,
                decisionReason="primary_policy_match",
                routeDecisionState="selected_primary",
                recordedAt="2026-04-24T00:00:00Z",
            )

    def test_event_envelope_enforces_contract_required_fields_and_full_name(self):
        contracts = load_event_contracts(ROOT)
        envelope = EventEnvelope.from_contract(
            contracts,
            eventName="route.decision.recorded",
            eventId="evt-001",
            emittedAt="2026-04-24T00:00:00Z",
            traceId="trace-001",
            producer="dark-factory-router",
            causationId="run-001",
            correlationId="corr-001",
            sequenceNo=1,
            runId="run-001",
            attemptId="attempt-001",
            payload={
                "routeDecisionId": "rd-001",
                "workloadClass": "chat",
                "routePolicyRef": "policy://routing/v3/default",
                "selectedExecutorClass": "general_chat_executor",
                "fallbackDepth": 0,
                "decisionReason": "primary_policy_match",
            },
        )

        self.assertEqual(envelope.eventVersion, "v1")
        self.assertEqual(envelope.full_name, "route.decision.recorded.v1")
        self.assertEqual(envelope.to_dict()["protocolReleaseTag"], PROTOCOL_RELEASE_TAG)

        with self.assertRaisesRegex(ValueError, "decisionReason"):
            EventEnvelope.from_contract(
                contracts,
                eventName="route.decision.recorded",
                eventId="evt-002",
                emittedAt="2026-04-24T00:00:00Z",
                traceId="trace-001",
                producer="dark-factory-router",
                causationId="run-001",
                correlationId="corr-001",
                sequenceNo=2,
                payload={
                    "routeDecisionId": "rd-001",
                    "workloadClass": "chat",
                    "routePolicyRef": "policy://routing/v3/default",
                    "selectedExecutorClass": "general_chat_executor",
                    "fallbackDepth": 0,
                },
            )

    def test_journal_is_append_only_and_rejects_out_of_order_sequences(self):
        journal = InMemoryAppendOnlyJournal()
        first = EventEnvelope(
            eventName="route.decision.recorded",
            eventVersion="v1",
            eventId="evt-001",
            emittedAt="2026-04-24T00:00:00Z",
            traceId="trace-001",
            producer="dark-factory-router",
            causationId="run-001",
            correlationId="corr-001",
            sequenceNo=1,
            runId="run-001",
            attemptId="attempt-001",
            payload={
                "routeDecisionId": "rd-001",
                "workloadClass": "chat",
                "routePolicyRef": "policy://routing/v3/default",
                "selectedExecutorClass": "general_chat_executor",
                "fallbackDepth": 0,
                "decisionReason": "primary_policy_match",
            },
        )
        journal.append(first)

        self.assertEqual(journal.read_all()[0].eventId, "evt-001")
        self.assertEqual(json.loads(journal.to_jsonl()).get("eventId"), "evt-001")

        with self.assertRaisesRegex(JournalAppendError, "duplicate eventId"):
            journal.append(first)

        out_of_order = EventEnvelope(
            eventName="route.decision.recorded",
            eventVersion="v1",
            eventId="evt-000",
            emittedAt="2026-04-24T00:00:00Z",
            traceId="trace-001",
            producer="dark-factory-router",
            causationId="run-001",
            correlationId="corr-001",
            sequenceNo=1,
            runId="run-001",
            payload={"routeDecisionId": "rd-000"},
        )
        with self.assertRaisesRegex(JournalAppendError, "sequenceNo"):
            journal.append(out_of_order)

    def test_golden_timelines_replay_into_append_only_journal(self):
        journal = replay_golden_timeline(ROOT / "tests/golden_timelines/v3_0/GL-V30-routing-chat.jsonl")

        events = journal.read_all()
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].eventName, "route.decision.recorded")
        self.assertEqual(events[0].payload["workloadClass"], "chat")
        self.assertEqual(events[0].protocolReleaseTag, PROTOCOL_RELEASE_TAG)

    def test_all_golden_timelines_replay_and_preserve_event_contract_versions(self):
        contracts = load_event_contracts(ROOT)
        for timeline in sorted((ROOT / "tests/golden_timelines/v3_0").glob("*.jsonl")):
            with self.subTest(timeline=timeline.name):
                journal = replay_golden_timeline(timeline)
                self.assertTrue(journal.read_all(), timeline.name)
                for event in journal.read_all():
                    self.assertEqual(event.eventVersion, contracts[event.eventName]["version"])
                    self.assertEqual(event.protocolReleaseTag, PROTOCOL_RELEASE_TAG)


if __name__ == "__main__":
    unittest.main()
