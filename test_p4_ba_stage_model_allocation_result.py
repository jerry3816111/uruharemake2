import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
RESULT = ROOT / "analysis" / "p4_ba_stage_model_allocation_evidence_2026-09-26.json"


def _load():
    return json.loads(RESULT.read_text(encoding="utf-8"))


def _arm(arm_id):
    return next(row for row in _load()["arms"] if row["arm_id"] == arm_id)


def _generation(model, case_id):
    return next(
        row
        for row in _load()["generation"]
        if row["model"] == model and row["case_id"] == case_id
    )


def _fixture(model, case_id):
    return next(
        row
        for row in _load()["review_fixtures"]
        if row["model"] == model and row["case_id"] == case_id
    )


def test_p4_ba_preserves_the_single_no_retry_formal_failure():
    evidence = _load()

    assert evidence["schema"] == "uruha_p4_ba_stage_model_allocation_evidence_v1"
    assert evidence["status"] == "fail"
    assert evidence["executed_exactly_once_per_unique_model_case"] is True
    assert evidence["retry_count"] == 0
    assert evidence["selected_arm"] is None
    assert evidence["product_runtime_changed"] is False
    assert len(evidence["generation"]) == 4
    assert len(evidence["review_fixtures"]) == 8
    assert len(evidence["full_pipeline_reviews"]) == 8
    assert all(row["eligible"] is False for row in evidence["arms"])


def test_p4_ba_all_model_calls_completed_with_parseable_json_and_tokens():
    evidence = _load()
    calls = [row["call"] for key in ("generation", "review_fixtures", "full_pipeline_reviews") for row in evidence[key]]

    assert len(calls) == 20
    assert all(call["attempted"] is True for call in calls)
    assert all(call["completed"] is True for call in calls)
    assert all(call["json_parse_success"] is True for call in calls)
    assert all(call["prompt_tokens"] > 0 for call in calls)
    assert all(call["completion_tokens"] > 0 for call in calls)
    assert all(row["metrics"]["token_accounting_complete"] is True for row in evidence["arms"])


def test_p4_ba_generation_failed_the_frozen_mechanism_gate_for_both_models():
    expected_structural = {"qwen3.5:9b": 1, "qwen3.5:4b": 0}

    for model, structural_count in expected_structural.items():
        rows = [row for row in _load()["generation"] if row["model"] == model]
        assert sum(row["selected_structurally_valid"] for row in rows) == structural_count
        assert sum(row["selected_mechanism_allowed"] for row in rows) == 0
        assert {row["selected_plan"]["progress_mechanism"] for row in rows} == {"group_by_rule"}

    assert _generation("qwen3.5:9b", "p4_ba_gen_zh_cognitive_001")["candidate_state"]["status"] == "no_structurally_valid_candidate"
    assert _generation("qwen3.5:9b", "p4_ba_gen_en_report_001")["selected_structurally_valid"] is True


def test_p4_ba_reviewers_did_not_meet_positive_negative_discrimination():
    evidence = _load()
    rows_9b = [row for row in evidence["review_fixtures"] if row["model"] == "qwen3.5:9b"]
    rows_08b = [row for row in evidence["review_fixtures"] if row["model"] == "qwen3.5:0.8b"]

    assert sum(row["correct"] for row in rows_9b) == 3
    assert sum(row["accepted"] for row in rows_9b) == 1
    assert sum(row["correct"] for row in rows_08b) == 2
    assert sum(row["accepted"] for row in rows_08b) == 0
    assert _fixture("qwen3.5:9b", "p4_ba_review_report_valid_001")["surface_violations"] == ["casual_japanese"]
    assert _fixture("qwen3.5:0.8b", "p4_ba_review_report_valid_001")["correct"] is False
    assert _fixture("qwen3.5:0.8b", "p4_ba_review_sort_valid_001")["correct"] is False


def test_p4_ba_fastest_arm_met_latency_only_and_remained_ineligible():
    arm = _arm("g4_r08")

    assert arm["metrics"]["maximum_two_stage_seconds"] == 16.78266
    assert arm["metrics"]["median_two_stage_seconds"] == 16.53749
    assert "maximum_two_stage_seconds" not in arm["failed_gates"]
    assert arm["failed_gates"] == [
        "generation_structurally_valid_count",
        "generation_allowed_mechanism_count",
        "review_fixture_correct_count",
        "full_pipeline_accepted_count",
    ]
    assert arm["eligible"] is False


def test_p4_ba_full_pipeline_kept_source_language_and_memory_boundaries_but_accepted_nothing():
    evidence = _load()

    assert all(row["accepted"] is False for row in evidence["full_pipeline_reviews"])
    for arm in evidence["arms"]:
        metrics = arm["metrics"]
        assert metrics["full_pipeline_accepted_count"] == 0
        assert metrics["full_pipeline_source_exact_count"] == 2
        assert metrics["full_pipeline_natural_japanese_count"] == 2
        assert metrics["full_pipeline_raw_dialogue_trace_count"] == 0
        assert metrics["full_pipeline_factual_memory_write_count"] == 0


def test_p4_ba_claim_boundary_does_not_overstate_the_negative_benchmark():
    evidence = _load()

    assert "later fresh product integration test" in evidence["claim_boundary"]
    assert "not establish human usefulness" in evidence["claim_boundary"]
    assert "human equation" in evidence["claim_boundary"]
