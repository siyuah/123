import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from dark_factory_v3.control_plane import ControlPlane, ControlPlaneError
from dark_factory_v3.journal import FileBackedJsonlJournal, InMemoryAppendOnlyJournal, JournalAppendError
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

    def test_projection_rehydrates_manual_gate_with_unique_ordered_event_lineage(self):
        reducer = RunLifecycleReducer()
        manual = reducer.replay(replay_golden_timeline(ROOT / "tests/golden_timelines/v3_0/GL-V30-manual-park-rehydrate.jsonl").read_all())

        run = manual.get_run("run-manual-001")
        previous_attempt = manual.get_attempt("attempt-manual-001")
        new_attempt = manual.get_attempt("attempt-manual-002")
        self.assertEqual(run.currentState, "planning")
        self.assertEqual(previous_attempt.currentState, "superseded")
        self.assertEqual(new_attempt.currentState, "created")
        self.assertEqual(run.eventIds, ("evt-manual-001", "evt-manual-002"))
        self.assertEqual(previous_attempt.eventIds, ("evt-manual-002",))
        self.assertEqual(new_attempt.eventIds, ("evt-manual-002",))
        self.assertEqual(run.eventIds.count("evt-manual-002"), 1)
        self.assertEqual(previous_attempt.eventIds.count("evt-manual-002"), 1)

    def test_all_golden_timeline_projection_event_lineage_is_unique(self):
        reducer = RunLifecycleReducer()
        for timeline in sorted((ROOT / "tests/golden_timelines/v3_0").glob("*.jsonl")):
            with self.subTest(timeline=timeline.name):
                projection = reducer.replay(replay_golden_timeline(timeline).read_all())
                for run in projection.runs.values():
                    self.assertEqual(list(run.eventIds), list(dict.fromkeys(run.eventIds)))
                for attempt in projection.attempts.values():
                    self.assertEqual(list(attempt.eventIds), list(dict.fromkeys(attempt.eventIds)))

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
    def test_control_plane_happy_path_appends_contract_events_and_projects_state(self):
        plane = ControlPlane(root=ROOT, clock=lambda: "2026-04-24T00:00:00Z")

        first = plane.request_run(run_id="run-cp-001", correlation_id="corr-cp-001", trace_id="trace-cp-001")
        route = plane.record_route_decision(
            run_id="run-cp-001",
            attempt_id="attempt-cp-001",
            route_decision_id="rd-cp-001",
            workload_class="code",
            route_policy_ref="policy://routing/v3/default",
            selected_executor_class="code_executor",
            fallback_depth=0,
            decision_reason="primary_policy_match",
            correlation_id="corr-cp-001",
            trace_id="trace-cp-001",
        )
        booting = plane.transition_attempt(
            run_id="run-cp-001",
            attempt_id="attempt-cp-001",
            old_state="created",
            new_state="booting",
            transition_trigger="sandbox_allocated",
            correlation_id="corr-cp-001",
            trace_id="trace-cp-001",
        )
        active = plane.transition_attempt(
            run_id="run-cp-001",
            attempt_id="attempt-cp-001",
            old_state="booting",
            new_state="active",
            transition_trigger="first_checkpoint",
            correlation_id="corr-cp-001",
            trace_id="trace-cp-001",
        )
        plane.transition_run(
            run_id="run-cp-001",
            old_state="validating",
            new_state="planning",
            transition_trigger="validation_passed",
            correlation_id="corr-cp-001",
            trace_id="trace-cp-001",
        )
        plane.transition_run(
            run_id="run-cp-001",
            old_state="planning",
            new_state="executing",
            transition_trigger="execution_starts",
            correlation_id="corr-cp-001",
            trace_id="trace-cp-001",
        )
        parked = plane.park_manual(
            run_id="run-cp-001",
            attempt_id="attempt-cp-001",
            park_id="park-cp-001",
            manual_gate_type="operator_review",
            rehydration_token_id="rt-cp-001",
            correlation_id="corr-cp-001",
            trace_id="trace-cp-001",
        )
        rehydrated = plane.rehydrate_manual(
            run_id="run-cp-001",
            previous_attempt_id="attempt-cp-001",
            new_attempt_id="attempt-cp-002",
            rehydration_token_id="rt-cp-001",
            correlation_id="corr-cp-001",
            trace_id="trace-cp-001",
        )

        self.assertEqual(first.eventName, "run.lifecycle.transitioned")
        self.assertEqual(first.eventVersion, "v1")
        self.assertEqual(first.protocolReleaseTag, PROTOCOL_RELEASE_TAG)
        self.assertEqual(first.payload["oldState"], "requested")
        self.assertEqual(first.payload["newState"], "validating")
        self.assertEqual(route.idempotencyKey, "rd-cp-001")
        self.assertEqual(parked.idempotencyKey, "park-cp-001")
        self.assertEqual(rehydrated.idempotencyKey, "rt-cp-001")
        self.assertEqual([event.sequenceNo for event in plane.journal.read_by_correlation("corr-cp-001")], list(range(1, 9)))
        self.assertEqual([event.eventId for event in plane.journal.read_all()], [
            first.eventId,
            route.eventId,
            booting.eventId,
            active.eventId,
            "evt-corr-cp-001-0005",
            "evt-corr-cp-001-0006",
            parked.eventId,
            rehydrated.eventId,
        ])

        projection = plane.projection()
        self.assertEqual(projection.get_run("run-cp-001").currentState, "planning")
        self.assertEqual(projection.get_attempt("attempt-cp-001").currentState, "superseded")
        self.assertEqual(projection.get_attempt("attempt-cp-002").currentState, "created")
        self.assertEqual(projection.get_route_decision("rd-cp-001").decision.workloadClass, "code")

    def test_control_plane_rejects_illegal_transition_without_polluting_journal(self):
        plane = ControlPlane(root=ROOT)
        plane.request_run(run_id="run-cp-002", correlation_id="corr-cp-002", trace_id="trace-cp-002")
        before = plane.journal.read_all()

        with self.assertRaisesRegex(ControlPlaneError, "illegal run transition"):
            plane.transition_run(
                run_id="run-cp-002",
                old_state="validating",
                new_state="completed",
                transition_trigger="closure_success",
                correlation_id="corr-cp-002",
                trace_id="trace-cp-002",
            )

        self.assertEqual(plane.journal.read_all(), before)
        self.assertEqual(plane.projection().get_run("run-cp-002").currentState, "validating")

    def test_control_plane_surfaces_duplicate_event_ids_and_preserves_journal(self):
        plane = ControlPlane(root=ROOT)
        plane.request_run(run_id="run-cp-003", correlation_id="corr-cp-003", trace_id="trace-cp-003", event_id="evt-fixed")
        before = plane.journal.read_all()

        with self.assertRaisesRegex(ControlPlaneError, "duplicate eventId"):
            plane.transition_run(
                run_id="run-cp-003",
                old_state="validating",
                new_state="planning",
                transition_trigger="validation_passed",
                correlation_id="corr-cp-003",
                trace_id="trace-cp-003",
                event_id="evt-fixed",
            )

        self.assertEqual(plane.journal.read_all(), before)

    def test_control_plane_projection_query_api_reads_current_journal(self):
        plane = ControlPlane(root=ROOT)
        plane.request_run(run_id="run-cp-004", correlation_id="corr-cp-004", trace_id="trace-cp-004")

        self.assertEqual(plane.get_run("run-cp-004").currentState, "validating")
        self.assertIsNone(plane.get_attempt("attempt-missing"))
        self.assertIsNone(plane.get_route_decision("rd-missing"))
    def test_file_backed_jsonl_journal_round_trips_and_enforces_append_invariants(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "journal.jsonl"
            journal = FileBackedJsonlJournal(path)
            journal.append(make_event(eventId="evt-file-001", sequenceNo=1))
            journal.append(make_event(eventId="evt-file-002", sequenceNo=2))

            self.assertTrue(path.exists())
            self.assertEqual(path.read_text(encoding="utf-8").count("\n"), 2)
            restored = FileBackedJsonlJournal.load(path)
            self.assertEqual([event.eventId for event in restored.read_all()], ["evt-file-001", "evt-file-002"])
            self.assertTrue(all(event.isReplay for event in restored.read_all()))

            with self.assertRaisesRegex(JournalAppendError, "duplicate eventId"):
                restored.append(make_event(eventId="evt-file-001", sequenceNo=3))
            with self.assertRaisesRegex(JournalAppendError, "sequenceNo"):
                restored.append(make_event(eventId="evt-file-003", sequenceNo=2))
            self.assertEqual(len(path.read_text(encoding="utf-8").splitlines()), 2)

    def test_control_plane_loaded_from_jsonl_path_continues_correlation_sequence(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "journal.jsonl"
            first = ControlPlane.from_jsonl_path(ROOT, path, clock=lambda: "2026-04-24T00:00:00Z")
            first.request_run(run_id="run-file-001", correlation_id="corr-file-001", trace_id="trace-file-001")

            restored = ControlPlane.from_jsonl_path(ROOT, path, clock=lambda: "2026-04-24T00:00:01Z")
            second = restored.transition_run(
                run_id="run-file-001",
                old_state="validating",
                new_state="planning",
                transition_trigger="validation_passed",
                correlation_id="corr-file-001",
                trace_id="trace-file-001",
            )

            self.assertEqual(second.sequenceNo, 2)
            self.assertEqual(second.eventId, "evt-corr-file-001-0002")
            reloaded = ControlPlane.from_jsonl_path(ROOT, path)
            self.assertEqual(reloaded.get_run("run-file-001").currentState, "planning")

    def run_cli(self, *args, check=False):
        return subprocess.run(
            [sys.executable, str(ROOT / "tools/v3_control_plane.py"), *args],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=check,
        )

    def run_smoke(self, *args, check=False):
        return subprocess.run(
            [sys.executable, str(ROOT / "tools/v3_control_plane_smoke.py"), *args],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=check,
        )

    def test_control_plane_cli_version_outputs_stable_contract_summary(self):
        result = self.run_cli("version", check=True)

        payload = json.loads(result.stdout)
        expected_commands = [
            "request-run",
            "transition-run",
            "transition-attempt",
            "record-route-decision",
            "park-manual",
            "rehydrate-manual",
            "projection",
            "verify-journal",
            "version",
        ]
        self.assertEqual(payload["ok"], True)
        self.assertEqual(payload["protocolReleaseTag"], PROTOCOL_RELEASE_TAG)
        self.assertEqual(payload["commands"], expected_commands)
        self.assertEqual(payload["eventContract"]["eventVersion"], "v1")
        self.assertEqual(payload["eventContract"]["producer"], "dark-factory-control-plane")

    def test_control_plane_smoke_script_runs_complete_timeline_and_projects_expected_state(self):
        result = self.run_smoke(check=True)

        payload = json.loads(result.stdout)
        projection = payload["projection"]
        self.assertEqual(payload["ok"], True)
        self.assertEqual(payload["events"], 8)
        self.assertTrue(payload["journal"].endswith("v3_control_plane_smoke.jsonl"))
        self.assertEqual(projection["runs"]["run-smoke-001"]["currentState"], "planning")
        self.assertEqual(projection["attempts"]["attempt-smoke-001"]["currentState"], "superseded")
        self.assertEqual(projection["attempts"]["attempt-smoke-002"]["currentState"], "created")
        self.assertIn("rd-smoke-001", projection["routeDecisions"])
        self.assertEqual(payload["sequenceNos"], list(range(1, 9)))
        rehydrated_event_id = "evt-corr-smoke-001-0008"
        for collection_name in ("runs", "attempts"):
            for entity_id, entity in projection[collection_name].items():
                with self.subTest(collection=collection_name, entity=entity_id):
                    self.assertEqual(entity["eventIds"], list(dict.fromkeys(entity["eventIds"])))
        self.assertLessEqual(projection["runs"]["run-smoke-001"]["eventIds"].count(rehydrated_event_id), 1)
        self.assertLessEqual(projection["attempts"]["attempt-smoke-001"]["eventIds"].count(rehydrated_event_id), 1)

    def test_control_plane_smoke_script_keeps_user_supplied_journal_path(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            journal = Path(tmpdir) / "kept-smoke.jsonl"
            result = self.run_smoke("--journal", str(journal), check=True)

            payload = json.loads(result.stdout)
            self.assertEqual(payload["ok"], True)
            self.assertEqual(Path(payload["journal"]), journal)
            self.assertTrue(journal.exists())
            self.assertEqual(len(journal.read_text(encoding="utf-8").splitlines()), 8)

    def test_control_plane_smoke_script_illegal_transition_outputs_json_error_without_polluting_journal(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            journal = Path(tmpdir) / "bad-smoke.jsonl"
            result = self.run_smoke("--journal", str(journal), "--inject-illegal-transition", check=False)

            error = json.loads(result.stderr)
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(result.stdout, "")
            self.assertEqual(error["ok"], False)
            self.assertEqual(error["error"]["type"], "SmokeAssertionError")
            self.assertIn("illegal run transition", error["error"]["message"])
            self.assertTrue(journal.exists())
            self.assertEqual(len(journal.read_text(encoding="utf-8").splitlines()), 4)

    def make_smoke_journal(self, path: Path) -> dict:
        result = self.run_smoke("--journal", str(path), check=True)
        return json.loads(result.stdout)

    def rewrite_journal_event(self, path: Path, index: int, **updates):
        events = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
        events[index].update(updates)
        path.write_text("\n".join(json.dumps(event, ensure_ascii=False, sort_keys=True) for event in events) + "\n", encoding="utf-8")
        return events

    def test_cli_verify_journal_accepts_smoke_journal_and_outputs_stable_summary(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            journal = Path(tmpdir) / "smoke.jsonl"
            smoke_payload = self.make_smoke_journal(journal)

            result = self.run_cli("verify-journal", "--journal", str(journal), check=True)

            payload = json.loads(result.stdout)
            self.assertEqual(payload["ok"], True)
            self.assertEqual(Path(payload["journal"]), journal)
            self.assertEqual(payload["events"], smoke_payload["events"])
            self.assertTrue(all(isinstance(check, dict) for check in payload["checks"]))
            self.assertEqual(
                [check["id"] for check in payload["checks"]],
                [
                    "jsonl.valid_json",
                    "journal.not_empty",
                    "journal.sequence_contiguous",
                    "journal.event_id_unique",
                    "envelope.required_fields",
                    "envelope.protocol_release_tag",
                    "envelope.event_version_compatible",
                    "projection.replay",
                    "projection.event_ids_unique",
                    "projection.event_ids_resolvable",
                ],
            )
            self.assertTrue(all(check["status"] == "pass" for check in payload["checks"]))
            self.assertTrue(all(check.get("message") for check in payload["checks"]))
            self.assertEqual(payload["checkIds"], [check["id"] for check in payload["checks"]])
            self.assertEqual(payload["projectionSummary"], {
                "attempts": 2,
                "routeDecisions": 1,
                "runs": 1,
                "unknownEvents": 0,
            })
            self.assertEqual(result.stderr, "")

    def test_control_plane_smoke_runs_verify_journal_and_includes_summary(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            journal = Path(tmpdir) / "smoke.jsonl"

            result = self.run_smoke("--journal", str(journal), check=True)

            payload = json.loads(result.stdout)
            self.assertEqual(payload["verifyJournal"]["ok"], True)
            self.assertEqual(payload["verifyJournal"]["events"], 8)
            self.assertEqual(payload["verifyJournal"]["projectionSummary"], {
                "attempts": 2,
                "routeDecisions": 1,
                "runs": 1,
                "unknownEvents": 0,
            })

    def test_cli_verify_journal_sequence_gap_fails_with_stable_json_error(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            journal = Path(tmpdir) / "gap.jsonl"
            self.make_smoke_journal(journal)
            self.rewrite_journal_event(journal, 1, sequenceNo=3)

            result = self.run_cli("verify-journal", "--journal", str(journal))

            error = json.loads(result.stderr)
            self.assertEqual(result.stdout, "")
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(error["ok"], False)
            self.assertEqual(error["error"]["type"], "JournalVerificationError")
            self.assertEqual(error["error"]["checkId"], "journal.sequence_contiguous")
            self.assertEqual(error["error"]["lineNumber"], 2)
            self.assertEqual(error["error"]["eventId"], "evt-corr-smoke-001-0002")
            self.assertIn("expected sequenceNo 2", error["error"]["message"])

    def test_cli_verify_journal_duplicate_event_id_fails_with_stable_json_error(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            journal = Path(tmpdir) / "duplicate.jsonl"
            self.make_smoke_journal(journal)
            self.rewrite_journal_event(journal, 1, eventId="evt-corr-smoke-001-0001")

            result = self.run_cli("verify-journal", "--journal", str(journal))

            error = json.loads(result.stderr)
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(error["error"]["checkId"], "journal.event_id_unique")
            self.assertEqual(error["error"]["lineNumber"], 2)
            self.assertEqual(error["error"]["eventId"], "evt-corr-smoke-001-0001")
            self.assertIn("duplicate eventId", error["error"]["message"])

    def test_cli_verify_journal_invalid_protocol_release_tag_fails(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            journal = Path(tmpdir) / "bad-protocol.jsonl"
            self.make_smoke_journal(journal)
            self.rewrite_journal_event(journal, 0, protocolReleaseTag="v2.9-agent-control-r1")

            result = self.run_cli("verify-journal", "--journal", str(journal))

            error = json.loads(result.stderr)
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(error["error"]["checkId"], "envelope.protocol_release_tag")
            self.assertEqual(error["error"]["lineNumber"], 1)
            self.assertEqual(error["error"]["eventId"], "evt-corr-smoke-001-0001")

    def test_cli_verify_journal_non_json_line_fails_with_line_number(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            journal = Path(tmpdir) / "bad-json.jsonl"
            self.make_smoke_journal(journal)
            lines = journal.read_text(encoding="utf-8").splitlines()
            lines[2] = "{not-json"
            journal.write_text("\n".join(lines) + "\n", encoding="utf-8")

            result = self.run_cli("verify-journal", "--journal", str(journal))

            error = json.loads(result.stderr)
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(error["error"]["checkId"], "jsonl.valid_json")
            self.assertEqual(error["error"]["lineNumber"], 3)
            self.assertNotIn("Traceback", result.stderr)

    def test_cli_verify_journal_output_writes_report_and_stdout_includes_output_path(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            journal = Path(tmpdir) / "smoke.jsonl"
            report = Path(tmpdir) / "verify-report.json"
            self.make_smoke_journal(journal)

            result = self.run_cli("verify-journal", "--journal", str(journal), "--output", str(report), check=True)

            stdout_payload = json.loads(result.stdout)
            report_payload = json.loads(report.read_text(encoding="utf-8"))
            self.assertEqual(stdout_payload["ok"], True)
            self.assertEqual(stdout_payload["outputPath"], str(report))
            self.assertEqual(report_payload, stdout_payload)
            self.assertEqual([check["status"] for check in stdout_payload["checks"]], ["pass"] * len(stdout_payload["checks"]))

    def test_cli_verify_journal_run_id_filters_summary_only_after_full_replay(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            journal = Path(tmpdir) / "multi-run.jsonl"
            self.make_smoke_journal(journal)
            extra = self.run_cli(
                "request-run",
                "--journal", str(journal),
                "--run-id", "run-extra-001",
                "--correlation-id", "corr-extra-001",
                "--trace-id", "trace-extra-001",
                check=True,
            )
            extra_event = json.loads(extra.stdout)["event"]
            extra_event["sequenceNo"] = 9
            extra_event["eventId"] = "evt-corr-extra-001-0009"
            extra_event["idempotencyKey"] = "evt-corr-extra-001-0009"
            lines = journal.read_text(encoding="utf-8").splitlines()
            lines[-1] = json.dumps(extra_event, ensure_ascii=False, sort_keys=True)
            journal.write_text("\n".join(lines) + "\n", encoding="utf-8")

            result = self.run_cli("verify-journal", "--journal", str(journal), "--run-id", "run-smoke-001", check=True)

            payload = json.loads(result.stdout)
            self.assertEqual(payload["ok"], True)
            self.assertEqual(payload["events"], 9)
            self.assertEqual(payload["runId"], "run-smoke-001")
            self.assertEqual(payload["projectionSummary"], {
                "attempts": 2,
                "routeDecisions": 1,
                "runs": 1,
                "unknownEvents": 0,
            })
            self.assertEqual(payload["fullProjectionSummary"], {
                "attempts": 2,
                "routeDecisions": 1,
                "runs": 2,
                "unknownEvents": 0,
            })

    def test_cli_verify_journal_empty_journal_fails_with_stable_json_error(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            journal = Path(tmpdir) / "empty.jsonl"
            journal.write_text("", encoding="utf-8")

            result = self.run_cli("verify-journal", "--journal", str(journal), "--strict-empty")

            error = json.loads(result.stderr)
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(result.stdout, "")
            self.assertEqual(error["ok"], False)
            self.assertEqual(error["error"], {
                "type": "JournalVerificationError",
                "checkId": "journal.not_empty",
                "message": "journal must contain at least one event",
            })

    def test_makefile_smoke_and_verify_journal_targets_run(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            journal = Path(tmpdir) / "make-smoke.jsonl"
            smoke = subprocess.run(
                ["make", "smoke-v3-control-plane", f"JOURNAL={journal}"],
                cwd=ROOT,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=True,
            )
            smoke_payload = json.loads(smoke.stdout[smoke.stdout.index("{"):])
            self.assertEqual(smoke.returncode, 0)
            self.assertTrue(smoke.stdout.strip())
            self.assertEqual(smoke_payload["ok"], True)
            self.assertEqual(smoke_payload["verifyJournal"]["ok"], True)
            self.assertTrue(journal.exists())

            verify = subprocess.run(
                ["make", "verify-v3-journal", f"JOURNAL={journal}"],
                cwd=ROOT,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=True,
            )
            verify_payload = json.loads(verify.stdout[verify.stdout.index("{"):])
            self.assertEqual(verify.returncode, 0)
            self.assertTrue(verify.stdout.strip())
            self.assertEqual(verify_payload["ok"], True)
            self.assertEqual(Path(verify_payload["journal"]), journal)
            self.assertTrue(all(isinstance(check, dict) for check in verify_payload["checks"]))
            self.assertTrue(verify_payload["checks"])
            for check in verify_payload["checks"]:
                self.assertIn("id", check)
                self.assertIn("status", check)
                self.assertIn("message", check)

    def test_makefile_verify_journal_target_requires_journal(self):
        result = subprocess.run(
            ["make", "verify-v3-journal"],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("JOURNAL is required", result.stderr)

    def test_cli_projection_outputs_stable_json_summary(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "journal.jsonl"
            plane = ControlPlane.from_jsonl_path(ROOT, path, clock=lambda: "2026-04-24T00:00:00Z")
            plane.request_run(run_id="run-cli-proj-001", correlation_id="corr-cli-proj-001", trace_id="trace-cli-proj-001")
            result = subprocess.run(
                [sys.executable, str(ROOT / "tools/v3_control_plane.py"), "projection", "--journal", str(path)],
                cwd=ROOT,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=True,
            )

            payload = json.loads(result.stdout)
            self.assertEqual(payload["ok"], True)
            self.assertEqual(payload["projection"]["runs"]["run-cli-proj-001"]["currentState"], "validating")
            self.assertEqual(payload["projection"]["attempts"], {})
            self.assertEqual(payload["projection"]["routeDecisions"], {})
            self.assertEqual(payload["projection"]["unknownEvents"], [])

    def test_cli_illegal_transition_exits_nonzero_without_polluting_journal(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "journal.jsonl"
            ok = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "tools/v3_control_plane.py"),
                    "request-run",
                    "--journal",
                    str(path),
                    "--run-id",
                    "run-cli-bad-001",
                    "--correlation-id",
                    "corr-cli-bad-001",
                    "--trace-id",
                    "trace-cli-bad-001",
                ],
                cwd=ROOT,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=True,
            )
            before = path.read_text(encoding="utf-8")
            bad = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "tools/v3_control_plane.py"),
                    "transition-run",
                    "--journal",
                    str(path),
                    "--run-id",
                    "run-cli-bad-001",
                    "--old-state",
                    "validating",
                    "--new-state",
                    "completed",
                    "--transition-trigger",
                    "closure_success",
                    "--correlation-id",
                    "corr-cli-bad-001",
                    "--trace-id",
                    "trace-cli-bad-001",
                ],
                cwd=ROOT,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

            self.assertEqual(json.loads(ok.stdout)["event"]["sequenceNo"], 1)
            self.assertNotEqual(bad.returncode, 0)
            self.assertIn("illegal run transition", bad.stderr)
            self.assertEqual(path.read_text(encoding="utf-8"), before)

    def test_cli_request_run_and_transition_run_happy_path_persist_events(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "journal.jsonl"
            subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "tools/v3_control_plane.py"),
                    "request-run",
                    "--journal",
                    str(path),
                    "--run-id",
                    "run-cli-001",
                    "--correlation-id",
                    "corr-cli-001",
                    "--trace-id",
                    "trace-cli-001",
                ],
                cwd=ROOT,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=True,
            )
            transitioned = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "tools/v3_control_plane.py"),
                    "transition-run",
                    "--journal",
                    str(path),
                    "--run-id",
                    "run-cli-001",
                    "--old-state",
                    "validating",
                    "--new-state",
                    "planning",
                    "--transition-trigger",
                    "validation_passed",
                    "--correlation-id",
                    "corr-cli-001",
                    "--trace-id",
                    "trace-cli-001",
                ],
                cwd=ROOT,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=True,
            )

            event = json.loads(transitioned.stdout)["event"]
            self.assertEqual(event["sequenceNo"], 2)
            self.assertEqual(event["eventId"], "evt-corr-cli-001-0002")
            projection = ControlPlane.from_jsonl_path(ROOT, path).projection()
            self.assertEqual(projection.get_run("run-cli-001").currentState, "planning")
            self.assertEqual(len(path.read_text(encoding="utf-8").splitlines()), 2)

    def test_cli_record_route_decision_projects_stable_route_decision_json(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "journal.jsonl"
            recorded = self.run_cli(
                "record-route-decision",
                "--journal", str(path),
                "--run-id", "run-cli-route-001",
                "--attempt-id", "attempt-cli-route-001",
                "--route-decision-id", "rd-cli-route-001",
                "--workload-class", "code",
                "--route-policy-ref", "policy://routing/v3/default",
                "--selected-executor-class", "code_executor",
                "--fallback-depth", "0",
                "--decision-reason", "primary_policy_match",
                "--correlation-id", "corr-cli-route-001",
                "--trace-id", "trace-cli-route-001",
                check=True,
            )
            projection = self.run_cli("projection", "--journal", str(path), check=True)

            event = json.loads(recorded.stdout)["event"]
            payload = json.loads(projection.stdout)
            route = payload["projection"]["routeDecisions"]["rd-cli-route-001"]
            self.assertEqual(event["eventName"], "route.decision.recorded")
            self.assertEqual(route["eventId"], event["eventId"])
            self.assertEqual(route["decision"]["workloadClass"], "code")
            self.assertEqual(list(payload["projection"]["routeDecisions"].keys()), ["rd-cli-route-001"])
            self.assertEqual(list(payload["projection"]["runs"].keys()), ["run-cli-route-001"])
            self.assertEqual(list(payload["projection"]["attempts"].keys()), ["attempt-cli-route-001"])

    def test_cli_transition_attempt_created_booting_active_happy_path(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "journal.jsonl"
            first = self.run_cli(
                "transition-attempt",
                "--journal", str(path),
                "--run-id", "run-cli-attempt-001",
                "--attempt-id", "attempt-cli-attempt-001",
                "--old-state", "created",
                "--new-state", "booting",
                "--transition-trigger", "sandbox_allocated",
                "--correlation-id", "corr-cli-attempt-001",
                "--trace-id", "trace-cli-attempt-001",
                check=True,
            )
            second = self.run_cli(
                "transition-attempt",
                "--journal", str(path),
                "--run-id", "run-cli-attempt-001",
                "--attempt-id", "attempt-cli-attempt-001",
                "--old-state", "booting",
                "--new-state", "active",
                "--transition-trigger", "first_checkpoint",
                "--correlation-id", "corr-cli-attempt-001",
                "--trace-id", "trace-cli-attempt-001",
                check=True,
            )
            projection = json.loads(self.run_cli("projection", "--journal", str(path), check=True).stdout)["projection"]

            self.assertEqual(json.loads(first.stdout)["event"]["sequenceNo"], 1)
            self.assertEqual(json.loads(second.stdout)["event"]["sequenceNo"], 2)
            self.assertEqual(projection["attempts"]["attempt-cli-attempt-001"]["currentState"], "active")
            self.assertEqual(projection["attempts"]["attempt-cli-attempt-001"]["eventIds"], [
                "evt-corr-cli-attempt-001-0001",
                "evt-corr-cli-attempt-001-0002",
            ])

    def test_cli_park_manual_and_rehydrate_manual_project_attempt_supersession(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "journal.jsonl"
            for args in [
                ("request-run", "--journal", str(path), "--run-id", "run-cli-manual-001", "--correlation-id", "corr-cli-manual-001", "--trace-id", "trace-cli-manual-001"),
                ("transition-run", "--journal", str(path), "--run-id", "run-cli-manual-001", "--old-state", "validating", "--new-state", "planning", "--transition-trigger", "validation_passed", "--correlation-id", "corr-cli-manual-001", "--trace-id", "trace-cli-manual-001"),
                ("transition-run", "--journal", str(path), "--run-id", "run-cli-manual-001", "--old-state", "planning", "--new-state", "executing", "--transition-trigger", "execution_starts", "--correlation-id", "corr-cli-manual-001", "--trace-id", "trace-cli-manual-001"),
                ("transition-attempt", "--journal", str(path), "--run-id", "run-cli-manual-001", "--attempt-id", "attempt-cli-manual-001", "--old-state", "created", "--new-state", "booting", "--transition-trigger", "sandbox_allocated", "--correlation-id", "corr-cli-manual-001", "--trace-id", "trace-cli-manual-001"),
                ("transition-attempt", "--journal", str(path), "--run-id", "run-cli-manual-001", "--attempt-id", "attempt-cli-manual-001", "--old-state", "booting", "--new-state", "active", "--transition-trigger", "first_checkpoint", "--correlation-id", "corr-cli-manual-001", "--trace-id", "trace-cli-manual-001"),
            ]:
                self.run_cli(*args, check=True)

            parked = self.run_cli(
                "park-manual",
                "--journal", str(path),
                "--run-id", "run-cli-manual-001",
                "--attempt-id", "attempt-cli-manual-001",
                "--park-id", "park-cli-manual-001",
                "--manual-gate-type", "operator_review",
                "--rehydration-token-id", "rt-cli-manual-001",
                "--correlation-id", "corr-cli-manual-001",
                "--trace-id", "trace-cli-manual-001",
                check=True,
            )
            rehydrated = self.run_cli(
                "rehydrate-manual",
                "--journal", str(path),
                "--run-id", "run-cli-manual-001",
                "--previous-attempt-id", "attempt-cli-manual-001",
                "--new-attempt-id", "attempt-cli-manual-002",
                "--rehydration-token-id", "rt-cli-manual-001",
                "--correlation-id", "corr-cli-manual-001",
                "--trace-id", "trace-cli-manual-001",
                check=True,
            )
            projection = json.loads(self.run_cli("projection", "--journal", str(path), check=True).stdout)["projection"]

            self.assertEqual(json.loads(parked.stdout)["event"]["eventName"], "manual_gate.parked")
            self.assertEqual(json.loads(rehydrated.stdout)["event"]["eventName"], "manual_gate.rehydrated")
            self.assertEqual(projection["runs"]["run-cli-manual-001"]["currentState"], "planning")
            self.assertEqual(projection["attempts"]["attempt-cli-manual-001"]["currentState"], "superseded")
            self.assertEqual(projection["attempts"]["attempt-cli-manual-002"]["currentState"], "created")

    def test_cli_illegal_transition_attempt_outputs_json_error_without_polluting_journal(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "journal.jsonl"
            self.run_cli(
                "transition-attempt",
                "--journal", str(path),
                "--run-id", "run-cli-attempt-bad-001",
                "--attempt-id", "attempt-cli-attempt-bad-001",
                "--old-state", "created",
                "--new-state", "booting",
                "--transition-trigger", "sandbox_allocated",
                "--correlation-id", "corr-cli-attempt-bad-001",
                "--trace-id", "trace-cli-attempt-bad-001",
                check=True,
            )
            before = path.read_text(encoding="utf-8")

            bad = self.run_cli(
                "transition-attempt",
                "--journal", str(path),
                "--run-id", "run-cli-attempt-bad-001",
                "--attempt-id", "attempt-cli-attempt-bad-001",
                "--old-state", "booting",
                "--new-state", "superseded",
                "--transition-trigger", "new_attempt_launched",
                "--correlation-id", "corr-cli-attempt-bad-001",
                "--trace-id", "trace-cli-attempt-bad-001",
            )

            error = json.loads(bad.stderr)
            self.assertNotEqual(bad.returncode, 0)
            self.assertEqual(error["ok"], False)
            self.assertEqual(error["error"]["type"], "ControlPlaneError")
            self.assertIn("illegal attempt transition", error["error"]["message"])
            self.assertEqual(path.read_text(encoding="utf-8"), before)

    def test_cli_duplicate_event_id_outputs_stable_json_error(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "journal.jsonl"
            self.run_cli(
                "request-run",
                "--journal", str(path),
                "--run-id", "run-cli-dup-001",
                "--correlation-id", "corr-cli-dup-001",
                "--trace-id", "trace-cli-dup-001",
                "--event-id", "evt-cli-dup-fixed",
                check=True,
            )
            before = path.read_text(encoding="utf-8")

            duplicate = self.run_cli(
                "transition-run",
                "--journal", str(path),
                "--run-id", "run-cli-dup-001",
                "--old-state", "validating",
                "--new-state", "planning",
                "--transition-trigger", "validation_passed",
                "--correlation-id", "corr-cli-dup-001",
                "--trace-id", "trace-cli-dup-001",
                "--event-id", "evt-cli-dup-fixed",
            )

            error = json.loads(duplicate.stderr)
            self.assertEqual(duplicate.stdout, "")
            self.assertNotEqual(duplicate.returncode, 0)
            self.assertEqual(error, {
                "ok": False,
                "error": {
                    "type": "ControlPlaneError",
                    "message": "duplicate eventId 'evt-cli-dup-fixed'",
                },
            })
            self.assertEqual(path.read_text(encoding="utf-8"), before)


if __name__ == "__main__":
    unittest.main()
