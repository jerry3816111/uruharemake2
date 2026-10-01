import hashlib
import json
from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parent
CONTRACT = ROOT / "configs" / "p4_i_multilingual_current_preference_contract_v1.json"
FREEZE = ROOT / "research" / "p4_i_multilingual_current_preference_freeze_2026-09-21.json"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256_at_commit(commit: str, path: str) -> str:
    payload = subprocess.check_output(["git", "show", f"{commit}:{path}"], cwd=ROOT)
    return hashlib.sha256(payload).hexdigest()


def test_contract_binds_the_immutable_p4_h_gap_without_replay_authority():
    contract = _load(CONTRACT)
    before = contract["prechange_counterexample"]
    assert _sha256(ROOT / before["result_path"]) == before["result_sha256"]
    assert _sha256(ROOT / before["release_path"]) == before["release_sha256"]
    result = _load(ROOT / before["result_path"])
    release = _load(ROOT / before["release_path"])
    assert result["status"] == "pass"
    boundary = result["observed_semantic_boundary"]
    assert boundary["typed_profile_after_turn_2"]["likes"] == []
    assert boundary["typed_profile_after_turn_2"]["dislikes"] == ["氣泡水"]
    observed = release["observed_but_not_passed_scope"]
    assert observed["turn_1_english_preference_typed_as_like"] is False
    assert observed["turn_2_new_chinese_preference_typed_as_like"] is False
    assert before["same_case_may_be_rerun"] is False


def test_contract_freezes_three_language_sequences_and_scope_isolation():
    contract = _load(CONTRACT)
    assert [(row["language"], row["scope"]) for row in contract["sequences"]] == [
        ("en", "drink"),
        ("zh", "飲料"),
        ("ja", "general"),
    ]
    assert all(row["write_value"] != row["new_value"] for row in contract["sequences"])
    assert contract["typed_state_contract"]["history_policy"].startswith("same_scope")
    assert contract["scope_isolation_case"]["expected_active_current_preference_count"] == 2


def test_contract_preserves_episode_shadow_and_research_boundaries():
    contract = _load(CONTRACT)
    invariants = contract["invariants"]
    assert invariants["episode_write_or_episode_document_changed"] is False
    assert invariants["profile_state_shadow_answer_use_activated"] is False
    assert invariants["research_dataset_baseline_or_gate_changed"] is False
    assert invariants["old_profile_records_deleted_or_rewritten"] is False
    assert contract["typed_state_contract"]["answer_use_authorized"] is False


def test_freeze_binds_prechange_code_contract_and_test():
    freeze = _load(FREEZE)
    assert freeze["status"] == "frozen_before_p4_i_implementation"
    commit = freeze["design_review"]["prechange_commit"]
    for name in ("brain_runtime", "profile_memory", "product_entry", "p4_h_authority"):
        binding = freeze["bindings"][name]
        assert _sha256_at_commit(commit, binding["path"]) == binding["sha256"]
    for name in ("contract", "freeze_test", "p4_h_result", "p4_h_release"):
        binding = freeze["bindings"][name]
        assert _sha256(ROOT / binding["path"]) == binding["sha256"]


def test_freeze_forbids_real_turns_and_limits_implementation_files():
    freeze = _load(FREEZE)
    assert freeze["authorized_changes"] == [
        "uruha_multilingual_current_preference_p4.py",
        "test_p4_i_multilingual_current_preference.py",
        "uruha_web_ui_product.py",
    ]
    effects = freeze["authorized_external_effects_before_implementation_release"]
    assert effects == {
        "real_product_turns": 0,
        "local_model_calls": 0,
        "external_network_calls": 0,
        "paid_api_calls": 0,
        "external_deployments": 0,
        "production_memory_accesses": 0,
    }
    assert freeze["failure_policy"]["same_p4_h_case_rerun_allowed"] is False
    assert freeze["failure_policy"]["implementation_batches_maximum"] == 2
