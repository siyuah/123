"""Dark Factory V3 HTTP Server

Wraps the existing ControlPlane, Journal, and Projection modules as a
lightweight REST API for local development and integration testing.

Usage:
    python3 server.py                    # default port 9701
    python3 server.py --port 9702        # custom port
    python3 server.py --journal /tmp/df  # custom journal dir
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time
import uuid
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable, Iterable, Optional

from fastapi import FastAPI, Header, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dark_factory_v3.control_plane import ControlPlane, ControlPlaneError  # noqa: E402
from dark_factory_v3.projection import ProjectionState, RouteDecisionProjection  # noqa: E402
from dark_factory_v3.protocol import PROTOCOL_RELEASE_TAG  # noqa: E402


DEFAULT_PORT = 9701
DEFAULT_JOURNAL_PATH = ROOT / ".dark_factory_http" / "journal.jsonl"
DEFAULT_ROUTE_POLICY_REF = "policy://routing/v3/default"
SERVER_VERSION = "3.0.0-local-mvp.1"
DEFAULT_EXECUTOR_BY_WORKLOAD = {
    "chat": "general_chat_executor",
    "code": "code_executor",
    "reasoning": "reasoning_executor",
    "vision": "vision_executor",
    "memory_maintenance": "memory_maintenance_executor",
    "repair": "repair_executor",
    "operator_adjudication": "operator_adjudication_executor",
}


Clock = Callable[[], str]
LOGGER = logging.getLogger("dark_factory_v3.http")
SENSITIVE_FIELD_MARKERS = ("api_key", "apikey", "authorization", "password", "secret", "token", "x-api-key")
REDACTED = "***REDACTED***"


def utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")


class JsonLogFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": utc_now(),
            "level": record.levelname,
            "message": record.getMessage(),
        }
        structured = getattr(record, "structured", None)
        if isinstance(structured, dict):
            payload.update(structured)
        return json.dumps(payload, ensure_ascii=False, sort_keys=True)


def configure_logging() -> None:
    if LOGGER.handlers:
        return
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonLogFormatter())
    LOGGER.addHandler(handler)
    LOGGER.setLevel(logging.INFO)
    LOGGER.propagate = False


def log_event(level: int, message: str, **fields: Any) -> None:
    LOGGER.log(level, message, extra={"structured": fields})


def redact_sensitive(value: Any) -> Any:
    if isinstance(value, dict):
        redacted: dict[str, Any] = {}
        for key, nested in value.items():
            normalized_key = key.replace("-", "_").lower()
            if any(marker in normalized_key for marker in SENSITIVE_FIELD_MARKERS):
                redacted[key] = REDACTED
            else:
                redacted[key] = redact_sensitive(nested)
        return redacted
    if isinstance(value, list):
        return [redact_sensitive(item) for item in value]
    if isinstance(value, str) and len(value) > 2048:
        return value[:2048] + "...[truncated]"
    return value


def parse_request_body(raw_body: bytes) -> Any:
    if not raw_body:
        return None
    try:
        return json.loads(raw_body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return {"unparsedBodyBytes": len(raw_body)}


def trace_id_from_request(request: Request, body: Any = None) -> str:
    header_trace_id = request.headers.get("x-trace-id")
    if header_trace_id:
        return header_trace_id
    if isinstance(body, dict):
        trace_id = body.get("traceId") or body.get("trace_id")
        if isinstance(trace_id, str) and trace_id:
            return trace_id
    return f"trace-{uuid.uuid4().hex}"


def mask_client_ip(host: str | None) -> str:
    if not host:
        return "unknown"
    if "." in host:
        parts = host.split(".")
        if len(parts) >= 4:
            return ".".join(parts[:2] + ["x", "x"])
    if ":" in host:
        parts = host.split(":")
        return ":".join(parts[:2] + ["x", "x"])
    return "unknown"


def stable_projection_value(value: Any) -> Any:
    if isinstance(value, tuple):
        return [stable_projection_value(item) for item in value]
    if isinstance(value, list):
        return [stable_projection_value(item) for item in value]
    if isinstance(value, dict):
        return {key: stable_projection_value(value[key]) for key in sorted(value)}
    return value


def projection_to_dict(projection: ProjectionState) -> dict[str, Any]:
    return {
        "runs": {
            key: stable_projection_value(asdict(value))
            for key, value in sorted(projection.runs.items())
        },
        "attempts": {
            key: stable_projection_value(asdict(value))
            for key, value in sorted(projection.attempts.items())
        },
        "routeDecisions": {
            key: {
                "decision": stable_projection_value(asdict(value.decision)),
                "eventId": value.eventId,
            }
            for key, value in sorted(projection.route_decisions.items())
        },
        "unknownEvents": [event.to_dict() for event in sorted(projection.unknown_events, key=lambda event: event.eventId)],
    }


class ErrorResponse(BaseModel):
    protocolReleaseTag: str = PROTOCOL_RELEASE_TAG
    errorCode: str
    message: str
    traceId: str
    retryable: bool = False


class CreateExternalRunRequest(BaseModel):
    protocolReleaseTag: str
    requestedBy: str
    workloadClass: str
    inputRef: str
    traceId: str
    routePolicyRef: Optional[str] = None
    runId: Optional[str] = None
    attemptId: Optional[str] = None
    correlationId: Optional[str] = None
    selectedExecutorClass: Optional[str] = None
    decisionReason: Optional[str] = None


class ParkRunRequest(BaseModel):
    protocolReleaseTag: str
    manualGateType: str
    parkReasonCode: str
    attemptId: Optional[str] = None
    parkId: Optional[str] = None
    traceId: Optional[str] = None
    correlationId: Optional[str] = None
    rehydrationTokenId: Optional[str] = None
    executionSuspensionState: str = "resources_released_truth_obligation_retained"


class RehydrateRunRequest(BaseModel):
    protocolReleaseTag: str
    rehydrationTokenId: str
    previousAttemptId: Optional[str] = None
    newAttemptId: Optional[str] = None
    traceId: Optional[str] = None
    correlationId: Optional[str] = None


class RepairRunRequest(BaseModel):
    protocolReleaseTag: str
    triggeredBy: str
    triggerFaultClass: str
    repairPlanRef: str
    traceId: Optional[str] = None
    repairAttemptId: Optional[str] = None


class ArchiveRestoreRequest(BaseModel):
    protocolReleaseTag: str
    objectId: str
    restoreReason: str


class RunView(BaseModel):
    protocolReleaseTag: str = PROTOCOL_RELEASE_TAG
    runId: str
    runState: str
    traceId: str
    activeAttemptId: str
    blockedBy: list[str] = Field(default_factory=list)
    currentManualGateType: Optional[str] = None
    currentExecutionSuspensionState: Optional[str] = None
    routeDecisionId: Optional[str] = None
    journalCursor: str
    lastSequenceNo: int
    sourceJournalRef: str


class RouteDecisionView(BaseModel):
    protocolReleaseTag: str = PROTOCOL_RELEASE_TAG
    routeDecisionId: str
    runId: str
    workloadClass: str
    selectedExecutorClass: str
    fallbackDepth: int
    decisionReason: str
    routeDecisionState: str
    attemptId: str
    routePolicyRef: str
    recordedAt: str


class ProviderFailureView(BaseModel):
    protocolReleaseTag: str = PROTOCOL_RELEASE_TAG
    failureId: str
    runId: str
    providerFaultClass: str
    recoveryLane: str
    cutoverPerformed: bool = False


class RepairAttemptView(BaseModel):
    protocolReleaseTag: str = PROTOCOL_RELEASE_TAG
    repairAttemptId: str
    runId: str
    outcome: str
    verificationEvidenceRef: str
    operatorApprovalRequired: bool = False


class ArchiveSearchResult(BaseModel):
    protocolReleaseTag: str = PROTOCOL_RELEASE_TAG
    objectId: str
    objectType: str
    archivedAt: str
    truthBacked: bool


class HealthView(BaseModel):
    ok: bool
    protocolReleaseTag: str
    journal: str
    events: int
    projection: dict[str, int]


class ServerState:
    def __init__(self, *, root: Path, journal_path: Path, clock: Clock = utc_now, api_key: str | None = None, auth_enabled: bool = True) -> None:
        self.root = root
        self.journal_path = journal_path
        self.clock = clock
        self.api_key = api_key
        self.auth_enabled = auth_enabled

    def plane(self) -> ControlPlane:
        return ControlPlane.from_jsonl_path(self.root, self.journal_path, clock=self.clock)


def ensure_protocol(value: str | None, *, trace_id: str) -> None:
    if value != PROTOCOL_RELEASE_TAG:
        raise http_error(
            400,
            "protocol_release_tag_mismatch",
            f"protocolReleaseTag must be {PROTOCOL_RELEASE_TAG}",
            trace_id=trace_id,
        )


def http_error(status_code: int, error_code: str, message: str, *, trace_id: str, retryable: bool = False) -> HTTPException:
    return HTTPException(
        status_code=status_code,
        detail=ErrorResponse(errorCode=error_code, message=message, traceId=trace_id, retryable=retryable).model_dump(),
    )


def require_protocol_header(header_value: str | None, *, trace_id: str) -> None:
    ensure_protocol(header_value, trace_id=trace_id)


def request_trace_id(request: Request, body_trace_id: str | None = None) -> str:
    return body_trace_id or request.headers.get("x-trace-id") or f"trace-{uuid.uuid4().hex}"


def correlation_id_for(run_id: str, explicit: str | None = None) -> str:
    return explicit or f"corr-{run_id}"


def active_attempt_for(projection: ProjectionState, run_id: str) -> str:
    attempts = [attempt for attempt in projection.attempts.values() if attempt.runId == run_id]
    if not attempts:
        return ""
    active_states = {"created", "booting", "active", "frozen", "handoff_pending", "parked_manual", "rehydrate_pending", "finalizer_owned"}
    preferred = [attempt for attempt in attempts if attempt.currentState in active_states]
    selected = sorted(preferred or attempts, key=lambda attempt: attempt.attemptId)[-1]
    return selected.attemptId


def route_for_run(projection: ProjectionState, run_id: str) -> RouteDecisionProjection | None:
    decisions = [
        decision
        for decision in projection.route_decisions.values()
        if decision.decision.runId == run_id
    ]
    return sorted(decisions, key=lambda decision: decision.decision.routeDecisionId)[-1] if decisions else None


def last_sequence_no(plane: ControlPlane) -> int:
    events = plane.journal.read_all()
    return max((event.sequenceNo for event in events), default=0)


def source_journal_ref(journal_path: Path) -> str:
    return f"file://{journal_path}"


def journal_cursor(journal_path: Path, sequence_no: int) -> str:
    return f"dark-factory://journal/{journal_path.name}#{sequence_no}"


def run_view(plane: ControlPlane, run_id: str, *, trace_id: str) -> RunView:
    projection = plane.projection()
    run = projection.get_run(run_id)
    if run is None:
        raise http_error(404, "run_not_found", f"run {run_id!r} was not found", trace_id=trace_id)

    route = route_for_run(projection, run_id)
    last_seq = last_sequence_no(plane)
    manual_gate_event = None
    if run.currentState == "parked_manual":
        manual_gate_event = next(
            (
                event
                for event in reversed(plane.journal.read_all())
                if event.runId == run_id and event.eventName == "manual_gate.parked"
            ),
            None,
        )
    blocked_by: list[str] = []
    if run.currentState in {"waiting_approval", "waiting_input", "parked_manual"}:
        blocked_by.append(run.currentState)

    return RunView(
        runId=run.runId,
        runState=run.currentState,
        traceId=trace_id,
        activeAttemptId=active_attempt_for(projection, run_id),
        blockedBy=blocked_by,
        currentManualGateType=(manual_gate_event.payload.get("manualGateType") if manual_gate_event else None),
        currentExecutionSuspensionState=(manual_gate_event.payload.get("executionSuspensionState") if manual_gate_event else None),
        routeDecisionId=(route.decision.routeDecisionId if route else None),
        journalCursor=journal_cursor(plane.journal.path if hasattr(plane.journal, "path") else DEFAULT_JOURNAL_PATH, last_seq),
        lastSequenceNo=last_seq,
        sourceJournalRef=source_journal_ref(plane.journal.path if hasattr(plane.journal, "path") else DEFAULT_JOURNAL_PATH),
    )


def route_decision_view(value: RouteDecisionProjection) -> RouteDecisionView:
    decision = value.decision
    return RouteDecisionView(
        routeDecisionId=decision.routeDecisionId,
        runId=decision.runId,
        workloadClass=decision.workloadClass,
        selectedExecutorClass=decision.selectedExecutorClass,
        fallbackDepth=decision.fallbackDepth,
        decisionReason=decision.decisionReason,
        routeDecisionState=decision.routeDecisionState,
        attemptId=decision.attemptId,
        routePolicyRef=decision.routePolicyRef,
        recordedAt=decision.recordedAt,
    )


def require_existing_attempt(projection: ProjectionState, run_id: str, attempt_id: str | None, *, trace_id: str) -> str:
    if attempt_id:
        attempt = projection.get_attempt(attempt_id)
        if attempt is None or attempt.runId != run_id:
            raise http_error(404, "attempt_not_found", f"attempt {attempt_id!r} was not found for run {run_id!r}", trace_id=trace_id)
        return attempt_id
    active_attempt_id = active_attempt_for(projection, run_id)
    if not active_attempt_id:
        raise http_error(409, "run_has_no_attempt", f"run {run_id!r} does not have an attempt to operate on", trace_id=trace_id)
    return active_attempt_id


def activate_attempt_if_needed(plane: ControlPlane, *, run_id: str, attempt_id: str, correlation_id: str, trace_id: str) -> None:
    attempt = plane.projection().get_attempt(attempt_id)
    if attempt is None:
        raise http_error(404, "attempt_not_found", f"attempt {attempt_id!r} was not found for run {run_id!r}", trace_id=trace_id)
    if attempt.currentState == "created":
        plane.transition_attempt(
            run_id=run_id,
            attempt_id=attempt_id,
            old_state="created",
            new_state="booting",
            transition_trigger="sandbox_allocated",
            correlation_id=correlation_id,
            trace_id=trace_id,
        )
        attempt = plane.projection().get_attempt(attempt_id)
    if attempt and attempt.currentState == "booting":
        plane.transition_attempt(
            run_id=run_id,
            attempt_id=attempt_id,
            old_state="booting",
            new_state="active",
            transition_trigger="first_checkpoint",
            correlation_id=correlation_id,
            trace_id=trace_id,
        )


def create_app(*, journal_path: Path = DEFAULT_JOURNAL_PATH, root: Path = ROOT, api_key: str | None = None, auth_enabled: bool = True) -> FastAPI:
    configure_logging()
    state = ServerState(root=root, journal_path=journal_path, api_key=api_key, auth_enabled=auth_enabled)
    app = FastAPI(
        title="Paperclip Dark Factory V3.0 External Runs API",
        version="3.0.0",
        description="Local development HTTP facade for the Dark Factory V3 control plane.",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def security_and_logging_middleware(request: Request, call_next):
        start = time.perf_counter()
        raw_body = await request.body()
        parsed_body = parse_request_body(raw_body)
        trace_id = trace_id_from_request(request, parsed_body)
        redacted_body = redact_sensitive(parsed_body)
        status_code = 500
        response: Response
        try:
            is_health_check = request.method == "GET" and request.url.path in {"/api/health", "/health"}
            if state.auth_enabled and not is_health_check:
                provided_key = request.headers.get("x-api-key")
                if not state.api_key or provided_key != state.api_key:
                    response = JSONResponse(
                        status_code=401,
                        content={
                            "protocolReleaseTag": PROTOCOL_RELEASE_TAG,
                            "error": "unauthorized",
                            "message": "Invalid or missing API key",
                        },
                    )
                    status_code = response.status_code
                    return response
            response = await call_next(request)
            status_code = response.status_code
            return response
        except Exception as exc:
            status_code = 500
            log_event(
                logging.ERROR,
                "request_exception",
                trace_id=trace_id,
                exception_type=type(exc).__name__,
                exception_message=str(exc),
                method=request.method,
                path=request.url.path,
            )
            return JSONResponse(
                status_code=500,
                content=ErrorResponse(
                    errorCode="internal_server_error",
                    message="Internal server error",
                    traceId=trace_id,
                    retryable=True,
                ).model_dump(),
            )
        finally:
            duration_ms = round((time.perf_counter() - start) * 1000, 2)
            log_event(
                logging.INFO,
                "request",
                method=request.method,
                path=request.url.path,
                status_code=status_code,
                duration_ms=duration_ms,
                trace_id=trace_id,
                client_ip=mask_client_ip(request.client.host if request.client else None),
                request_body=redacted_body,
            )

    @app.exception_handler(HTTPException)
    async def http_exception_handler(_request: Request, exc: HTTPException) -> Response:
        detail = exc.detail
        if isinstance(detail, dict) and detail.get("protocolReleaseTag") == PROTOCOL_RELEASE_TAG:
            return JSONResponse(status_code=exc.status_code, content=detail)
        return JSONResponse(
            status_code=exc.status_code,
            content=ErrorResponse(errorCode="http_error", message=str(detail), traceId="trace-unavailable").model_dump(),
        )

    @app.get("/health", response_model=HealthView)
    @app.get("/api/health", response_model=HealthView)
    async def health() -> HealthView:
        plane = state.plane()
        projection = plane.projection()
        return HealthView(
            ok=True,
            protocolReleaseTag=PROTOCOL_RELEASE_TAG,
            journal=str(journal_path),
            events=len(plane.journal.read_all()),
            projection={
                "runs": len(projection.runs),
                "attempts": len(projection.attempts),
                "routeDecisions": len(projection.route_decisions),
                "unknownEvents": len(projection.unknown_events),
            },
        )

    @app.get("/projection")
    @app.get("/api/projection")
    async def projection() -> dict[str, Any]:
        plane = state.plane()
        return {
            "ok": True,
            "protocolReleaseTag": PROTOCOL_RELEASE_TAG,
            "journal": str(journal_path),
            "lastSequenceNo": last_sequence_no(plane),
            "projection": projection_to_dict(plane.projection()),
        }

    @app.post("/external-runs", status_code=201, response_model=RunView)
    @app.post("/api/external-runs", status_code=201, response_model=RunView)
    async def create_external_run(
        body: CreateExternalRunRequest,
        request: Request,
        x_protocol_release_tag: str | None = Header(default=None),
    ) -> RunView:
        trace_id = request_trace_id(request, body.traceId)
        require_protocol_header(x_protocol_release_tag, trace_id=trace_id)
        ensure_protocol(body.protocolReleaseTag, trace_id=trace_id)

        run_id = body.runId or f"run-{uuid.uuid4().hex}"
        attempt_id = body.attemptId or f"attempt-{uuid.uuid4().hex}"
        route_decision_id = f"rd-{run_id}"
        correlation_id = correlation_id_for(run_id, body.correlationId)
        plane = state.plane()
        if plane.get_run(run_id) is not None:
            return run_view(plane, run_id, trace_id=trace_id)

        try:
            plane.request_run(run_id=run_id, correlation_id=correlation_id, trace_id=trace_id)
            plane.record_route_decision(
                run_id=run_id,
                attempt_id=attempt_id,
                route_decision_id=route_decision_id,
                workload_class=body.workloadClass,
                route_policy_ref=body.routePolicyRef or DEFAULT_ROUTE_POLICY_REF,
                selected_executor_class=body.selectedExecutorClass or DEFAULT_EXECUTOR_BY_WORKLOAD.get(body.workloadClass, "general_executor"),
                fallback_depth=0,
                decision_reason=body.decisionReason or f"external_run_requested_by:{body.requestedBy}",
                correlation_id=correlation_id,
                trace_id=trace_id,
            )
            plane.transition_run(
                run_id=run_id,
                old_state="validating",
                new_state="planning",
                transition_trigger="validation_passed",
                correlation_id=correlation_id,
                trace_id=trace_id,
            )
            return run_view(plane, run_id, trace_id=trace_id)
        except ControlPlaneError as exc:
            raise http_error(409, "control_plane_rejected", str(exc), trace_id=trace_id) from exc

    @app.get("/external-runs/{run_id}", response_model=RunView)
    @app.get("/api/external-runs/{run_id}", response_model=RunView)
    async def get_external_run(run_id: str, request: Request) -> RunView:
        trace_id = request_trace_id(request)
        return run_view(state.plane(), run_id, trace_id=trace_id)

    @app.post("/external-runs/{run_id}:park", response_model=RunView)
    @app.post("/api/external-runs/{run_id}:park", response_model=RunView)
    async def park_external_run(
        run_id: str,
        body: ParkRunRequest,
        request: Request,
        x_protocol_release_tag: str | None = Header(default=None),
    ) -> RunView:
        trace_id = request_trace_id(request, body.traceId)
        require_protocol_header(x_protocol_release_tag, trace_id=trace_id)
        ensure_protocol(body.protocolReleaseTag, trace_id=trace_id)
        plane = state.plane()
        projection = plane.projection()
        run = projection.get_run(run_id)
        if run is None:
            raise http_error(404, "run_not_found", f"run {run_id!r} was not found", trace_id=trace_id)
        if run.currentState == "planning":
            plane.transition_run(
                run_id=run_id,
                old_state="planning",
                new_state="executing",
                transition_trigger="execution_starts",
                correlation_id=correlation_id_for(run_id, body.correlationId),
                trace_id=trace_id,
            )
            projection = plane.projection()
        attempt_id = require_existing_attempt(projection, run_id, body.attemptId, trace_id=trace_id)
        try:
            correlation_id = correlation_id_for(run_id, body.correlationId)
            activate_attempt_if_needed(
                plane,
                run_id=run_id,
                attempt_id=attempt_id,
                correlation_id=correlation_id,
                trace_id=trace_id,
            )
            plane.park_manual(
                run_id=run_id,
                attempt_id=attempt_id,
                park_id=body.parkId or f"park-{uuid.uuid4().hex}",
                manual_gate_type=body.manualGateType,
                execution_suspension_state=body.executionSuspensionState,
                rehydration_token_id=body.rehydrationTokenId or f"rt-{uuid.uuid4().hex}",
                correlation_id=correlation_id,
                trace_id=trace_id,
            )
            return run_view(plane, run_id, trace_id=trace_id)
        except ControlPlaneError as exc:
            raise http_error(409, "control_plane_rejected", str(exc), trace_id=trace_id) from exc

    @app.post("/external-runs/{run_id}:rehydrate", response_model=RunView)
    @app.post("/api/external-runs/{run_id}:rehydrate", response_model=RunView)
    async def rehydrate_external_run(
        run_id: str,
        body: RehydrateRunRequest,
        request: Request,
        x_protocol_release_tag: str | None = Header(default=None),
    ) -> RunView:
        trace_id = request_trace_id(request, body.traceId)
        require_protocol_header(x_protocol_release_tag, trace_id=trace_id)
        ensure_protocol(body.protocolReleaseTag, trace_id=trace_id)
        plane = state.plane()
        projection = plane.projection()
        run = projection.get_run(run_id)
        if run is None:
            raise http_error(404, "run_not_found", f"run {run_id!r} was not found", trace_id=trace_id)
        previous_attempt_id = require_existing_attempt(projection, run_id, body.previousAttemptId, trace_id=trace_id)
        try:
            plane.rehydrate_manual(
                run_id=run_id,
                previous_attempt_id=previous_attempt_id,
                new_attempt_id=body.newAttemptId or f"attempt-{uuid.uuid4().hex}",
                rehydration_token_id=body.rehydrationTokenId,
                correlation_id=correlation_id_for(run_id, body.correlationId),
                trace_id=trace_id,
            )
            return run_view(plane, run_id, trace_id=trace_id)
        except ControlPlaneError as exc:
            raise http_error(409, "control_plane_rejected", str(exc), trace_id=trace_id) from exc

    @app.get("/external-runs/{run_id}/route-decisions", response_model=list[RouteDecisionView])
    @app.get("/api/external-runs/{run_id}/route-decisions", response_model=list[RouteDecisionView])
    async def list_route_decisions(run_id: str, request: Request) -> list[RouteDecisionView]:
        trace_id = request_trace_id(request)
        plane = state.plane()
        if plane.get_run(run_id) is None:
            raise http_error(404, "run_not_found", f"run {run_id!r} was not found", trace_id=trace_id)
        return [
            route_decision_view(decision)
            for decision in plane.projection().route_decisions.values()
            if decision.decision.runId == run_id
        ]

    @app.get("/external-runs/{run_id}/provider-failures", response_model=list[ProviderFailureView])
    @app.get("/api/external-runs/{run_id}/provider-failures", response_model=list[ProviderFailureView])
    async def list_provider_failures(run_id: str, request: Request) -> list[ProviderFailureView]:
        trace_id = request_trace_id(request)
        if state.plane().get_run(run_id) is None:
            raise http_error(404, "run_not_found", f"run {run_id!r} was not found", trace_id=trace_id)
        return []

    @app.get("/external-runs/{run_id}/repair-attempts", response_model=list[RepairAttemptView])
    @app.get("/api/external-runs/{run_id}/repair-attempts", response_model=list[RepairAttemptView])
    async def list_repair_attempts(run_id: str, request: Request) -> list[RepairAttemptView]:
        trace_id = request_trace_id(request)
        if state.plane().get_run(run_id) is None:
            raise http_error(404, "run_not_found", f"run {run_id!r} was not found", trace_id=trace_id)
        return []

    @app.post("/external-runs/{run_id}:repair", status_code=202, response_model=RepairAttemptView)
    @app.post("/api/external-runs/{run_id}:repair", status_code=202, response_model=RepairAttemptView)
    async def start_repair_attempt(
        run_id: str,
        body: RepairRunRequest,
        request: Request,
        x_protocol_release_tag: str | None = Header(default=None),
    ) -> RepairAttemptView:
        trace_id = request_trace_id(request, body.traceId)
        require_protocol_header(x_protocol_release_tag, trace_id=trace_id)
        ensure_protocol(body.protocolReleaseTag, trace_id=trace_id)
        if state.plane().get_run(run_id) is None:
            raise http_error(404, "run_not_found", f"run {run_id!r} was not found", trace_id=trace_id)
        return RepairAttemptView(
            repairAttemptId=body.repairAttemptId or f"repair-{uuid.uuid4().hex}",
            runId=run_id,
            outcome="accepted",
            verificationEvidenceRef=body.repairPlanRef,
            operatorApprovalRequired=body.triggerFaultClass == "operator_adjudication_required",
        )

    @app.get("/archive/search", response_model=list[ArchiveSearchResult])
    @app.get("/api/archive/search", response_model=list[ArchiveSearchResult])
    async def search_archive(q: str | None = None) -> list[ArchiveSearchResult]:
        _ = q
        return []

    @app.post("/archive/restore", status_code=202, response_model=ArchiveSearchResult)
    @app.post("/api/archive/restore", status_code=202, response_model=ArchiveSearchResult)
    async def restore_archive_object(
        body: ArchiveRestoreRequest,
        request: Request,
        x_protocol_release_tag: str | None = Header(default=None),
    ) -> ArchiveSearchResult:
        trace_id = request_trace_id(request)
        require_protocol_header(x_protocol_release_tag, trace_id=trace_id)
        ensure_protocol(body.protocolReleaseTag, trace_id=trace_id)
        return ArchiveSearchResult(
            objectId=body.objectId,
            objectType="unknown",
            archivedAt=utc_now(),
            truthBacked=False,
        )

    return app


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the Dark Factory V3 HTTP server")
    parser.add_argument("--host", default="127.0.0.1", help="Bind host. Defaults to 127.0.0.1.")
    parser.add_argument("--port", default=DEFAULT_PORT, type=int, help=f"Bind port. Defaults to {DEFAULT_PORT}.")
    parser.add_argument("--journal", default=str(DEFAULT_JOURNAL_PATH), help="JSONL journal file path.")
    parser.add_argument("--no-auth", action="store_true", help="Disable API key authentication for local development only.")
    parser.add_argument("--reload", action="store_true", help="Enable uvicorn reload for local development.")
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    args = build_parser().parse_args(list(argv) if argv is not None else None)
    import uvicorn

    configure_logging()
    journal_path = Path(args.journal).expanduser().resolve()
    auth_enabled = not args.no_auth
    api_key = os.environ.get("DF_API_KEY")
    generated_key = False
    if auth_enabled and not api_key:
        api_key = str(uuid.uuid4())
        generated_key = True
    if not auth_enabled:
        print("WARNING: Authentication disabled. Do not use in production.", flush=True)
    elif generated_key:
        print(f"API key authentication enabled. Generated key: {api_key}", flush=True)
    else:
        print(f"API key authentication enabled. Key: {api_key}", flush=True)
    log_event(
        logging.WARNING if not auth_enabled else logging.INFO,
        "server_startup",
        server_version=SERVER_VERSION,
        port=args.port,
        auth_mode="disabled" if not auth_enabled else ("api_key_generated" if generated_key else "api_key_env"),
        journal_mode="file-jsonl",
        journal_path=str(journal_path),
    )
    app = create_app(journal_path=journal_path, api_key=api_key, auth_enabled=auth_enabled)
    uvicorn.run(app, host=args.host, port=args.port, reload=args.reload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
