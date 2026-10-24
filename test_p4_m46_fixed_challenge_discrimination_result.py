"""Immutable outcome checks for the one-shot M46 fixed-challenge study."""

from decimal import Decimal
import hashlib
import json
from pathlib import Path
from statistics import median


ROOT = Path(__file__).resolve().parent
ARTIFACT = ROOT / "analysis/p4_m46_fixed_challenge_discrimination_2026-09-30.json"
CONTRACT = ROOT / "configs/p4_m46_fixed_challenge_discrimination_v1.json"
ARTIFACT_SHA256 = "e7b163957152a9ab05d20094e6d5061d134efa80d47c66274538932faaabedfa"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _frozen_result():
    raw = ARTIFACT.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == ARTIFACT_SHA256
    return json.loads(raw), json.loads(CONTRACT.read_text(encoding="utf-8"))


def test_fixed_challenge_failure_and_prior_generation_failure_are_immutable():
    result, contract = _frozen_result()
    assert result["schema"] == "uruha_p4_m46_fixed_challenge_discrimination_result_v1"
    assert result["status"] == result["summary"]["status"] == "fixed_discrimination_fail"
    assert result["contract_sha256"] == _sha256(CONTRACT)
    assert result["dataset_sha256"] == contract["dataset"]["sha256"]
    assert result["dataset_sha256"] == _sha256(ROOT / contract["dataset"]["path"])
    assert result["runner_sha256"] == _sha256(ROOT / "run_p4_m46_fixed_challenge_discrimination.py")
    assert result["claim_boundary"] == result["summary"]["claim_boundary"] == contract["claim_boundary"]

    prior = contract["prior_inconclusive_result"]
    old_path = ROOT / prior["path"]
    assert result["prior_failure_sha256"] == prior["sha256"] == _sha256(old_path)
    old = json.loads(old_path.read_text(encoding="utf-8"))
    assert old["status"] == prior["status"] == "generation_call_failed_partial_no_resume"
    assert old["review_calls"] == prior["review_calls"] == 0
    assert old["retry_count"] == 0
    assert len(old["rows"]) == 1
    assert old["rows"][0]["batch"] is None
    assert old["rows"][0]["call"]["json_parse_success"] is False
    assert old["rows"][0]["call"]["error_type"] == "JSONDecodeError"


