from __future__ import annotations

import csv
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from .protocol import EventEnvelope, PROTOCOL_RELEASE_TAG, RouteDecision


class ProjectionReplayError(ValueError):
    """Raised when a journal cannot be reduced into V3 projections."""


@dataclass(frozen=True)
class RunProjection:
    runId: str
    currentState: str
    eventIds: tuple[str, ...] = ()


@dataclass(frozen=True)
class AttemptProjection:
    attemptId: str
    runId: str
    currentState: str
    eventIds: tuple[str, ...] = ()


@dataclass(frozen=True)
class RouteDecisionProjection:
    decision: RouteDecision
    eventId: str


@dataclass(frozen=True)
class ProjectionState:
    runs: Dict[str, RunProjection] = field(default_factory=dict)
    attempts: Dict[str, AttemptProjection] = field(default_factory=dict)
    route_decisions: Dict[str, RouteDecisionProjection] = field(default_factory=dict)
    unknown_events: tuple[EventEnvelope, ...] = ()

    def get_run(self, run_id: str) -> Optional[RunProjection]:
        return self.runs.get(run_id)

    def get_attempt(self, attempt_id: str) -> Optional[AttemptProjection]:
        return self.attempts.get(attempt_id)

    def get_route_decision(self, route_decision_id: str) -> Optional[RouteDecisionProjection]:
        return self.route_decisions.get(route_decision_id)


_DEFAULT_TRANSITIONS = {
    ("run", "requested", "request_accepted", "validating"),
    ("run", "validating", "validation_passed", "planning"),
    ("run", "validating", "validation_failed", "failed"),
    ("run", "planning", "approval_required", "waiting_approval"),
    ("run", "planning", "execution_starts", "executing"),
    ("run", "executing", "human_input_required", "waiting_input"),
    ("run", "executing", "manual_park_requested", "parked_manual"),
    ("run", "parked_manual", "rehydration_requested", "rehydrating"),
    ("run", "rehydrating", "rehydration_completed", "planning"),
    ("run", "executing", "takeover_starts", "finalizing"),
    ("run", "finalizing", "closure_success", "completed"),
    ("run", "finalizing", "closure_failed", "failed"),
    ("run", "finalizing", "cancel_wins", "cancelled"),
    ("attempt", "created", "sandbox_allocated", "booting"),
    ("attempt", "booting", "first_checkpoint", "active"),
    ("attempt", "active", "override_or_recon_request", "frozen"),
    ("attempt", "active", "lease_lost_or_worker_crash", "handoff_pending"),
    ("attempt", "active", "manual_park_requested", "parked_manual"),
    ("attempt", "frozen", "recon_required", "rehydrate_pending"),
    ("attempt", "parked_manual", "rehydration_requested", "rehydrate_pending"),
    ("attempt", "rehydrate_pending", "new_attempt_launched", "superseded"),
    ("attempt", "handoff_pending", "closure_claim_success", "finalizer_owned"),
    ("attempt", "finalizer_owned", "closure_succeeded", "succeeded"),
    ("attempt", "finalizer_owned", "closure_failed", "failed"),
    ("attempt", "finalizer_owned", "closure_cancelled", "cancelled"),
}


def load_state_transitions(root: Path | str) -> set[Tuple[str, str, str, str]]:
    path = Path(root) / "paperclip_darkfactory_v3_0_state_transition_matrix.csv"
    if not path.exists():
        return set(_DEFAULT_TRANSITIONS)
    with path.open(newline="", encoding="utf-8") as handle:
        return {
            (row["domain"], row["current_state"], row["trigger"], row["next_state"])
            for row in csv.DictReader(handle)
            if row["domain"] in {"run", "attempt"}
        }


