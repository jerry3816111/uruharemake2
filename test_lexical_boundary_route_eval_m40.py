import pytest
from uruha_lexical_boundary_route_eval_m40 import evaluate_reserve_m40, validate_reserve_m40


def _dev_case():
    return {"id":"dev-not-reserve","language":"en","category":"benign_affirmation",
            "input":"That's excellent.","expected_protected":False}


def test_duplicate_and_inconsistent_labels_rejected():
    row = _dev_case()
    with pytest.raises(ValueError):
        validate_reserve_m40({"cases":[row,row]})
    with pytest.raises(ValueError):
        validate_reserve_m40({"cases":[{**row,"expected_boundary_intent":"abuse_pushback"}]})


def test_development_comparison_counts_actual_rule_output_not_declared_action():
    result = evaluate_reserve_m40({"cases":[_dev_case()]}, {"gates":{"system_protection_accuracy_min":1.0}})
    assert result["decision"] == "pass_all_frozen_gates"
    assert result["metrics"]["baseline_protection_accuracy"] == 0
    assert result["metrics"]["system_protection_accuracy"] == 1
    assert result["metrics"]["model_call_count"] == 0
    assert result["metrics"]["raw_trace_write_count"] == 0
