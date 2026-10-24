import json
from pathlib import Path

import p3_b71a_source3_caption_availability as b71a


ROOT = Path(__file__).resolve().parent
RELEASE_PATH = ROOT / "research" / "p3_b71a_source3_caption_availability_release_2026-09-20.json"


def test_b71a_release_binds_available_track_and_b70_next_stage():
    release = json.loads(RELEASE_PATH.read_text(encoding="utf-8"))
    assert release["status"] == "released_source3_automatic_ja_json3_for_b70_bound_prediction"
    assert release["result"]["caption_content_download_count"] == 0
    assert release["result"]["future_content_access_count"] == 0
    assert release["next_stage"]["id"] == "P3-B71B"
    assert release["next_stage"]["bind_b70_adapter_before_execution"] is True
    assert release["next_stage"]["future_windows_remain_locked"] is True


def test_b71a_release_binding_hashes_match():
    release = json.loads(RELEASE_PATH.read_text(encoding="utf-8"))
    for binding in release["bindings"].values():
        path = ROOT / binding["path"]
        assert path.is_file()
        assert b71a.sha256_file(path) == binding["sha256"]
