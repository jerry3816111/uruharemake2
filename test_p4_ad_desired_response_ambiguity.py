import json
from pathlib import Path

import p4_ad_desired_response_ambiguity_gate as gate
import uruha_desired_response_ambiguity_p4 as ambiguity


ROOT = Path(__file__).resolve().parent
DATASET = ROOT / "datasets" / "p4_ad_desired_response_ambiguity_holdout_v1.json"


def _trace(text, turn_index=1):
    state, decision, mode = ambiguity._isolated_inputs(text, turn_index)
    visible, trace = ambiguity.shadow_visible_reply_p4(
        "この返事は変えない。",
        state,
        decision,
        mode,
    )
    return visible, trace


def test_exposed_user_counterexample_preserves_competing_response_expectations():
    text = "我從早上就一直坐不住，腦子停不下來。"
    visible, trace = _trace(text)
    modes = {row["mode"] for row in trace["candidate_expectations"]}
    assert visible == "この返事は変えない。"
    assert trace["status"] == "ambiguity_preserved"
    assert trace["selected_action"]["mode"] == "low_pressure_clarification"
    assert {"practical_help", "listening", "playful_tease", "low_pressure_clarification"}.issubset(modes)
    assert trace["private_reason_status"] == "unknown_not_observed"
    assert trace["selected_action_is_private_truth_commitment"] is False
    assert trace["candidate_action_score_is_private_truth_probability"] is False
    assert trace["candidate_contract_passed"] is True
    assert text not in json.dumps(trace, ensure_ascii=False)


def test_explicit_solution_and_tease_only_authorize_response_form_not_private_reason():
    solution = "我真的在問現在怎麼讓腦袋慢下來，先給我一個能做的方法。"
    tease = "不是要方法啦，我是在等你吐槽我，平常不是都會互相吐槽嗎？"
    _, solution_trace = _trace(solution, 2)
    _, tease_trace = _trace(tease, 3)
    assert solution_trace["status"] == "explicit_response_form_observed"
    assert solution_trace["selected_action"]["mode"] == "practical_help"
    assert tease_trace["status"] == "explicit_response_form_observed"
    assert tease_trace["selected_action"]["mode"] == "playful_tease"
    for trace in (solution_trace, tease_trace):
        assert trace["private_reason_status"] == "unknown_beyond_explicit_response_form"
        assert trace["selected_action"]["selection_is_private_truth_commitment"] is False


def test_candidate_evidence_and_outcome_contracts_keep_known_inferred_unknown_separate():
    _, trace = _trace("我從早上就一直坐不住，腦子停不下來。")
    for candidate in trace["candidate_expectations"]:
        assert candidate["score_semantics"] == ambiguity.ACTION_SCORE_SEMANTICS
        assert candidate["selected_as_private_truth"] is False
        assert candidate["long_term_fact_write_allowed"] is False
        assert candidate["verification_contract"] == {
            "supporting_outcome": "next_turn_explicit_acceptance_of_same_response_mode",
            "contradicting_outcome": "next_turn_explicit_rejection_or_different_response_mode",
            "unknown_outcome": "topic_change_or_unlinked_reply",
            "unknown_counts_as_success": False,
        }
        for evidence in candidate["support_evidence"]:
            assert evidence["source_path"].startswith("desired_response_state_m18.atoms.")
            assert evidence["epistemic_status"] in {
                "current_visible_evidence",
                "verified_reversible_history",
                "unknown_no_decisive_evidence",
                "provisional_operational_inference",
            }


def test_graph_node_is_unique_before_utterance_and_reply_is_unchanged():
    _, trace = _trace("我從早上就一直坐不住，腦子停不下來。")
    result = {
        "reply": "そのまま。",
        "logic": {},
        "runtime_trace": {
            "blackboard": [
                {"stage": "surface", "label": "utterance", "payload": {}}
            ]
        },
    }
    ambiguity.append_desired_response_ambiguity_node_p4(result, trace)
    ambiguity.append_desired_response_ambiguity_node_p4(result, trace)
    labels = [row["label"] for row in result["runtime_trace"]["blackboard"]]
    assert result["reply"] == "そのまま。"
    assert labels == [ambiguity.LABEL, "utterance"]
    assert result["logic"][ambiguity.LABEL] == trace
    assert result["runtime_trace"][ambiguity.LABEL] == trace


def test_frozen_multilingual_dataset_meets_gate_without_model_or_memory_side_effects():
    evidence = ambiguity.build_dataset_evidence_p4_ad(DATASET)
    result = gate.evaluate_evidence(gate.load_contract(), evidence)
    assert result["status"] == "pass", result["failed_gates"]
    assert result["failed_gates"] == []