class RunLifecycleReducer:
    """Minimal V3 control-plane projection reducer.

    The reducer treats the append-only EventEnvelope stream as the truth path and
    builds queryable read models for runs, attempts, and route decisions. Unknown
    event families are retained for audit/replay diagnostics without blocking
    projection of known runtime events.
    """

    def __init__(self, *, transitions: Optional[Iterable[Tuple[str, str, str, str]]] = None, root: Path | str | None = None) -> None:
        if transitions is not None:
            self._transitions = set(transitions)
        elif root is not None:
            self._transitions = load_state_transitions(root)
        else:
            self._transitions = set(_DEFAULT_TRANSITIONS)

    def replay(self, events: Sequence[EventEnvelope]) -> ProjectionState:
        runs: Dict[str, RunProjection] = {}
        attempts: Dict[str, AttemptProjection] = {}
        route_decisions: Dict[str, RouteDecisionProjection] = {}
        unknown_events: List[EventEnvelope] = []

        for event in events:
            if event.protocolReleaseTag != PROTOCOL_RELEASE_TAG:
                raise ProjectionReplayError(f"event {event.eventId} has invalid protocolReleaseTag")
            if event.eventName == "route.decision.recorded":
                self._apply_route_decision(event, runs, attempts, route_decisions)
            elif event.eventName == "run.lifecycle.transitioned":
                self._apply_run_transition(event, runs)
            elif event.eventName == "attempt.lifecycle.transitioned":
                self._apply_attempt_transition(event, attempts)
            elif event.eventName == "manual_gate.parked":
                self._apply_manual_parked(event, runs, attempts)
            elif event.eventName == "manual_gate.rehydrated":
                self._apply_manual_rehydrated(event, runs, attempts)
            else:
                unknown_events.append(event)

        return ProjectionState(
            runs=dict(runs),
            attempts=dict(attempts),
            route_decisions=dict(route_decisions),
            unknown_events=tuple(unknown_events),
        )

    def _apply_route_decision(
        self,
        event: EventEnvelope,
        runs: Dict[str, RunProjection],
        attempts: Dict[str, AttemptProjection],
        route_decisions: Dict[str, RouteDecisionProjection],
    ) -> None:
        run_id = self._required(event, "runId", event.runId)
        attempt_id = self._required(event, "attemptId", event.attemptId)
        decision_id = self._required(event, "routeDecisionId", event.payload.get("routeDecisionId"))
        if decision_id in route_decisions:
            raise ProjectionReplayError(f"duplicate routeDecisionId {decision_id!r}")
        decision = RouteDecision(
            routeDecisionId=decision_id,
            runId=run_id,
            attemptId=attempt_id,
            workloadClass=self._required(event, "workloadClass", event.payload.get("workloadClass")),
            routePolicyRef=self._required(event, "routePolicyRef", event.payload.get("routePolicyRef")),
            selectedExecutorClass=self._required(event, "selectedExecutorClass", event.payload.get("selectedExecutorClass")),
            fallbackDepth=event.payload.get("fallbackDepth", 0),
            decisionReason=self._required(event, "decisionReason", event.payload.get("decisionReason")),
            routeDecisionState=event.payload.get("routeDecisionState", "selected_primary"),
            recordedAt=event.payload.get("recordedAt", event.emittedAt),
        )
        route_decisions[decision_id] = RouteDecisionProjection(decision=decision, eventId=event.eventId)
        self._ensure_run(runs, run_id, event.eventId, preferred_state="planning")
        self._ensure_attempt(attempts, attempt_id, run_id, event.eventId, preferred_state="created")

    def _apply_manual_parked(
        self,
        event: EventEnvelope,
        runs: Dict[str, RunProjection],
        attempts: Dict[str, AttemptProjection],
    ) -> None:
        run_id = self._required(event, "runId", event.runId)
        self._transition_run(runs, run_id, "executing", "manual_park_requested", "parked_manual", event.eventId, allow_bootstrap=True)
        attempt_id = event.attemptId or event.payload.get("attemptId")
        if attempt_id:
            self._transition_attempt(attempts, attempt_id, run_id, "active", "manual_park_requested", "parked_manual", event.eventId, allow_bootstrap=True)

    def _apply_manual_rehydrated(
        self,
        event: EventEnvelope,
        runs: Dict[str, RunProjection],
        attempts: Dict[str, AttemptProjection],
    ) -> None:
        run_id = self._required(event, "runId", event.runId)
        self._transition_run(runs, run_id, "parked_manual", "rehydration_requested", "rehydrating", event.eventId, allow_bootstrap=False)
        self._transition_run(runs, run_id, "rehydrating", "rehydration_completed", "planning", event.eventId, allow_bootstrap=False)

        previous_attempt_id = event.payload.get("previousAttemptId")
        if previous_attempt_id:
            self._transition_attempt(attempts, previous_attempt_id, run_id, "parked_manual", "rehydration_requested", "rehydrate_pending", event.eventId, allow_bootstrap=True)
            self._transition_attempt(attempts, previous_attempt_id, run_id, "rehydrate_pending", "new_attempt_launched", "superseded", event.eventId, allow_bootstrap=False)
        new_attempt_id = event.payload.get("newAttemptId") or event.attemptId
        if new_attempt_id:
            self._ensure_attempt(attempts, new_attempt_id, run_id, event.eventId, preferred_state="created")

    def _apply_run_transition(self, event: EventEnvelope, runs: Dict[str, RunProjection]) -> None:
        run_id = self._required(event, "runId", event.runId)
        old_state = self._required(event, "oldState", event.payload.get("oldState") or event.payload.get("fromState"))
        new_state = self._required(event, "newState", event.payload.get("newState") or event.payload.get("toState"))
        trigger = self._required(event, "transitionTrigger", event.payload.get("transitionTrigger") or event.payload.get("trigger"))
        self._transition_run(runs, run_id, old_state, trigger, new_state, event.eventId, allow_bootstrap=True)

    def _apply_attempt_transition(self, event: EventEnvelope, attempts: Dict[str, AttemptProjection]) -> None:
        run_id = self._required(event, "runId", event.runId)
        attempt_id = self._required(event, "attemptId", event.attemptId)
        old_state = self._required(event, "oldState", event.payload.get("oldState") or event.payload.get("fromState"))
        new_state = self._required(event, "newState", event.payload.get("newState") or event.payload.get("toState"))
        trigger = self._required(event, "transitionTrigger", event.payload.get("transitionTrigger") or event.payload.get("trigger"))
        self._transition_attempt(attempts, attempt_id, run_id, old_state, trigger, new_state, event.eventId, allow_bootstrap=True)

    def _transition_run(
        self,
        runs: Dict[str, RunProjection],
        run_id: str,
        old_state: str,
        trigger: str,
        new_state: str,
        event_id: str,
        *,
        allow_bootstrap: bool,
    ) -> None:
        self._assert_legal("run", old_state, trigger, new_state, event_id)
        current = runs.get(run_id)
        if current is None:
            if not allow_bootstrap:
                raise ProjectionReplayError(f"run {run_id!r} missing before transition event {event_id}")
            current = RunProjection(runId=run_id, currentState=old_state)
        elif current.currentState != old_state:
            raise ProjectionReplayError(
                f"run {run_id!r} transition state mismatch at {event_id}: expected {old_state!r}, got {current.currentState!r}"
            )
        runs[run_id] = replace(current, currentState=new_state, eventIds=current.eventIds + (event_id,))

    def _transition_attempt(
        self,
        attempts: Dict[str, AttemptProjection],
        attempt_id: str,
        run_id: str,
        old_state: str,
        trigger: str,
        new_state: str,
        event_id: str,
        *,
        allow_bootstrap: bool,
    ) -> None:
        self._assert_legal("attempt", old_state, trigger, new_state, event_id)
        current = attempts.get(attempt_id)
        if current is None:
            if not allow_bootstrap:
                raise ProjectionReplayError(f"attempt {attempt_id!r} missing before transition event {event_id}")
            current = AttemptProjection(attemptId=attempt_id, runId=run_id, currentState=old_state)
        elif current.currentState != old_state:
            raise ProjectionReplayError(
                f"attempt {attempt_id!r} transition state mismatch at {event_id}: expected {old_state!r}, got {current.currentState!r}"
            )
        attempts[attempt_id] = replace(current, currentState=new_state, eventIds=current.eventIds + (event_id,))

    def _ensure_run(self, runs: Dict[str, RunProjection], run_id: str, event_id: str, *, preferred_state: str) -> None:
        current = runs.get(run_id)
        if current is None:
            runs[run_id] = RunProjection(runId=run_id, currentState=preferred_state, eventIds=(event_id,))
        else:
            runs[run_id] = replace(current, eventIds=current.eventIds + (event_id,))

    def _ensure_attempt(
        self,
        attempts: Dict[str, AttemptProjection],
        attempt_id: str,
        run_id: str,
        event_id: str,
        *,
        preferred_state: str,
    ) -> None:
        current = attempts.get(attempt_id)
        if current is None:
            attempts[attempt_id] = AttemptProjection(attemptId=attempt_id, runId=run_id, currentState=preferred_state, eventIds=(event_id,))
        else:
            attempts[attempt_id] = replace(current, eventIds=current.eventIds + (event_id,))

    def _assert_legal(self, domain: str, old_state: str, trigger: str, new_state: str, event_id: str) -> None:
        if (domain, old_state, trigger, new_state) not in self._transitions:
            raise ProjectionReplayError(
                f"illegal {domain} transition at {event_id}: {old_state!r} --{trigger!r}--> {new_state!r}"
            )

    @staticmethod
    def _required(event: EventEnvelope, field_name: str, value: object) -> str:
        if not isinstance(value, str) or not value:
            raise ProjectionReplayError(f"event {event.eventId} missing required projection field {field_name}")
        return value
