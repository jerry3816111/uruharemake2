from copy import deepcopy
import json
from pathlib import Path

import pytest

import p3_b72_cross_source_proxy_validity_audit as b72


ROOT = Path(__file__).resolve().parent


def test_contract_binds_exposed_results_and_allows_no_new_evidence_access():
    contract = b72.load_contract()
    assert b72.validate_contract(contract) == {"valid": True, "errors": []}
    assert contract["status"] == "post_result_diagnostic_audit_frozen_before_execution_not_preregistered_effect_test"
    assert all(value == 0 for value in contract["execution_limits"].values())
    assert contract["decision"]["source_expansion_allowed_on_failure"] is False


def test_contract_fails_closed_on_binding_or_diagnostic_drift(tmp_path: Path):
    contract = b72.load_contract()
    copied = tmp_path / "copied.json"
    copied.write_text("{}", encoding="utf-8")
    changed = deepcopy(contract)
    changed["bindings"]["source1_result"] = {"path": copied.name, "sha256": "0" * 64}
    changed["diagnostics"]["minimum_distinct_actual_labels_per_source"] = 1
    validation = b72.validate_contract(changed, root=tmp_path)
    assert validation["valid"] is False
    assert "binding_hash:source1_result" in validation["errors"]
    assert "minimum_label_diversity" in validation["errors"]


def test_audit_recomputes_exposed_cross_source_metrics_and_rejects_proxy():
    result = b72.audit()
    assert b72.validate_result(result) == {"valid": True, "errors": []}
    assert result["status"] == "proxy_not_adequate_for_system_advantage_claim"
    source1, source3 = result["source_summaries"]
    assert source1["distinct_actual_label_count"] == 2
    assert source1["marker_hit_count"] == 1
    assert source3["distinct_actual_label_count"] == 1
    assert source3["marker_hit_count"] == 0
    assert "label_diversity:source3" in result["diagnostic_failures"]
    assert "marker_hit:source3" in result["diagnostic_failures"]
    assert "aggregate_metric_direction_conflict" in result["diagnostic_failures"]
    assert "source_direction_reversal" in result["diagnostic_failures"]
    assert result["source_expansion_authorized"] is False


def test_audit_reports_all_metrics_instead_of_cherry_picking_row_wins():
    result = b72.audit()
    aggregate = result["cross_source_aggregate"]
    assert aggregate["row_wins"] == {"BASELINE_LITERAL": 2, "SYSTEM_PRAGMATIC_STATE": 6, "TIE": 0}
    baseline = aggregate["condition_metrics"]["BASELINE_LITERAL"]
    system = aggregate["condition_metrics"]["SYSTEM_PRAGMATIC_STATE"]
    assert baseline["mean_actual_label_probability"] == 0.31875
    assert system["mean_actual_label_probability"] == 0.2625
    assert baseline["mean_multiclass_brier"] == 0.9947
    assert system["mean_multiclass_brier"] == 0.982775
    assert baseline["mean_log_loss"] == 5.609082790262
    assert system["mean_log_loss"] == 1.796384009447
    assert baseline["top1_hits"] == 3
    assert system["top1_hits"] == 2
    assert aggregate["metric_directions"] == {
        "row_wins": "SYSTEM_PRAGMATIC_STATE",
        "mean_actual_label_probability": "BASELINE_LITERAL",
        "mean_multiclass_brier": "SYSTEM_PRAGMATIC_STATE",
        "mean_log_loss": "SYSTEM_PRAGMATIC_STATE",
        "top1_hits": "BASELINE_LITERAL",
    }


def test_result_hash_detects_mutation():
    result = b72.audit()
    changed = json.loads(json.dumps(result))
    changed["cross_source_aggregate"]["row_count"] = 9
    assert b72.validate_result(changed)["valid"] is False


@pytest.mark.parametrize(
    "field",
    [
        "network_access_count",
        "new_source_or_future_access_count",
        "model_human_or_llm_judge_call_count",
        "prediction_mutation_count",
        "training_or_production_memory_write_count",
    ],
)
def test_result_rejects_forbidden_counts(field: str):
    result = b72.audit()
    result[field] = 1
    assert b72.validate_result(result)["valid"] is False
