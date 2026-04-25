import json
import unittest
from pathlib import Path

from dark_factory_v3.journal import InMemoryAppendOnlyJournal, JournalAppendError
from dark_factory_v3.projection import ProjectionReplayError, RunLifecycleReducer
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


def make_event(*, eventId="evt-001", correlationId="corr-001", sequenceNo=1, eventName="route.decision.recorded", **overrides):
    data = {
        "eventName": eventName,
        "eventVersion": "v1",
        "eventId": eventId,
        "emittedAt": "2026-04-24T00:00:00Z",
        "traceId": "trace-001",
        "producer": "dark-factory-router",
        "causationId": "run-001",
        "correlationId": correlationId,
        "sequenceNo": sequenceNo,
        "runId": "run-001",
        "attemptId": "attempt-001",
        "payload": {
            "routeDecisionId": "rd-001",
            "workloadClass": "chat",
            "routePolicyRef": "policy://routing/v3/default",
            "selectedExecutorClass": "general_chat_executor",
            "fallbackDepth": 0,
            "decisionReason": "primary_policy_match",
        },
    }
    data.update(overrides)
    return EventEnvelope(**data)


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
        first = make_event()
        journal.append(first)

        self.assertEqual(journal.read_all()[0].eventId, "evt-001")
        self.assertEqual(json.loads(journal.to_jsonl()).get("eventId"), "evt-001")

        with self.assertRaisesRegex(JournalAppendError, "duplicate eventId"):
            journal.append(first)

        out_of_order = make_event(eventId="evt-000", sequenceNo=1)
        with self.assertRaisesRegex(JournalAppendError, "sequenceNo"):
            journal.append(out_of_order)

    def test_journal_readers_are_correlation_scoped_and_immutable_snapshots(self):
        journal = InMemoryAppendOnlyJournal()
        first = journal.append(make_event(eventId="evt-a1", correlationId="corr-a", sequenceNo=1))
        second = journal.append(make_event(eventId="evt-b1", correlationId="corr-b", sequenceNo=1))
        third = journal.append(make_event(eventId="evt-a2", correlationId="corr-a", sequenceNo=2))

        snapshot = journal.read_all()
        snapshot.clear()

        self.assertEqual([event.eventId for event in journal.read_all()], ["evt-a1", "evt-b1", "evt-a2"])
        self.assertEqual(journal.read_by_correlation("corr-a"), [first, third])
        self.assertEqual(journal.get_event("evt-b1"), second)
        self.assertIsNone(journal.get_event("missing"))

    def test_journal_can_round_trip_jsonl_and_validate_replay_sequence(self):
        journal = InMemoryAppendOnlyJournal()
        journal.append(make_event(eventId="evt-001", sequenceNo=1))
        journal.append(make_event(eventId="evt-002", sequenceNo=2))

        replayed = InMemoryAppendOnlyJournal.from_jsonl(journal.to_jsonl())

        self.assertEqual([event.eventId for event in replayed.read_all()], ["evt-001", "evt-002"])
        self.assertTrue(all(event.isReplay for event in replayed.read_all()))

        broken_jsonl = "\n".join([
            json.dumps(make_event(eventId="evt-001", sequenceNo=2).to_dict()),
            json.dumps(make_event(eventId="evt-002", sequenceNo=1).to_dict()),
        ])
        with self.assertRaisesRegex(JournalAppendError, "sequenceNo"):
            InMemoryAppendOnlyJournal.from_jsonl(broken_jsonl)

    def test_protocol_objects_reject_empty_identifiers_and_bad_route_decision_shape(self):
        with self.assertRaisesRegex(ValueError, "runId"):
            Run(runId="", currentState="requested")
        with self.assertRaisesRegex(ValueError, "attemptId"):
            Attempt(attemptId="", runId="run-001", currentState="created")
        with self.assertRaisesRegex(ValueError, "routePolicyRef"):
            RouteDecision(
                routeDecisionId="rd-001",
                runId="run-001",
                attemptId="attempt-001",
                workloadClass="chat",
                routePolicyRef="",
                selectedExecutorClass="general_chat_executor",
                fallbackDepth=0,
                decisionReason="primary_policy_match",
                routeDecisionState="selected_primary",
                recordedAt="2026-04-24T00:00:00Z",
            )

    def test_golden_timelines_replay_into_append_only_journal(self):
        journal = replay_golden_timeline(ROOT / "tests/golden_timelines/v3_0/GL-V30-routing-chat.jsonl")

        events = journal.read_all()
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].eventName, "route.decision.recorded")
        self.assertEqual(events[0].payload["workloadClass"], "chat")
        self.assertEqual(events[0].protocolReleaseTag, PROTOCOL_RELEASE_TAG)
        self.assertTrue(events[0].isReplay)

    def test_all_golden_timelines_replay_and_preserve_event_contract_versions(self):
        contracts = load_event_contracts(ROOT)
        for timeline in sorted((ROOT / "tests/golden_timelines/v3_0").glob("*.jsonl")):
            with self.subTest(timeline=timeline.name):
                journal = replay_golden_timeline(timeline)
                self.assertTrue(journal.read_all(), timeline.name)
                for event in journal.read_all():
                    self.assertEqual(event.eventVersion, contracts[event.eventName]["version"])
                    self.assertEqual(event.protocolReleaseTag, PROTOCOL_RELEASE_TAG)
                    self.assertTrue(event.isReplay)

    def test_golden_timelines_replay_into_queryable_control_plane_projection(self):
        reducer = RunLifecycleReducer()
        expected_runs = {
            "GL-V30-routing-chat.jsonl": ("run-routing-chat-001", "planning"),
            "GL-V30-routing-code.jsonl": ("run-routing-code-001", "planning"),
            "GL-V30-routing-vision.jsonl": ("run-routing-vision-001", "planning"),
            "GL-V30-manual-park-rehydrate.jsonl": ("run-manual-001", "planning"),
        }
        for timeline in sorted((ROOT / "tests/golden_timelines/v3_0").glob("*.jsonl")):
            with self.subTest(timeline=timeline.name):
                journal = replay_golden_timeline(timeline)
                projection = reducer.replay(journal.read_all())
                self.assertEqual(len(projection.unknown_events), len([
                    event for event in journal.read_all()
                    if event.eventName not in {
                        "route.decision.recorded",
                        "run.lifecycle.transitioned",
                        "attempt.lifecycle.transitioned",
                        "manual_gate.parked",
                        "manual_gate.rehydrated",
                    }
                ]))
                if timeline.name in expected_runs:
                    run_id, expected_state = expected_runs[timeline.name]
                    run = projection.get_run(run_id)
                    self.assertIsNotNone(run)
                    self.assertEqual(run.currentState, expected_state)

        routing = reducer.replay(replay_golden_timeline(ROOT / "tests/golden_timelines/v3_0/GL-V30-routing-chat.jsonl").read_all())
        route = routing.get_route_decision("rd-chat-001")
        self.assertIsNotNone(route)
        self.assertEqual(route.decision.workloadClass, "chat")
        self.assertEqual(route.decision.routeDecisionState, "selected_primary")
        self.assertEqual(routing.get_attempt("attempt-routing-chat-001").currentState, "created")

        manual = reducer.replay(replay_golden_timeline(ROOT / "tests/golden_timelines/v3_0/GL-V30-manual-park-rehydrate.jsonl").read_all())
        self.assertEqual(manual.get_run("run-manual-001").currentState, "planning")
        self.assertEqual(manual.get_attempt("attempt-manual-001").currentState, "superseded")
        self.assertEqual(manual.get_attempt("attempt-manual-002").currentState, "created")

    def test_projection_rejects_illegal_run_state_transition(self):
        reducer = RunLifecycleReducer()
        illegal = EventEnvelope(
            eventName="run.lifecycle.transitioned",
            eventVersion="v1",
            eventId="evt-run-illegal-001",
            emittedAt="2026-04-24T00:00:00Z",
            traceId="trace-illegal-001",
            producer="dark-factory-orchestrator",
            causationId="run-illegal-001",
            correlationId="corr-illegal-001",
            sequenceNo=1,
            runId="run-illegal-001",
            payload={
                "oldState": "requested",
                "newState": "completed",
                "transitionTrigger": "closure_success",
            },
        )

        with self.assertRaisesRegex(ProjectionReplayError, "illegal run transition"):
            reducer.replay([illegal])

    def test_projection_applies_explicit_lifecycle_transition_events(self):
        reducer = RunLifecycleReducer()
        events = [
            EventEnvelope(
                eventName="run.lifecycle.transitioned",
                eventVersion="v1",
                eventId="evt-run-001",
                emittedAt="2026-04-24T00:00:00Z",
                traceId="trace-run-001",
                producer="dark-factory-orchestrator",
                causationId="run-001",
                correlationId="corr-run-001",
                sequenceNo=1,
                runId="run-001",
                payload={"oldState": "requested", "newState": "validating", "transitionTrigger": "request_accepted"},
            ),
            EventEnvelope(
                eventName="attempt.lifecycle.transitioned",
                eventVersion="v1",
                eventId="evt-attempt-001",
                emittedAt="2026-04-24T00:00:01Z",
                traceId="trace-run-001",
                producer="dark-factory-executor",
                causationId="evt-run-001",
                correlationId="corr-run-001",
                sequenceNo=2,
                runId="run-001",
                attemptId="attempt-001",
                payload={"oldState": "created", "newState": "booting", "transitionTrigger": "sandbox_allocated"},
            ),
        ]

        projection = reducer.replay(events)

        self.assertEqual(projection.get_run("run-001").currentState, "validating")
        self.assertEqual(projection.get_attempt("attempt-001").currentState, "booting")


if __name__ == "__main__":
    unittest.main()
