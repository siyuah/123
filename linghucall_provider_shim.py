"""LinghuCall-backed Dark Factory provider shim.

This is an operator-controlled alpha shim that exposes the Dark Factory V3
external-runs HTTP contract while using LinghuCall's OpenAI-compatible
`/v1/chat/completions` endpoint as the downstream model provider.

The shim is intentionally narrow:

- Dark Factory Journal remains the truth source for the bridge-facing contract.
- The bridge authenticates to this shim with `DF_API_KEY` or `DF_API_KEY_FILE`.
- The LinghuCall credential is read only from `LINGHUCALL_API_KEY`.
- No resolved credential value is logged, returned, or written to the journal.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterable, Mapping, Optional, Protocol

from fastapi import FastAPI, Header, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dark_factory_v3.protocol import PROTOCOL_RELEASE_TAG  # noqa: E402
from server import api_key_from_environment, mask_client_ip, redact_sensitive  # noqa: E402


DEFAULT_PORT = 9791
DEFAULT_JOURNAL_PATH = ROOT / ".dark_factory_http" / "linghucall_provider_shim.jsonl"
DEFAULT_LINGHUCALL_BASE_URL = "https://api.linghucall.net/v1"
DEFAULT_LINGHUCALL_MODEL = "gpt-5.5"
DEFAULT_ROUTE_POLICY_REF = "policy://routing/v3/linghucall-alpha"
SERVER_VERSION = "3.0.0-linghucall-shim-alpha.1"
LOGGER = logging.getLogger("dark_factory_v3.linghucall_shim")


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
    LOGGER.log(level, message, extra={"structured": redact_sensitive(fields)})


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
    providerEvidenceRef: Optional[str] = None
    providerResponseId: Optional[str] = None
    providerModel: Optional[str] = None
    providerFinishReason: Optional[str] = None


class HealthView(BaseModel):
    ok: bool
    protocolReleaseTag: str
    journal: str
    events: int
    projection: dict[str, int]
    provider: dict[str, Any]


class LinghuCallResult(BaseModel):
    responseId: str
    model: str
    finishReason: str
    contentPreview: str
    usage: dict[str, Any]


class LinghuCallClient(Protocol):
    def chat_completion(self, *, run_id: str, trace_id: str, workload_class: str, input_ref: str) -> LinghuCallResult:
        ...


class LinghuCallProviderError(Exception):
    def __init__(self, code: str, message: str, *, status: int = 502, retryable: bool = True, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.status = status
        self.retryable = retryable
        self.details = details or {}


class HttpLinghuCallClient:
    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        model: str,
        timeout_seconds: float = 20.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.timeout_seconds = timeout_seconds

    @classmethod
    def from_environment(cls, env: Mapping[str, str] = os.environ) -> "HttpLinghuCallClient":
        api_key = env.get("LINGHUCALL_API_KEY", "")
        if not api_key:
            raise LinghuCallProviderError(
                "linghucall_credential_missing",
                "LINGHUCALL_API_KEY is required for the LinghuCall provider shim",
                status=503,
                retryable=False,
            )
        return cls(
            base_url=env.get("LINGHUCALL_BASE_URL", DEFAULT_LINGHUCALL_BASE_URL),
            api_key=api_key,
            model=env.get("LINGHUCALL_MODEL", DEFAULT_LINGHUCALL_MODEL),
            timeout_seconds=float(env.get("LINGHUCALL_TIMEOUT_SECONDS", "20")),
        )

    def chat_completion(self, *, run_id: str, trace_id: str, workload_class: str, input_ref: str) -> LinghuCallResult:
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": "You are a Dark Factory provider shim health/execution probe. Reply with a concise acknowledgement.",
                },
                {
                    "role": "user",
                    "content": f"Dark Factory run {run_id} workload={workload_class} inputRef={input_ref} trace={trace_id}. Reply with pong.",
                },
            ],
            "stream": False,
        }
        request = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            method="POST",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
        )
        started_at = time.perf_counter()
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                raw = response.read().decode("utf-8")
                response_payload = json.loads(raw)
        except urllib.error.HTTPError as exc:
            raw = exc.read().decode("utf-8", errors="replace")
            message = provider_error_message(raw, exc.reason)
            raise LinghuCallProviderError(
                "linghucall_http_error",
                message,
                status=exc.code,
                retryable=exc.code in {408, 429, 500, 502, 503, 504},
                details={"status": exc.code},
            ) from exc
        except urllib.error.URLError as exc:
            raise LinghuCallProviderError(
                "linghucall_unreachable",
                str(exc.reason),
                status=503,
                retryable=True,
            ) from exc
        except json.JSONDecodeError as exc:
            raise LinghuCallProviderError(
                "linghucall_invalid_json",
                f"LinghuCall returned invalid JSON: {exc}",
                status=502,
                retryable=True,
            ) from exc

        duration_ms = round((time.perf_counter() - started_at) * 1000, 2)
        choice = (response_payload.get("choices") or [{}])[0]
        message = choice.get("message") or {}
        content = str(message.get("content") or "")
        log_event(
            logging.INFO,
            "linghucall_completion_observed",
            run_id=run_id,
            model=response_payload.get("model") or self.model,
            response_id=response_payload.get("id"),
            finish_reason=choice.get("finish_reason"),
            duration_ms=duration_ms,
        )
        return LinghuCallResult(
            responseId=str(response_payload.get("id") or f"linghucall-{uuid.uuid4().hex}"),
            model=str(response_payload.get("model") or self.model),
            finishReason=str(choice.get("finish_reason") or "unknown"),
            contentPreview=content[:200],
            usage=response_payload.get("usage") if isinstance(response_payload.get("usage"), dict) else {},
        )


@dataclass
class ShimRun:
    run_id: str
    run_state: str
    trace_id: str
    active_attempt_id: str
    route_decision_id: str
    journal_cursor: str
    last_sequence_no: int
    source_journal_ref: str
    blocked_by: list[str] = field(default_factory=list)
    current_manual_gate_type: str | None = None
    current_execution_suspension_state: str | None = None


@dataclass
class ShimRouteDecision:
    route_decision_id: str
    run_id: str
    workload_class: str
    selected_executor_class: str
    fallback_depth: int
    decision_reason: str
    route_decision_state: str
    attempt_id: str
    route_policy_ref: str
    recorded_at: str
    provider_evidence_ref: str
    provider_response_id: str
    provider_model: str
    provider_finish_reason: str


class ShimState:
    def __init__(self, *, journal_path: Path, provider_client: LinghuCallClient) -> None:
        self.journal_path = journal_path
        self.provider_client = provider_client
        self.lock = threading.Lock()
        self.runs: dict[str, ShimRun] = {}
        self.route_decisions: dict[str, ShimRouteDecision] = {}
        self.sequence_no = self._load_sequence_no()

    def _load_sequence_no(self) -> int:
        if not self.journal_path.exists():
            return 0
        max_sequence = 0
        for line in self.journal_path.read_text(encoding="utf-8").splitlines():
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                continue
            sequence_no = payload.get("sequenceNo")
            if isinstance(sequence_no, int):
                max_sequence = max(max_sequence, sequence_no)
        return max_sequence

    def append_event(self, *, event_name: str, run_id: str, trace_id: str, payload: dict[str, Any]) -> int:
        self.sequence_no += 1
        self.journal_path.parent.mkdir(parents=True, exist_ok=True)
        event = {
            "protocolReleaseTag": PROTOCOL_RELEASE_TAG,
            "eventId": f"evt-linghucall-{run_id}-{self.sequence_no:04d}",
            "eventName": event_name,
            "sequenceNo": self.sequence_no,
            "runId": run_id,
            "traceId": trace_id,
            "recordedAt": utc_now(),
            "payload": redact_sensitive(payload),
        }
        with self.journal_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")
        return self.sequence_no

    def cursor(self, run_id: str, sequence_no: int) -> str:
        return f"dark-factory://linghucall-shim/{self.journal_path.name}/{run_id}#{sequence_no}"

    def source_journal_ref(self) -> str:
        return f"file://{self.journal_path}"


def create_app(
    *,
    journal_path: Path = DEFAULT_JOURNAL_PATH,
    bridge_api_key: str | None = None,
    auth_enabled: bool = True,
    provider_client: LinghuCallClient | None = None,
) -> FastAPI:
    configure_logging()
    state = ShimState(
        journal_path=journal_path,
        provider_client=provider_client or HttpLinghuCallClient.from_environment(),
    )
    app = FastAPI(
        title="Dark Factory LinghuCall Provider Shim",
        version=SERVER_VERSION,
        description="Dark Factory V3 external-runs shim backed by LinghuCall chat completions.",
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
        status_code = 500
        try:
            is_health_check = request.method == "GET" and request.url.path in {"/health", "/api/health"}
            if auth_enabled and not is_health_check:
                provided_key = request.headers.get("x-api-key")
                if not bridge_api_key or provided_key != bridge_api_key:
                    status_code = 401
                    return JSONResponse(
                        status_code=401,
                        content={
                            "protocolReleaseTag": PROTOCOL_RELEASE_TAG,
                            "error": "unauthorized",
                            "message": "Invalid or missing API key",
                        },
                    )
            response = await call_next(request)
            status_code = response.status_code
            return response
        finally:
            duration_ms = round((time.perf_counter() - start) * 1000, 2)
            log_event(
                logging.INFO,
                "request",
                method=request.method,
                path=request.url.path,
                status_code=status_code,
                duration_ms=duration_ms,
                client_ip=mask_client_ip(request.client.host if request.client else None),
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
        return HealthView(
            ok=True,
            protocolReleaseTag=PROTOCOL_RELEASE_TAG,
            journal=str(journal_path),
            events=state.sequence_no,
            projection={
                "runs": len(state.runs),
                "attempts": len(state.runs),
                "routeDecisions": len(state.route_decisions),
                "unknownEvents": 0,
            },
            provider={
                "kind": "linghucall_openai_compatible",
                "model": os.environ.get("LINGHUCALL_MODEL", DEFAULT_LINGHUCALL_MODEL),
                "baseUrlHostOnly": host_only(os.environ.get("LINGHUCALL_BASE_URL", DEFAULT_LINGHUCALL_BASE_URL)),
                "credentialPresent": bool(os.environ.get("LINGHUCALL_API_KEY")),
                "credentialValueRedacted": True,
            },
        )

    @app.post("/external-runs", status_code=201, response_model=RunView)
    @app.post("/api/external-runs", status_code=201, response_model=RunView)
    async def create_external_run(
        body: CreateExternalRunRequest,
        request: Request,
        x_protocol_release_tag: str | None = Header(default=None),
    ) -> RunView:
        trace_id = request_trace_id(request, body.traceId)
        require_protocol(x_protocol_release_tag, trace_id=trace_id)
        require_protocol(body.protocolReleaseTag, trace_id=trace_id)
        run_id = body.runId or f"run-{uuid.uuid4().hex}"
        attempt_id = body.attemptId or f"attempt-{uuid.uuid4().hex}"
        with state.lock:
            existing = state.runs.get(run_id)
            if existing:
                return run_view(existing)
            try:
                provider_result = state.provider_client.chat_completion(
                    run_id=run_id,
                    trace_id=trace_id,
                    workload_class=body.workloadClass,
                    input_ref=body.inputRef,
                )
            except LinghuCallProviderError as exc:
                raise http_error(exc.status, exc.code, str(exc), trace_id=trace_id, retryable=exc.retryable) from exc

            sequence_no = state.append_event(
                event_name="provider.linghucall.chat_completion_observed",
                run_id=run_id,
                trace_id=trace_id,
                payload={
                    "requestedBy": body.requestedBy,
                    "workloadClass": body.workloadClass,
                    "inputRef": body.inputRef,
                    "attemptId": attempt_id,
                    "providerResponseId": provider_result.responseId,
                    "providerModel": provider_result.model,
                    "providerFinishReason": provider_result.finishReason,
                    "usage": provider_result.usage,
                    "contentPreview": provider_result.contentPreview,
                    "terminalStateAdvanced": False,
                },
            )
            route_decision_id = f"rd-{run_id}"
            evidence_ref = state.cursor(run_id, sequence_no)
            state.runs[run_id] = ShimRun(
                run_id=run_id,
                run_state="planning",
                trace_id=trace_id,
                active_attempt_id=attempt_id,
                route_decision_id=route_decision_id,
                journal_cursor=evidence_ref,
                last_sequence_no=sequence_no,
                source_journal_ref=state.source_journal_ref(),
            )
            state.route_decisions[run_id] = ShimRouteDecision(
                route_decision_id=route_decision_id,
                run_id=run_id,
                workload_class=body.workloadClass,
                selected_executor_class=body.selectedExecutorClass or f"linghucall:{provider_result.model}",
                fallback_depth=0,
                decision_reason=body.decisionReason or "linghucall_chat_completion_observed",
                route_decision_state="selected",
                attempt_id=attempt_id,
                route_policy_ref=body.routePolicyRef or DEFAULT_ROUTE_POLICY_REF,
                recorded_at=utc_now(),
                provider_evidence_ref=evidence_ref,
                provider_response_id=provider_result.responseId,
                provider_model=provider_result.model,
                provider_finish_reason=provider_result.finishReason,
            )
            return run_view(state.runs[run_id])

    @app.get("/external-runs/{run_id}", response_model=RunView)
    @app.get("/api/external-runs/{run_id}", response_model=RunView)
    async def get_external_run(run_id: str, request: Request) -> RunView:
        trace_id = request_trace_id(request)
        run = state.runs.get(run_id)
        if not run:
            raise http_error(404, "run_not_found", f"run {run_id!r} was not found", trace_id=trace_id)
        return run_view(run)

    @app.post("/external-runs/{run_id}:park", response_model=RunView)
    @app.post("/api/external-runs/{run_id}:park", response_model=RunView)
    async def park_external_run(
        run_id: str,
        body: ParkRunRequest,
        request: Request,
        x_protocol_release_tag: str | None = Header(default=None),
    ) -> RunView:
        trace_id = request_trace_id(request, body.traceId)
        require_protocol(x_protocol_release_tag, trace_id=trace_id)
        require_protocol(body.protocolReleaseTag, trace_id=trace_id)
        with state.lock:
            run = require_run(state, run_id, trace_id)
            sequence_no = state.append_event(
                event_name="manual_gate.parked",
                run_id=run_id,
                trace_id=trace_id,
                payload={
                    "manualGateType": body.manualGateType,
                    "parkReasonCode": body.parkReasonCode,
                    "attemptId": body.attemptId or run.active_attempt_id,
                    "parkId": body.parkId or f"park-{uuid.uuid4().hex}",
                    "rehydrationTokenId": body.rehydrationTokenId,
                    "terminalStateAdvanced": False,
                },
            )
            run.run_state = "parked_manual"
            run.blocked_by = ["parked_manual"]
            run.current_manual_gate_type = body.manualGateType
            run.current_execution_suspension_state = body.executionSuspensionState
            run.last_sequence_no = sequence_no
            run.journal_cursor = state.cursor(run_id, sequence_no)
            return run_view(run)

    @app.post("/external-runs/{run_id}:rehydrate", response_model=RunView)
    @app.post("/api/external-runs/{run_id}:rehydrate", response_model=RunView)
    async def rehydrate_external_run(
        run_id: str,
        body: RehydrateRunRequest,
        request: Request,
        x_protocol_release_tag: str | None = Header(default=None),
    ) -> RunView:
        trace_id = request_trace_id(request, body.traceId)
        require_protocol(x_protocol_release_tag, trace_id=trace_id)
        require_protocol(body.protocolReleaseTag, trace_id=trace_id)
        with state.lock:
            run = require_run(state, run_id, trace_id)
            sequence_no = state.append_event(
                event_name="manual_gate.rehydrated",
                run_id=run_id,
                trace_id=trace_id,
                payload={
                    "previousAttemptId": body.previousAttemptId or run.active_attempt_id,
                    "newAttemptId": body.newAttemptId or f"{run.active_attempt_id}-rehydrated",
                    "rehydrationTokenId": body.rehydrationTokenId,
                    "terminalStateAdvanced": False,
                },
            )
            run.run_state = "planning"
            run.blocked_by = []
            run.current_manual_gate_type = None
            run.current_execution_suspension_state = None
            run.active_attempt_id = body.newAttemptId or f"{run.active_attempt_id}-rehydrated"
            run.last_sequence_no = sequence_no
            run.journal_cursor = state.cursor(run_id, sequence_no)
            decision = state.route_decisions.get(run_id)
            if decision:
                decision.attempt_id = run.active_attempt_id
            return run_view(run)

    @app.get("/external-runs/{run_id}/route-decisions", response_model=list[RouteDecisionView])
    @app.get("/api/external-runs/{run_id}/route-decisions", response_model=list[RouteDecisionView])
    async def list_route_decisions(run_id: str, request: Request) -> list[RouteDecisionView]:
        trace_id = request_trace_id(request)
        require_run(state, run_id, trace_id)
        decision = state.route_decisions.get(run_id)
        return [route_decision_view(decision)] if decision else []

    return app


def run_view(run: ShimRun) -> RunView:
    return RunView(
        runId=run.run_id,
        runState=run.run_state,
        traceId=run.trace_id,
        activeAttemptId=run.active_attempt_id,
        blockedBy=list(run.blocked_by),
        currentManualGateType=run.current_manual_gate_type,
        currentExecutionSuspensionState=run.current_execution_suspension_state,
        routeDecisionId=run.route_decision_id,
        journalCursor=run.journal_cursor,
        lastSequenceNo=run.last_sequence_no,
        sourceJournalRef=run.source_journal_ref,
    )


def route_decision_view(decision: ShimRouteDecision) -> RouteDecisionView:
    return RouteDecisionView(
        routeDecisionId=decision.route_decision_id,
        runId=decision.run_id,
        workloadClass=decision.workload_class,
        selectedExecutorClass=decision.selected_executor_class,
        fallbackDepth=decision.fallback_depth,
        decisionReason=decision.decision_reason,
        routeDecisionState=decision.route_decision_state,
        attemptId=decision.attempt_id,
        routePolicyRef=decision.route_policy_ref,
        recordedAt=decision.recorded_at,
        providerEvidenceRef=decision.provider_evidence_ref,
        providerResponseId=decision.provider_response_id,
        providerModel=decision.provider_model,
        providerFinishReason=decision.provider_finish_reason,
    )


def require_run(state: ShimState, run_id: str, trace_id: str) -> ShimRun:
    run = state.runs.get(run_id)
    if not run:
        raise http_error(404, "run_not_found", f"run {run_id!r} was not found", trace_id=trace_id)
    return run


def require_protocol(value: str | None, *, trace_id: str) -> None:
    if value != PROTOCOL_RELEASE_TAG:
        raise http_error(
            400,
            "protocol_release_tag_mismatch",
            f"protocolReleaseTag must be {PROTOCOL_RELEASE_TAG}",
            trace_id=trace_id,
            retryable=False,
        )


def http_error(status_code: int, error_code: str, message: str, *, trace_id: str, retryable: bool = False) -> HTTPException:
    return HTTPException(
        status_code=status_code,
        detail=ErrorResponse(errorCode=error_code, message=message, traceId=trace_id, retryable=retryable).model_dump(),
    )


def request_trace_id(request: Request, body_trace_id: str | None = None) -> str:
    return body_trace_id or request.headers.get("x-trace-id") or f"trace-{uuid.uuid4().hex}"


def provider_error_message(raw_body: str, fallback: str) -> str:
    try:
        payload = json.loads(raw_body)
    except json.JSONDecodeError:
        return fallback
    if isinstance(payload, dict):
        error = payload.get("error")
        if isinstance(error, dict) and isinstance(error.get("message"), str):
            return error["message"]
        if isinstance(payload.get("message"), str):
            return payload["message"]
    return fallback


def host_only(url: str) -> str:
    try:
        parsed = urllib.parse.urlparse(url)
        return parsed.netloc or "unknown"
    except Exception:
        return "unknown"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the LinghuCall-backed Dark Factory provider shim")
    parser.add_argument("--host", default="127.0.0.1", help="Bind host. Defaults to 127.0.0.1.")
    parser.add_argument("--port", default=DEFAULT_PORT, type=int, help=f"Bind port. Defaults to {DEFAULT_PORT}.")
    parser.add_argument("--journal", default=str(DEFAULT_JOURNAL_PATH), help="JSONL journal file path.")
    parser.add_argument("--bridge-api-key-file", default=None, help="Read bridge API key from a file. Defaults to DF_API_KEY_FILE when set.")
    parser.add_argument("--no-auth", action="store_true", help="Disable bridge API key authentication for local development only.")
    parser.add_argument("--reload", action="store_true", help="Enable uvicorn reload for local development.")
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    args = build_parser().parse_args(list(argv) if argv is not None else None)
    import uvicorn

    configure_logging()
    journal_path = Path(args.journal).expanduser().resolve()
    auth_enabled = not args.no_auth
    bridge_api_key: str | None = None
    api_key_source = "disabled"
    generated_key = False
    if auth_enabled:
        bridge_api_key, api_key_source, generated_key = api_key_from_environment(api_key_file=args.bridge_api_key_file)
    if not auth_enabled:
        print("WARNING: Authentication disabled. Do not use in production.", flush=True)
    elif generated_key:
        print(f"Bridge API key authentication enabled. Generated key: {bridge_api_key}", flush=True)
    else:
        print(f"Bridge API key authentication enabled. Key source: {api_key_source}", flush=True)
    log_event(
        logging.WARNING if not auth_enabled else logging.INFO,
        "linghucall_shim_startup",
        server_version=SERVER_VERSION,
        port=args.port,
        auth_mode="disabled" if not auth_enabled else f"api_key_{api_key_source}",
        journal_path=str(journal_path),
        provider_base_host=host_only(os.environ.get("LINGHUCALL_BASE_URL", DEFAULT_LINGHUCALL_BASE_URL)),
        provider_model=os.environ.get("LINGHUCALL_MODEL", DEFAULT_LINGHUCALL_MODEL),
        provider_credential_present=bool(os.environ.get("LINGHUCALL_API_KEY")),
        provider_credential_value_redacted=True,
    )
    app = create_app(journal_path=journal_path, bridge_api_key=bridge_api_key, auth_enabled=auth_enabled)
    uvicorn.run(app, host=args.host, port=args.port, reload=args.reload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
