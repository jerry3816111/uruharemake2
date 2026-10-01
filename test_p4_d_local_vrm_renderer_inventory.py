import json
from pathlib import Path

import p4_d_local_vrm_renderer_inventory as inventory


ROOT = Path(__file__).resolve().parent
CONTRACT = ROOT / "configs" / "p4_d_local_vrm_renderer_contract_v1.json"


def test_contract_pins_offline_renderer_and_user_asset_boundary():
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    assert contract["pinned_dependencies"]["@pixiv/three-vrm"]["version"] == "3.5.5"
    assert contract["pinned_dependencies"]["three"]["version"] == "0.180.0"
    assert contract["asset_boundary"]["bundled_character_or_persona_asset_allowed"] is False
    assert contract["asset_boundary"]["server_upload_allowed"] is False
    assert contract["renderer_surface"]["external_runtime_network_allowed"] is False
    assert contract["forbidden_connections"]["vrm_action_policy_import"] is True
    assert contract["forbidden_connections"]["physical_or_state_changing_execution"] is True


def test_inventory_finds_no_existing_assets_or_renderer():
    report = inventory.build_inventory()
    assert inventory.validate_inventory(report) == []
    assert report["roots"]["safe_worktree"]["asset_count"] == 0
    assert report["roots"]["original_checkout_read_only"]["asset_count"] == 0
    assert report["roots"]["original_checkout_read_only"]["package_manifest_count"] == 0
    assert report["research_policy_is_renderer"] is False


def test_validator_rejects_asset_drift():
    report = inventory.build_inventory()
    report["roots"]["safe_worktree"]["asset_count"] = 1
    assert "unexpected_local_asset:safe_worktree" in inventory.validate_inventory(report)
