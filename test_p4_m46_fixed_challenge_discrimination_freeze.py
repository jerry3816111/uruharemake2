"""Zero-model-call checks for the separate M46 fixed-challenge-only freeze."""

from collections import Counter
import hashlib
import json
from pathlib import Path

import p4_m46_reviewer_necessity_scoring as scoring
import uruha_actionable_help_delivery_m45 as m45
import uruha_goal_progress_delivery_m46 as m46
import uruha_state_changing_candidates_m51 as m51


ROOT = Path(__file__).resolve().parent
CONTRACT = json.loads(
    (ROOT / "configs/p4_m46_fixed_challenge_discrimination_v1.json").read_text(encoding="utf-8")
)
ORIGINAL = json.loads((ROOT / "configs/p4_m46_reviewer_necessity_v1.json").read_text(encoding="utf-8"))
DATASET = json.loads((ROOT / CONTRACT["dataset"]["path"]).read_text(encoding="utf-8"))


def _sha256(relative: str) -> str:
    return hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()


def test_new_study_is_bound_to_unchanged_inputs_and_old_failure():
    assert CONTRACT["status"] == "prospectively_frozen_before_model_execution"
    assert CONTRACT["single_variable"] == "presence_of_existing_M46_counterfactual_model_review"
    assert CONTRACT["dataset"]["selected_collection"] == "challenge_packets_only"
    assert _sha256(CONTRACT["dataset"]["path"]) == CONTRACT["dataset"]["sha256"]
    assert CONTRACT["dataset"]["sha256"] == ORIGINAL["dataset"]["sha256"]
    for record in CONTRACT["hash_bound_dependencies"].values():
        assert _sha256(record["path"]) == record["sha256"]
    assert CONTRACT["hash_bound_dependencies"]["old_runner_shared_call_helpers_only"]["path"] == (
        "run_p4_m46_reviewer_necessity.py"
    )

    old = CONTRACT["prior_inconclusive_result"]
    assert _sha256(old["path"]) == old["sha256"]
    result = json.loads((ROOT / old["path"]).read_text(encoding="utf-8"))
    assert result["status"] == old["status"] == "generation_call_failed_partial_no_resume"
    assert result["review_calls"] == old["review_calls"] == 0
    assert result["rows"][0]["call"]["json_parse_success"] is False
    assert CONTRACT["execution"]["result_path"] != old["path"]


def test_unchanged_model_options_and_strict_component_only_claim():
    assert CONTRACT["model"] == ORIGINAL["model"] == "qwen3.5:9b"
    assert CONTRACT["model_digest"] == ORIGINAL["model_digest"]
    assert CONTRACT["hardware"] == ORIGINAL["hardware"] == "Apple M2 Pro 12-core 32GB"
    constants = CONTRACT["controlled_constants"]
    before = ORIGINAL["controlled_constants"]
    assert constants["m46_prompt_and_schema"] == before["m46_review_prompt_and_schema"]
    assert (constants["temperature"], constants["seed"], constants["num_ctx"], constants["num_predict"]) == (
        before["temperature"], before["m46_seed"], before["num_ctx"], before["m46_num_predict"]
    )
    for key in ("stream", "think", "keep_alive", "retry_count", "prewarm_once_before_scoring",
                "prewarm_counted_as_case_latency"):
        assert constants[key] == before[key]
    execution = CONTRACT["execution"]
    assert execution["generation_scored_call_count"] == 0
    assert execution["maximum_review_scored_calls"] == 8
    assert execution["reviewer_timeout_seconds"] == 30
    assert execution["review_plan_mechanism_hidden"] is True
    assert execution["review_payload_excludes_gold_and_category"] is True
    assert execution["same_selected_plan_replayed_to_both_arms"] is True
    assert execution["localhost_only"] is True
    assert execution["production_database_access"] is False
    assert execution["product_runtime_changed"] is False
    assert CONTRACT["arms"]["B"].endswith("offline_only")
    assert CONTRACT["preregistered_gates"]["B_product_bypass_authorized"] is False
    assert CONTRACT["latency_interpretation"]["product_two_stage_budget_seconds"] == 20
    assert "necessary_not_sufficient" in CONTRACT["latency_interpretation"]["reviewer_only_at_most_20_seconds"]
    for limit in ("not natural M51 generation", "unseen holdout", "independent human judgment",
                  "reviewer product necessity", "full two-stage latency", "M45/Web delivery"):
        assert limit in CONTRACT["claim_boundary"]


