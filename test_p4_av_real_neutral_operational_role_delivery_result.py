import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
RESULT = ROOT / "analysis" / "p4_av_real_neutral_operational_role_delivery_evidence_2026-09-26.json"


def _load():
    return json.loads(RESULT.read_text(encoding="utf-8"))


def test_p4_av_real_result_preserves_the_turn_one_formal_failure_and_stop():
    evidence = _load()

    assert evidence["status"] == "fail"
    assert evidence["executed_turn_count"] == 1
    assert evidence["stopped_after_prerequisite_failure"] is True
    assert evidence["rerun_allowed"] is False
    assert evidence["execution"]["turn_2_was_not_sent"] is True
    assert evidence["metrics"]["turn_1_p4_as_executed_count"] == 0
    assert evidence["metrics"]["turn_1_exact_m44_receipt_count"] == 0
    assert evidence["metrics"]["turn_1_future_locked_count"] == 0


def test_p4_av_real_result_keeps_surface_success_separate_from_event_identity():
    turn = _load()["turns"][0]

    assert turn["selected_policy"] == "calibrate_need"
    assert turn["m39_status"] == "accepted_verified_surface"
    assert turn["m39_policy_act_match_after"] is True
    assert turn["p4_as_status"] == "not_applicable"
    assert turn["p4_as_failed_checks"] == [
        "early_authority_exact",
        "direct_user_first_person",
    ]
    assert turn["m44_receipt_status"] == "not_registered"
    assert turn["p4_ar_status"] == "blocked_unexecuted_shadow_action"


def test_p4_av_real_result_preserves_temporal_fail_closed_behavior():
    turn = _load()["turns"][0]

    assert turn["p4_ag_candidate_count"] == 6
    assert turn["p4_ag_binding_status"] == "pending"
    assert turn["temporal_present_candidate_count"] == 0
    assert turn["temporal_selected_policy"] is None
    assert turn["temporal_future_status"] == "not_available"
    assert turn["p4_av_status"] == "not_reached"
    assert turn["m53_status"] == "not_reached"


def test_p4_av_real_result_preserves_safari_graph_and_runtime_artifacts():
    evidence = _load()
    turn = evidence["turns"][0]

    assert [
        turn["p4_as_node_index"],
        turn["p4_ar_node_index"],
        turn["p4_ag_node_index"],
        turn["temporal_node_index"],
        turn["utterance_node_index"],
    ] == [64, 65, 66, 68, 69]
    assert turn["p4_as_failure_visually_observed_in_safari"] is True
    assert evidence["execution"]["closed_tab_count"] == 0
    assert evidence["raw_runtime_artifacts"]["conversation_jsonl_rows"] == 1
    assert evidence["raw_runtime_artifacts"]["conversation_jsonl_sha256"] == (
        "439b7e313e04b89f322b1846bb898426abde366a7d0a75248895810256755a89"
    )


def test_p4_av_real_failure_does_not_overclaim_the_unreached_capability():
    evidence = _load()

    assert "P4-AV was never reached" in evidence["analysis"]
    assert "Do not send Turn 2" in evidence["next_design_implication"]
