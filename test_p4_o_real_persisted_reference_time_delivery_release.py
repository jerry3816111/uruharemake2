import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
RELEASE = ROOT / "research" / "p4_o_real_persisted_reference_time_delivery_release_2026-09-22.json"


def _load():
    return json.loads(RELEASE.read_text(encoding="utf-8"))


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_release_binds_pass_result_evidence_acceptance_and_test():
    release = _load()
    assert release["status"] == "released_pass"
    for binding in release["result_checkpoint"].values():
        if isinstance(binding, dict):
            assert _sha256(ROOT / binding["path"]) == binding["sha256"]


def test_release_records_real_no_retry_delivery_not_broad_memory():
    evidence = _load()["released_evidence"]
    assert evidence["frozen_gate_status"] == "pass"
    assert evidence["failed_gate_count"] == 0
    assert evidence["safari_product_turns"] == 2
    assert evidence["successful_product_turns"] == 2
    assert evidence["retry_count"] == 0
    assert evidence["profile_record_unchanged"] is True
    boundary = _load()["claim_boundary"]
    assert "not arbitrary memory" in boundary
    assert "human equation" in boundary


def test_next_stage_is_correction_lifecycle_not_same_case_expansion():
    next_stage = _load()["next_stage"]
    assert next_stage["id"] == "P4-P"
    assert next_stage["capability"] == "cross-language correction lifecycle with restart delivery"
    assert next_stage["single_variable_policy"].startswith("first diagnose")
    assert any("do not reuse" in item for item in next_stage["forbidden"])
    assert any("historical records" in item for item in next_stage["forbidden"])
