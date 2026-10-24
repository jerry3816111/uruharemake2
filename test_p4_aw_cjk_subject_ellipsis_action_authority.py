import json
from copy import deepcopy
from pathlib import Path

import p4_aw_cjk_subject_ellipsis_action_authority_gate as gate
import uruha_cjk_subject_ellipsis_action_authority_p4 as p4_aw


ROOT = Path(__file__).resolve().parent
DATASET = ROOT / "datasets" / "p4_aw_cjk_subject_ellipsis_action_authority_v1.json"
EVIDENCE = ROOT / "analysis" / "p4_aw_cjk_subject_ellipsis_action_authority_evidence_2026-09-26.json"


def test_p4_aw_offline_evidence_passes_the_prospectively_frozen_gate():
    evidence = p4_aw.build_dataset_evidence_p4_aw(DATASET)
    evaluated = gate.evaluate_offline_evidence(gate.load_contract(), evidence)

    assert evaluated["status"] == "pass", (evaluated, evidence["metrics"])
    assert evaluated["failed_gates"] == []


def test_p4_aw_saved_evidence_matches_the_frozen_generated_metrics():
    generated = p4_aw.build_dataset_evidence_p4_aw(DATASET)
    saved = json.loads(EVIDENCE.read_text(encoding="utf-8"))

    assert saved["status"] == "pass"
    assert saved["failed_gates"] == []
    assert saved["contract"]["dataset_sha256"] == generated["dataset_sha256"]
    assert saved["metrics"] == generated["metrics"]


def test_p4_aw_fresh_cjk_subjectless_cases_reach_the_existing_exact_chain():
    evidence = p4_aw.build_dataset_evidence_p4_aw(DATASET)
    rows = [row for row in evidence["cases"] if row["split"] == "fresh_positive"]

    assert len(rows) == 6
    for row in rows:
        assert row["provisional_status"] == p4_aw.PROVISIONAL_STATUS
        assert row["status"] == p4_aw.FINAL_STATUS
        assert row["typed_cognitive_overactivity"] is True
        assert row["p4_as_status"] == "executed_and_committed"
        assert row["p4_as_receipt_status"] == "registered_for_next_user_turn"
        assert row["p4_ar_authorized"] is True


def test_p4_aw_all_fresh_control_families_remain_fail_closed():
    evidence = p4_aw.build_dataset_evidence_p4_aw(DATASET)
    rows = [row for row in evidence["cases"] if row["split"] == "fresh_control"]

    assert len(rows) == 12
    assert {row["control_family"] for row in rows} == {
        "third_party",
        "quoted_metalinguistic",
        "news_or_report",
        "physical_object_motion",
        "resolved_state",
        "ambiguous_role",
    }
    for row in rows:
        assert row["status"] == "blocked"
        assert row["p4_as_status"] != "executed_and_committed"
        assert row["p4_ar_authorized"] is False


def test_p4_aw_explicit_first_person_predecessor_does_not_depend_on_ellipsis():
    evidence = p4_aw.build_dataset_evidence_p4_aw(DATASET)
    rows = [row for row in evidence["cases"] if row["split"] == "predecessor_control"]

    assert len(rows) == 2
    for row in rows:
        assert row["provisional_status"] == "predecessor_explicit_authority_preserved"
        assert row["status"] == "preserve_explicit_predecessor"
        assert row["p4_as_status"] == "executed_and_committed"


