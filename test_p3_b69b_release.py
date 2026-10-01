import json
from pathlib import Path

import p3_b69b_source2_multiwindow_predictions as b69b


ROOT = Path(__file__).resolve().parent
RELEASE_PATH = ROOT / "research" / "p3_b69b_source2_multiwindow_prediction_release_2026-09-20.json"


def test_b69b_release_preserves_terminal_failure_and_forbids_future_unlock():
    release = json.loads(RELEASE_PATH.read_text(encoding="utf-8"))
    assert release["status"] == "released_terminal_incomplete_batch_future_locked"
    assert release["result"]["model_call_count"] == 7
    assert release["result"]["required_model_call_count"] == 8
    assert release["result"]["prediction_side_future_access_count"] == 0
    assert release["b69c_future_unlock_authorized"] is False
    assert all(value is False for value in release["terminal_boundary"].values())
    assert release["next_stage"]["id"] == "P3-B70"


def test_b69b_release_binding_hashes_and_saved_result_are_valid():
    release = json.loads(RELEASE_PATH.read_text(encoding="utf-8"))
    for binding in release["bindings"].values():
        path = ROOT / binding["path"]
        assert path.is_file()
        assert b69b.sha256_file(path) == binding["sha256"]
    result = json.loads((ROOT / release["bindings"]["saved_result"]["path"]).read_text(encoding="utf-8"))
    assert b69b.validate_result(result) == {"valid": True, "errors": []}
    assert result["result_hash"] == release["result"]["result_hash"]
