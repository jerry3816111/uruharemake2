"""Immutable, zero-model-call checks for the one-shot M46 decision-interface result."""

import hashlib
import json
from pathlib import Path
from statistics import median


ROOT = Path(__file__).resolve().parent
RESULT = ROOT / "analysis/p4_m46_decision_interface_result_2026-09-30.json"
CONTRACT = ROOT / "configs/p4_m46_decision_interface_v1.json"
RESULT_SHA256 = "66321bb7b01eae6dafe0a81dbb79f74f355ee6c64debab1eae4e5eec83692a46"
FREEZE_SHA = "7abf74579e7793c22d3111b149037d9d7bdc5393"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _digest(value: object) -> str:
    if not isinstance(value, str):
        value = json.dumps(value, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]


def _frozen_result():
    raw = RESULT.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == RESULT_SHA256
    result = json.loads(raw)
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    dataset = json.loads((ROOT / contract["dataset"]["path"]).read_text(encoding="utf-8"))
    return result, contract, dataset


def test_formal_failure_is_bound_to_full_freeze_and_unchanged_inputs():
    result, contract, _ = _frozen_result()
    summary = result["summary"]
    assert result["schema"] == "uruha_p4_m46_decision_interface_result_v1"
    assert result["status"] == summary["status"] == "review_required_component_fail"
    assert result["freeze_sha"] == FREEZE_SHA
    assert len(result["freeze_sha"]) == 40
    assert result["contract_sha256"] == _sha256(CONTRACT)
    assert result["dataset_sha256"] == contract["dataset"]["sha256"] == _sha256(
        ROOT / contract["dataset"]["path"]
    )
    assert result["runner_sha256"] == _sha256(ROOT / "run_p4_m46_decision_interface.py")
    assert contract["plan"]["sha256"] == _sha256(ROOT / contract["plan"]["path"])
    for dependency in contract["hash_bound_dependencies"].values():
        assert dependency["sha256"] == _sha256(ROOT / dependency["path"])
    assert result["claim_boundary"] == summary["claim_boundary"] == contract["claim_boundary"]

    constants = contract["controlled_constants"]
    execution = contract["execution"]
    gates = contract["preregistered_gates"]
    assert result["retry_count"] == constants["retry_count"] == gates["retry_count"] == 0
    assert result["generation_scored_calls"] == execution["generation_scored_calls"] == 0
    assert result["maximum_review_scored_calls"] == execution["maximum_review_scored_calls"] == 20
    assert result["prewarm"]["model"] == contract["model"] == "qwen3.5:9b"
    assert result["prewarm"]["attempted"] is result["prewarm"]["completed"] is True
    assert result["production_database_access"] is execution["production_database_access"] is False
    assert result["product_runtime_changed"] is execution["product_runtime_changed"] is False
    assert result["product_eligible"] is summary["product_eligible"] is False
    assert summary["A_component_gate_pass"] is summary["B_component_gate_pass"] is False
    assert summary["reason_quality_human_validated"] is False
    assert gates["B_product_eligible_from_component_only"] is False


