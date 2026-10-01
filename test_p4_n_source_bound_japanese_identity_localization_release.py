import hashlib
import json
from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parent
RELEASE = ROOT / "research" / "p4_n_source_bound_japanese_identity_localization_release_2026-09-22.json"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _sha256_at_commit(commit: str, path: str) -> str:
    payload = subprocess.check_output(["git", "show", f"{commit}:{path}"], cwd=ROOT)
    return hashlib.sha256(payload).hexdigest()


def _load():
    return json.loads(RELEASE.read_text(encoding="utf-8"))


def test_release_binds_immutable_implementation_result_and_acceptance():
    release = _load()
    assert release["status"] == (
        "offline_source_bound_japanese_identity_surface_ready_for_separate_product_acceptance"
    )
    checkpoint = release["implementation_checkpoint"]
    for binding in checkpoint.values():
        if isinstance(binding, dict):
            assert _sha256_at_commit(checkpoint["commit"], binding["path"]) == binding["sha256"]
    for binding in release["bindings"].values():
        assert _sha256(ROOT / binding["path"]) == binding["sha256"]


def test_release_records_bounded_pass_without_rewriting_p4_m():
    scope = _load()["implemented_scope"]
    assert scope["source_provenance_bounded_japanese_identity_localization"] is True
    assert scope["unsafe_or_unprovenanced_value_abstains_without_raw_value"] is True
    assert scope["historical_p4_j_implementation_hash_preserved"] is True
    assert scope["p4_m_exposed_value_added_to_lookup"] is False
    preserved = _load()["preserved_failure"]
    assert preserved["p4_m_status"] == "fail"
    assert preserved["p4_m_same_case_rerun"] is False


def test_next_stage_requires_new_value_and_freeze_before_real_turn():
    stage = _load()["next_stage"]
    assert stage["id"] == "P4-N-REAL"
    assert stage["real_product_turns_before_freeze"] == 0
    assert any("absent from the P4-N development fixtures" in item for item in stage["requirements"])
    assert any("do not reuse P4-M" in item for item in stage["forbidden_change"])


def test_release_does_not_claim_product_or_research_advantage():
    boundary = _load()["claim_boundary"]
    assert "does not establish real cross-restart product delivery" in boundary
    assert "LLM superiority" in boundary
    assert "human equation" in boundary
