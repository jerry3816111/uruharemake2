import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
RELEASE = ROOT / "research" / "p4_d_local_vrm_renderer_release_2026-09-20.json"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def test_release_binds_contract_freezes_result_and_acceptance():
    release = json.loads(RELEASE.read_text(encoding="utf-8"))
    assert release["status"] == "released_truthful_browser_local_vrm_renderer"
    for binding in release["bindings"].values():
        assert _sha256(ROOT / binding["path"]) == binding["sha256"]


def test_release_preserves_passed_missing_negative_and_next_scope():
    release = json.loads(RELEASE.read_text(encoding="utf-8"))
    passed = release["passed_scope"]
    assert passed["valid_vrm_actual_safari_render"] is True
    assert passed["invalid_vrm_actual_safari_fail_closed"] is True
    assert passed["server_upload_count"] == 0
    assert passed["p4_d_added_model_or_tool_calls"] == 0
    assert release["preserved_negative_evidence"]["raw_http_literal_proxy_passed"] is False
    assert release["not_passed_or_not_present"]["uruha_character_asset"] == "not_present"
    assert release["not_passed_or_not_present"]["tool_controlled_avatar_action"] == "not_present"
    assert release["next_stage"]["id"] == "P4-E"
    assert release["next_stage"]["production_memory_access_authorized"] is False
    assert release["next_stage"]["prompt_or_memory_retuning_after_result_authorized"] is False