def test_exactly_twenty_paired_calls_preserve_source_plan_and_common_guard():
    result, contract, dataset = _frozen_result()
    rows = result["rows"]
    packets = dataset["challenge_packets"]
    metrics = result["summary"]["metrics"]
    assert [row["packet_id"] for row in rows] == contract["dataset"]["packet_order"]
    assert [row["packet_id"] for row in rows] == [packet["packet_id"] for packet in packets]
    assert len(rows) == metrics["packet_count"] == 11
    assert metrics == {
        "packet_count": 11,
        "deterministic_eligible_packet_count": 10,
        "valid_packet_count": 3,
        "invalid_packet_count": 7,
        "guard_control_both_arms_blocked_count": 1,
        "selector_parity_all_packets": True,
        "source_and_selected_plan_identity_both_arms": True,
        "review_scored_call_count": 20,
    }
    assert result["summary"]["common_failed_gates"] == []
    assert result["arm_order_rule"] == "eligible case index even A-B, odd B-A"
    assert sum(row["call_started"][arm] for row in rows for arm in ("A", "B")) == 20

    call_ids = set()
    for index, (row, packet) in enumerate(zip(rows, packets)):
        score = row["score"]
        source = packet["source"]
        plan = score["selected_plan"]
        assert row["source"] == source
        assert row["batch_digest"] == _digest(packet["batch"])
        assert row["gold_label"] == score["gold_label"] == packet["gold"]["label"]
        assert row["expected_failed_axis"] == score["expected_failed_axis"] == packet["gold"][
            "expected_failed_axis"
        ]
        assert score["source_id"] == plan["goal_source_id"] == source["id"]
        assert plan["goal_source_span"] == source["text"]
        assert score["source_digest"] == _digest(source["text"])
        assert row["selected_plan_digest_before_review"] == score["selected_plan_digest"] == _digest(plan)
        assert row["selected_fingerprint_before_review"] == score["selected_fingerprint"]
        assert score["selection_guard_parity"] is True
        assert score["selected_index"] == packet["expected_deterministic_guard"]["selected_index"] == 0
        assert score["deterministic_eligible"] is row["deterministic_eligible"]
        assert score["model_calls_by_scorer"] == 0
        assert score["product_runtime_changed"] is False
        assert "not human judgment" in score["claim_boundary"]

        if index == 10:
            assert row["category"] == "guard_control"
            assert row["deterministic_eligible"] is False
            assert row["arm_order"] == []
            assert row["call_started"] == {"A": False, "B": False}
            assert row["calls"] == row["reviews"] == {"A": None, "B": None}
            assert score["guard_violations"] == ["nonprogress_or_unknown_mechanism"]
            assert score["arms"]["old_contract"]["would_deliver"] is False
            assert score["arms"]["new_contract"]["would_deliver"] is False
            continue

        assert row["deterministic_eligible"] is True
        assert score["guard_violations"] == []
        assert row["arm_order"] == (["A", "B"] if index % 2 == 0 else ["B", "A"])
        assert row["call_started"] == {"A": True, "B": True}
        assert row["calls"]["A"]["payload_digest"] == row["calls"]["B"]["payload_digest"]
        payload = {
            "sources": [source],
            "plan": {key: value for key, value in plan.items() if key != "progress_mechanism"},
            "planned_payload_digest": _digest({"sources": [source], "plan": plan}),
        }
        assert row["calls"]["A"]["payload_digest"] == _digest(payload)
        for arm in ("A", "B"):
            call = row["calls"][arm]
            review = row["reviews"][arm]
            assert call["call_id"] == f'{"review" if arm == "A" else "review_b"}:{row["packet_id"]}'
            assert call["call_id"] not in call_ids
            call_ids.add(call["call_id"])
            assert call["stage"] == "review"
            assert call["model"] == contract["model"]
            assert call["attempted"] is call["completed"] is call["json_parse_success"] is True
            assert call["options"] == {
                key: contract["controlled_constants"][key]
                for key in ("temperature", "seed", "num_ctx", "num_predict")
            }
            assert call["prompt_tokens"] > 0
            assert 0 < call["completion_tokens"] <= contract["controlled_constants"]["num_predict"]
            assert call["wall_seconds"] > 0
            assert review["source_id"] == source["id"]
            assert review["source_span"] == source["text"]
    assert len(call_ids) == metrics["review_scored_call_count"] == 20


