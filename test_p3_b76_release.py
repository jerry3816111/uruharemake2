import json
from pathlib import Path

import p3_b76_official_channel_inventory_selection as b76


ROOT = Path(__file__).resolve().parent
RELEASE = ROOT / "research" / "p3_b76_official_channel_inventory_release_2026-09-20.json"


def test_release_closes_automatic_discovery_without_erasing_protocol():
    release = json.loads(RELEASE.read_text(encoding="utf-8"))
    assert release["status"] == "released_insufficient_inventory_sources_discovery_branch_closed"
    assert release["result"]["eligible_source_count_found"] == 0
    assert release["result"]["content_media_model_or_outcome_access_count"] == 0
    assert release["branch_decision"]["observational_source_discovery_status"] == "review_required_closed_to_automatic_retry"
    assert release["branch_decision"]["additional_keyword_limit_tab_or_manual_retry_allowed"] is False
    assert release["branch_decision"]["b73_protocol_and_b74_site_preserved"] is True


def test_release_bindings_match_and_next_lane_stays_separate():
    release = json.loads(RELEASE.read_text(encoding="utf-8"))
    for binding in release["bindings"].values():
        path = ROOT / binding["path"]
        assert path.is_file()
        assert b76.sha256_file(path) == binding["sha256"]
    assert release["next_stage"]["id"] == "P3-C1"
    assert release["next_stage"]["new_uruha_future_access_allowed"] is False
    assert release["next_stage"]["may_not_replace_observational_reference_person_prediction"] is True
    assert release["next_stage"]["model_execution_allowed_before_contract_data_and_freeze"] is False
