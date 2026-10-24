import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
AMENDMENT = ROOT / "research" / "p4_o_additive_product_entry_amendment_2026-09-22.json"
REJECTED = ROOT / "analysis" / "p4_o_product_entry_mutation_rejected_2026-09-22.json"
P4_N = ROOT / "uruha_source_bound_japanese_value_surface_p4.py"
PRODUCT = ROOT / "uruha_web_ui_product.py"


def _load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_second_rejected_attempt_preserves_released_product_entry():
    rejected = _load(REJECTED)
    assert rejected["status"] == "second_implementation_attempt_rejected_before_commit"
    assert rejected["affected_suite"]["passed"] == 50
    assert rejected["affected_suite"]["failed"] == 1
    assert rejected["preservation"]["rejected_change_committed"] is False
    assert _sha256(PRODUCT) == rejected["preservation"]["product_entry_restored_sha256"]
    assert rejected["correction_budget"]["informed_correction_batches_used"] == 2


def test_final_amendment_requires_new_entry_and_immutable_released_files():
    amendment = _load(AMENDMENT)
    architecture = amendment["required_architecture"]
    assert amendment["status"] == "frozen_before_second_and_final_accepted_implementation_batch"
    assert amendment["allowed_implementation_files"] == [
        "uruha_persisted_reference_time_p4.py",
        "uruha_web_ui_product_p4_o.py",
    ]
    assert architecture["released_p4_n_adapter_mutation_allowed"] is False
    assert architecture["released_product_entry_mutation_allowed"] is False
    assert _sha256(P4_N) == "bd7389af47aa62b69571f1e9382c1d362c277a417bd2e5c265c4b302d6339ec8"
    assert _sha256(PRODUCT) == "842169743c3c8d8cc0d0c9e6d0747690b08add7e7aa8709b287f00f909e9e694"
    assert "REVIEW_REQUIRED" in amendment["terminal_policy"]
