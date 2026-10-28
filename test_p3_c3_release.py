import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
RELEASE = ROOT / "research" / "p3_c3_external_pragmatic_benchmark_discovery_release_2026-09-20.json"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def test_release_binds_exact_discovery_evidence():
    release = json.loads(RELEASE.read_text(encoding="utf-8"))
    assert release["status"] == "released_no_executable_external_benchmark_now"
    for binding in release["bindings"].values():
        path = ROOT / binding["path"]
        assert path.is_file()
        assert _sha256(path) == binding["sha256"]


def test_result_preserves_candidate_specific_decisions_and_zero_answer_access():
    release = json.loads(RELEASE.read_text(encoding="utf-8"))
    result_path = ROOT / release["bindings"]["discovery_result"]["path"]
    result = json.loads(result_path.read_text(encoding="utf-8"))
    decisions = {candidate["id"]: candidate["decision"] for candidate in result["candidates"]}
    assert decisions == {
        "DRInQ": "conditionally_eligible_blocked",
        "PaCE": "method_fit_artifact_blocked",
        "PUB": "rejected_for_p3_c3",
    }
    assert result["aggregate_decision"]["executable_candidate_count"] == 0
    assert result["access_accounting"]["benchmark_dataset_file_download_count"] == 0
    assert result["access_accounting"]["benchmark_dataset_row_read_count"] == 0
    assert result["access_accounting"]["benchmark_hidden_test_answer_access_count"] == 0
    assert result["access_accounting"]["model_call_count"] == 0


def test_release_does_not_turn_discovery_into_effect_or_product_authorization():
    release = json.loads(RELEASE.read_text(encoding="utf-8"))
    assert release["decision"]["additional_search_or_dataset_access_authorized"] is False
    assert release["decision"]["c1_holdout_execution_authorized"] is False
    assert release["decision"]["explicit_pragmatic_state_product_integration_authorized"] is False
    assert release["p3_controlled_lane_disposition"]["system_advantage_claim_authorized"] is False
    assert release["p3_controlled_lane_disposition"]["preserve_c1_holdout_locked"] is True
    assert release["next_stage"]["id"] == "P4-A"
    assert release["next_stage"]["read_only_inventory_first"] is True
    assert release["next_stage"]["new_dashboard_authorized"] is False
