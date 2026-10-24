import json
from pathlib import Path

import p3_b72_cross_source_proxy_validity_audit as b72


ROOT = Path(__file__).resolve().parent
RESULT = ROOT / "analysis" / "p3_b72_cross_source_proxy_validity_audit_result_2026-09-20.json"


def test_saved_result_is_valid_and_rejects_current_proxy():
    result = json.loads(RESULT.read_text(encoding="utf-8"))
    assert b72.validate_result(result) == {"valid": True, "errors": []}
    assert result["status"] == "proxy_not_adequate_for_system_advantage_claim"
    assert result["source_expansion_authorized"] is False
    assert result["diagnostic_failures"] == [
        "label_diversity:source3",
        "marker_hit:source3",
        "aggregate_metric_direction_conflict",
        "source_direction_reversal",
    ]
    assert result["result_hash"] == "abae2c923249e4cfa9f1db5b1c2c39620a4687b37ea311a4c30cf6a97d113992"


def test_saved_result_preserves_conflicting_metrics_and_zero_new_evidence_access():
    result = json.loads(RESULT.read_text(encoding="utf-8"))
    aggregate = result["cross_source_aggregate"]
    assert aggregate["row_wins"] == {"BASELINE_LITERAL": 2, "SYSTEM_PRAGMATIC_STATE": 6, "TIE": 0}
    assert aggregate["condition_metrics"]["BASELINE_LITERAL"]["top1_hits"] == 3
    assert aggregate["condition_metrics"]["SYSTEM_PRAGMATIC_STATE"]["top1_hits"] == 2
    assert set(aggregate["metric_directions"].values()) == {"BASELINE_LITERAL", "SYSTEM_PRAGMATIC_STATE"}
    assert result["new_source_or_future_access_count"] == 0
    assert result["model_human_or_llm_judge_call_count"] == 0
    assert result["prediction_mutation_count"] == 0
