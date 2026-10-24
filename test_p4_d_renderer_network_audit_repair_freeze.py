import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
FREEZE = ROOT / "research" / "p4_d_renderer_network_audit_repair_freeze_2026-09-20.json"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def test_repair_freeze_binds_implementation_bundle_and_measurement_repair():
    freeze = json.loads(FREEZE.read_text(encoding="utf-8"))
    assert freeze["status"] == "frozen_before_post_commit_product_acceptance"
    for binding in freeze["bindings"].values():
        assert _sha256(ROOT / binding["path"]) == binding["sha256"]


def test_freeze_preserves_failed_proxy_and_unchanged_no_network_requirement():
    freeze = json.loads(FREEZE.read_text(encoding="utf-8"))
    repair = freeze["first_build_and_repair"]
    assert repair["original_raw_literal_proxy_passed"] is False
    assert repair["repair_batch_count"] == 1
    assert repair["dependency_or_runtime_behavior_changed_by_repair"] is False
    verified = freeze["offline_verified_behavior"]
    assert verified["entry_source_remote_url_count"] == 0
    assert verified["entry_source_fetch_or_xhr_count"] == 0
    assert verified["server_upload_count"] == 0
    assert verified["action_policy_connection_count"] == 0


def test_browser_acceptance_remains_pending_and_zero_call():
    freeze = json.loads(FREEZE.read_text(encoding="utf-8"))
    acceptance = freeze["post_commit_acceptance"]
    assert acceptance["safari_valid_local_vrm_render_required"] is True
    assert acceptance["safari_invalid_file_failure_required"] is True
    assert acceptance["browser_external_request_count_exact"] == 0
    assert acceptance["additional_model_or_tool_call_ceiling"] == 0
