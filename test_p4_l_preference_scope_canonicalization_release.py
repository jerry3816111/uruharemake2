import hashlib
import json
from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parent
RELEASE = ROOT / "research" / "p4_l_preference_scope_canonicalization_release_2026-09-21.json"


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


def test_release_binds_freeze_contract_and_immutable_implementation_checkpoint():
    release = _load()
    assert release["status"] == (
        "offline_scope_canonicalization_ready_for_separate_product_acceptance_freeze"
    )
    for binding in release["bindings"].values():
        assert _sha256(ROOT / binding["path"]) == binding["sha256"]
    checkpoint = release["implementation_checkpoint"]
    for key in ("implementation", "product_entry"):
        binding = checkpoint[key]
        assert _sha256_at_commit(checkpoint["commit"], binding["path"]) == binding["sha256"]


def test_release_is_exact_alias_projection_not_value_or_query_retuning():
    scope = _load()["implemented_scope"]
    assert scope["exact_alias_count"] == 3
    assert scope["default_general_inferred_from_value"] is False
    assert scope["unsupported_scope_changed"] is False
    assert scope["p4_i_or_p4_j_source_file_changed"] is False
    assert scope["value_and_value_digest_preserved"] is True
    assert scope["answer_authority_added"] is False
    assert scope["model_call_added"] is False


def test_release_keeps_product_and_research_claims_pending():
    missing = _load()["not_established"]
    assert missing["full_product_cross_language_scope_join"] is True
    assert missing["open_domain_multilingual_ontology_alignment"] is True
    assert missing["human_felt_understanding"] is True
    assert missing["strong_llm_advantage"] is True
    assert missing["human_equation"] is True


def test_next_stage_requires_new_freeze_before_any_real_turn():
    stage = _load()["next_stage"]
    assert stage["id"] == "P4-L-REAL"
    assert stage["real_product_turns_before_freeze"] == 0
    assert any("P4-L memory graph node" in item for item in stage["requirements"])
    assert any("disclose any value-level overlap" in item for item in stage["requirements"])
