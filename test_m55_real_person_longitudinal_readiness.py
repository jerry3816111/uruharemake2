from copy import deepcopy
import json

import audit_m55_real_person_longitudinal_readiness as m55
import uruha_human_response_equation_m54 as m54


def test_current_precontent_contract_is_ready_but_human_pilot_is_not_complete():
    report = m55.build_readiness_m55()
    assert report["precontent_ready"] is True
    assert report["m55_pilot_complete"] is False
    assert report["m56_authorized"] is False
    assert report["decision"] == "do_not_run_m56"
    assert report["blocking_gate"] == "complete_two_independent_v7_18_slot_ledgers"


def test_target_frame_has_three_dated_sources_thirty_slots_and_no_sealed_future():
    report = m55.build_readiness_m55()
    assert report["counts"]["target_source_count"] == 3
    assert report["counts"]["target_sampling_slot_count"] == 30
    assert report["counts"]["sealed_future_source_count_in_frame"] == 0
    assert report["gates"]["target_source_publication_dates_available"] is True
    assert report["gates"]["sealed_future_excluded"] is True


def test_local_ledgers_are_counted_without_copying_private_entries():
    report = m55.build_readiness_m55()
    assert report["counts"]["v7_completed_slots_by_ledger"] == [0, 0]
    assert report["counts"]["v7_completed_ledgers"] == 0
    assert report["privacy"]["private_ledger_contents_in_report"] is False
    serialized = json.dumps(report, ensure_ascii=False)
    assert "observable_context_paraphrase" not in serialized
    assert "observable_behavior_paraphrase" not in serialized


def test_missing_reliability_is_never_replaced_by_synthetic_or_model_labels():
    report = m55.build_readiness_m55()
    assert report["reliability"] == {"available": False, "passed": False, "decision": "not_available"}
    assert report["privacy"]["synthetic_tests_count_as_reliability"] is False
    assert report["privacy"]["model_generated_labels_count_as_human"] is False


def test_invalid_equation_contract_blocks_precontent_readiness():
    contract = m54.load_contract()
    contract["variables"][3]["persistence"] = "factual_memory"
    report = m55.build_readiness_m55(contract=contract)
    assert report["gates"]["equation_contract_valid"] is False
    assert report["precontent_ready"] is False
    assert report["blocking_gate"] == "repair_precontent_contract"


def test_empty_frozen_artifact_bindings_fail_closed():
    v7_result = m55.load_json(m55.V7_RESULT)
    v7_result["frozen_artifacts"] = {}
    report = m55.build_readiness_m55(v7_result=v7_result)
    assert report["gates"]["v7_construction_frozen_and_bound"] is False
    assert report["precontent_ready"] is False


def test_target_counts_cannot_be_promoted_by_changing_only_local_progress(tmp_path):
    fake_ledgers = []
    for coder in ("a", "b"):
        path = tmp_path / f"{coder}.json"
        path.write_text(json.dumps({"entries": {str(i): {} for i in range(18)}}), encoding="utf-8")
        fake_ledgers.append(path)
    report = m55.build_readiness_m55(ledger_paths=fake_ledgers)
    assert report["gates"]["two_independent_v7_ledgers_complete"] is True
    assert report["gates"]["v7_reliability_passed"] is False
    assert report["m55_pilot_complete"] is False
    assert report["blocking_gate"] == "compute_and_pass_frozen_v7_reliability"


def test_graphical_gate_is_outsider_readable_and_does_not_expose_tokens_or_urls():
    report = m55.build_readiness_m55()
    html = m55.render_readiness_m55(report)
    for phrase in ("M54 方程式契約", "V7 分類可靠度", "V9 Uruha 校準", "M55 真實縱向 pilot", "M56 公平模型比較", "0/2 位真人完成", "0/30 事件雙人編碼"):
        assert phrase in html
    assert "token=" not in html
    assert "youtube.com" not in html
