import json
from pathlib import Path

import p3_b73_prospective_response_target_protocol as b73


ROOT = Path(__file__).resolve().parent
RELEASE = ROOT / "research" / "p3_b73_prospective_response_target_protocol_release_2026-09-20.json"


def test_release_keeps_human_reliability_unstarted_and_zero_evidence_access():
    release = json.loads(RELEASE.read_text(encoding="utf-8"))
    assert release["status"] == "released_protocol_tooling_ready_human_reliability_not_started"
    assert release["result"]["required_distinct_human_coders"] == 2
    assert release["result"]["required_episode_count_each"] == 18
    assert release["result"]["human_label_count"] == 0
    assert release["result"]["human_reliability_status"] == "not_started"
    assert release["result"]["new_source_content_access_count"] == 0


def test_release_binding_hashes_match_and_b74_remains_synthetic_only():
    release = json.loads(RELEASE.read_text(encoding="utf-8"))
    for binding in release["bindings"].values():
        path = ROOT / binding["path"]
        assert path.is_file()
        assert b73.sha256_file(path) == binding["sha256"]
    assert release["next_stage"]["id"] == "P3-B74"
    assert release["next_stage"]["synthetic_packets_only_until_real_manifest_preregistered"] is True
    assert release["next_stage"]["new_source_content_access_allowed"] is False
    assert release["next_stage"]["human_reliability_claim_allowed"] is False
