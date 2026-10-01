"""Immutable checks for the one completed P4-BE paired run; no model calls."""

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
RESULT = ROOT / "analysis/p4_be_role_value_prompt_evidence_2026-09-29.json"
CONTRACT = ROOT / "configs/p4_be_role_value_prompt_v1.json"
DATASET = ROOT / "datasets/p4_be_role_value_prompt_v1.json"
RUNNER = ROOT / "run_p4_be_role_value_prompt.py"


def _load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def _arm(evidence, name):
    return next(item for item in evidence["arms"] if item["arm"] == name)


def _row(evidence, arm, case_id):
    return next(
        item for item in evidence["rows"]
        if item["arm"] == arm and item["case_id"] == case_id
    )


def test_p4_be_formal_result_is_bound_to_frozen_inputs_and_one_shot_schedule():
    evidence = _load(RESULT)
    contract = _load(CONTRACT)
    dataset = _load(DATASET)
    cases = dataset["positive_cases"] + dataset["control_cases"]
    rows = evidence["rows"]
    calls = [row["call"] for row in rows]

    assert evidence["schema"] == "uruha_p4_be_role_value_prompt_evidence_v1"
    assert evidence["freeze_sha"] == "90b4c4af2583f37a43997f9662485e81584fae04"
    assert evidence["runner_sha256"] == hashlib.sha256(RUNNER.read_bytes()).hexdigest()
    assert evidence["contract"] == {
        "path": "configs/p4_be_role_value_prompt_v1.json",
        "sha256": hashlib.sha256(CONTRACT.read_bytes()).hexdigest(),
    }
    assert evidence["dataset_sha256"] == hashlib.sha256(DATASET.read_bytes()).hexdigest()
    assert evidence["prompt_sha256_by_arm"] == {
        "bc_frozen_prompt": contract["baseline_prompt"]["sha256"],
        "be_role_value_prompt": contract["intervention_prompt"]["sha256"],
    }
    assert contract["model"] == "qwen3.5:9b"
    assert contract["model_digest"] == "6488c96fa5faab64bb65cbd30d4289e20e6130ef535a93ef9a49f42eda893ea7"
    assert evidence["executed_exactly_once_per_arm_case"] is True
    assert evidence["retry_count"] == 0
    assert len(evidence["prewarm"]) == 1
    assert evidence["prewarm"][0]["model"] == contract["model"]
    assert evidence["prewarm"][0]["completed"] is True
    assert len(rows) == len(calls) == contract["execution"]["max_scored_calls"] == 28
    assert len({call["call_id"] for call in calls}) == 28
    assert all(call["attempted"] and call["completed"] and call["json_parse_success"] for call in calls)
    assert all(call["prompt_tokens"] > 0 and call["completion_tokens"] > 0 for call in calls)
    assert all(row["source_identity_valid"] for row in rows)

    for index, case in enumerate(cases):
        pair = rows[index * 2:index * 2 + 2]
        order = contract["arms"] if index % 2 == 0 else list(reversed(contract["arms"]))
        assert [row["arm"] for row in pair] == order
        assert [row["case_id"] for row in pair] == [case["case_id"]] * 2
        assert [row["case_order_index"] for row in pair] == [index, index]
        assert [row["arm_order_index"] for row in pair] == [0, 1]
        assert pair[0]["call"]["schema_sha256"] == pair[1]["call"]["schema_sha256"]
        assert pair[0]["call"]["payload_digest"] == pair[1]["call"]["payload_digest"]
        for row in pair:
            assert row["model"] == contract["model"]
            assert row["call"]["system_sha256"] == evidence["prompt_sha256_by_arm"][row["arm"]]
            assert row["call"]["call_id"] == f"{row['kind']}:{row['arm']}:{case['case_id']}"


def test_p4_be_paired_advantage_passes_but_both_absolute_arms_fail():
    evidence = _load(RESULT)
    baseline = _arm(evidence, "bc_frozen_prompt")
    candidate = _arm(evidence, "be_role_value_prompt")
    comparison = evidence["comparison"]

    assert evidence["status"] == "fail"
    assert evidence["selected_prompt"] is None
    assert evidence["next_state_if_failed"] == "REVIEW_REQUIRED"
    assert evidence["product_runtime_changed"] is False
    assert baseline["absolute_eligible"] is False
    assert candidate["absolute_eligible"] is False
    assert comparison["paired_advantage"] is True
    assert comparison["failed_paired_gates"] == []
    assert comparison["metrics"] == {
        "bc_and_be_all_calls_completed_and_json_parseable": True,
        "be_only_full_accept": 1,
        "bc_only_full_accept": 0,
        "both_full_accept": 0,
        "both_full_fail": 5,
        "be_only_raw_role_value_evidence_with_both_source_identities_valid": 1,
    }
    assert len(comparison["pairs"]) == 6
    assert all(pair["both_source_identities_valid"] for pair in comparison["pairs"])
    assert [pair["case_id"] for pair in comparison["pairs"] if pair["be_only_raw_role_value_uplift"]] == [
        "p4_be_zh_scaffold_001"
    ]

    bc = baseline["metrics"]
    be = candidate["metrics"]
    assert bc["positive_full_accept_count"] == 0
    assert be["positive_full_accept_count"] == 1
    assert (bc["positive_role_value_evidence_count"], be["positive_role_value_evidence_count"]) == (1, 2)
    assert (bc["positive_accepted_atom_count"], be["positive_accepted_atom_count"]) == (12, 11)
    assert (bc["raw_accepted_atom_count"], be["raw_accepted_atom_count"]) == (12, 13)
    assert (bc["positive_slots_exact_count"], be["positive_slots_exact_count"]) == (4, 3)
    assert (bc["positive_downstream_compiled_count"], be["positive_downstream_compiled_count"]) == (6, 3)
    assert (bc["positive_typed_spec_count"], be["positive_typed_spec_count"]) == (6, 5)
    assert (bc["positive_non_span_exact_count"], be["positive_non_span_exact_count"]) == (4, 3)
    assert be["positive_role_value_packet_count"] == 1
    assert be["positive_template_exact_count"] == 5
    assert be["positive_natural_japanese_count"] == 3
    assert "positive_full_accept_count" in candidate["failed_absolute_gates"]
    assert "positive_role_value_evidence_count" in candidate["failed_absolute_gates"]
    assert "positive_slots_exact_count" in candidate["failed_absolute_gates"]
    assert "positive_downstream_compiled_count" in candidate["failed_absolute_gates"]


