import json
from pathlib import Path

import p3_c1_controlled_context_flip_lane as c1


ROOT = Path(__file__).resolve().parent
RELEASE = ROOT / "research" / "p3_c2_controlled_context_flip_release_2026-09-20.json"


def test_c2_release_preserves_failed_sesoi_and_locks_holdout():
    release = json.loads(RELEASE.read_text(encoding="utf-8"))
    assert release["status"] == "released_complete_development_batch_primary_sesoi_not_met_holdout_locked"
    assert release["execution"]["model_calls"] == 32
    assert release["execution"]["validated_predictions"] == 32
    assert release["execution"]["retry_count"] == 0
    assert release["execution"]["holdout_input_access_count"] == 0
    assert release["execution"]["holdout_target_access_count"] == 0
    assert release["result"]["system_improvement"] == 0.012333
    assert release["result"]["preregistered_sesoi"] == 0.03
    assert release["result"]["primary_sesoi_passed"] is False
    assert release["result"]["controlled_lane_success"] is False
    assert release["claims"]["system_advantage_authorized"] is False
    assert release["claims"]["holdout_execution_authorized"] is False


def test_c2_release_binds_exact_freeze_result_and_acceptance():
    release = json.loads(RELEASE.read_text(encoding="utf-8"))
    for binding in release["bindings"].values():
        path = ROOT / binding["path"]
        assert path.is_file()
        assert c1.sha256_file(path) == binding["sha256"]
    assert release["next_stage"]["id"] == "P3-C3"
    assert release["next_stage"]["metadata_schema_and_license_discovery_only"] is True
    assert release["next_stage"]["benchmark_test_answer_access_authorized"] is False
    assert release["next_stage"]["model_call_authorized"] is False
