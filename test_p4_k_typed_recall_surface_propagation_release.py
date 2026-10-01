import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
RELEASE = ROOT / "research" / "p4_k_typed_recall_surface_propagation_release_2026-09-21.json"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load():
    return json.loads(RELEASE.read_text(encoding="utf-8"))


def test_release_binds_contract_freeze_implementation_and_regression():
    release = _load()
    assert release["status"] == (
        "offline_propagation_fix_ready_for_separate_product_acceptance_freeze"
    )
    for binding in release["bindings"].values():
        assert _sha256(ROOT / binding["path"]) == binding["sha256"]


def test_release_is_one_propagation_fix_with_safety_and_delegation_preserved():
    scope = _load()["implemented_scope"]
    assert scope["current_turn_memory_data_recovery_when_normalized_logic_omits_contract"] is True
    assert scope["recovered_contract_copied_into_final_logic"] is True
    assert scope["exact_selected_core_applied_after_existing_language_guard"] is True
    assert scope["select_stage_graph_materialization_enabled"] is True
    assert scope["safety_sensitive_route_override"] is False
    assert scope["nonselected_or_invalid_contract_surface_change"] is False
    assert scope["query_classifier_storage_resolver_localization_change"] is False


def test_release_preserves_real_failure_and_requires_new_freeze():
    release = _load()
    assert release["preserved_failure"]["p4_j_frozen_real_result_status"] == "fail"
    assert release["preserved_failure"]["p4_j_same_case_rerun"] is False
    assert release["verification"]["real_product_turns"] == 0
    assert release["verification"]["model_calls"] == 0
    assert release["next_stage"]["id"] == "P4-K-REAL"
    assert release["next_stage"]["real_product_turns_before_freeze"] == 0