def test_fixed_packets_and_category_reasons_are_preregistered_without_models(monkeypatch):
    def forbidden(*_args, **_kwargs):
        raise AssertionError("Freeze test must make no model call")

    monkeypatch.setattr(m45, "_native_json", forbidden)
    monkeypatch.setattr(m51, "_native_candidates", forbidden)
    packets = DATASET["challenge_packets"]
    assert len(packets) == CONTRACT["execution"]["challenge_packet_count"] == 9
    assert len(DATASET["generation_cases"]) == 6  # Present in the reused file, never run here.
    by_id = {packet["packet_id"]: packet for packet in packets}
    order = CONTRACT["dataset"]["packet_order"]
    assert len(order) == len(set(order)) == len(by_id) == 9
    assert set(order) == set(by_id)
    assert order[-1] == "p4_m46_fixture_guard_block_001"
    assert Counter(packet["category"] for packet in packets) == {
        "valid": 3, "wrong_task": 1, "unsupported_specificity": 1,
        "private_inference": 1, "non_action": 1, "surface": 1, "guard_block": 1,
    }

    relevant = CONTRACT["invalid_category_relevant_false_checks"]
    assert set(relevant) == {"wrong_task", "unsupported_specificity", "private_inference",
                             "non_action", "surface"}
    for paths in relevant.values():
        assert paths
        for path in paths:
            group, key = path.split(".")
            assert (group == "content_checks" and key in m46.CONTENT_CHECKS) or (
                group == "surface_checks" and key in m46.SURFACE_CHECKS
            )

    scores = []
    for packet_id in order:
        packet = by_id[packet_id]
        source, batch = packet["source"], packet["batch"]
        gold = "valid" if packet["gold"]["accept"] else "invalid"
        score = scoring.score_packet(source, batch, None, gold)
        expected = packet["expected_deterministic_guard"]
        assert score["selected_index"] == expected["selected_index"] == 0
        assert score["selection_guard_parity"] is True
        assert score["selected_plan"]["goal_source_id"] == source["id"]
        assert score["selected_plan"]["goal_source_span"] == source["text"]
        assert score["selected_plan_digest"] == m45.digest(score["selected_plan"])
        assert score["deterministic_eligible"] is expected["arm_b_would_allow"]
        assert score["arms"]["B_deterministic_only"]["would_deliver"] is expected["arm_b_would_allow"]
        assert score["arms"]["A_model_review"]["would_deliver"] is False
        assert score["model_calls_by_scorer"] == 0
        if score["deterministic_eligible"]:
            assert score["m39_final_byte_identical"] is True
            assert score["m39_surface_trace"]["action"] == "accept"
            assert m45._japanese(score["selected_plan"]["instruction_jp"])
        scores.append((packet, score))

    gates = CONTRACT["preregistered_gates"]
    eligible = [(packet, score) for packet, score in scores if score["deterministic_eligible"]]
    assert len(eligible) == gates["deterministic_eligible_packet_count"] == 8
    assert sum(packet["category"] == "valid" for packet, _ in eligible) == gates["valid_packet_count"] == 3
    assert sum(packet["category"] in relevant for packet, _ in eligible) == gates[
        "semantic_or_surface_invalid_packet_count"
    ] == 5
    assert sum(packet["category"] == "guard_block" for packet, _ in scores) == gates["guard_control_count"] == 1
    assert sum(score["arms"]["B_deterministic_only"]["valid_retained"] for _, score in scores) == gates[
        "B_valid_retained_count_preflight"
    ] == 3
    assert sum(score["arms"]["B_deterministic_only"]["false_action"] for _, score in scores) == gates[
        "B_invalid_false_action_count_preflight"
    ] == 5
    guard = next(score for packet, score in scores if packet["category"] == "guard_block")
    assert not guard["arms"]["A_model_review"]["would_deliver"]
    assert not guard["arms"]["B_deterministic_only"]["would_deliver"]
    assert gates["guard_control_both_arms_blocked_count"] == 1
    assert gates["selector_parity_all_packets"] is True
    assert gates["A_review_completed_json_and_tokens_count"] == 8
    assert gates["A_review_source_identity_exact_count"] == 8
    assert gates["A_valid_retained_count"] == 3
    assert gates["A_invalid_false_action_count"] == 0
    assert gates["A_category_relevant_false_check_count"] == 5
    assert gates["natural_japanese_and_m39_exact_count"] == 8
    assert gates["retry_count"] == 0
