import json
from copy import deepcopy
from pathlib import Path

import p4_at_executed_action_outcome_closure_gate as gate
import uruha_adaptive_person_model as adaptive
import uruha_executed_action_outcome_closure_p4 as p4_at
import uruha_executed_action_receipt_m44 as receipt_m44


ROOT = Path(__file__).resolve().parent
DATASET = ROOT / "datasets" / "p4_at_executed_action_outcome_closure_v1.json"


def test_p4_at_offline_evidence_passes_frozen_gate():
    evidence = p4_at.build_dataset_evidence_p4_at(DATASET)
    evaluated = gate.evaluate_offline_evidence(gate.load_contract(), evidence)

    assert evaluated["status"] == "pass", (evaluated, evidence["metrics"])
    assert evaluated["failed_gates"] == []


def test_p4_at_dual_act_cases_keep_outcome_and_current_request_separate():
    evidence = p4_at.build_dataset_evidence_p4_at(DATASET)
    positives = [
        row
        for row in evidence["cases"]
        if row["partition"] in {"development_sequences", "fresh_positive_sequences"}
    ]

    assert len(positives) == 10
    for row in positives:
        assert row["previous_action_outcome"] == row["expected_previous_action_outcome"]
        assert row["current_request_policy"] == row["expected_current_request_policy"]
        assert row["exact_receipt_identity"] is True
        assert row["performed_action_strictly_earlier"] is True
        assert row["p4_ag_identity_bound"] is True
        assert row["p4_ag_feedback_linked"] is True
        assert row["visible_action_act_match"] is True
        assert row["visible_reply_japanese"] is True
        assert row["candidate_score_or_order_unchanged"] is True


def test_p4_at_controls_do_not_create_false_previous_action_support():
    evidence = p4_at.build_dataset_evidence_p4_at(DATASET)
    controls = [
        row
        for row in evidence["cases"]
        if row["partition"] == "fresh_control_sequences"
    ]

    assert len(controls) == 7
    for row in controls:
        if row["expected_previous_action_outcome"] == "unknown":
            assert row["previous_action_outcome"] == "unknown"
            assert row["unknown_counted_as_success"] is False
        assert row["current_request_policy"] == row["expected_current_request_policy"]
        assert row["raw_dialogue_persisted"] is False


def test_p4_at_current_request_projection_overrides_prior_question_wording_only():
    original = adaptive.classify_explicit_desired_response_m25
    text = "Asking that first was the right move. Now I need one concrete method."
    base = original(text)
    projected = p4_at.classify_explicit_desired_response_with_p4_at(text, original)

    assert base["selected_policy"] == "calibrate_need"
    assert projected["selected_policy"] == "solve_regulation"
    assert projected["authority"] == "current_explicit_desired_response"
    assert projected["p4_at_current_request_projection"]["private_state_truth_claimed"] is False


def test_p4_at_prior_outcome_requires_exact_pending_receipt_identity():
    model, _binding = p4_at._fixture_pending()
    before = deepcopy(model)
    model[receipt_m44.STORE][0]["prediction_id"] = "p1-9-mismatch"
    trace = p4_at.decompose_executed_action_feedback_p4(
        "That was the right question. I need one concrete method.",
        model,
        2,
    )

    assert trace["exact_pending_receipt_identity"] is False
    assert trace["previous_action_outcome"] == "unknown"
    assert trace["prediction_id"] is None
    assert before["pending_prediction"] == model["pending_prediction"]


def test_p4_at_graph_payload_precedes_binding_temporal_and_utterance():
    feedback = {
        p4_at.LABEL: {
            "schema": p4_at.SCHEMA,
            "previous_action_outcome": "supported",
            "current_request_policy": "solve_regulation",
            "prediction_id": "p1-1-test",
            "raw_dialogue_persisted": False,
        }
    }
    result = {
        "reply": "じゃあ、まず一個だけ決めよ。",
        "logic": {
            "semantic_persona_surface_verifier_m39": {
                "selected_policy_id": "solve_regulation",
                "policy_act_match_after": True,
                "unresolved_violations": [],
            },
            "desired_response_outcome_binding_p4": {
                "previous_resolution": {
                    "status": "resolved",
                    "identity_bound": True,
                    "feedback_linked": True,
                    "outcome": "supported",
                }
            },
            "runtime_temporal_graph_delivery_p4": {
                "present": {"previous_outcome_verification": "supported"},
                "transition": {"current_verification_queued_for_later": True},
            },
        },
        "runtime_trace": {
            "blackboard": [
                {"label": "desired_response_outcome_binding_p4"},
                {"label": "runtime_temporal_graph_delivery_p4"},
                {"label": "utterance"},
            ]
        },
    }

    updated = p4_at.materialize_executed_action_outcome_closure_p4(result, feedback)
    labels = [row["label"] for row in updated["runtime_trace"]["blackboard"]]

    assert labels.index(p4_at.LABEL) < labels.index("desired_response_outcome_binding_p4")
    assert labels.index(p4_at.LABEL) < labels.index("runtime_temporal_graph_delivery_p4")
    assert labels.index(p4_at.LABEL) < labels.index("utterance")
    assert updated["logic"][p4_at.LABEL] == updated["runtime_trace"][p4_at.LABEL]
    assert updated["logic"][p4_at.LABEL]["same_turn_outcome_relabelled_as_old_past"] is False


def test_p4_at_source_has_no_frozen_full_case_lookup():
    source = (ROOT / "uruha_executed_action_outcome_closure_p4.py").read_text(
        encoding="utf-8"
    )
    dataset = json.loads(DATASET.read_text(encoding="utf-8"))

    for partition in (
        "development_sequences",
        "fresh_positive_sequences",
        "fresh_control_sequences",
    ):
        for row in dataset[partition]:
            assert row["turn_2"] not in source


def test_p4_at_product_entry_is_additive_after_p4_as():
    source = (ROOT / "uruha_web_ui_product_p4_at.py").read_text(encoding="utf-8")
    launcher = (ROOT / "p4_at_safe_isolated_product_launcher.py").read_text(
        encoding="utf-8"
    )

    assert "import uruha_web_ui_product_p4_as as _p4_as" in source
    assert "install_executed_action_outcome_closure_p4()" in source
    assert 'ENTRYPOINT = ROOT / "uruha_web_ui_product_p4_at.py"' in launcher
    assert "sandboxed_p4_at_probe" in launcher
