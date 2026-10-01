import json
from pathlib import Path

import p3_b71_source3_selection as b71


ROOT = Path(__file__).resolve().parent
RELEASE_PATH = ROOT / "research" / "p3_b71_source3_selection_release_2026-09-20.json"


def test_b71_release_binds_source3_and_metadata_only_next_stage():
    release = json.loads(RELEASE_PATH.read_text(encoding="utf-8"))
    assert release["status"] == "released_source3_and_windows_frozen_before_caption_access"
    assert release["result"]["video_id"] == "j6Hlk9cY9LQ"
    assert release["result"]["caption_metadata_access_count"] == 0
    assert release["result"]["caption_content_access_count"] == 0
    assert release["next_stage"]["id"] == "P3-B71A"
    assert release["next_stage"]["caption_content_download_allowed"] is False
    assert release["next_stage"]["source_query_or_window_substitution_allowed"] is False


def test_b71_release_binding_hashes_match():
    release = json.loads(RELEASE_PATH.read_text(encoding="utf-8"))
    for binding in release["bindings"].values():
        path = ROOT / binding["path"]
        assert path.is_file()
        assert b71.sha256_file(path) == binding["sha256"]
