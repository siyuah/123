from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

from .protocol import PROTOCOL_RELEASE_TAG

TRUTH_SOURCE = "dark-factory-journal"


@dataclass(frozen=True)
class FaultPlaybook:
    playbookId: str
    title: str
    triggerFaultClasses: tuple[str, ...]
    recoveryLane: str
    riskLevel: str
    approvalLevel: str
    autoRecoveryAllowed: bool
    steps: tuple[str, ...]
    verificationSignals: tuple[str, ...]
    operatorNote: str
    protocolReleaseTag: str = PROTOCOL_RELEASE_TAG
    authoritative: bool = False
    truthSource: str = TRUTH_SOURCE

    def to_dict(self) -> dict[str, Any]:
        return {
            "protocolReleaseTag": self.protocolReleaseTag,
            "playbookId": self.playbookId,
            "title": self.title,
            "triggerFaultClasses": list(self.triggerFaultClasses),
            "recoveryLane": self.recoveryLane,
            "riskLevel": self.riskLevel,
            "approvalLevel": self.approvalLevel,
            "autoRecoveryAllowed": self.autoRecoveryAllowed,
            "steps": list(self.steps),
            "verificationSignals": list(self.verificationSignals),
            "operatorNote": self.operatorNote,
            "authoritative": self.authoritative,
            "truthSource": self.truthSource,
        }


def default_fault_playbooks() -> tuple[FaultPlaybook, ...]:
    """Return the deterministic built-in recovery playbook registry."""
    return (
        FaultPlaybook(
            playbookId="transient-retry",
            title="Retry transient provider failures",
            triggerFaultClasses=("transient_timeout", "transient_5xx"),
            recoveryLane="retry_same_route",
            riskLevel="low",
            approvalLevel="P2_auto",
            autoRecoveryAllowed=True,
            steps=("record failure evidence", "retry same route once", "verify response contract"),
            verificationSignals=("provider_retry_attempts_timeout", "provider_retry_attempts_5xx"),
            operatorNote="Auto recovery is limited to one low-risk retry.",
        ),
        FaultPlaybook(
            playbookId="rate-limit-backoff",
            title="Back off rate-limited provider",
            triggerFaultClasses=("rate_limited",),
            recoveryLane="degrade_low_risk_only",
            riskLevel="medium",
            approvalLevel="P1_single_confirm",
            autoRecoveryAllowed=False,
            steps=("record 429 evidence", "pause expensive writes", "resume after operator review"),
            verificationSignals=("provider_429_count", "provider_health_timeout_count"),
            operatorNote="Requires operator review before resuming normal write throughput.",
        ),
        FaultPlaybook(
            playbookId="quota-exhausted-cutover",
            title="Cut over after quota exhaustion",
            triggerFaultClasses=("quota_exhausted",),
            recoveryLane="cutover_fallback_route",
            riskLevel="medium",
            approvalLevel="P1_single_confirm",
            autoRecoveryAllowed=False,
            steps=("record quota evidence", "select fallback provider", "require operator confirmation"),
            verificationSignals=("provider_fallback_activated_count",),
            operatorNote="Fallback is allowed only after explicit operator confirmation.",
        ),
        FaultPlaybook(
            playbookId="auth-invalid-park",
            title="Park run on invalid provider authentication",
            triggerFaultClasses=("auth_invalid",),
            recoveryLane="park_manual",
            riskLevel="critical",
            approvalLevel="P0_dual_confirm",
            autoRecoveryAllowed=False,
            steps=("redact credential evidence", "park affected runs", "request dual confirmation"),
            verificationSignals=("auth_invalid_count",),
            operatorNote="Never print or persist credential values while collecting evidence.",
        ),
        FaultPlaybook(
            playbookId="capability-unsupported-cutover",
            title="Cut over unsupported capability requests",
            triggerFaultClasses=("capability_unsupported",),
            recoveryLane="cutover_fallback_route",
            riskLevel="medium",
            approvalLevel="P1_single_confirm",
            autoRecoveryAllowed=False,
            steps=("record capability mismatch", "select compatible provider", "keep original journal event"),
            verificationSignals=("capability_unsupported_count",),
            operatorNote="Cutover is a projection decision; the original journal event remains truth.",
        ),
        FaultPlaybook(
            playbookId="context-length-degrade",
            title="Degrade low-risk context overflow",
            triggerFaultClasses=("context_length_exceeded",),
            recoveryLane="degrade_low_risk_only",
            riskLevel="medium",
            approvalLevel="P1_single_confirm",
            autoRecoveryAllowed=False,
            steps=("record context length evidence", "block high-risk writes", "offer low-risk summary lane"),
            verificationSignals=("context_length_exceeded_count",),
            operatorNote="High-risk write operations stay blocked until reviewed.",
        ),
        FaultPlaybook(
            playbookId="response-contract-repair",
            title="Enter repair lane for response contract drift",
            triggerFaultClasses=("response_contract_invalid",),
            recoveryLane="enter_repair_lane",
            riskLevel="high",
            approvalLevel="P1_single_confirm",
            autoRecoveryAllowed=False,
            steps=("record invalid response evidence", "open repair attempt", "verify repair evidence"),
            verificationSignals=("repair_attempt_started_count", "repair_attempt_completed_count"),
            operatorNote="Repair output must be verified before downstream consumption.",
        ),
        FaultPlaybook(
            playbookId="provider-unreachable-cutover",
            title="Cut over unreachable provider",
            triggerFaultClasses=("provider_unreachable",),
            recoveryLane="cutover_fallback_route",
            riskLevel="medium",
            approvalLevel="P1_single_confirm",
            autoRecoveryAllowed=False,
            steps=("record reachability evidence", "mark provider degraded", "activate fallback if confirmed"),
            verificationSignals=("provider_health_timeout_count", "provider_fallback_activated_count"),
            operatorNote="Fallback activation must remain non-authoritative until journal-backed.",
        ),
    )


def fault_playbook_registry() -> dict[str, FaultPlaybook]:
    return {playbook.playbookId: playbook for playbook in default_fault_playbooks()}


def recommend_playbooks(provider_fault_class: str, *, registry: Iterable[FaultPlaybook] | None = None) -> tuple[FaultPlaybook, ...]:
    playbooks = tuple(registry or default_fault_playbooks())
    return tuple(playbook for playbook in playbooks if provider_fault_class in playbook.triggerFaultClasses)


def validate_fault_playbook_registry(playbooks: Iterable[FaultPlaybook]) -> list[str]:
    errors: list[str] = []
    seen: set[str] = set()
    for playbook in playbooks:
        if playbook.playbookId in seen:
            errors.append(f"duplicate playbookId: {playbook.playbookId}")
        seen.add(playbook.playbookId)
        if playbook.protocolReleaseTag != PROTOCOL_RELEASE_TAG:
            errors.append(f"{playbook.playbookId}: invalid protocolReleaseTag")
        if playbook.authoritative is not False:
            errors.append(f"{playbook.playbookId}: authoritative must be false")
        if playbook.truthSource != TRUTH_SOURCE:
            errors.append(f"{playbook.playbookId}: truthSource must be {TRUTH_SOURCE}")
        if playbook.autoRecoveryAllowed and (playbook.riskLevel != "low" or playbook.approvalLevel != "P2_auto"):
            errors.append(f"{playbook.playbookId}: auto recovery must be low risk and P2_auto")
    return errors
