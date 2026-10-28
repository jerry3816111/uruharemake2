import json
from pathlib import Path

import p3_b71b_source3_b70_prediction_batch as b71b


ROOT = Path(__file__).resolve().parent
RELEASE = ROOT / "research" / "p3_b71b_source3_b70_prediction_release_2026-09-20.json"


def test_release_binds_complete_batch_and_future_scoring_next():
    release = json.loads(RELEASE.read_text(encoding="utf-8"))
    assert release["status"] == "released_complete_source3_prediction_batch_future_locked"
    assert release["result"]["model_call_count"] == 8
    assert release["result"]["normalization_applied_count"] == 0
    assert release["result"]["prediction_side_future_access_count"] == 0
    assert release["next_stage"]["id"] == "P3-B71C"
    assert release["next_stage"]["prediction_mutation_allowed"] is False


def test_release_binding_hashes_match():
    release = json.loads(RELEASE.read_text(encoding="utf-8"))
    for binding in release["bindings"].values():
        path = ROOT / binding["path"]
        assert path.is_file()
        assert b71b.sha256_file(path) == binding["sha256"]
