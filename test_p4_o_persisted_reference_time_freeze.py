import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
CONTRACT = ROOT / "configs" / "p4_o_persisted_reference_time_contract_v1.json"
BEFORE = ROOT / "analysis" / "p4_o_persisted_reference_time_before_2026-09-22.json"
FREEZE = ROOT / "research" / "p4_o_persisted_reference_time_freeze_2026-09-22.json"


def _load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path):
    digest = hashlib.sha256()
    digest.update(path.read_bytes())
    return digest.hexdigest()


def test_contract_freezes_one_new_offline_case_and_one_changed_variable():
    contract = _load(CONTRACT)
    case = contract["development_case"]
    assert contract["single_changed_variable"] == (
        "default reference_time exactly once at the P4-N adapter boundary and pass that same non-null value to both reads"
    )
    assert case["value"] == "ごぼう茶"
    assert case["future_product_case_allowed"] is False
    assert "ごぼう茶" in case["expected_surface"]
    assert contract["resource_limits"]["model_calls"] == 0
    assert contract["resource_limits"]["product_turns"] == 0


def test_before_evidence_is_a_real_persisted_chroma_exception_not_a_missing_record():
    before = _load(BEFORE)
    contract = _load(CONTRACT)
    assert before["status"] == "reproduced_terminal_exception_before_implementation"
    assert before["execution"]["storage"].startswith("chromadb.PersistentClient")
    assert before["case"]["write_status"] == "typed_current_preference_written"
    assert before["case"]["persistent_record_count"] == 1
    assert hashlib.sha256(
        contract["development_case"]["write_input"].encode("utf-8")
    ).hexdigest() == before["case"]["write_input_sha256"]
    assert before["observed_failure"] == {
        "exception_type": "ValueError",
        "exception_message": "reference_time must be an ISO datetime or datetime instance",
        "failed_layer": "P4-N additive persisted-record validity re-read",
        "surface_returned": False,
    }


def test_freeze_binds_old_adapter_and_terminal_p4_n_evidence():
    freeze = _load(FREEZE)
    assert freeze["status"] == "frozen_before_implementation"
    assert _sha256(ROOT / freeze["bindings"]["adapter_before"]) == freeze["hashes"][
        "adapter_before_sha256"
    ]
    assert _sha256(ROOT / "analysis/p4_n_real_source_bound_japanese_delivery_result_2026-09-22.json") == freeze[
        "hashes"
    ]["p4_n_real_result_sha256"]
    assert _sha256(ROOT / "research/p4_n_real_source_bound_japanese_delivery_release_2026-09-22.json") == freeze[
        "hashes"
    ]["p4_n_real_release_sha256"]
    assert freeze["authorization"]["real_product_execution_before_offline_release"] is False
    assert any("そば茶" in item for item in freeze["forbidden"])