def test_p4_be_formal_counterexamples_keep_role_slot_and_source_failures_distinct():
    evidence = _load(RESULT)
    baseline = _row(evidence, "bc_frozen_prompt", "p4_be_zh_scaffold_001")
    improved = _row(evidence, "be_role_value_prompt", "p4_be_zh_scaffold_001")
    assert baseline["raw_model_output"]["evidence_atoms"][2] == {"role": "request", "text": "小步驟"}
    assert baseline["role_value_per_role"]["request"]["accepted"] is False
    assert baseline["full_accept"] is False
    assert improved["raw_model_output"]["evidence_atoms"][2] == {
        "role": "request", "text": "請只給我一個現在能開始的小步驟"
    }
    assert improved["role_value_packet_exact"] is True
    assert improved["full_accept"] is True

    wrong_slots = _row(evidence, "be_role_value_prompt", "p4_be_zh_group_001")
    assert wrong_slots["role_value_evidence"] is True
    assert wrong_slots["accepted_atom_count"] == 3
    assert wrong_slots["raw_model_output"]["slots"]["left_label_jp"] == "公司名あり"
    assert wrong_slots["slots_exact"] is False
    assert wrong_slots["downstream_compiled"] is False
    assert wrong_slots["full_accept"] is False

    missing_slot = _row(evidence, "be_role_value_prompt", "p4_be_en_extract_001")
    assert missing_slot["raw_model_output"]["slots"]["unknown_constraint_jp"] == ""
    assert missing_slot["normalization"] == {"status": "invalid", "reason": "typed_spec_contract_mismatch"}
    assert missing_slot["raw_model_output"]["evidence_atoms"][2] == {"role": "completion", "text": "then stop"}
    assert missing_slot["typed_spec"] is False
    assert missing_slot["role_value_packet_exact"] is False

    translated_or_synthetic = _row(evidence, "be_role_value_prompt", "p4_be_en_verify_001")
    assert translated_or_synthetic["raw_model_output"]["evidence_atoms"][2] == {
        "role": "limit", "text": "check once ... then stop"
    }
    assert translated_or_synthetic["role_value_per_role"]["limit"]["source_exact"] is False
    assert translated_or_synthetic["downstream_compiled"] is False
    assert translated_or_synthetic["full_accept"] is False

    wrong_completion = _row(evidence, "be_role_value_prompt", "p4_be_ja_atomic_001")
    assert wrong_completion["raw_model_output"]["evidence_atoms"][2] == {
        "role": "limit", "text": "最初の一手を教えて"
    }
    assert wrong_completion["role_value_per_role"]["limit"]["accepted"] is False
    assert wrong_completion["full_accept"] is False


def test_p4_be_controls_and_cost_do_not_override_failed_positive_gates():
    evidence = _load(RESULT)
    calls = [row["call"] for row in evidence["rows"]]
    baseline = _arm(evidence, "bc_frozen_prompt")["metrics"]
    candidate = _arm(evidence, "be_role_value_prompt")["metrics"]

    for metrics in (baseline, candidate):
        assert metrics["case_count"] == metrics["json_parse_success_count"] == 14
        assert metrics["control_unavailable_count"] == metrics["control_reason_exact_count"] == 8
        assert metrics["control_false_spec_count"] == metrics["assistant_or_private_source_count"] == 0
        assert metrics["token_accounting_complete"] is True
        assert metrics["maximum_call_seconds"] < 20
        assert metrics["strict_exact_spec_count"] == metrics["strict_evidence_exact_count"] == 0
    assert (baseline["maximum_call_seconds"], candidate["maximum_call_seconds"]) == (15.32578, 16.079)
    assert (baseline["median_call_seconds"], candidate["median_call_seconds"]) == (10.11207, 10.47381)
    assert (baseline["prompt_tokens"], candidate["prompt_tokens"]) == (12811, 16843)
    assert (baseline["completion_tokens"], candidate["completion_tokens"]) == (3732, 3749)
    assert sum(call["prompt_tokens"] for call in calls) == 29654
    assert sum(call["completion_tokens"] for call in calls) == 7481
    assert round(sum(call["wall_seconds"] for call in calls), 5) == 328.1185
    assert evidence["prewarm"][0]["wall_seconds"] == 4.08504
    assert "developer-authored bounded-action positives" in evidence["claim_boundary"]
    assert "full-runtime or Safari performance" in evidence["claim_boundary"]
