"""Zero-model-call checks for prospective M46 decision-interface comparison."""

from collections import Counter
import hashlib
import json
from pathlib import Path

import p4_m46_decision_interface_scoring as scoring
import p4_m46_reviewer_necessity_scoring as legacy
import uruha_actionable_help_delivery_m45 as m45
import uruha_goal_progress_delivery_m46 as m46
import uruha_state_changing_candidates_m51 as m51


ROOT = Path(__file__).resolve().parent
CONFIG = json.loads((ROOT / "configs/p4_m46_decision_interface_v1.json").read_text(encoding="utf-8"))
DATASET = json.loads((ROOT / CONFIG["dataset"]["path"]).read_text(encoding="utf-8"))


def _hash(relative):
    return hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()


def test_freeze_binds_single_variable_model_cost_and_prior_failure():
    assert CONFIG["status"] == "prospectively_frozen_before_model_execution"
    assert CONFIG["single_variable"] == "M46_single_review_decision_interface_prompt_plus_schema_as_one_contract"
    assert _hash(CONFIG["plan"]["path"]) == CONFIG["plan"]["sha256"]
    assert _hash(CONFIG["dataset"]["path"]) == CONFIG["dataset"]["sha256"]
    for record in CONFIG["hash_bound_dependencies"].values():
        assert _hash(record["path"]) == record["sha256"]
    prior = json.loads((ROOT / CONFIG["hash_bound_dependencies"]["prior_exposed_fixed_failure"]["path"])
                       .read_text(encoding="utf-8"))
    assert prior["status"] == "fixed_discrimination_fail"
    assert CONFIG["model"] == "qwen3.5:9b"
    assert CONFIG["model_digest"] == "6488c96fa5faab64bb65cbd30d4289e20e6130ef535a93ef9a49f42eda893ea7"
    assert CONFIG["hardware"] == "Apple M2 Pro 12-core 32GB"
    constants = CONFIG["controlled_constants"]
    assert (constants["temperature"], constants["seed"], constants["num_ctx"],
            constants["num_predict"], constants["retry_count"]) == (0, 20260829, 4096, 320, 0)
    assert constants["stream"] is constants["think"] is False
    assert constants["prewarm_once_before_scoring"] is True
    assert constants["prewarm_counted_as_case_latency"] is False
    assert CONFIG["execution"]["review_plan_mechanism_hidden"] is True
    assert CONFIG["execution"]["review_payload_excludes_gold_and_category"] is True
    assert CONFIG["execution"]["generation_scored_calls"] == 0
    assert CONFIG["execution"]["maximum_review_scored_calls"] == 20
    assert CONFIG["preregistered_gates"]["B_product_eligible_from_component_only"] is False
    assert CONFIG["failure_policy"]["product_runtime_may_be_changed_by_this_study"] is False


def test_new_packets_are_unique_balanced_and_never_old_scored_sources():
    assert DATASET["status"] == "sealed_before_model_execution"
    assert DATASET["scored_packet_count"] == 10
    assert DATASET["guard_control_count"] == 1
    assert DATASET["maximum_paired_review_calls"] == 20
    packets = DATASET["challenge_packets"]
    assert len(packets) == 11
    assert [item["packet_id"] for item in packets] == CONFIG["dataset"]["packet_order"]
    assert len({item["packet_id"] for item in packets}) == 11
    assert len({item["source"]["id"] for item in packets}) == 11
    assert len({item["source"]["text"] for item in packets}) == 11
    assert all(item["source"]["kind"] == "current_user" for item in packets)
    assert Counter(item["category"] for item in packets) == {
        "valid": 3, "wrong_task": 1, "unsupported_specificity": 1,
        "private_inference": 1, "non_action": 1, "actor_surface": 1,
        "invented_prerequisite": 1, "unnatural_surface": 1, "guard_control": 1,
    }
    assert {item["language"] for item in packets} == {"zh-TW", "en", "ja"}
    old = json.loads((ROOT / "datasets/p4_m46_reviewer_necessity_v1.json").read_text(encoding="utf-8"))
    old_texts = {item["source"]["text"] for item in old["challenge_packets"] + old["generation_cases"]}
    assert {item["source"]["text"] for item in packets}.isdisjoint(old_texts)
    assert "Developer-authored" in DATASET["annotation_provenance"]
    assert "no independent human" in DATASET["annotation_provenance"]


