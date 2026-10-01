import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
RELEASE = ROOT / "research" / "p4_c_product_function_calling_release_2026-09-20.json"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def test_release_binds_contract_gate_integration_result_and_acceptance():
    release = json.loads(RELEASE.read_text(encoding="utf-8"))
    assert release["status"] == "released_one_read_only_product_tool_with_chat_regression_pass"
    for binding in release["bindings"].values():
        assert _sha256(ROOT / binding["path"]) == binding["sha256"]


def test_release_preserves_passed_missing_and_next_scope():
    release = json.loads(RELEASE.read_text(encoding="utf-8"))
    assert release["actual_status_turn"]["tool_execution_count"] == 1
    assert release["actual_status_turn"]["side_effect_count"] == 0
    assert release["actual_chat_regression_turn"]["p4_c_added_model_call_count"] == 0
    assert release["not_passed_or_not_present"]["general_function_calling"] == "not_established"
    assert release["not_passed_or_not_present"]["vrm_3d"] == "not_present"
    assert release["next_stage"]["id"] == "P4-D"
    assert release["next_stage"]["unprovenanced_asset_download_authorized"] is False
    assert release["next_stage"]["state_changing_or_physical_execution_authorized"] is False
