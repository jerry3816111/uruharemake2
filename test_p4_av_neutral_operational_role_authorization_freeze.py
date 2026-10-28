import hashlib
import json
from pathlib import Path

import uruha_source_neutral_scaffold_m53 as m53


ROOT = Path(__file__).resolve().parent
DATASET = ROOT / "datasets" / "p4_av_neutral_operational_role_authorization_v1.json"
CONFIG = ROOT / "configs" / "p4_av_neutral_operational_role_authorization_v1.json"


def _sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load():
    return json.loads(DATASET.read_text(encoding="utf-8")), json.loads(
        CONFIG.read_text(encoding="utf-8")
    )


def _plan(case):
    return {
        "progress_criterion_jp": case["instruction_jp"],
        "action_object_jp": "考え",
        "action_step_jp": case["instruction_jp"],
        "expected_state_change_jp": case["instruction_jp"],
        "completion_jp": "一つ置いたら停止する",
        "instruction_jp": case["instruction_jp"],
    }


def _sources(case):
    return [{"id": f"current:{case['id']}", "kind": "current_user", "text": case["source"]}]


def test_p4_av_dataset_is_frozen_before_implementation():
    dataset, config = _load()

    assert config["status"] == "prospectively_frozen_before_implementation"
    assert config["dataset"]["sha256"] == _sha(DATASET)
    assert len(dataset["cases"]) == config["dataset"]["case_count"] == 17
    assert dataset["frozen_before_implementation"] is True


def test_p4_av_split_counts_and_ids_are_fixed():
    dataset, config = _load()
    cases = dataset["cases"]

    assert len({case["id"] for case in cases}) == len(cases)
    for split, key in (
        ("exposed_development", "exposed_development_count"),
        ("fresh_positive", "fresh_positive_count"),
        ("fresh_control", "fresh_control_count"),
        ("predecessor_control", "predecessor_control_count"),
    ):
        assert sum(case["split"] == split for case in cases) == config["dataset"][key]


def test_p4_av_predecessor_blocks_every_new_operational_role_case():
    dataset, _ = _load()
    cases = [
        case
        for case in dataset["cases"]
        if case["split"] in {"exposed_development", "fresh_positive"}
    ]

    assert len(cases) == 7
    for case in cases:
        state = m53.authorize_named_scaffold_m53(_plan(case), _sources(case))
        assert state["status"] == case["expected_predecessor_status"] == "blocked"
        assert state["unsupported_count"] == len(case["labels"])


def test_p4_av_fresh_controls_are_unsupported_private_or_concrete_labels():
    dataset, _ = _load()
    controls = [case for case in dataset["cases"] if case["split"] == "fresh_control"]

    assert {case["control_family"] for case in controls} == {
        "invented_topic",
        "hidden_priority",
        "hidden_emotion",
        "diagnosis",
        "hidden_preference",
        "hidden_feasibility",
        "invented_attribute",
    }
    for case in controls:
        state = m53.authorize_named_scaffold_m53(_plan(case), _sources(case))
        assert state["status"] == case["expected_predecessor_status"] == "blocked"
        assert case["expected_status"] == "blocked"


def test_p4_av_preserves_exact_source_existing_neutral_and_unquoted_controls():
    dataset, _ = _load()
    controls = [case for case in dataset["cases"] if case["split"] == "predecessor_control"]

    observed = {}
    for case in controls:
        state = m53.authorize_named_scaffold_m53(_plan(case), _sources(case))
        observed[case["control_family"]] = state["status"]
        assert state["status"] == case["expected_predecessor_status"]
        assert case["expected_status"] == "preserve_predecessor"
    assert observed == {
        "exact_source": "authorized",
        "existing_neutral_role": "authorized",
        "unquoted": "no_named_labels",
    }


def test_p4_av_contract_forbids_downstream_gate_and_claim_changes():
    _, config = _load()
    forbidden = set(config["single_variable"]["forbidden_changes"])

    assert {
        "m46_independent_review",
        "m45_or_m39_fail_closed_gate",
        "model_prompt_or_schema",
        "visible_reply",
        "topic_priority_emotion_diagnosis_preference_or_feasibility_authorization",
    }.issubset(forbidden)
    assert "does not prove plan usefulness" in config["claim_boundary"]
    assert config["failure_policy"]["same_fresh_case_retry_allowed"] is False
