#!/usr/bin/env python3
import csv
import hashlib
import json
import re
import sys
from pathlib import Path

import yaml

BUNDLE = Path(__file__).resolve().parent

CORE_ENUMS = BUNDLE / "paperclip_darkfactory_v2_9_core_enums.yaml"
EVENTS = BUNDLE / "paperclip_darkfactory_v2_9_event_contracts.yaml"
OPENAPI = BUNDLE / "paperclip_darkfactory_v2_9_external_runs.openapi.yaml"
SCHEMA = BUNDLE / "paperclip_darkfactory_v2_9_core_objects.schema.json"
README = BUNDLE / "README.md"
INVARIANTS = BUNDLE / "paperclip_darkfactory_v2_9_invariants.md"
MANIFEST = BUNDLE / "paperclip_darkfactory_v2_9_bundle_manifest.json"
TEST_ASSET_SPEC = BUNDLE / "paperclip_darkfactory_v2_9_test_asset_spec.md"
TIMELINE_DIR = BUNDLE / "golden_timelines"


def load_yaml(path: Path):
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def collect_schema_enums(schema_obj):
    enums = {}
    defs = schema_obj.get("$defs", {})
    mapping = {
        "artifactCertificationState": "ArtifactCertificationState",
        "inputDependencyState": "InputDependencyState",
        "dependencyConsumptionPolicy": "DependencyConsumptionPolicy",
        "profileConformanceStatus": "ProfileConformanceStatus",
        "capsuleHealth": "CapsuleHealth",
        "manualGateType": "ManualGateType",
        "runState": "RunState",
        "executionSuspensionState": "ExecutionSuspensionState",
        "reasonCode": "ReasonCode",
        "parkReasonCode": "ParkReasonCode",
        "capability": "Capability",
    }
    for out_name, def_name in mapping.items():
        enums[out_name] = defs[def_name]["enum"]
    return enums


def get_openapi_schema(root, name):
    return root["components"]["schemas"][name]


def require_equal(label, left, right, errors):
    if left != right:
        errors.append(f"{label} mismatch: {left!r} != {right!r}")


def require_true(label, cond, errors):
    if not cond:
        errors.append(label)


def require_in_set(label, value, allowed, errors):
    if value not in allowed:
        errors.append(f"{label} must be one of {sorted(allowed)!r}, got {value!r}")


def load_timeline_entries(path: Path):
    entries = []
    for line_no, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        raw = raw.strip()
        if not raw:
            continue
        try:
            obj = json.loads(raw)
        except Exception as e:
            raise ValueError(f"{path.name}:{line_no} invalid JSON: {e}") from e
        if "eventName" not in obj:
            raise ValueError(f"{path.name}:{line_no} missing eventName")
        entries.append((line_no, obj))
    return entries


