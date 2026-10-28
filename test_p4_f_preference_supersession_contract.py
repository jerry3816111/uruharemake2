import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CONTRACT = ROOT / "configs" / "p4_f_explicit_preference_supersession_contract_v1.json"
GAP = ROOT / "analysis" / "p4_f_preference_supersession_prechange_gap_2026-09-20.json"


def test_contract_is_bounded_to_selected_memory_and_one_product_adapter():
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    assert contract["single_changed_variable"] == "bounded_explicit_preference_supersession_in_speaker_qualified_selected_memory"
    assert contract["allowed_files"] == [
        "uruha_speaker_qualified_fact_p3.py",
        "test_speaker_qualified_fact_p3.py",
        "test_p4_f_explicit_preference_supersession.py",
    ]
    boundary = contract["implementation_boundary"]
    assert boundary["general_memory_ranking_change_allowed"] is False
    assert boundary["chroma_or_database_rewrite_allowed"] is False
    assert boundary["general_planner_prompt_change_allowed"] is False
    assert boundary["existing_episodes_must_remain_immutable"] is True
    assert boundary["resolution_must_use_only_already_selected_memory"] is True


def test_prechange_gap_preserves_exact_counterexample_and_zero_effects():
    gap = json.loads(GAP.read_text(encoding="utf-8"))
    assert gap["status"] == "confirmed_current_adapter_cannot_apply_explicit_supersession"
    assert gap["observed"]["status"] == "ambiguous_multiple_user_preferences"
    assert gap["observed"]["candidate_count"] == 2
    assert gap["observed"]["candidate_memory_ids"] == ["correction", "old"]
    assert gap["observed"]["visible_surface"] == "候補が二つある。どっちの好みの話？"
    assert gap["observed"]["explicit_correction_applied"] is False
    assert set(gap["accounting"].values()) == {0}


def test_real_product_acceptance_is_zero_retry_and_answer_absent_after_restart():
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    acceptance = contract["post_commit_product_acceptance"]
    assert acceptance["real_product_turns_total"] == 3
    assert acceptance["actual_process_restart_count"] == 1
    assert acceptance["retry_count"] == 0
    assert acceptance["production_memory_access_count"] == 0
    assert acceptance["paid_api_call_count"] == 0
    assert contract["supported_correction_shape"]["expected_current_value_jp"] == "紅茶"


def test_gap_file_is_exactly_the_contract_bound_artifact():
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    assert ROOT / contract["prechange_gap"]["path"] == GAP
    assert json.loads(GAP.read_text(encoding="utf-8"))["status"] == contract["prechange_gap"]["required_status"]
    assert hashlib.sha256(GAP.read_bytes()).hexdigest()
