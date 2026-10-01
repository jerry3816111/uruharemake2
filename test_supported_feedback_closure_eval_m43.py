"""Evaluator mechanics use generated development rows, never the reserve."""
from copy import deepcopy
import pytest
from uruha_supported_feedback_closure_eval_m43 import evaluate_reserve_m43,validate_reserve_m43,CATEGORIES


def development_dataset():
    inputs={"pure_support":"Correct, thanks a lot!","support_with_new_content":"Correct, now tell me more.",
            "ordinary_statement":"Our club voted yes yesterday.","quotation_or_negation":"That's not correct.",
            "unverified":"Indeed!","protected":"Yes, absolutely correct.","unresolved_question":"Correct about what?"}
    cases=[]
    for i,category in enumerate(sorted(CATEGORIES)):
        pure=category=="pure_support"
        cases.append({"id":f"eval-dev-{i}","language":"en","category":category,"input":inputs[category],
                      "feedback":"uncertain_linked" if category=="unverified" else "supported_linked",
                      "plan":"crisis" if category=="protected" else "normal",
                      "pending":"linked" if pure else "unrelated","expected_authority":pure,"expected_closed":pure})
    return {"cases":cases}


def test_metrics_include_controls_and_denominators():
    data=development_dataset()
    result=evaluate_reserve_m43(data,{"gates":{"authority_accuracy_min":1,"raw_trace_write_count_max":0},"evidence_boundary":"development only"})
    assert result["decision"]=="pass_all_frozen_gates"
    assert result["metrics"]["case_count"]==7
    assert result["metrics"]["precise_pending_closure_accuracy"]==1
    assert result["metrics"]["unrelated_pending_preservation"]==1
    assert result["metrics"]["upstream_outcome_invariance"]==1
    assert result["metrics"]["protected_plan_invariance"]==1
    assert result["metrics"]["baseline_authority_accuracy"]<1


def test_missing_duplicate_or_invalid_data_is_rejected():
    data=development_dataset()
    for altered in [{"cases":[]},{"cases":data["cases"][:-1]},
                    {"cases":data["cases"]+[data["cases"][0]]}]:
        with pytest.raises(ValueError):validate_reserve_m43(altered)
    bad=deepcopy(data);bad["cases"][0]["expected_authority"]="yes"
    with pytest.raises(ValueError):validate_reserve_m43(bad)
