import json
from pathlib import Path

import p4_ay_response_form_constraint_boundary_gate as gate
import uruha_response_form_constraint_boundary_p4 as p4_ay
import uruha_source_bound_current_action_delivery_p4 as p4_au


ROOT = Path(__file__).resolve().parent
DATASET = ROOT / "datasets" / "p4_ay_response_form_constraint_boundary_v1.json"
EVIDENCE = ROOT / "analysis" / "p4_ay_response_form_constraint_boundary_evidence_2026-09-26.json"


def test_p4_ay_offline_evidence_preserves_the_two_gate_failure():
    evidence = p4_ay.build_dataset_evidence_p4_ay(DATASET)
    evaluated = gate.evaluate_offline_evidence(gate.load_contract(), evidence)

    assert evaluated["status"] == "fail"
    assert evaluated["failed_gates"] == [
        "metric_mismatch:development_authorized_count",
        "metric_mismatch:development_prior_source_linked_count",
    ]


def test_p4_ay_saved_evidence_records_the_same_frozen_failure():
    evidence = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    evaluated = gate.evaluate_offline_evidence(gate.load_contract(), evidence)

    assert evidence["status"] == "fail"
    assert evaluated["status"] == "fail"
    assert evaluated["failed_gates"] == [
        "metric_mismatch:development_authorized_count",
        "metric_mismatch:development_prior_source_linked_count",
    ]


def test_p4_ay_exposed_development_stops_at_untouched_prior_role_guard():
    evidence = p4_ay.build_dataset_evidence_p4_ay(DATASET)
    development = [
        row for row in evidence["cases"] if row["partition"] == "development_sequences"
    ]

    assert len(development) == 1
    assert development[0]["p4_au_status_before"] == "blocked_current_task_replacement"
    assert development[0]["p4_ay_status"] == "blocked_non_task_p4_au_guard"
    assert development[0]["prior_source_added"] is False


def test_p4_ay_fresh_positives_link_the_exact_prior_problem_source():
    evidence = p4_ay.build_dataset_evidence_p4_ay(DATASET)
    positives = [row for row in evidence["cases"] if row["partition"] == "fresh_positive_sequences"]

    assert len(positives) == 6
    for row in positives:
        assert row["p4_au_status_before"] == "blocked_current_task_replacement"
        assert row["p4_ay_status"] == p4_ay.AUTHORIZED_STATUS
        assert row["p4_au_status_after"] == "prior_source_linked"
        assert row["prior_source_added"] is True
        assert row["exact_source_identity"] is True
        assert row["downstream_action_contract_passed"] is True


def test_p4_ay_genuine_topic_replacement_and_other_controls_fail_closed():
    evidence = p4_ay.build_dataset_evidence_p4_ay(DATASET)
    controls = [row for row in evidence["cases"] if row["partition"] == "fresh_control_sequences"]

    assert len(controls) == 12
    for row in controls:
        assert row["p4_ay_status"] == row["expected_p4_ay_status"]
        assert row["prior_source_added"] is False
    replacements = [row for row in controls if row["control_family"] == "genuine_topic_replacement"]
    assert len(replacements) == 3
    assert all(row["p4_ay_status"] == "blocked_genuine_task_replacement" for row in replacements)
    assert all(row["genuine_task_ref_count"] >= 1 for row in replacements)


def test_p4_ay_preserves_existing_p4_au_positive_links():
    evidence = p4_ay.build_dataset_evidence_p4_ay(DATASET)

    assert len(evidence["predecessor_cases"]) == 6
    for row in evidence["predecessor_cases"]:
        assert row["p4_au_status_before"] == "prior_source_linked"
        assert row["p4_ay_status"] == "predecessor_preserved"
        assert row["p4_au_status_after"] == "prior_source_linked"
        assert row["prior_source_added"] is False
        assert row["effective_prior_source_present"] is True


def test_p4_ay_trace_is_raw_free_and_does_not_weaken_non_task_guards():
    evidence = p4_ay.build_dataset_evidence_p4_ay(DATASET)
    metrics = evidence["metrics"]

    assert metrics["p4_at_outcome_mutation_count"] == 0
    assert metrics["p4_au_non_task_guard_bypass_count"] == 0
    assert metrics["candidate_score_or_order_change_count"] == 0
    assert metrics["added_model_call_count"] == 0
    assert metrics["factual_memory_write_count"] == 0
    assert metrics["assistant_source_count"] == 0
    assert metrics["private_inference_source_count"] == 0
    assert metrics["raw_dialogue_persisted_count"] == 0
    assert metrics["visible_reply_change_count"] == 0
    assert metrics["full_fresh_string_patch_count"] == 0


def test_p4_ay_graph_node_precedes_p4_au_delivery_and_utterance():
    payload = {"schema": p4_ay.SCHEMA, "status": p4_ay.AUTHORIZED_STATUS}
    token = p4_ay._TRACE.set(payload)
    result = {
        "logic": {},
        "runtime_trace": {
            "blackboard": [
                {"label": p4_au.LABEL},
                {"label": "current_task_source_bundle_m50"},
                {"label": "actionable_help_delivery_m45"},
                {"label": "utterance"},
            ]
        },
    }
    try:
        p4_ay.materialize_response_form_constraint_boundary_p4_ay(result)
        p4_ay.materialize_response_form_constraint_boundary_p4_ay(result)
    finally:
        p4_ay._TRACE.reset(token)

    labels = [row["label"] for row in result["runtime_trace"]["blackboard"]]
    assert labels.count(p4_ay.LABEL) == 1
    assert labels.index(p4_ay.LABEL) < labels.index(p4_au.LABEL)
    assert labels.index(p4_ay.LABEL) < labels.index("current_task_source_bundle_m50")
    assert labels.index(p4_ay.LABEL) < labels.index("actionable_help_delivery_m45")
    assert labels.index(p4_ay.LABEL) < labels.index("utterance")


def test_p4_ay_source_has_no_frozen_complete_case_lookup():
    source = (ROOT / "uruha_response_form_constraint_boundary_p4.py").read_text(encoding="utf-8")
    dataset = json.loads(DATASET.read_text(encoding="utf-8"))

    for row in dataset["fresh_positive_sequences"] + dataset["fresh_control_sequences"]:
        assert row["turn_1"] not in source
        assert row["turn_2"] not in source


def test_p4_ay_product_entry_and_launcher_are_additive_after_p4_ax():
    entry = (ROOT / "uruha_web_ui_product_p4_ay.py").read_text(encoding="utf-8")
    launcher = (ROOT / "p4_ay_safe_isolated_product_launcher.py").read_text(encoding="utf-8")

    assert "import uruha_web_ui_product_p4_ax as _p4_ax" in entry
    assert "install_response_form_constraint_boundary_p4_ay()" in entry
    assert 'ENTRYPOINT = ROOT / "uruha_web_ui_product_p4_ay.py"' in launcher
    assert "sandboxed_p4_ay_probe" in launcher
