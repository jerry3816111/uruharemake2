import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent


def test_b69_source_and_windows_are_frozen_before_caption_access():
    contract = json.loads(
        (ROOT / "configs" / "p3_b69_source_level_replication_selection_v1.json").read_text()
    )
    assert contract["status"] == "source_and_windows_frozen_before_caption_metadata_or_content_access"
    assert contract["selected_source"]["video_id"] == "Mlk5e3hBnb8"
    assert contract["selected_source"]["channel_id"] == "UC5LyYg6cCA4yHEYvtUsir3g"
    assert contract["selected_source"]["duration_seconds"] >= 7200
    assert contract["selected_source"]["video_id"] != "4y5GiQpgJgo"
    assert contract["discovery"]["caption_metadata_or_content_observed_during_selection"] is False
    assert [row["row_id"] for row in contract["frozen_rows"]] == [
        "s2r0600", "s2r1200", "s2r1800", "s2r2400"
    ]
    assert contract["next_stage"]["caption_content_download_allowed"] is False
    assert contract["next_stage"]["source_or_window_substitution_on_unavailable_result_allowed"] is False
    assert all(contract["denied_actions"].values())