def test_p4_aw_provisional_candidate_cannot_authorize_with_one_missing_exact_gate():
    provisional = {
        "schema": p4_aw.SCHEMA,
        "status": p4_aw.PROVISIONAL_STATUS,
        "private_state_truth_claimed": False,
    }
    exact = {
        "direct_user_first_person": False,
        "early_authority_exact": True,
        "decision_applied": True,
        "policy_calibrate_need": True,
        "genuine_p1_identity": True,
        "turn_exact": True,
        "input_digest_exact": True,
        "plan_applied": False,
        "plan_identity_exact": True,
        "plan_policy_exact": True,
        "m39_verified": True,
        "m39_unprotected": True,
        "m39_policy_exact": True,
        "m39_policy_act_realized": True,
        "m39_no_unresolved_violation": True,
        "m39_reply_digest_exact": True,
        "m39_source_digest_exact": True,
        "pending_absent_or_exact": True,
        "no_third_party": True,
    }

    result = p4_aw.finalize_cjk_subject_ellipsis_authority_p4_aw(provisional, exact)

    assert result["status"] == "blocked_final_exact_chain"
    assert result["final_exact_chain_verified"] is False
    assert result["failed_final_checks"] == ["plan_applied"]


def test_p4_aw_changes_no_source_detector_guard_candidate_reply_model_or_memory_fields():
    metrics = p4_aw.build_dataset_evidence_p4_aw(DATASET)["metrics"]

    assert metrics["source_frame_mutation_count"] == 0
    assert metrics["trigger_detector_mutation_count"] == 0
    assert metrics["p1_or_p4_ar_guard_weakening_count"] == 0
    assert metrics["candidate_score_or_order_change_count"] == 0
    assert metrics["feedback_classifier_change_count"] == 0
    assert metrics["visible_reply_change_count"] == 0
    assert metrics["added_model_call_count"] == 0
    assert metrics["factual_memory_write_count"] == 0
    assert metrics["raw_dialogue_persisted_count"] == 0
    assert metrics["private_state_truth_claim_count"] == 0
    assert metrics["full_fresh_string_patch_count"] == 0


def test_p4_aw_materializes_one_raw_free_node_before_p4_as_and_utterance():
    payload = {
        "schema": p4_aw.SCHEMA,
        "status": p4_aw.FINAL_STATUS,
        "evidence_digest": "digest-only",
        "raw_dialogue_persisted": False,
    }
    result = {
        "logic": {
            "selected_action_surface_execution_p4": {
                p4_aw.LABEL: deepcopy(payload),
            }
        },
        "runtime_trace": {
            "blackboard": [
                {"label": "selected_action_surface_execution_p4"},
                {"label": "executed_action_identity_gate_p4"},
                {"label": "utterance"},
            ]
        },
    }

    p4_aw.append_cjk_subject_ellipsis_action_authority_node_p4_aw(result)
    p4_aw.append_cjk_subject_ellipsis_action_authority_node_p4_aw(result)
    labels = [row["label"] for row in result["runtime_trace"]["blackboard"]]

    assert labels.count(p4_aw.LABEL) == 1
    assert labels.index(p4_aw.LABEL) < labels.index("selected_action_surface_execution_p4")
    assert labels.index(p4_aw.LABEL) < labels.index("utterance")
    assert result["logic"][p4_aw.LABEL] == result["runtime_trace"][p4_aw.LABEL]


def test_p4_aw_source_contains_no_complete_fresh_case_patch():
    source = (ROOT / "uruha_cjk_subject_ellipsis_action_authority_p4.py").read_text(
        encoding="utf-8"
    )
    dataset = json.loads(DATASET.read_text(encoding="utf-8"))

    for row in dataset["cases"]:
        if row["split"] in {"fresh_positive", "fresh_control"}:
            assert row["input"] not in source


def test_p4_aw_product_entry_and_launcher_are_additive_after_p4_av():
    entry = (ROOT / "uruha_web_ui_product_p4_aw.py").read_text(encoding="utf-8")
    launcher = (ROOT / "p4_aw_safe_isolated_product_launcher.py").read_text(encoding="utf-8")

    assert "import uruha_web_ui_product_p4_av as _p4_av" in entry
    assert "install_cjk_subject_ellipsis_action_authority_p4_aw()" in entry
    assert 'ENTRYPOINT = ROOT / "uruha_web_ui_product_p4_aw.py"' in launcher
    assert "sandboxed_p4_aw_probe" in launcher
