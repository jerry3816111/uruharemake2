import json
from pathlib import Path

import p3_b72_cross_source_proxy_validity_audit as b72


ROOT = Path(__file__).resolve().parent
RELEASE = ROOT / "research" / "p3_b72_cross_source_proxy_validity_audit_release_2026-09-20.json"


def test_release_stops_source_expansion_and_preserves_conflict():
    release = json.loads(RELEASE.read_text(encoding="utf-8"))
    assert release["status"] == "released_proxy_not_adequate_source_expansion_stopped"
    assert release["result"]["row_wins"] == {"BASELINE_LITERAL": 2, "SYSTEM_PRAGMATIC_STATE": 6, "TIE": 0}
    assert release["result"]["top1_hits"] == {"BASELINE_LITERAL": 3, "SYSTEM_PRAGMATIC_STATE": 2}
    assert release["result"]["source_expansion_authorized"] is False
    assert release["result"]["source3_marker_hit_count"] == 0


def test_release_binding_hashes_match_and_next_stage_has_no_new_source_access():
    release = json.loads(RELEASE.read_text(encoding="utf-8"))
    for binding in release["bindings"].values():
        path = ROOT / binding["path"]
        assert path.is_file()
        assert b72.sha256_file(path) == binding["sha256"]
    assert release["next_stage"]["id"] == "P3-B73"
    assert release["next_stage"]["new_source_content_access_allowed"] is False
    assert release["next_stage"]["new_prediction_or_outcome_access_allowed"] is False
    assert release["next_stage"]["human_evidence_may_not_be_replaced_by_llm_or_codex"] is True
