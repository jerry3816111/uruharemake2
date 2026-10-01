import json
from pathlib import Path

import p4_ad_desired_response_ambiguity_gate as gate
import uruha_desired_response_ambiguity_p4 as ambiguity


ROOT = Path(__file__).resolve().parent
DATASET = ROOT / "datasets" / "p4_ad_desired_response_ambiguity_holdout_v1.json"
EVIDENCE = ROOT / "analysis" / "p4_ad_desired_response_ambiguity_evidence_2026-09-23.json"
RESULT = ROOT / "analysis" / "p4_ad_desired_response_ambiguity_result_2026-09-23.json"
INITIAL_FAILURE = ROOT / "analysis" / "p4_ad_initial_implementation_failure_2026-09-23.json"


def _load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_saved_evidence_matches_fresh_deterministic_evidence_and_frozen_pass():
    saved = _load(EVIDENCE)
    fresh = ambiguity.build_dataset_evidence_p4_ad(DATASET)
    assert {key: saved[key] for key in fresh} == fresh
    result = _load(RESULT)
    assert gate.evaluate_evidence(gate.load_contract(), saved) == result
    assert result["status"] == "pass"
    assert result["failed_gates"] == []


def test_initial_failure_is_preserved_and_only_one_informed_correction_was_used():
    failure = _load(INITIAL_FAILURE)
    evidence = _load(EVIDENCE)
    assert failure["status"] == "fail"
    assert failure["metrics"]["holdout_exact_status_count"] == 5
    assert failure["metrics"]["holdout_required_candidate_modes_complete_count"] == 5
    assert evidence["metrics"]["holdout_exact_status_count"] == 9
    assert evidence["metrics"]["holdout_required_candidate_modes_complete_count"] == 9
    assert evidence["correction_history"]["informed_correction_batches_used"] == 1
    assert evidence["correction_history"]["new_lexical_rules_added"] == 0
    assert evidence["correction_history"]["frozen_case_or_gate_changes"] == 0
    assert evidence["scientific_evidence_status"]["post_correction_nine_case_suite_status"] == (
        "exposed_development_regression_not_independent_holdout"
    )
    assert evidence["scientific_evidence_status"]["fresh_post_correction_holdout_required"] is True


def test_pass_does_not_mutate_reply_or_claim_private_truth_or_write_memory():
    evidence = _load(EVIDENCE)
    assert evidence["metrics"]["visible_reply_changed_count"] == 0
    assert evidence["metrics"]["selected_action_private_truth_commitment_count"] == 0
    assert evidence["metrics"]["raw_input_trace_count"] == 0
    assert evidence["metrics"]["new_model_call_count"] == 0
    assert evidence["metrics"]["fact_write_count"] == 0
    assert evidence["metrics"]["profile_write_count"] == 0
    assert evidence["metrics"]["episode_write_count"] == 0
