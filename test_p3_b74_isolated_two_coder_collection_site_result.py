import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
RESULT = ROOT / "analysis" / "p3_b74_isolated_two_coder_collection_site_result_2026-09-20.json"


def test_saved_result_records_real_safari_roundtrip_and_ledger_isolation():
    result = json.loads(RESULT.read_text(encoding="utf-8"))
    assert result["status"] == "synthetic_collection_site_ready_safari_visible_human_reliability_not_started"
    assert result["safari_acceptance"]["status"] == "passed_synthetic_page_only"
    assert result["safari_acceptance"]["before_progress"] == "0/18"
    assert result["safari_acceptance"]["after_progress"] == "1/18"
    assert result["safari_acceptance"]["new_safari_tab_count"] == 1
    assert result["live_isolation_observation"]["ledger_entry_counts_after_safari_submission"] == [1, 0]
    assert result["live_isolation_observation"]["other_coder_entries_visible"] is False


def test_saved_result_does_not_convert_synthetic_calculation_to_human_evidence():
    result = json.loads(RESULT.read_text(encoding="utf-8"))
    analysis = result["complete_synthetic_analysis"]
    assert set(analysis["primary_nominal_krippendorff_alpha"].values()) == {1.0}
    assert analysis["calculation_gate_passed"] is True
    assert analysis["synthetic_fixture_authorizes_human_reliability"] is False
    assert analysis["real_source_prediction_authorized"] is False
    assert result["evidence_counts"]["real_source_content_count"] == 0
    assert result["evidence_counts"]["actual_human_research_label_count"] == 0