def sha256_file(path: Path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def extract_test_case_ids(spec_text: str):
    return set(re.findall(r"`(TC-V29-[a-z]+-[0-9]{3})`", spec_text))


def load_traceability_rows(path: Path):
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def validate_timeline_projection(path: Path, line_no: int, obj: dict, enums: dict, errors: list[str]):
    projection = obj.get("expectedProjectionDelta")
    require_true(f"{path.name}:{line_no} missing expectedProjectionDelta", isinstance(projection, dict), errors)
    if not isinstance(projection, dict):
        return

    enum_fields = {
        "artifactCertificationState": enums["artifactCertificationState"],
        "inputDependencyState": enums["inputDependencyState"],
        "dependencyConsumptionPolicy": enums["dependencyConsumptionPolicy"],
        "profileConformanceStatus": enums["profileConformanceStatus"],
        "capsuleHealth": enums["capsuleHealth"],
        "runState": enums["runState"],
        "reasonCode": enums["reasonCode"],
        "parkReasonCode": enums["parkReasonCode"],
        "executionSuspensionState": enums["executionSuspensionState"],
        "blockedBy": enums["blockedBy"],
    }
    for field, allowed in enum_fields.items():
        if field in projection:
            require_in_set(f"{path.name}:{line_no} expectedProjectionDelta.{field}", projection[field], allowed, errors)

    if "observedCapabilitySet" in projection:
        value = projection["observedCapabilitySet"]
        require_true(
            f"{path.name}:{line_no} expectedProjectionDelta.observedCapabilitySet must be an array",
            isinstance(value, list),
            errors,
        )
        if isinstance(value, list):
            for idx, item in enumerate(value):
                require_in_set(
                    f"{path.name}:{line_no} expectedProjectionDelta.observedCapabilitySet[{idx}]",
                    item,
                    enums["capability"],
                    errors,
                )

    manual_gate = obj.get("expectedManualGate")
    if manual_gate is not None:
        require_in_set(
            f"{path.name}:{line_no} expectedManualGate",
            manual_gate,
            enums["manualGateType"],
            errors,
        )

    suspension_state = obj.get("expectedExecutionSuspensionState")
    require_true(
        f"{path.name}:{line_no} missing expectedExecutionSuspensionState",
        suspension_state is not None,
        errors,
    )
    if suspension_state is not None:
        require_in_set(
            f"{path.name}:{line_no} expectedExecutionSuspensionState",
            suspension_state,
            enums["executionSuspensionState"],
            errors,
        )

    require_true(
        f"{path.name}:{line_no} expectedBlockNewHighRiskWrites must be boolean",
        isinstance(obj.get("expectedBlockNewHighRiskWrites"), bool),
        errors,
    )


def main():
    errors = []

    core = load_yaml(CORE_ENUMS)
    events = load_yaml(EVENTS)
    openapi = load_yaml(OPENAPI)
    schema = load_json(SCHEMA)
    manifest = load_json(MANIFEST)
    traceability = BUNDLE / "paperclip_darkfactory_v2_9_test_traceability.csv"
    spec_text = TEST_ASSET_SPEC.read_text(encoding="utf-8")

    enums = core["enums"]
    schema_enums = collect_schema_enums(schema)

    for key, schema_values in schema_enums.items():
        require_equal(f"enum {key} core-vs-schema", enums[key], schema_values, errors)

    view_manual = get_openapi_schema(openapi, "ExternalRunView")["properties"]["manualGateType"]["enum"]
    park_manual = get_openapi_schema(openapi, "ParkRequest")["properties"]["manualGateType"]["enum"]
    require_equal("enum manualGateType core-vs-openapi-view", enums["manualGateType"], view_manual, errors)
    require_equal("enum manualGateType core-vs-openapi-park", enums["manualGateType"], park_manual, errors)

    require_equal(
        "enum capsuleHealth core-vs-openapi",
        enums["capsuleHealth"],
        get_openapi_schema(openapi, "ExternalRunView")["properties"]["capsuleHealth"]["enum"],
        errors,
    )
    require_equal(
        "enum profileConformanceStatus core-vs-openapi",
        enums["profileConformanceStatus"],
        get_openapi_schema(openapi, "ExternalRunView")["properties"]["profileConformanceStatus"]["enum"],
        errors,
    )
    require_equal(
        "enum artifactCertificationState core-vs-openapi",
        enums["artifactCertificationState"],
        get_openapi_schema(openapi, "ArtifactView")["properties"]["artifactCertificationState"]["enum"],
        errors,
    )
    require_true(
        "ExternalRunView.runState must reference RunState",
        get_openapi_schema(openapi, "ExternalRunView")["properties"]["runState"].get("$ref") == "#/components/schemas/RunState",
        errors,
    )
    require_equal(
        "enum runState core-vs-openapi",
        enums["runState"],
        get_openapi_schema(openapi, "RunState")["enum"],
        errors,
    )
    require_true(
        "ParkRequest.reasonCode must reference ReasonCode",
        get_openapi_schema(openapi, "ParkRequest")["properties"]["reasonCode"].get("$ref") == "#/components/schemas/ReasonCode",
        errors,
    )
    require_true(
        "RehydrateRequest.reasonCode must reference ReasonCode",
        get_openapi_schema(openapi, "RehydrateRequest")["properties"]["reasonCode"].get("$ref") == "#/components/schemas/ReasonCode",
        errors,
    )
    require_true(
        "ConsumptionWaiverRequest.reasonCode must reference ReasonCode",
        get_openapi_schema(openapi, "ConsumptionWaiverRequest")["properties"]["reasonCode"].get("$ref") == "#/components/schemas/ReasonCode",
        errors,
    )
    require_equal(
        "enum reasonCode core-vs-openapi",
        enums["reasonCode"],
        get_openapi_schema(openapi, "ReasonCode")["enum"],
        errors,
    )
    require_equal(
        "enum inputDependencyState core-vs-openapi",
        enums["inputDependencyState"],
        get_openapi_schema(openapi, "LineageView")["properties"]["consumers"]["items"]["properties"]["inputDependencyState"]["enum"],
        errors,
    )

    openapi_error_codes = get_openapi_schema(openapi, "ErrorResponse")["properties"]["code"]["enum"]
    require_equal("enum errorCode core-vs-openapi", enums["errorCode"], openapi_error_codes, errors)

    event_names = [item["canonicalName"] for item in events["events"]]
    require_equal("eventCanonicalName core-vs-events", enums["eventCanonicalName"], event_names, errors)
    event_versions = {item["canonicalName"]: item["version"] for item in events["events"]}

    md = (BUNDLE / "paperclip_darkfactory_revised_framework_v2_9_companion_bound.md").read_text(encoding="utf-8")
    documented_tokens = set(re.findall(r"`([A-Za-z0-9_.]+)`", md))
    documented_event_set = {name for name in documented_tokens if name in event_names}
    require_true(
        "main doc must mention every canonical event at least once",
        set(event_names).issubset(documented_event_set),
        errors,
    )

    protocol_tag = core["protocolReleaseTag"]
    require_true(
        "README must declare protocolReleaseTag",
        f"protocolReleaseTag = {protocol_tag}" in README.read_text(encoding="utf-8"),
        errors,
    )
    require_true(
        "invariants must declare protocolReleaseTag",
        protocol_tag in INVARIANTS.read_text(encoding="utf-8"),
        errors,
    )

    mutation_ops = []
    for path_name, path_item in openapi["paths"].items():
        for method, op in path_item.items():
            if method.lower() not in {"post", "put", "patch", "delete"}:
                continue
            mutation_ops.append((path_name, method.lower(), op))
            params = op.get("parameters", [])
            has_header = any(p.get("$ref") == "#/components/parameters/ProtocolReleaseTagHeader" for p in params)
            require_true(f"mutation {method.upper()} {path_name} missing X-Protocol-Release-Tag header", has_header, errors)

            rb = op.get("requestBody", {})
            content = rb.get("content", {}).get("application/json", {})
            schema_ref = content.get("schema", {}).get("$ref")
            require_true(f"mutation {method.upper()} {path_name} request body missing schema", bool(schema_ref), errors)
            if schema_ref:
                schema_name = schema_ref.rsplit("/", 1)[-1]
                schema_obj = get_openapi_schema(openapi, schema_name)
                require_true(
                    f"mutation {method.upper()} {path_name} body missing protocolReleaseTag requirement",
                    "protocolReleaseTag" in schema_obj.get("required", []),
                    errors,
                )

    for schema_name in ["ExternalRunView", "ArtifactView", "LineageView", "ErrorResponse"]:
        schema_obj = get_openapi_schema(openapi, schema_name)
        require_true(f"response schema {schema_name} missing protocolReleaseTag required", "protocolReleaseTag" in schema_obj.get("required", []), errors)
        prop = schema_obj["properties"].get("protocolReleaseTag")
        require_true(f"response schema {schema_name} missing protocolReleaseTag enum", bool(prop and prop.get("enum") == [protocol_tag]), errors)

    required_event_envelope = {
        "eventName", "eventVersion", "eventId", "emittedAt", "protocolReleaseTag", "traceId",
        "producer", "causationId", "correlationId", "sequenceNo", "isReplay"
    }
    require_true(
        "event envelope missing required protocol fields",
        required_event_envelope.issubset(set(events["envelope"]["required"])),
        errors,
    )

    object_names = ["ExecutionCapabilityLease", "ArtifactCertification", "LineageEdge", "ConsumptionWaiver", "ShadowCompareRecord", "ParkRecord", "RehydrationToken", "ManualGateDefinition"]
    defs = schema["$defs"]
    for name in object_names:
        obj = defs[name]
        require_true(f"schema object {name} missing protocolReleaseTag required", "protocolReleaseTag" in obj.get("required", []), errors)

    legacy_aliases = {
        alias
        for item in events["events"]
        for alias in item.get("legacyAliases", [])
    }

    timeline_paths = sorted(TIMELINE_DIR.glob("*.jsonl"))
    timeline_names = {path.name for path in timeline_paths}
    for path in timeline_paths:
        try:
            timeline_entries = load_timeline_entries(path)
        except Exception as e:
            errors.append(str(e))
            continue
        require_true(f"{path.name} must contain at least one event", bool(timeline_entries), errors)
        for line_no, obj in timeline_entries:
            name = obj["eventName"]
            require_true(f"{path.name}:{line_no} uses non-canonical event {name}", name in event_names, errors)
            require_true(f"{path.name}:{line_no} uses legacy alias event {name}", name not in legacy_aliases, errors)
            require_true(
                f"{path.name}:{line_no} missing protocolReleaseTag",
                obj.get("protocolReleaseTag") == protocol_tag,
                errors,
            )
            require_true(
                f"{path.name}:{line_no} eventVersion mismatch for {name}",
                obj.get("eventVersion") == event_versions.get(name),
                errors,
            )
            validate_timeline_projection(path, line_no, obj, enums, errors)

    trace_rows = load_traceability_rows(traceability)
    require_true("traceability must contain release-blocking rows", any(r.get("release_blocking") == "true" for r in trace_rows), errors)

    spec_case_ids = extract_test_case_ids(spec_text)
    trace_case_ids = {r["test_case_id"] for r in trace_rows if r.get("test_case_id")}
    missing_in_trace = sorted(spec_case_ids - trace_case_ids)
    extra_in_trace = sorted(trace_case_ids - spec_case_ids)
    require_true(f"traceability missing spec test_case_id(s): {missing_in_trace}", not missing_in_trace, errors)
    require_true(f"traceability has unknown test_case_id(s): {extra_in_trace}", not extra_in_trace, errors)

    for row in trace_rows:
        golden_timeline = (row.get("golden_timeline") or "").strip()
        if not golden_timeline:
            continue
        if golden_timeline == "golden_timelines/*.jsonl":
            continue
        require_true(
            f"traceability references missing golden timeline {golden_timeline}",
            (BUNDLE / golden_timeline).exists(),
            errors,
        )

    manifest_files = manifest.get("files", [])
    manifest_paths = [item["path"] for item in manifest_files]
    require_true("manifest file paths must be unique", len(manifest_paths) == len(set(manifest_paths)), errors)
    for item in manifest_files:
        rel_path = item["path"]
        full_path = BUNDLE / rel_path
        require_true(f"manifest path missing on disk: {rel_path}", full_path.exists(), errors)
        digest = item.get("sha256")
        require_true(f"manifest entry missing sha256: {rel_path}", isinstance(digest, str) and len(digest) == 64, errors)
        if full_path.exists() and isinstance(digest, str) and len(digest) == 64:
            require_true(
                f"manifest sha256 mismatch: {rel_path}",
                sha256_file(full_path) == digest,
                errors,
            )

    if errors:
        print("FAILED")
        for item in errors:
            print(f"- {item}")
        sys.exit(1)

    print("PASS")
    print(f"checked mutation_ops={len(mutation_ops)} canonical_events={len(event_names)} golden_timelines={len(list(TIMELINE_DIR.glob('*.jsonl')))}")


if __name__ == "__main__":
    main()
