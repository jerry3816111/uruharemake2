import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
FREEZE = ROOT / "research" / "p4_d_local_vrm_renderer_implementation_freeze_2026-09-20.json"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def test_freeze_binds_contract_manifest_and_inventory():
    freeze = json.loads(FREEZE.read_text(encoding="utf-8"))
    assert freeze["status"] == "frozen_before_package_install_or_renderer_implementation"
    for binding in freeze["bindings"].values():
        assert _sha256(ROOT / binding["path"]) == binding["sha256"]


def test_freeze_allows_one_dependency_install_but_no_character_asset():
    freeze = json.loads(FREEZE.read_text(encoding="utf-8"))
    access = freeze["authorized_external_access_after_this_freeze"]
    assert access["npm_registry_package_install_count"] == 1
    assert access["character_or_persona_asset_download_count"] == 0
    assert access["login_or_paid_api_count"] == 0
    fixture = freeze["fixture_boundary"]
    assert fixture["repository_character_asset"] is False
    assert fixture["claims_uruha_likeness"] is False


def test_freeze_requires_truthful_offline_renderer_without_action_connection():
    freeze = json.loads(FREEZE.read_text(encoding="utf-8"))
    contract = freeze["implementation_contract"]
    assert "no CDN" in contract["renderer_runtime"]
    assert "no Gradio upload" in contract["asset_transport"]
    assert contract["persona_asset"] == "none"
    assert contract["action_policy_connection"] == "none"
    assert freeze["resource_ceiling"]["model_call_count"] == 0
    assert freeze["resource_ceiling"]["physical_vrm_action_count"] == 0
