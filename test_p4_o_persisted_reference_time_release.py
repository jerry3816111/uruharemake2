import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
RELEASE = ROOT / "research" / "p4_o_persisted_reference_time_release_2026-09-22.json"


def _load():
    return json.loads(RELEASE.read_text(encoding="utf-8"))


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_release_binds_offline_result_acceptance_and_test():
    release = _load()
    assert release["status"] == "released_offline_only"
    for binding in release["result_checkpoint"].values():
        if isinstance(binding, dict):
            assert _sha256(ROOT / binding["path"]) == binding["sha256"]


def test_release_does_not_promote_offline_fix_to_product_delivery():
    capability = _load()["released_capability"]
    assert capability["after_exact_surface_delivered"] is True
    assert capability["affected_regression_passed"] == 196
    assert capability["affected_regression_failed"] == 0
    assert capability["product_delivery_verified"] is False
    assert capability["safari_verified"] is False


def test_next_stage_requires_new_no_retry_case_and_new_entry():
    next_stage = _load()["next_stage"]
    assert next_stage["id"] == "P4-O-REAL"
    assert next_stage["required_entry"] == "uruha_web_ui_product_p4_o.py"
    assert next_stage["resource_limits"] == {
        "retry_count": 0,
        "planner_model_call_count": 0,
        "fallback_count": 0,
        "paid_api_call_count": 0,
    }
    assert any("ごぼう茶" in item and "そば茶" in item for item in next_stage["forbidden"])
