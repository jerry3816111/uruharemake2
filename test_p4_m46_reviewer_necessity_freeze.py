"""0-call prospective freeze checks for the M46 reviewer ablation."""

import hashlib
import json
from pathlib import Path

import p4_m46_reviewer_necessity_scoring as scoring


ROOT = Path(__file__).resolve().parent
CONFIG = json.loads((ROOT / "configs/p4_m46_reviewer_necessity_v1.json").read_text(encoding="utf-8"))
DATASET = json.loads((ROOT / CONFIG["dataset"]["path"]).read_text(encoding="utf-8"))


def _source_texts(payload):
    rows = payload.get("positive_cases", []) + payload.get("control_cases", [])
    rows += payload.get("generation_cases", []) + payload.get("review_fixtures", [])
    return {row["source"]["text"] for row in rows if isinstance(row.get("source"), dict)}


def test_input_hashes_model_and_single_variable_are_frozen():
    assert CONFIG["status"] == "prospectively_frozen_before_model_execution"
    assert DATASET["status"] == "sealed_before_model_execution"
    assert hashlib.sha256((ROOT / CONFIG["dataset"]["path"]).read_bytes()).hexdigest() == CONFIG["dataset"]["sha256"]
    for record in CONFIG["hash_bound_implementation"].values():
        assert hashlib.sha256((ROOT / record["path"]).read_bytes()).hexdigest() == record["sha256"]
    assert CONFIG["model"] == "qwen3.5:9b"
    assert CONFIG["model_digest"] == "6488c96fa5faab64bb65cbd30d4289e20e6130ef535a93ef9a49f42eda893ea7"
    assert CONFIG["single_variable"] == "presence_of_existing_M46_counterfactual_model_review"
    assert CONFIG["arms"]["B"].endswith("offline_only")
    assert CONFIG["failure_policy"]["product_runtime_may_be_changed_by_this_experiment"] is False


def test_new_source_only_cases_are_unique_balanced_and_not_old_examples():
    generation = DATASET["generation_cases"]
    challenge = DATASET["challenge_packets"]
    assert len(generation) == CONFIG["execution"]["generation_case_count"] == 6
    assert len(challenge) == CONFIG["execution"]["challenge_packet_count"] == 9
    assert {language: sum(row["language"] == language for row in generation) for language in ("zh-TW", "en", "ja")} == {
        "zh-TW": 2, "en": 2, "ja": 2,
    }
    all_sources = [row["source"] for row in generation + challenge]
    assert len({row["id"] for row in all_sources}) == len(all_sources)
    assert len({row["text"] for row in all_sources}) == len(all_sources)
    assert all(row["kind"] == "current_user" for row in all_sources)
    for row in generation:
        support = row["predeclared_source_support"]
        assert support["literal_goal"] and support["constraints"] and support["forbidden_inference"]
        assert "batch" not in row and "gold" not in row
    old_texts = set()
    for filename in (
        "p4_ba_stage_model_allocation_v1.json",
        "p4_bc_raw_dialogue_typed_spec_v1.json",
        "p4_bd_role_aware_evidence_v1.json",
        "p4_be_role_value_prompt_v1.json",
    ):
        old_texts.update(_source_texts(json.loads((ROOT / "datasets" / filename).read_text(encoding="utf-8"))))
    assert {row["text"] for row in all_sources}.isdisjoint(old_texts)
    assert DATASET["development_only"] is True
    assert "not independent human" in DATASET["annotation_provenance"]


def test_frozen_challenge_gold_and_deterministic_guard_preconditions():
    expected_categories = {
        "valid": 3, "wrong_task": 1, "unsupported_specificity": 1,
        "private_inference": 1, "non_action": 1, "surface": 1, "guard_block": 1,
    }
    challenge = DATASET["challenge_packets"]
    assert {category: sum(row["category"] == category for row in challenge) for category in expected_categories} == expected_categories
    for packet in challenge:
        source, batch = packet["source"], packet["batch"]
        assert batch["sid"] == source["id"] and batch["span"] == source["text"]
        assert len(batch["items"]) == 2
        assert packet["gold"]["reason"]
        assert packet["gold"]["accept"] is (packet["category"] == "valid")
        result = scoring.score_packet(source, batch, None, packet["gold"]["accept"])
        expected = packet["expected_deterministic_guard"]
        assert result["selected_index"] == expected["selected_index"]
        assert result["selection_guard_parity"] is True
        assert result["deterministic_eligible"] is expected["arm_b_would_allow"]
        assert result["arms"]["B_deterministic_only"]["would_deliver"] is expected["arm_b_would_allow"]
        assert result["arms"]["A_model_review"]["would_deliver"] is False
        assert result["model_calls_by_scorer"] == 0


def test_cost_quality_and_failure_branches_are_numerically_predeclared():
    execution = CONFIG["execution"]
    gates = CONFIG["preregistered_gates"]
    assert execution["maximum_total_scored_calls"] == execution["maximum_generation_scored_calls"] + execution["maximum_review_scored_calls"] == 20
    assert (execution["generator_timeout_seconds"], execution["reviewer_timeout_seconds"]) == (45, 30)
    assert execution["per_case_product_latency_gate_seconds"] == gates["maximum_product_case_total_wall_seconds"] == 20
    assert execution["generation_commit_before_any_review"] and execution["quality_labels_commit_before_any_review"]
    assert execution["one_generator_output_replayed_to_both_arms"] and execution["review_plan_mechanism_hidden"]
    assert CONFIG["controlled_constants"]["retry_count"] == gates["retry_count"] == 0
    assert (gates["challenge_valid_count"], gates["challenge_semantic_or_surface_invalid_count"], gates["challenge_guard_control_count"]) == (3, 5, 1)
    assert gates["challenge_A_valid_retained_count"] == 3 and gates["challenge_A_false_action_count"] == 0
    assert gates["challenge_B_false_action_count_for_bypass_eligibility"] == 0
    assert gates["generated_A_invalid_or_uncertain_false_action_count"] == 0
    assert gates["generated_B_invalid_or_uncertain_false_action_count_for_bypass_eligibility"] == 0
    assert CONFIG["generated_plan_label_protocol"]["gold_authority"].startswith("developer_authored_proxy")
    assert CONFIG["failure_policy"]["if_both_arms_fail"] == "KEEP_PRODUCT_FAIL_CLOSED_AND_DESIGN_REVIEW"
