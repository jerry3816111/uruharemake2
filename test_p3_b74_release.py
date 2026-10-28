import json
from pathlib import Path

import p3_b74_isolated_two_coder_collection_site as b74


ROOT = Path(__file__).resolve().parent
RELEASE = ROOT / "research" / "p3_b74_isolated_two_coder_collection_site_release_2026-09-20.json"


def test_release_records_safari_pass_without_human_claim():
    release = json.loads(RELEASE.read_text(encoding="utf-8"))
    assert release["status"] == "released_synthetic_site_ready_safari_pass_human_reliability_not_started"
    assert release["result"]["safari_status"] == "passed_synthetic_page_only"
    assert release["result"]["safari_progress_before_after"] == ["0/18", "1/18"]
    assert release["result"]["ledger_entry_counts_after_safari_submission"] == [1, 0]
    assert release["result"]["synthetic_fixture_authorizes_human_reliability"] is False
    assert release["result"]["actual_human_research_label_count"] == 0


def test_release_bindings_match_and_b75_forbids_fixed_window_fallback():
    release = json.loads(RELEASE.read_text(encoding="utf-8"))
    for binding in release["bindings"].values():
        path = ROOT / binding["path"]
        assert path.is_file()
        assert b74.sha256_file(path) == binding["sha256"]
    assert release["next_stage"]["id"] == "P3-B75"
    assert release["next_stage"]["source_selection_must_precede_content_review"] is True
    assert release["next_stage"]["clear_stimulus_response_boundary_required"] is True
    assert release["next_stage"]["model_prediction_allowed"] is False
    assert release["next_stage"]["fixed_time_window_fallback_allowed"] is False
