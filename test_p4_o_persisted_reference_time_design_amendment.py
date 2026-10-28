import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
AMENDMENT = ROOT / "research" / "p4_o_persisted_reference_time_design_amendment_2026-09-22.json"
REJECTED = ROOT / "analysis" / "p4_o_direct_mutation_rejected_2026-09-22.json"
P4_N = ROOT / "uruha_source_bound_japanese_value_surface_p4.py"


def _load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_rejected_attempt_is_preserved_and_released_p4_n_is_restored():
    rejected = _load(REJECTED)
    assert rejected["status"] == "implementation_attempt_rejected_before_commit"
    assert rejected["affected_suite"] == {
        "passed": 55,
        "failed": 2,
        "failures": [
            "test_p4_o_persisted_reference_time_freeze.py::test_freeze_binds_old_adapter_and_terminal_p4_n_evidence",
            "test_p4_n_source_bound_japanese_identity_localization_result.py::test_result_binds_frozen_design_amendment_and_implementation",
        ],
    }
    assert rejected["preservation"]["rejected_change_committed"] is False
    assert _sha256(P4_N) == rejected["preservation"]["p4_n_adapter_restored_sha256"]


def test_amendment_only_changes_the_implementation_location():
    amendment = _load(AMENDMENT)
    assert amendment["status"] == "frozen_before_accepted_implementation"
    assert amendment["required_architecture"]["released_p4_n_mutation_allowed"] is False
    assert amendment["allowed_implementation_files"] == [
        "uruha_persisted_reference_time_p4.py",
        "uruha_web_ui_product.py",
    ]
    assert any("research question" in item for item in amendment["unchanged"])
    assert any("real product turn" in item for item in amendment["forbidden"])
