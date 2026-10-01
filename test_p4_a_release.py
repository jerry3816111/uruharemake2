import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
RELEASE = ROOT / "research" / "p4_a_unified_local_entry_inventory_release_2026-09-20.json"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def test_release_binds_exact_inventory_artifacts():
    release = json.loads(RELEASE.read_text(encoding="utf-8"))
    assert release["status"] == "released_inventory_complete_two_integrated_two_missing"
    for binding in release["bindings"].values():
        path = ROOT / binding["path"]
        assert path.is_file()
        assert _sha256(path) == binding["sha256"]


def test_release_preserves_missing_capabilities_and_evidence_layers():
    release = json.loads(RELEASE.read_text(encoding="utf-8"))
    disposition = release["capability_disposition"]
    assert disposition["chat"] == "integrated_in_product_entry"
    assert disposition["truthful_runtime_graph"] == "integrated_same_turn_output"
    assert disposition["vrm_3d"] == "absent_from_product_runtime"
    assert disposition["function_calling"] == "research_policy_only_not_product_runtime"
    assert release["verification"]["runtime_launch_count"] == 0
    assert release["verification"]["safari_operation_count"] == 0
    assert release["verification"]["tool_execution_count"] == 0
    assert release["verification"]["physical_vrm_action_count"] == 0
    assert release["next_stage"]["id"] == "P4-B"
    assert release["next_stage"]["function_calling_or_vrm_integration_authorized"] is False