def test_absolute_arm_metrics_cost_and_paired_decisions_preserve_failure():
    result, contract, _ = _frozen_result()
    rows = [row for row in result["rows"] if row["deterministic_eligible"]]
    valid = [row for row in rows if row["gold_label"] == "valid"]
    invalid = [row for row in rows if row["gold_label"] == "invalid"]
    arms = result["summary"]["arms"]
    gates = contract["preregistered_gates"]
    assert len(valid) == gates["valid_packet_count"] == 3
    assert len(invalid) == gates["invalid_packet_count"] == 7
    assert arms["A"] == {
        "metrics": {
            "completed_parseable_token_count": 10,
            "source_exact_count": 10,
            "valid_retained_count": 2,
            "invalid_false_action_count": 2,
            "mapped_expected_axis_false_check_count": 5,
            "reviewer_only_max_wall_seconds": 14.72437,
            "reviewer_only_median_wall_seconds": 13.601790000000001,
            "prompt_tokens": 8606,
            "completion_tokens": 2891,
        },
        "failed_gates": [
            "valid_retained_count", "invalid_false_action_count",
            "mapped_expected_axis_false_check_count",
        ],
        "reason_diagnostic_kind": "legacy_many_to_one_false_check_proxy",
        "component_gate_pass": False,
    }
    assert arms["B"] == {
        "metrics": {
            "completed_parseable_token_count": 10,
            "source_exact_count": 10,
            "valid_retained_count": 0,
            "invalid_false_action_count": 0,
            "explicit_expected_axis_fail_count": 0,
            "reviewer_only_max_wall_seconds": 10.78069,
            "reviewer_only_median_wall_seconds": 8.64255,
            "prompt_tokens": 6876,
            "completion_tokens": 1652,
        },
        "failed_gates": ["valid_retained_count", "explicit_expected_axis_fail_count"],
        "reason_diagnostic_kind": "explicit_expected_axis_fail_and_primary_proxy",
        "component_gate_pass": False,
    }
    for arm, key, reason_key in (
        ("A", "old_contract", "old_category_reason_hit"),
        ("B", "new_contract", "new_category_reason_hit"),
    ):
        metrics = arms[arm]["metrics"]
        calls = [row["calls"][arm] for row in rows]
        assert metrics["completed_parseable_token_count"] == len(calls) == 10
        assert metrics["source_exact_count"] == sum(
            row["reviews"][arm]["source_id"] == row["source"]["id"]
            and row["reviews"][arm]["source_span"] == row["source"]["text"] for row in rows
        )
        assert metrics["valid_retained_count"] == sum(
            row["score"]["arms"][key]["valid_retained"] for row in valid
        )
        assert metrics["invalid_false_action_count"] == sum(
            row["score"]["arms"][key]["false_action"] for row in invalid
        )
        assert metrics[
            "mapped_expected_axis_false_check_count" if arm == "A" else "explicit_expected_axis_fail_count"
        ] == sum(row["score"][reason_key] for row in invalid)
        assert metrics["prompt_tokens"] == sum(call["prompt_tokens"] for call in calls)
        assert metrics["completion_tokens"] == sum(call["completion_tokens"] for call in calls)
        walls = [call["wall_seconds"] for call in calls]
        assert metrics["reviewer_only_max_wall_seconds"] == max(walls) < gates[
            "per_arm_reviewer_only_max_wall_seconds"
        ]
        assert metrics["reviewer_only_median_wall_seconds"] == median(walls)
    assert result["summary"]["paired"] == {
        "B_only_decision_correct_count": 2,
        "A_only_decision_correct_count": 2,
        "B_only_decision_correct_packet_ids": [
            "p4_m46_di_wrong_task_zh_001", "p4_m46_di_private_inference_ja_001",
        ],
        "A_only_decision_correct_packet_ids": [
            "p4_m46_di_valid_en_001", "p4_m46_di_valid_ja_001",
        ],
        "valid_retention_B_only_count": 0,
        "valid_retention_A_only_count": 2,
        "invalid_block_B_only_count": 2,
        "invalid_block_A_only_count": 0,
        "reason_metrics_not_semantically_symmetric": True,
    }


def test_individual_counterexamples_keep_correct_blocks_separate_from_reasons():
    result, _, _ = _frozen_result()
    rows = {row["category"]: row for row in result["rows"]}
    assert {row["category"] for row in result["rows"] if row["score"]["old_category_reason_hit"]} == {
        "unsupported_specificity", "non_action", "actor_surface",
        "invented_prerequisite", "unnatural_surface",
    }
    assert not any(row["score"]["new_category_reason_hit"] for row in result["rows"])

    valid_zh = next(
        row for row in result["rows"] if row["packet_id"] == "p4_m46_di_valid_zh_001"
    )
    assert valid_zh["packet_id"] == "p4_m46_di_valid_zh_001"
    assert valid_zh["score"]["arms"]["old_contract"]["would_deliver"] is False
    assert valid_zh["score"]["arms"]["new_contract"]["would_deliver"] is False
    assert valid_zh["score"]["new_review_audit"]["evidence_anchored"] is False

    wrong_task = rows["wrong_task"]
    private = rows["private_inference"]
    for row, expected_axis in ((wrong_task, "task_alignment"), (private, "private_claim")):
        assert row["expected_failed_axis"] == expected_axis
        assert row["score"]["arms"]["old_contract"]["false_action"] is True
        assert row["score"]["arms"]["new_contract"]["would_deliver"] is False
        assert row["score"]["old_review_audit"]["content_passed"] is True
        assert row["score"]["old_review_audit"]["surface_passed"] is True
        assert row["reviews"]["B"]["checks"][expected_axis] == "pass"
        assert row["score"]["new_review_audit"]["primary_failure"] == "actor_capability"
        assert row["score"]["new_category_reason_hit"] is False

    for packet_id in ("p4_m46_di_valid_en_001", "p4_m46_di_valid_ja_001"):
        row = next(item for item in result["rows"] if item["packet_id"] == packet_id)
        assert row["score"]["arms"]["old_contract"]["valid_retained"] is True
        assert row["score"]["arms"]["new_contract"]["valid_retained"] is False
        assert row["reviews"]["B"]["checks"]["actor_capability"] == "fail"
        assert row["score"]["new_review_audit"]["primary_failure"] == "actor_capability"
    assert rows["actor_surface"]["reviews"]["B"]["checks"]["actor_capability"] == "fail"
    assert rows["actor_surface"]["score"]["new_review_audit"]["schema_passed"] is False
    assert rows["actor_surface"]["score"]["new_review_audit"]["violations"] == [
        "evidence_not_source_or_instruction_anchored"
    ]
    assert rows["unnatural_surface"]["reviews"]["B"]["checks"]["natural_japanese"] == "pass"
