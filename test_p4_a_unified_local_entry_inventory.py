import tempfile
from pathlib import Path

import p4_a_unified_local_entry_inventory as p4a


def test_current_product_inventory_is_truthful_and_side_effect_free():
    report = p4a.build_inventory()
    assert p4a.validate_inventory(report) == []
    assert report["capabilities"]["chat"]["status"] == "integrated_in_product_entry"
    assert report["capabilities"]["truthful_runtime_graph"]["status"] == "integrated_same_turn_output"
    assert report["capabilities"]["vrm_3d"]["status"] == "absent_from_product_runtime"
    assert report["capabilities"]["function_calling"]["status"] == "research_policy_only_not_product_runtime"
    assert report["capabilities"]["vrm_3d"]["checks"]["tracked_3d_asset_count"] == 0
    assert report["capabilities"]["function_calling"]["checks"]["offline_action_policy_exists"] is True
    assert report["capabilities"]["function_calling"]["checks"]["product_action_policy_imported"] is False
    assert all(value == 0 for value in report["access_accounting"].values())


def test_inventory_does_not_call_an_asset_an_integration_without_renderer_and_executor():
    report = p4a.build_inventory(tracked=["models/avatar.vrm"], worktree_python_exists=True)
    vrm = report["capabilities"]["vrm_3d"]
    assert vrm["checks"]["tracked_3d_asset_count"] == 1
    assert vrm["status"] == "absent_from_product_runtime"


def test_validator_rejects_claim_that_missing_capabilities_are_integrated():
    report = p4a.build_inventory()
    report["capabilities"]["vrm_3d"]["status"] = "integrated"
    report["capabilities"]["function_calling"]["status"] = "integrated"
    errors = p4a.validate_inventory(report)
    assert "unexpected_vrm_integration" in errors
    assert "unexpected_function_calling_integration" in errors


def test_cli_writes_requested_inventory_only():
    with tempfile.TemporaryDirectory() as temporary:
        output = Path(temporary) / "inventory.json"
        assert p4a.main(["--output", str(output), "--require-valid"]) == 0
        assert output.is_file()
