import hashlib
import json
from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parent
FREEZE = ROOT / "research" / "p4_l_preference_scope_canonicalization_freeze_2026-09-21.json"


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
    return json.loads(FREEZE.read_text(encoding="utf-8"))


def test_freeze_binds_contract_prechange_and_prospective_regression():
    freeze = _load()
    assert freeze["status"] == "frozen_before_p4_l_implementation"
    for key in ("contract", "prechange", "prospective_regression", "p4_k_release"):
        binding = freeze["bindings"][key]
        assert _sha256(ROOT / binding["path"]) == binding["sha256"]


def test_freeze_binds_old_p4_i_p4_j_and_product_entry_to_prechange_commit():
    freeze = _load()
    commit = freeze["design_review"]["prechange_commit"]
    for key in ("p4_i_implementation_before", "p4_j_implementation_before", "product_entry_before"):
        binding = freeze["bindings"][key]
        assert _sha256_at_commit(commit, binding["path"]) == binding["sha256"]


def test_freeze_is_one_alias_projection_variable_and_forbids_adjacent_retuning():
    freeze = _load()
    assert "canonical scope alias projection" in freeze["design_review"]["single_changed_variable"]
    policy = freeze["failure_policy"]
    assert policy["alias_table_expansion_after_result_allowed"] is False
    assert policy["p4_i_or_p4_j_frozen_case_rerun_allowed"] is False
    assert policy["preference_value_extraction_or_localization_change_allowed"] is False
    assert policy["real_product_turn_before_separate_acceptance_freeze_allowed"] is False


def test_freeze_authorizes_no_real_turn_model_network_or_production_memory():
    effects = _load()["authorized_external_effects_before_implementation_release"]
    assert all(value == 0 for value in effects.values())