def test_gold_and_shared_guard_preflight_make_no_model_calls(monkeypatch):
    def forbidden(*_args, **_kwargs):
        raise AssertionError("Freeze test must not call a model")

    monkeypatch.setattr(m45, "_native_json", forbidden)
    monkeypatch.setattr(m51, "_native_candidates", forbidden)
    eligible = []
    blocked = []
    for packet in DATASET["challenge_packets"]:
        source, batch, gold = packet["source"], packet["batch"], packet["gold"]
        assert batch["sid"] == source["id"]
        assert batch["span"] == source["text"]
        assert len(batch["items"]) == 2
        assert gold["rationale_zh"]
        assert type(gold["content_valid"]) is bool
        assert type(gold["japanese_surface_valid"]) is bool
        assert type(gold["actor_valid"]) is bool
        assert (gold["label"] == "valid") is (
            gold["content_valid"] and gold["japanese_surface_valid"] and gold["actor_valid"]
        )
        if gold["label"] == "valid":
            assert gold["expected_failed_axis"] is None
        else:
            assert gold["expected_failed_axis"] in scoring.AXES
        score = scoring.score_packet(source, batch, None, None,
                                     gold["label"], gold["expected_failed_axis"])
        expected = packet["expected_deterministic_guard"]
        assert score["selected_index"] == expected["selected_index"] == 0
        assert score["selection_guard_parity"] is True
        assert score["selected_plan"]["goal_source_id"] == source["id"]
        assert score["selected_plan"]["goal_source_span"] == source["text"]
        assert score["deterministic_eligible"] is expected["review_eligible"]
        assert score["model_calls_by_scorer"] == 0
        assert score["selected_plan_digest"] == m45.digest(score["selected_plan"])
        old_guard = legacy.score_packet(source, batch, None, gold["label"])
        assert old_guard["selected_plan_digest"] == score["selected_plan_digest"]
        assert old_guard["selected_fingerprint"] == score["selected_fingerprint"]
        assert old_guard["m39_surface_trace"]["action"] == "accept"
        assert old_guard["m39_final_byte_identical"] is expected["m39_exact_accept"]
        if score["deterministic_eligible"]:
            eligible.append(packet)
            assert expected["selected_structural_pass"] is True
            assert expected["m39_exact_accept"] is True
            assert score["guard_violations"] == []
        else:
            blocked.append(packet)
            assert expected["selected_structural_pass"] is False
            assert score["guard_violations"] == ["nonprogress_or_unknown_mechanism"]
    assert len(eligible) == CONFIG["preregistered_gates"]["deterministic_eligible_packet_count"] == 10
    assert sum(item["gold"]["label"] == "valid" for item in eligible) == 3
    assert sum(item["gold"]["label"] == "invalid" for item in eligible) == 7
    assert [item["category"] for item in blocked] == ["guard_control"]
    assert CONFIG["preregistered_gates"]["guard_control_both_arms_blocked_count"] == 1
    assert CONFIG["preregistered_gates"]["per_arm_completed_parseable_token_count"] == 10
    assert CONFIG["preregistered_gates"]["per_arm_valid_retained_count"] == 3
    assert CONFIG["preregistered_gates"]["per_arm_invalid_false_action_count"] == 0
    assert CONFIG["preregistered_gates"]["per_arm_explicit_expected_axis_fail_count"] == 7
    assert CONFIG["preregistered_gates"]["per_arm_reviewer_only_max_wall_seconds"] == 20


def test_schema_and_payload_hide_mechanism_and_gold():
    packet = DATASET["challenge_packets"][0]
    prior = scoring.score_packet(packet["source"], packet["batch"], None, None, "valid")
    source, plan = packet["source"], prior["selected_plan"]
    payload = scoring.decision_review_payload(source, plan)
    schema = scoring.decision_review_schema(source, plan)
    assert set(payload) == {"sources", "plan", "planned_payload_digest"}
    assert payload["sources"] == [source]
    assert "progress_mechanism" not in payload["plan"]
    assert "gold" not in json.dumps(payload)
    assert "category" not in json.dumps(payload)
    assert schema["properties"]["source_id"]["enum"] == [source["id"]]
    assert schema["properties"]["source_span"]["enum"] == [source["text"]]
