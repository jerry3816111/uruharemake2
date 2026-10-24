import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
RESULT = ROOT / "analysis" / "p4_o_persisted_reference_time_result_2026-09-22.json"


def _load():
    return json.loads(RESULT.read_text(encoding="utf-8"))


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_result_binds_design_and_additive_implementation():
    result = _load()
    assert result["status"] == "pass_offline"
    for group in ("design_bindings", "implementation"):
        for binding in result[group].values():
            assert _sha256(ROOT / binding["path"]) == binding["sha256"]


def test_result_preserves_released_p4_n_hashes():
    result = _load()
    immutable = result["immutable_predecessors"]
    assert _sha256(ROOT / "uruha_source_bound_japanese_value_surface_p4.py") == immutable[
        "p4_n_adapter_sha256"
    ]
    assert _sha256(ROOT / "uruha_web_ui_product.py") == immutable[
        "released_product_entry_sha256"
    ]
    assert immutable["hashes_unchanged"] is True


def test_result_reports_executed_evidence_and_keeps_product_pending():
    verification = _load()["verification"]
    assert verification["p4_o_dedicated"]["passed"] == 6
    assert verification["p4_o_dedicated"]["failed"] == 0
    assert verification["affected_p4_i_through_p4_o"]["test_files"] == 45
    assert verification["affected_p4_i_through_p4_o"]["passed"] == 196
    assert verification["affected_p4_i_through_p4_o"]["failed"] == 0
    assert verification["isolated_product_entry_import"]["runtime_reused"] is True
    assert verification["before_to_after"]["product_turns"] == 0
    assert "not Safari/product delivery" in _load()["claim_boundary"]


def test_environment_collection_failures_are_not_misreported_as_test_failures_or_passes():
    attempts = _load()["environment_attempts_not_counted_as_test_results"]
    assert len(attempts) == 2
    assert all("collection stopped" in row["outcome"] for row in attempts)
