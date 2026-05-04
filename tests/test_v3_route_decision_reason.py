import json
from pathlib import Path

import yaml

from server import route_decision_reasons_for

ROOT = Path(__file__).resolve().parents[1]


def test_route_decision_reason_codes_are_declared_in_core_enums_and_schema():
    enums = yaml.safe_load((ROOT / "paperclip_darkfactory_v3_0_core_enums.yaml").read_text(encoding="utf-8"))["enums"]
    schema = json.loads((ROOT / "paperclip_darkfactory_v3_0_core_objects.schema.json").read_text(encoding="utf-8"))

    assert enums["routeDecisionReasonCode"] == [
        "workload_class_code",
        "requires_capability_lease",
        "provider_degraded",
        "provider_exhausted",
        "manual_gate_required",
        "high_risk_write",
        "memory_injection_required",
        "repair_lane_required",
        "fallback_allowed",
        "fallback_blocked_by_policy",
    ]
    assert enums["riskLevel"] == ["low", "medium", "high", "critical"]
    assert enums["costLevel"] == ["low_cost", "standard", "expensive", "operator_confirmed"]
    assert "RouteDecisionReason" in schema["$defs"]
    assert schema["$defs"]["RouteDecision"]["properties"]["routeDecisionReasons"]["items"]["$ref"] == "#/$defs/RouteDecisionReason"


def test_route_decision_reason_projection_explains_primary_and_fallback_selection():
    primary = route_decision_reasons_for("chat", "general_chat_executor", 0)
    fallback = route_decision_reasons_for("chat", "fallback-chat-lite", 1)

    assert [reason["reasonCode"] for reason in primary] == ["workload_class_code"]
    assert primary[0]["sourceSignal"] == "chat"
    assert primary[0]["confidence"] == 1.0
    assert [reason["reasonCode"] for reason in fallback] == ["workload_class_code", "fallback_allowed"]
    assert fallback[1]["costLevel"] == "operator_confirmed"