def test_fixed_challenge_rows_preserve_predeclared_gates_and_actual_fail():
    result, contract = _frozen_result()
    gates = contract["preregistered_gates"]
    metrics = result["summary"]["metrics"]
    rows = result["rows"]
    assert [row["packet_id"] for row in rows] == contract["dataset"]["packet_order"]
    assert len(rows) == metrics["packet_count"] == contract["execution"]["challenge_packet_count"] == 9
    assert result["generation_scored_calls"] == contract["execution"]["generation_scored_call_count"] == 0
    assert result["maximum_review_scored_calls"] == contract["execution"]["maximum_review_scored_calls"] == 8
    assert result["retry_count"] == gates["retry_count"] == 0
    assert result["production_database_access"] is False
    assert result["product_runtime_changed"] is False
    assert result["prewarm"]["attempted"] is result["prewarm"]["completed"] is True
    assert result["prewarm"]["model"] == contract["model"]

    eligible = [row for row in rows if row["deterministic_eligible"]]
    assert len(eligible) == gates["deterministic_eligible_packet_count"] == 8
    assert metrics["selector_parity_all_packets"] is gates["selector_parity_all_packets"] is True
    assert metrics["source_and_selected_plan_identity_both_arms"] is gates[
        "source_and_selected_plan_identity_both_arms"
    ] is True
    for row in rows:
        score = row["score"]
        source = row["source"]
        selected = score["selected_plan"]
        assert score["selection_guard_parity"] is True
        assert score["selected_index"] == score["m53_aware_selected_index"] == 0
        assert score["source_id"] == selected["goal_source_id"] == source["id"]
        assert selected["goal_source_span"] == source["text"]
        assert row["selected_plan_digest_before_review"] == score["selected_plan_digest"]
        assert row["selected_fingerprint_before_review"] == score["selected_fingerprint"]
        assert score["model_calls_by_scorer"] == 0
        assert score["product_runtime_changed"] is False

    for row in eligible:
        call = row["review_call"]
        assert row["review_call_started"] is True
        assert call["call_id"] == f'review:{row["packet_id"]}'
        assert call["stage"] == "review"
        assert call["model"] == contract["model"]
        assert call["attempted"] is call["completed"] is call["json_parse_success"] is True
        assert call["prompt_tokens"] > 0
        assert 0 < call["completion_tokens"] <= contract["controlled_constants"]["num_predict"]
        for option in ("temperature", "seed", "num_ctx", "num_predict"):
            assert call["options"][option] == contract["controlled_constants"][option]
        assert row["review"]["source_id"] == row["source"]["id"]
        assert row["review"]["source_span"] == row["source"]["text"]
        assert row["score"]["m39_final_byte_identical"] is True
        assert row["score"]["m39_surface_trace"]["action"] == "accept"

    guard = rows[-1]
    assert guard["category"] == "guard_block"
    assert guard["review_call_started"] is False
    assert guard["review_call"] is None
    assert "review" not in guard
    assert guard["score"]["arms"]["A_model_review"]["would_deliver"] is False
    assert guard["score"]["arms"]["B_deterministic_only"]["would_deliver"] is False
    assert metrics["guard_control_both_arms_blocked_count"] == gates[
        "guard_control_both_arms_blocked_count"
    ] == 1

    valid = [row for row in eligible if row["gold_label"] == "valid"]
    invalid = [row for row in eligible if row["gold_label"] == "invalid"]
    assert len(valid) == gates["valid_packet_count"] == 3
    assert len(invalid) == gates["semantic_or_surface_invalid_packet_count"] == 5
    assert (sum(row["score"]["arms"]["A_model_review"]["valid_retained"] for row in valid)
            == metrics["A_valid_retained_count"] == 1)
    assert (sum(row["score"]["arms"]["A_model_review"]["false_action"] for row in invalid)
            == metrics["A_invalid_false_action_count"] == gates["A_invalid_false_action_count"] == 0)
    assert (sum(row["score"]["arms"]["B_deterministic_only"]["valid_retained"] for row in valid)
            == metrics["B_valid_retained_count"] == gates["B_valid_retained_count_preflight"] == 3)
    assert (sum(row["score"]["arms"]["B_deterministic_only"]["false_action"] for row in invalid)
            == metrics["B_invalid_false_action_count"] == gates["B_invalid_false_action_count_preflight"] == 5)

    relevant_checks = contract["invalid_category_relevant_false_checks"]
    assert {row["category"] for row in invalid} == set(relevant_checks)
    for row in invalid:
        relevant_false = any(
            row["review"][group][check] is False
            for group, check in (path.split(".") for path in relevant_checks[row["category"]])
        )
        assert row["category_relevant_false_check"] is relevant_false
    assert (sum(row["category_relevant_false_check"] for row in invalid)
            == metrics["A_category_relevant_false_check_count"] == 4)
    surface = next(row for row in invalid if row["category"] == "surface")
    assert surface["category_relevant_false_check"] is False
    assert surface["review"]["surface_checks"]["no_identity_or_role_error"] is True
    assert gates["A_valid_retained_count"] == 3
    assert gates["A_category_relevant_false_check_count"] == 5
    assert metrics["review_scored_call_count"] == 8
    assert metrics["review_completed_json_and_tokens_count"] == gates[
        "A_review_completed_json_and_tokens_count"
    ] == 8
    assert metrics["review_source_identity_exact_count"] == gates[
        "A_review_source_identity_exact_count"
    ] == 8
    assert metrics["natural_japanese_and_m39_exact_count"] == gates[
        "natural_japanese_and_m39_exact_count"
    ] == 8
    assert result["summary"]["failed_quality_gates"] == [
        "A_valid_retained_count", "A_category_relevant_false_check_count"
    ]
    assert result["summary"]["A_fixed_quality_pass"] is False
    assert result["summary"]["B_product_bypass_authorized"] is gates["B_product_bypass_authorized"] is False
    assert result["summary"]["product_qualified"] is False


def test_reviewer_only_token_and_wall_accounting_does_not_claim_product_pass():
    result, contract = _frozen_result()
    metrics = result["summary"]["metrics"]
    calls = [row["review_call"] for row in result["rows"] if row["review_call_started"]]
    walls = [Decimal(str(call["wall_seconds"])) for call in calls]
    assert len(calls) == 8
    assert sum(call["prompt_tokens"] for call in calls) == metrics["review_prompt_tokens"] == 6568
    assert sum(call["completion_tokens"] for call in calls) == metrics["review_completion_tokens"] == 2304
    assert sum(walls) == Decimal("105.20729")
    assert max(walls) == Decimal(str(metrics["reviewer_only_max_wall_seconds"])) == Decimal("14.4233")
    assert median(walls) == Decimal(str(metrics["reviewer_only_median_wall_seconds"])) == Decimal(
        "13.210155"
    )
    assert Decimal(str(result["prewarm"]["wall_seconds"])) == Decimal("4.08774")
    assert result["summary"]["A_reviewer_only_within_20_seconds"] is True
    assert max(walls) < contract["latency_interpretation"]["product_two_stage_budget_seconds"]
    assert result["summary"]["product_qualified"] is False
