import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
CONTRACT = ROOT / "configs" / "p4_k_typed_recall_surface_propagation_contract_v1.json"
FREEZE = ROOT / "research" / "p4_k_typed_recall_surface_propagation_freeze_2026-09-21.json"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_p4_k_contract_binds_the_terminal_p4_j_failure():
    contract = _load(CONTRACT)
    assert contract["status"] == "prospectively_frozen_before_implementation"
    for key in ("result", "release"):
        binding = contract["p4_j_failure_binding"][key]
        assert _sha256(ROOT / binding["path"]) == binding["sha256"]
    result = _load(ROOT / contract["p4_j_failure_binding"]["result"]["path"])
    assert result["status"] == contract["p4_j_failure_binding"]["required_result_status"]
    assert result["process_2_turn"]["surface_failure_kind"] == (
        contract["p4_j_failure_binding"]["required_failure_kind"]
    )


def test_p4_k_freeze_binds_contract_red_regression_and_before_implementation():
    freeze = _load(FREEZE)
    assert freeze["status"] == "frozen_before_p4_k_implementation"
    for key in ("contract", "regression_specification", "before_implementation"):
        binding = freeze[key]
        assert _sha256(ROOT / binding["path"]) == binding["sha256"]
    assert freeze["regression_specification"]["before_result"] == "2_failed_3_passed"


def test_p4_k_is_one_surface_propagation_change_with_zero_real_execution():
    contract = _load(CONTRACT)
    assert contract["single_changed_variable"] == (
        "recover_the_already_selected_p4_j_contract_from_current_turn_memory_data_at_the_final_visible_guard_seam"
    )
    assert contract["implementation_boundary"]["allowed_files"] == [
        "uruha_typed_current_preference_recall_p4.py",
        "test_p4_k_typed_recall_surface_propagation.py",
    ]
    freeze = _load(FREEZE)
    assert freeze["authorized_external_effects"]["real_product_turns"] == 0
    assert freeze["authorized_external_effects"]["new_product_process_starts"] == 0
    assert freeze["authorized_external_effects"]["model_calls"] == 0


def test_p4_k_does_not_change_query_storage_safety_or_old_case():
    contract = _load(CONTRACT)
    delegation = contract["delegation_contract"]
    assert delegation["query_classifier_scope_or_localization_change_allowed"] is False
    assert delegation["p4_i_typed_writer_or_validity_change_allowed"] is False
    assert delegation["p4_f_episode_recall_change_allowed"] is False
    assert contract["surface_contract"]["safety_sensitive_route_override_allowed"] is False
    assert "p4_j_rooibos" in contract["forbidden_case_reuse"]
