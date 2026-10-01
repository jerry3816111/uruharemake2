import json
from pathlib import Path

import p3_b71c_source3_future_aggregate_scoring as b71c


ROOT = Path(__file__).resolve().parent
RELEASE = ROOT / "research" / "p3_b71c_source3_future_aggregate_release_2026-09-20.json"


def test_release_preserves_mixed_negative_result_and_proxy_collapse():
    release = json.loads(RELEASE.read_text(encoding="utf-8"))
    assert release["status"] == "released_mixed_source3_proxy_no_system_advantage_with_label_collapse"
    assert release["result"]["row_wins"] == {
        "BASELINE_LITERAL": 2,
        "SYSTEM_PRAGMATIC_STATE": 2,
        "TIE": 0,
    }
    assert release["result"]["actual_proxy_label_count"] == 1
    assert release["result"]["matched_proxy_marker_count"] == 0
    assert release["result"]["model_human_or_llm_judge_call_count"] == 0


def test_release_blocks_source_expansion_until_b72_proxy_audit():
    release = json.loads(RELEASE.read_text(encoding="utf-8"))
    next_stage = release["next_stage"]
    assert next_stage["id"] == "P3-B72"
    assert next_stage["new_source_or_future_access_allowed"] is False
    assert next_stage["source_expansion_authorized"] is False
    assert next_stage["prediction_mutation_allowed"] is False


def test_release_binding_hashes_match():
    release = json.loads(RELEASE.read_text(encoding="utf-8"))
    for binding in release["bindings"].values():
        path = ROOT / binding["path"]
        assert path.is_file()
        assert b71c.sha256_file(path) == binding["sha256"]
