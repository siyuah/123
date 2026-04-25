from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Dict, Optional

from .journal import InMemoryAppendOnlyJournal, JournalAppendError
from .projection import ProjectionReplayError, ProjectionState, RunLifecycleReducer
from .protocol import EventEnvelope, load_event_contracts


class ControlPlaneError(ValueError):
    """Raised when the V3 control-plane command layer rejects a command."""


Clock = Callable[[], str]


@dataclass
class ControlPlane:
    """Minimal journal-first V3 command/execution kernel.

    The control plane accepts command-shaped method calls, turns them into
    contract-backed EventEnvelope records, validates the resulting projection,
    then appends to the append-only journal only after the candidate timeline is
    known to replay cleanly.
    """

    root: Path | str
    journal: InMemoryAppendOnlyJournal = field(default_factory=InMemoryAppendOnlyJournal)
    clock: Clock = lambda: "1970-01-01T00:00:00Z"
    producer: str = "dark-factory-control-plane"

    def __post_init__(self) -> None:
        self.root = Path(self.root)
        self._contracts = load_event_contracts(self.root)
        self._reducer = RunLifecycleReducer(root=self.root)

    def request_run(
        self,
        *,
        run_id: str,
        correlation_id: str,
        trace_id: str,
        event_id: Optional[str] = None,
    ) -> EventEnvelope:
        return self.transition_run(
            run_id=run_id,
            old_state="requested",
            new_state="validating",
            transition_trigger="request_accepted",
            correlation_id=correlation_id,
            trace_id=trace_id,
            causation_id=run_id,
            event_id=event_id,
        )

    start_run = request_run

    def record_route_decision(
        self,
        *,
        run_id: str,
        attempt_id: str,
        route_decision_id: str,
        workload_class: str,
        route_policy_ref: str,
        selected_executor_class: str,
        fallback_depth: int,
        decision_reason: str,
        correlation_id: str,
        trace_id: str,
        route_decision_state: str = "selected_primary",
        recorded_at: Optional[str] = None,
        event_id: Optional[str] = None,
    ) -> EventEnvelope:
        payload = {
            "routeDecisionId": route_decision_id,
            "workloadClass": workload_class,
            "routePolicyRef": route_policy_ref,
            "selectedExecutorClass": selected_executor_class,
            "fallbackDepth": fallback_depth,
            "decisionReason": decision_reason,
            "routeDecisionState": route_decision_state,
            "recordedAt": recorded_at or self.clock(),
        }
        return self._append_contract_event(
            event_name="route.decision.recorded",
            event_id=event_id or self._next_event_id(correlation_id),
            trace_id=trace_id,
            causation_id=run_id,
            correlation_id=correlation_id,
            run_id=run_id,
            attempt_id=attempt_id,
            payload=payload,
        )

    def transition_run(
        self,
        *,
        run_id: str,
        old_state: str,
        new_state: str,
        transition_trigger: str,
        correlation_id: str,
        trace_id: str,
        causation_id: Optional[str] = None,
        event_id: Optional[str] = None,
    ) -> EventEnvelope:
        return self._append_contract_event(
            event_name="run.lifecycle.transitioned",
            event_id=event_id or self._next_event_id(correlation_id),
            trace_id=trace_id,
            causation_id=causation_id or run_id,
            correlation_id=correlation_id,
            run_id=run_id,
            payload={
                "oldState": old_state,
                "newState": new_state,
                "transitionTrigger": transition_trigger,
            },
        )

    def transition_attempt(
        self,
        *,
        run_id: str,
        attempt_id: str,
        old_state: str,
        new_state: str,
        transition_trigger: str,
        correlation_id: str,
        trace_id: str,
        causation_id: Optional[str] = None,
        event_id: Optional[str] = None,
    ) -> EventEnvelope:
        return self._append_contract_event(
            event_name="attempt.lifecycle.transitioned",
            event_id=event_id or self._next_event_id(correlation_id),
            trace_id=trace_id,
            causation_id=causation_id or run_id,
            correlation_id=correlation_id,
            run_id=run_id,
            attempt_id=attempt_id,
            payload={
                "oldState": old_state,
                "newState": new_state,
                "transitionTrigger": transition_trigger,
            },
        )

    def park_manual(
        self,
        *,
        run_id: str,
        attempt_id: str,
        park_id: str,
        manual_gate_type: str,
        rehydration_token_id: str,
        correlation_id: str,
        trace_id: str,
        execution_suspension_state: str = "resources_released_truth_obligation_retained",
        parked_at: Optional[str] = None,
        event_id: Optional[str] = None,
    ) -> EventEnvelope:
        return self._append_contract_event(
            event_name="manual_gate.parked",
            event_id=event_id or self._next_event_id(correlation_id),
            trace_id=trace_id,
            causation_id=run_id,
            correlation_id=correlation_id,
            run_id=run_id,
            attempt_id=attempt_id,
            payload={
                "runId": run_id,
                "parkId": park_id,
                "manualGateType": manual_gate_type,
                "executionSuspensionState": execution_suspension_state,
                "parkedAt": parked_at or self.clock(),
                "rehydrationTokenId": rehydration_token_id,
                "attemptId": attempt_id,
            },
        )

    def rehydrate_manual(
        self,
        *,
        run_id: str,
        previous_attempt_id: str,
        new_attempt_id: str,
        rehydration_token_id: str,
        correlation_id: str,
        trace_id: str,
        rehydrated_at: Optional[str] = None,
        event_id: Optional[str] = None,
    ) -> EventEnvelope:
        return self._append_contract_event(
            event_name="manual_gate.rehydrated",
            event_id=event_id or self._next_event_id(correlation_id),
            trace_id=trace_id,
            causation_id=previous_attempt_id,
            correlation_id=correlation_id,
            run_id=run_id,
            attempt_id=new_attempt_id,
            payload={
                "runId": run_id,
                "rehydrationTokenId": rehydration_token_id,
                "rehydratedAt": rehydrated_at or self.clock(),
                "previousAttemptId": previous_attempt_id,
                "newAttemptId": new_attempt_id,
            },
        )

    def projection(self) -> ProjectionState:
        return self._reducer.replay(self.journal.read_all())

    def get_run(self, run_id: str):
        return self.projection().get_run(run_id)

    def get_attempt(self, attempt_id: str):
        return self.projection().get_attempt(attempt_id)

    def get_route_decision(self, route_decision_id: str):
        return self.projection().get_route_decision(route_decision_id)

    def _append_contract_event(
        self,
        *,
        event_name: str,
        event_id: str,
        trace_id: str,
        causation_id: str,
        correlation_id: str,
        payload: Dict[str, object],
        run_id: Optional[str] = None,
        attempt_id: Optional[str] = None,
    ) -> EventEnvelope:
        idempotency_key = self._idempotency_key(event_name, payload, event_id)
        if event_name in self._contracts:
            event = EventEnvelope.from_contract(
                self._contracts,
                eventName=event_name,
                eventId=event_id,
                emittedAt=self.clock(),
                traceId=trace_id,
                producer=self.producer,
                causationId=causation_id,
                correlationId=correlation_id,
                sequenceNo=self._next_sequence_no(correlation_id),
                runId=run_id,
                attemptId=attempt_id,
                idempotencyKey=idempotency_key,
                payload=payload,
            )
        else:
            if event_name not in {"run.lifecycle.transitioned", "attempt.lifecycle.transitioned"}:
                raise ControlPlaneError(f"unknown eventName {event_name!r}")
            event = EventEnvelope(
                eventName=event_name,
                eventVersion="v1",
                eventId=event_id,
                emittedAt=self.clock(),
                traceId=trace_id,
                producer=self.producer,
                causationId=causation_id,
                correlationId=correlation_id,
                sequenceNo=self._next_sequence_no(correlation_id),
                partitionKey="runId",
                orderingScope="attempt" if event_name.startswith("attempt.") else "run",
                idempotencyKey=idempotency_key,
                runId=run_id,
                attemptId=attempt_id,
                payload=payload,
            )
        try:
            self._reducer.replay(self.journal.read_all() + [event])
            return self.journal.append(event)
        except (ProjectionReplayError, JournalAppendError, ValueError) as exc:
            raise ControlPlaneError(str(exc)) from exc

    def _next_sequence_no(self, correlation_id: str) -> int:
        return len(self.journal.read_by_correlation(correlation_id)) + 1

    def _next_event_id(self, correlation_id: str) -> str:
        return f"evt-{correlation_id}-{self._next_sequence_no(correlation_id):04d}"

    def _idempotency_key(self, event_name: str, payload: Dict[str, object], event_id: str) -> str:
        if event_name == "route.decision.recorded" and payload.get("routeDecisionId"):
            return str(payload["routeDecisionId"])
        if event_name == "manual_gate.parked" and payload.get("parkId"):
            return str(payload["parkId"])
        if event_name == "manual_gate.rehydrated" and payload.get("rehydrationTokenId"):
            return str(payload["rehydrationTokenId"])
        return event_id


CommandHandler = ControlPlane
