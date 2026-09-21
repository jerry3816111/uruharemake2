import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
RELEASE = ROOT / "research" / "p4_k_cross_restart_surface_delivery_release_2026-09-21.json"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load():
    return json.loads(RELEASE.read_text(encoding="utf-8"))


def test_release_binds_frozen_result_and_acceptance():
    release = _load()
    assert release["status"] == "released_bounded_cross_restart_surface_delivery_pass"
    for binding in release["bindings"].values():
        assert _sha256(ROOT / binding["path"]) == binding["sha256"]


def test_release_records_delivery_pass_without_retry_or_profile_mutation():
    established = _load()["established"]
    assert established["frozen_gate_status"] == "pass"
    assert established["failed_gate_count"] == 0
    assert established["exact_japanese_final_surface"] is True
    assert established["p4_j_select_graph_node_visible_in_safari"] is True
    assert established["typed_profile_count_id_and_content_unchanged_by_recall"] is True
    assert established["same_case_rerun_performed"] is False
    assert established["retry_count"] == 0


def test_release_discloses_semantic_overlap_and_does_not_claim_generalization():
    release = _load()
    boundary = release["semantic_boundary"]
    assert boundary["historical_p4_f_black_tea_overlap_disclosed_before_execution"] is True
    assert boundary["unseen_semantic_generalization_established"] is False
    missing = release["not_established"]
    assert missing["open_domain_recall"] is True
    assert missing["arbitrary_multilingual_scope_equivalence"] is True
    assert missing["strong_llm_advantage"] is True
    assert missing["human_equation"] is True


def test_next_stage_is_one_scope_canonicalization_variable_without_real_turns():
    stage = _load()["next_stage"]
    assert stage["id"] == "P4-L"
    assert stage["single_changed_variable"] == (
        "canonical_scope_alias_projection_for_explicit_p4_i_current_preference_writes"
    )
    assert stage["real_product_turns_before_separate_new_acceptance_freeze_authorized"] == 0
    assert any("do not change preference value extraction" in item for item in stage["forbidden_change"])
    assert any("do not edit or rerun" in item for item in stage["forbidden_change"])
