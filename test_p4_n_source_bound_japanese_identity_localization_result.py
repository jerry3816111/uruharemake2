import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
RESULT = ROOT / "analysis" / "p4_n_source_bound_japanese_identity_localization_result_2026-09-22.json"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load():
    return json.loads(RESULT.read_text(encoding="utf-8"))


def test_result_binds_frozen_design_amendment_and_implementation():
    result = _load()
    assert result["status"] == "pass_offline"
    for group in ("design_bindings", "implementation"):
        for binding in result[group].values():
            if isinstance(binding, dict) and "path" in binding:
                assert _sha256(ROOT / binding["path"]) == binding["sha256"]


def test_result_preserves_p4_j_and_does_not_lookup_patch_exposed_value():
    implementation = _load()["implementation"]
    assert implementation["p4_j_bound_file_changed"] is False
    assert implementation["p4_j_bound_file_sha256_before_and_after"] == _sha256(
        ROOT / "uruha_typed_current_preference_recall_p4.py"
    )
    assert implementation["p4_m_exposed_value_added_to_finite_map"] is False


def test_result_has_positive_negative_and_affected_regression_evidence():
    verification = _load()["verification"]
    assert verification["positive_development_fixtures"] == {
        "passed": 3,
        "total": 3,
        "values": ["玄米茶", "ジャスミンティー", "レモン・ティー"],
    }
    assert verification["negative_source_script_length_and_injection_fixtures"]["passed"] == 7
    assert verification["missing_or_wrong_provenance_fixtures"]["passed"] == 4
    assert verification["exact_and_affected_regression"]["passed"] == 166
    assert verification["exact_and_affected_regression"]["failed"] == 0
    assert verification["isolated_product_preflight"]["status"] == "ready"
    assert verification["real_product_turns"] == 0


def test_result_claim_boundary_does_not_promote_offline_pass():
    result = _load()
    assert result["not_established"]["real_product_identity_surface_delivery"] is True
    assert result["not_established"]["strong_llm_advantage"] is True
    assert result["not_established"]["human_equation"] is True
    assert "not real product evidence" in result["claim_boundary"]
