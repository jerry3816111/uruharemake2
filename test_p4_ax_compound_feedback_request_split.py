import json
from copy import deepcopy
from pathlib import Path

import p4_ax_compound_feedback_request_split_gate as gate
import uruha_compound_feedback_request_split_p4 as p4_ax
import uruha_executed_action_outcome_closure_p4 as p4_at
import uruha_executed_action_receipt_m44 as receipt_m44


ROOT = Path(__file__).resolve().parent
DATASET = ROOT / "datasets" / "p4_ax_compound_feedback_request_split_v1.json"


def test_p4_ax_offline_evidence_passes_frozen_gate():
    evidence = p4_ax.build_dataset_evidence_p4_ax(DATASET)
    evaluated = gate.evaluate_offline_evidence(gate.load_contract(), evidence)

    assert evaluated["status"] == "pass", (evaluated, evidence["metrics"])
    assert evaluated["failed_gates"] == []


def test_p4_ax_fresh_positives_decompose_support_and_current_request():
    evidence = p4_ax.build_dataset_evidence_p4_ax(DATASET)
    positives = [row for row in evidence["cases"] if row["split"] == "fresh_positive"]

    assert len(positives) == 9
    for row in positives:
        assert row["p4_ax_status"] == p4_ax.AUTHORIZED_STATUS
        assert row["previous_action_outcome"] == "supported"
        assert row["current_request_policy"] == "solve_regulation"
        assert row["two_independent_acts"] is True
        assert row["exact_receipt_identity"] is True
        assert row["p4_au_gate_bypassed"] is False


def test_p4_ax_controls_do_not_create_false_previous_action_support():
    evidence = p4_ax.build_dataset_evidence_p4_ax(DATASET)
    controls = [row for row in evidence["cases"] if row["split"] == "fresh_control"]

    assert len(controls) == 12
    for row in controls:
        assert row["previous_action_outcome"] == "unknown"
        assert row["p4_ax_status"] == "predecessor_preserved"
        assert row["private_state_truth_claimed"] is False
        assert row["raw_dialogue_persisted"] is False


def test_p4_ax_existing_p4_at_question_support_is_bitwise_preserved_in_core_fields():
    evidence = p4_ax.build_dataset_evidence_p4_ax(DATASET)
    predecessors = [row for row in evidence["cases"] if row["split"] == "predecessor_control"]

    assert len(predecessors) == 6
    for row in predecessors:
        assert row["previous_action_outcome"] == "supported"
        assert row["predecessor_core_unchanged"] is True
        assert row["p4_ax_status"] == "predecessor_preserved"


def test_p4_ax_cannot_support_without_exact_pending_receipt_identity():
    dataset = json.loads(DATASET.read_text(encoding="utf-8"))
    text = next(row["input"] for row in dataset["cases"] if row["split"] == "fresh_positive")
    model, _binding = p4_at._fixture_pending()
    before = deepcopy(model)
    model[receipt_m44.STORE][0]["prediction_id"] = "p1-9-mismatch"
    trace = p4_ax.decompose_compound_feedback_request_split_p4_ax(text, model, 2)

    assert trace["exact_pending_receipt_identity"] is False
    assert trace["previous_action_outcome"] == "unknown"
    assert trace[p4_ax.LABEL]["status"] == "predecessor_preserved"
    assert before["pending_prediction"] == model["pending_prediction"]


def test_p4_ax_graph_node_precedes_p4_at_binding_temporal_and_utterance():
    payload = {
        "schema": p4_ax.SCHEMA,
        "status": p4_ax.AUTHORIZED_STATUS,
        "raw_dialogue_persisted": False,
    }
    result = {
        "logic": {p4_at.LABEL: {p4_ax.LABEL: payload}},
        "runtime_trace": {
            "blackboard": [
                {"label": p4_at.LABEL},
                {"label": "desired_response_outcome_binding_p4"},
                {"label": "runtime_temporal_graph_delivery_p4"},
                {"label": "utterance"},
            ]
        },
    }

    updated = p4_ax.append_compound_feedback_request_split_node_p4_ax(result)
    labels = [row["label"] for row in updated["runtime_trace"]["blackboard"]]

    assert labels.index(p4_ax.LABEL) < labels.index(p4_at.LABEL)
    assert labels.index(p4_ax.LABEL) < labels.index("desired_response_outcome_binding_p4")
    assert labels.index(p4_ax.LABEL) < labels.index("runtime_temporal_graph_delivery_p4")
    assert labels.index(p4_ax.LABEL) < labels.index("utterance")
    assert updated["logic"][p4_ax.LABEL] == updated["runtime_trace"][p4_ax.LABEL]


def test_p4_ax_source_has_no_frozen_fresh_case_lookup():
    source = (ROOT / "uruha_compound_feedback_request_split_p4.py").read_text(encoding="utf-8")
    dataset = json.loads(DATASET.read_text(encoding="utf-8"))

    for row in dataset["cases"]:
        if row["split"] in {"fresh_positive", "fresh_control"}:
            assert row["input"] not in source


def test_p4_ax_product_entry_is_additive_after_p4_aw():
    source = (ROOT / "uruha_web_ui_product_p4_ax.py").read_text(encoding="utf-8")
    launcher = (ROOT / "p4_ax_safe_isolated_product_launcher.py").read_text(encoding="utf-8")

    assert "import uruha_web_ui_product_p4_aw as _p4_aw" in source
    assert "install_compound_feedback_request_split_p4_ax()" in source
    assert 'ENTRYPOINT = ROOT / "uruha_web_ui_product_p4_ax.py"' in launcher
    assert "sandboxed_p4_ax_probe" in launcher
