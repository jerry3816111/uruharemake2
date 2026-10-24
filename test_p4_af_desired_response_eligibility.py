from pathlib import Path

import p4_af_desired_response_eligibility_gate as gate
import uruha_desired_response_ambiguity_p4 as ambiguity
import uruha_desired_response_eligibility_p4 as eligibility


ROOT = Path(__file__).resolve().parent
DATASET = ROOT / "datasets" / "p4_af_desired_response_eligibility_v1.json"


def _traces(text, turn_index=1):
    state, decision, mode = ambiguity._isolated_inputs(text, turn_index)
    base = eligibility._ORIGINAL_LEDGER(state, decision, mode)
    guarded = eligibility.build_desired_response_eligibility_guard_p4(state, decision, mode)
    return base, guarded


def test_p4_ae_false_positive_is_suppressed_by_authority_not_phrase_patch():
    base, guarded = _traces("風扇一直轉，但我已經把報告寫完了。")
    assert base["status"] == "ambiguity_preserved"
    assert base["candidate_count"] == 6
    assert guarded["status"] == "not_applicable"
    assert guarded["candidate_count"] == 0
    assert guarded["eligibility"]["authority"] == "none_topic_only"
    assert guarded["eligibility"]["task_pressure_atom_present"] is True
    assert guarded["eligibility"]["topic_only_authorized"] is False
    assert guarded["suppressed_predecessor_candidate_count"] == 6


def test_cognitive_trigger_and_explicit_response_form_are_distinct_authorities():
    _, cognitive = _traces("我從早上就一直坐不住，腦子停不下來。", 2)
    _, explicit = _traces("我真的想知道怎麼把這份報告寫完，先給我一個方法。", 3)
    assert cognitive["eligibility"]["authority"] == "typed_cognitive_overactivity"
    assert cognitive["selected_action"]["mode"] == "low_pressure_clarification"
    assert explicit["eligibility"]["authority"] == "current_explicit_response_form"
    assert explicit["selected_action"]["mode"] == "practical_help"
    assert cognitive["candidate_ranking_unchanged"] is True
    assert explicit["candidate_ranking_unchanged"] is True


def test_guard_never_changes_visible_reply_model_or_memory():
    state, decision, mode = ambiguity._isolated_inputs(
        "風扇一直轉，但我已經把報告寫完了。",
        4,
    )
    visible, trace = eligibility.shadow_visible_reply_p4(
        "この返事は変えない。",
        state,
        decision,
        mode,
    )
    assert visible == "この返事は変えない。"
    assert trace["visible_reply_changed"] is False
    assert trace["model_call_added"] is False
    assert trace["fact_write_count"] == 0
    assert trace["profile_write_count"] == 0
    assert trace["episode_write_count"] == 0


def test_frozen_development_and_fresh_cases_pass_without_candidate_rerank():
    evidence = eligibility.build_dataset_evidence_p4_af(DATASET)
    result = gate.evaluate_evidence(gate.load_contract(), evidence)
    assert result["status"] == "pass", result["failed_gates"]
    assert result["failed_gates"] == []
