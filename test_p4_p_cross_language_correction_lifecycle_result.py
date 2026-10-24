import hashlib
import json
from pathlib import Path

import p4_p_cross_language_correction_lifecycle_gate as gate


ROOT = Path(__file__).resolve().parent
RESULT = ROOT / "analysis" / "p4_p_cross_language_correction_lifecycle_result_2026-09-22.json"


def _load():
    return json.loads(RESULT.read_text(encoding="utf-8"))


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_result_is_bound_to_freeze_and_recomputes_exact_failure():
    result = _load()
    binding = result["freeze_binding"]
    assert _sha256(ROOT / binding["path"]) == binding["sha256"]
    recomputed = gate.evaluate_evidence(gate.load_contract(), result)
    assert recomputed["status"] == "fail"
    assert recomputed["failed_gates"] == result["gate_evaluation"]["failed_gates"]
    assert result["status"] == "terminal_protocol_failure"


def test_lineage_and_hashes_survived_true_process_restart():
    result = _load()
    first = result["process_1"]
    second = result["process_2"]
    assert first["active_current_ids"] == [first["correction_memory_id"]]
    assert first["historical_current_ids"] == [first["write_memory_id"]]
    assert first["negative_correction_current_memory_id"] == first["correction_memory_id"]
    assert second["record_hashes_before"] == first["record_hashes_after"]
    assert second["record_hashes_after"] == first["record_hashes_after"]
    assert result["restart"]["old_pid"] != result["restart"]["new_pid"]


def test_failure_is_protocol_time_error_not_claimed_product_gap():
    localization = _load()["failure_localization"]
    assert localization["memory_loss_detected"] is False
    assert localization["cross_process_lineage_persisted"] is True
    assert localization["protocol_timestamp_error_detected"] is True
    assert localization["post_execution_clock_observation"] < localization[
        "frozen_write_valid_from"
    ]
    assert localization["product_gap_established"] is False
    assert localization["same_case_retry_performed"] is False


def test_next_stage_is_new_freeze_not_same_case_retry_or_product_patch():
    next_stage = _load()["next_stage"]
    assert next_stage["id"] == "P4-Q"
    assert next_stage["single_change"].startswith("protocol timestamps only")
    assert next_stage["requires_new_freeze"] is True
    assert next_stage["product_implementation_authorized"] is False
