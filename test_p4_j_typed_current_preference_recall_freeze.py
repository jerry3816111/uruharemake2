import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
CONTRACT = ROOT / "configs" / "p4_j_typed_current_preference_recall_contract_v1.json"
FREEZE = ROOT / "research" / "p4_j_typed_current_preference_recall_freeze_2026-09-21.json"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def test_p4_j_contract_freezes_one_read_only_exact_scope_variable():
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    assert contract["status"] == "prospectively_frozen_before_implementation"
    assert contract["single_changed_variable"] == (
        "bounded_active_typed_current_preference_read_authority_for_explicit_first_person_exact_scope_queries"
    )
    read = contract["read_contract"]
    assert read["allowed_partition"] == "active_only"
    assert read["exact_scope_match_required"] is True
    assert read["historical_answer_use_allowed"] is False
    assert read["explicit_negative_answer_use_allowed"] is False
    assert read["episode_answer_use_allowed"] is False
    assert read["profile_write_count"] == 0
    assert read["model_call_added"] is False


def test_p4_j_contract_binds_the_released_p4_i_result():
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    for binding in contract["p4_i_evidence_binding"].values():
        if isinstance(binding, dict):
            assert _sha256(ROOT / binding["path"]) == binding["sha256"]
    release = json.loads(
        (ROOT / contract["p4_i_evidence_binding"]["release"]["path"]).read_text(
            encoding="utf-8"
        )
    )
    assert release["status"] == contract["p4_i_evidence_binding"]["required_p4_i_status"]


def test_p4_j_freeze_forbids_real_execution_and_broad_answer_activation():
    freeze = json.loads(FREEZE.read_text(encoding="utf-8"))
    assert freeze["status"] == "frozen_before_p4_j_implementation"
    assert _sha256(ROOT / freeze["contract"]["path"]) == freeze["contract"]["sha256"]
    assert freeze["authorized_external_effects"]["real_product_turns"] == 0
    assert freeze["authorized_external_effects"]["new_product_process_starts"] == 0
    assert freeze["authorized_external_effects"]["model_calls"] == 0
    policy = freeze["failure_policy"]
    assert policy["historical_or_negative_value_as_current_answer_allowed"] is False
    assert policy["multiple_active_score_selection_allowed"] is False
    assert policy["general_profile_shadow_activation_allowed"] is False
    assert policy["p4_i_oolong_or_barley_case_rerun_allowed"] is False


def test_p4_j_allowed_files_are_narrow_and_do_not_edit_existing_memory_adapters():
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    assert contract["implementation_boundary"]["allowed_files"] == [
        "uruha_typed_current_preference_recall_p4.py",
        "uruha_web_ui_product.py",
        "test_p4_j_typed_current_preference_recall.py",
    ]
    assert contract["implementation_boundary"]["p4_i_writer_or_semantics_change_allowed"] is False
    assert contract["implementation_boundary"]["p4_f_episode_parser_localization_or_recall_change_allowed"] is False
