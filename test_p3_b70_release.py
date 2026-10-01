import json
from pathlib import Path

import p3_b70_prediction_interface_reliability as b70


ROOT = Path(__file__).resolve().parent
RELEASE_PATH = ROOT / "research" / "p3_b70_prediction_interface_reliability_release_2026-09-20.json"


def test_b70_release_binds_passed_offline_gate_and_requires_new_source():
    release = json.loads(RELEASE_PATH.read_text(encoding="utf-8"))
    assert release["status"] == "released_offline_probability_normalization_mechanism_gate"
    assert release["result"]["model_call_count"] == 0
    assert release["result"]["future_access_count"] == 0
    assert release["result"]["b69_retry_count"] == 0
    assert release["next_stage"]["id"] == "P3-B71"
    assert release["next_stage"]["exclude_b67_and_b69_sources"] is True
    assert release["next_stage"]["not_formal_independent_holdout"] is True


def test_b70_release_binding_hashes_match():
    release = json.loads(RELEASE_PATH.read_text(encoding="utf-8"))
    for binding in release["bindings"].values():
        path = ROOT / binding["path"]
        assert path.is_file()
        assert b70.sha256_file(path) == binding["sha256"]
