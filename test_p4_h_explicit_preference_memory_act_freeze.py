import hashlib
import json
from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parent
CONTRACT = ROOT / "configs" / "p4_h_explicit_preference_memory_act_contract_v1.json"
FREEZE = ROOT / "research" / "p4_h_explicit_preference_memory_act_freeze_2026-09-21.json"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256_at_commit(commit: str, path: str) -> str:
    payload = subprocess.check_output(
        ["git", "show", f"{commit}:{path}"],
        cwd=ROOT,
    )
    return hashlib.sha256(payload).hexdigest()


def test_freeze_binds_the_immutable_p4_g_negative_result():
    contract = _load(CONTRACT)
    counterexample = contract["prechange_counterexample"]
    result_path = ROOT / counterexample["result_path"]
    assert _sha256(result_path) == counterexample["result_sha256"]
    result = _load(result_path)
    assert result["status"] == "fail"
    assert len(result["gate_evaluation"]["failed_gates"]) == 10
    assert result["turns"][1]["selected_intent"] == "ask_like_me"
    assert counterexample["same_case_may_be_rerun"] is False


def test_contract_keeps_the_same_six_multilingual_positive_acts():
    contract = _load(CONTRACT)
    assert [(row["language"], row["act"]) for row in contract["positive_cases"]] == [
        ("en", "write"),
        ("zh", "write"),
        ("ja", "write"),
        ("en", "correction"),
        ("zh", "correction"),
        ("ja", "correction"),
    ]
    assert contract["authoritative_surfaces"]["write"] == "ん、その好みは覚えとく。"
    assert contract["authoritative_surfaces"]["correction"] == "ん、訂正の内容はそのまま覚えとく。"


def test_contract_adds_fail_closed_safety_and_action_guards():
    contract = _load(CONTRACT)
    negative_ids = {row["id"] for row in contract["negative_cases"]}
    assert {"protected_risk", "function_command", "vrm_command"} <= negative_ids
    assert contract["invariants"]["safety_surface_remains_authoritative"] is True
    assert contract["invariants"]["function_or_vrm_action_routing_changed"] is False


def test_freeze_binds_contract_test_prechange_code_and_result():
    freeze = _load(FREEZE)
    assert freeze["status"] == "frozen_before_p4_h_implementation"
    prechange = freeze["bindings"]["prechange_implementation"]
    assert _sha256_at_commit(
        freeze["design_review"]["prechange_commit"], prechange["path"]
    ) == prechange["sha256"]
    for name, binding in freeze["bindings"].items():
        if name == "prechange_implementation":
            continue
        assert _sha256(ROOT / binding["path"]) == binding["sha256"]
    assert freeze["authorized_changes"] == [
        "uruha_explicit_preference_acknowledgement_p4.py",
        "test_p4_h_explicit_preference_memory_act.py",
    ]


def test_freeze_forbids_p4_g_replay_and_real_turns_before_implementation_release():
    freeze = _load(FREEZE)
    assert freeze["failure_policy"]["same_p4_g_case_rerun_allowed"] is False
    assert freeze["authorized_external_effects_before_implementation_release"]["real_product_turns"] == 0
    assert freeze["authorized_external_effects_before_implementation_release"]["local_model_calls"] == 0
    assert freeze["claim_boundary"].startswith("P4-H is a bounded product")
