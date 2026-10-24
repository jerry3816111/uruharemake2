import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
AMENDMENT = ROOT / "research" / "p4_n_source_bound_japanese_identity_localization_design_amendment_2026-09-22.json"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def test_amendment_binds_original_freeze_and_discovered_release_conflict():
    amendment = json.loads(AMENDMENT.read_text(encoding="utf-8"))
    assert amendment["status"] == "amended_before_implementation"
    assert _sha256(ROOT / amendment["original_freeze"]["path"]) == amendment["original_freeze"]["sha256"]
    discovered = amendment["discovered_immutable_binding"]
    for key in ("release", "bound_implementation"):
        assert _sha256(ROOT / discovered[key]["path"]) == discovered[key]["sha256"]
    assert discovered["observed_failure_count"] == 1


def test_amendment_preserves_variable_but_moves_implementation_to_adapter():
    amendment = json.loads(AMENDMENT.read_text(encoding="utf-8"))
    decision = amendment["decision"]
    assert decision["single_changed_variable_unchanged"] == (
        "source_provenance_bounded_japanese_identity_localization"
    )
    assert decision["original_allowed_product_file_now_forbidden"] == (
        "uruha_typed_current_preference_recall_p4.py"
    )
    assert decision["allowed_product_files"] == [
        "uruha_source_bound_japanese_value_surface_p4.py",
        "uruha_web_ui_product.py",
    ]
    assert "after install_typed_current_preference_recall_p4" in decision["adapter_order"]


def test_amendment_precedes_product_change_and_real_execution():
    state = json.loads(AMENDMENT.read_text(encoding="utf-8"))["implementation_state_at_amendment"]
    assert state["product_change_committed_after_original_freeze"] is False
    assert state["p4_j_file_restored_to_bound_sha256"] is True
    assert state["real_product_turn_count"] == 0
    assert state["model_call_count"] == 0
