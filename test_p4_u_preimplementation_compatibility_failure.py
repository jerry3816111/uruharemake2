import json
from pathlib import Path

import uruha_utterance_frame_shadow_p4 as p4t


ROOT = Path(__file__).resolve().parent
DATASET = ROOT / "datasets" / "p4_u_frame_preserving_surface_repair_v1.json"
RESULT = ROOT / "analysis" / "p4_u_preimplementation_compatibility_failure_2026-09-22.json"


def test_saved_negative_result_reproduces_predecessor_coverage_gap():
    dataset = json.loads(DATASET.read_text(encoding="utf-8"))
    result = json.loads(RESULT.read_text(encoding="utf-8"))
    exact = 0
    mismatches = []
    for frozen in dataset["holdout_failures"]:
        trace = p4t.inspect_utterance_frame_shadow_p4(frozen["source"], frozen["candidate"])
        if trace["violations"] == frozen["expected_before_violations"]:
            exact += 1
        else:
            mismatches.append(
                {
                    "case_id": frozen["case_id"],
                    "expected": frozen["expected_before_violations"],
                    "observed": trace["violations"],
                }
            )
    assert exact == result["observed"]["holdout_exact_before_violation_count"] == 5
    assert len(mismatches) == len(result["mismatches"]) == 7
    assert [row["case_id"] for row in mismatches] == [row["case_id"] for row in result["mismatches"]]


def test_failure_does_not_relabel_exposed_cases_as_holdout_or_pass():
    result = json.loads(RESULT.read_text(encoding="utf-8"))
    assert result["status"] == "failed_before_product_integration"
    assert result["decision"]["p4_u_pass_claim_allowed"] is False
    assert result["decision"]["p4_u_holdout_reuse_allowed"] is False
    assert result["observed"]["product_integration_count"] == 0
    assert result["observed"]["safari_turn_count"] == 0
