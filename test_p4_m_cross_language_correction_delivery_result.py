import hashlib
import json
from pathlib import Path

import p4_m_cross_language_correction_delivery_gate as gate


ROOT = Path(__file__).resolve().parent
RESULT = ROOT / "analysis" / "p4_m_cross_language_correction_delivery_result_2026-09-22.json"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load():
    return json.loads(RESULT.read_text(encoding="utf-8"))


def test_result_is_bound_to_freeze_and_recomputes_terminal_fail():
    result = _load()
    binding = result["freeze_binding"]
    assert _sha256(ROOT / binding["path"]) == binding["sha256"]
    recomputed = gate.evaluate_evidence(gate.load_contract(), result)
    assert recomputed == result["gate_evaluation"]
    assert result["status"] == "fail"


def test_lineage_and_restart_passed_but_surface_authority_failed():
    result = _load()
    correction = result["session_1_correction_turn"]
    recall = result["session_2_recall_turn"]
    assert correction["active_current_ids"] == [correction["current_memory_id"]]
    assert correction["historical_current_ids"] == [correction["previous_current_memory_id"]]
    assert recall["p4_j_status"] == "unsupported_active_value_localization"
    assert recall["p4_j_answer_use_authorized"] is False
    assert recall["p4_j_reason"] == "active_value_not_in_bounded_japanese_localization"
    assert "柚子茶" not in recall["visible_output"]


def test_failure_was_not_memory_loss_or_old_value_selection():
    result = _load()
    state = result["persistent_state"]
    localization = result["failure_localization"]
    assert state["profile_record_count_before_recall"] == 3
    assert state["profile_record_count_after_recall"] == 3
    assert state["all_three_profile_record_hashes_unchanged"] is True
    assert localization["typed_lineage_survived_restart"] is True
    assert localization["memory_loss_detected"] is False
    assert localization["historical_value_selected_detected"] is False


def test_no_retry_and_claim_boundary_remains_bounded():
    result = _load()
    assert result["accounting"]["retry_count"] == 0
    assert result["failure_localization"]["same_case_retry_performed"] is False
    boundary = result["claim_boundary"]
    assert "terminal failure" in boundary
    assert "does not establish successful cross-language correction delivery" in boundary
    assert "human equation" in boundary
