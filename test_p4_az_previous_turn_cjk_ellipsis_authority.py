import json
from pathlib import Path

import p4_az_previous_turn_cjk_ellipsis_authority_gate as gate
import uruha_previous_turn_cjk_ellipsis_authority_p4 as p4_az
import uruha_response_form_constraint_boundary_p4 as p4_ay
import uruha_source_bound_current_action_delivery_p4 as p4_au


ROOT = Path(__file__).resolve().parent
DATASET = ROOT / "datasets" / "p4_az_previous_turn_cjk_ellipsis_authority_v1.json"
EVIDENCE = ROOT / "analysis" / "p4_az_previous_turn_cjk_ellipsis_authority_evidence_2026-09-26.json"


def test_p4_az_offline_evidence_passes_the_frozen_gate():
    evidence = p4_az.build_dataset_evidence_p4_az(DATASET)
    evaluated = gate.evaluate_offline_evidence(gate.load_contract(), evidence)

    assert evaluated["status"] == "pass", (evaluated, evidence["metrics"])
    assert evaluated["failed_gates"] == []


def test_p4_az_saved_evidence_passes_the_same_frozen_gate():
    evidence = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    evaluated = gate.evaluate_offline_evidence(gate.load_contract(), evidence)

    assert evaluated["status"] == "pass", evaluated


def test_p4_az_fresh_positives_link_exact_source_without_rewriting_role():
    evidence = p4_az.build_dataset_evidence_p4_az(DATASET)
    positives = [row for row in evidence["cases"] if row["partition"] == "fresh_positive_sequences"]

    assert len(positives) == 6
    for row in positives:
        assert row["p4_az_status"] == p4_az.AUTHORIZED_STATUS
        assert row["p4_au_status_after"] == "prior_source_linked"
        assert row["prior_source_added"] is True
        assert row["exact_source_identity"] is True
        assert row["source_speaker_role_preserved"] == "unspecified"
        assert row["typed_cognitive_trigger"] is True
        assert row["downstream_action_contract_passed"] is True


def test_p4_az_controls_never_gain_previous_user_authority():
    evidence = p4_az.build_dataset_evidence_p4_az(DATASET)
    controls = [row for row in evidence["cases"] if row["partition"] == "fresh_control_sequences"]

    assert len(controls) == 12
    for row in controls:
        assert row["p4_az_status"] == "blocked_prior_source_authority"
        assert row["prior_source_added"] is False
        assert row["effective_prior_source_present"] is False


def test_p4_az_preserves_existing_p4_ay_positive_sources():
    evidence = p4_az.build_dataset_evidence_p4_az(DATASET)

    assert len(evidence["predecessor_cases"]) == 6
    for row in evidence["predecessor_cases"]:
        assert row["p4_az_status"] == "blocked_prior_source_authority"
        assert row["p4_au_status_after"] == "prior_source_linked"
        assert row["prior_source_added"] is False
        assert row["effective_prior_source_present"] is True


def test_p4_az_does_not_mutate_p4_ay_or_weaken_non_role_gates():
    evidence = p4_az.build_dataset_evidence_p4_az(DATASET)
    metrics = evidence["metrics"]

    assert metrics["p4_ay_task_boundary_mutation_count"] == 0
    assert metrics["p4_au_non_role_guard_bypass_count"] == 0
    assert metrics["candidate_score_or_order_change_count"] == 0
    assert metrics["added_model_call_count"] == 0
    assert metrics["factual_memory_write_count"] == 0
    assert metrics["assistant_source_count"] == 0
    assert metrics["private_inference_source_count"] == 0
    assert metrics["raw_dialogue_persisted_count"] == 0
    assert metrics["visible_reply_change_count"] == 0
    assert metrics["full_fresh_string_patch_count"] == 0


def test_p4_az_graph_node_follows_p4_ay_and_precedes_p4_au_delivery():
    payload = {"schema": p4_az.SCHEMA, "status": p4_az.AUTHORIZED_STATUS}
    token = p4_az._TRACE.set(payload)
    result = {
        "logic": {},
        "runtime_trace": {
            "blackboard": [
                {"label": p4_ay.LABEL},
                {"label": p4_au.LABEL},
                {"label": "current_task_source_bundle_m50"},
                {"label": "actionable_help_delivery_m45"},
                {"label": "utterance"},
            ]
        },
    }
    try:
        p4_az.materialize_previous_turn_cjk_ellipsis_authority_p4_az(result)
        p4_az.materialize_previous_turn_cjk_ellipsis_authority_p4_az(result)
    finally:
        p4_az._TRACE.reset(token)

    labels = [row["label"] for row in result["runtime_trace"]["blackboard"]]
    assert labels.count(p4_az.LABEL) == 1
    assert labels.index(p4_ay.LABEL) < labels.index(p4_az.LABEL)
    assert labels.index(p4_az.LABEL) < labels.index(p4_au.LABEL)
    assert labels.index(p4_az.LABEL) < labels.index("current_task_source_bundle_m50")
    assert labels.index(p4_az.LABEL) < labels.index("actionable_help_delivery_m45")
    assert labels.index(p4_az.LABEL) < labels.index("utterance")


def test_p4_az_source_has_no_frozen_complete_case_lookup():
    source = (ROOT / "uruha_previous_turn_cjk_ellipsis_authority_p4.py").read_text(encoding="utf-8")
    dataset = json.loads(DATASET.read_text(encoding="utf-8"))

    for row in dataset["fresh_positive_sequences"] + dataset["fresh_control_sequences"]:
        assert row["turn_1"] not in source
        assert row["turn_2"] not in source


def test_p4_az_product_entry_and_launcher_are_additive_after_p4_ay():
    entry = (ROOT / "uruha_web_ui_product_p4_az.py").read_text(encoding="utf-8")
    launcher = (ROOT / "p4_az_safe_isolated_product_launcher.py").read_text(encoding="utf-8")

    assert "import uruha_web_ui_product_p4_ay as _p4_ay" in entry
    assert "install_previous_turn_cjk_ellipsis_authority_p4_az()" in entry
    assert 'ENTRYPOINT = ROOT / "uruha_web_ui_product_p4_az.py"' in launcher
    assert "sandboxed_p4_az_probe" in launcher
