import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VALIDATOR_PATH = ROOT / "tools" / "validate_v3_bundle.py"


def load_validator():
    spec = importlib.util.spec_from_file_location("validate_v3_bundle", VALIDATOR_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_validator_reports_clean_bundle():
    validator = load_validator()
    report = validator.validate_bundle(ROOT)
    assert report["summary"]["errors"] == 0
    assert report["summary"]["warnings"] == 0
    check_ids = {check["id"] for check in report["checks"]}
    assert "manifest-path-exists" in check_ids
    assert "manifest-sha256-match" in check_ids
    assert "event-enum-contract-parity" in check_ids
    assert "state-matrix-enum-parity" in check_ids
    assert "release-blocker-scenario-traceability" in check_ids
    assert "golden-timeline-exists" in check_ids
    assert "golden-timeline-event-contract-parity" in check_ids


def test_validator_can_render_reports():
    validator = load_validator()
    report = validator.validate_bundle(ROOT)
    markdown = validator.render_markdown(report)
    assert "# V3.0 Bundle Consistency Check" in markdown
    assert "errors: 0" in markdown
    assert "warnings: 0" in markdown
    assert "manifest-sha256-match" in markdown
