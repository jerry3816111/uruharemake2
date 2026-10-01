from copy import deepcopy

import run_p4_ba_stage_model_allocation as m


CONTRACT = {
    "formal_gates": {
        "generation_json_parse_success_count": 2,
        "generation_structurally_valid_count": 2,
        "generation_allowed_mechanism_count": 2,
        "review_fixture_correct_count": 4,
        "full_pipeline_accepted_count": 2,
        "full_pipeline_source_exact_count": 2,
        "full_pipeline_natural_japanese_count": 2,
        "full_pipeline_raw_dialogue_trace_count": 0,
        "full_pipeline_factual_memory_write_count": 0,
        "maximum_two_stage_seconds": 20,
        "token_accounting_complete": True,
    },
    "arms": [
        {"arm_id": "a", "generator": "g", "reviewer": "r"},
        {"arm_id": "b", "generator": "g", "reviewer": "bad"},
    ],
}


def _call(seconds=2):
    return {
        "completed": True,
        "json_parse_success": True,
        "wall_seconds": seconds,
        "prompt_tokens": 10,
        "completion_tokens": 5,
    }


def test_arm_summary_requires_every_quality_cost_and_accounting_gate():
    generation = [
        {
            "case_id": case,
            "model": "g",
            "call": _call(3),
            "selected_structurally_valid": True,
            "selected_mechanism_allowed": True,
        }
        for case in ("c1", "c2")
    ]
    fixtures = [
        {"case_id": f"f{i}", "model": reviewer, "call": _call(),
         "correct": reviewer == "r", "accepted": i < 2}
        for reviewer in ("r", "bad")
        for i in range(4)
    ]
    full = [
        {"case_id": case, "generator_model": "g", "model": reviewer,
         "call": _call(4), "accepted": reviewer == "r",
         "source_exact": True, "natural_japanese": True}
        for reviewer in ("r", "bad")
        for case in ("c1", "c2")
    ]

    rows = m.summarize_arms(CONTRACT, generation, fixtures, full)

    assert rows[0]["eligible"] is True
    assert rows[0]["metrics"]["maximum_two_stage_seconds"] == 7
    assert rows[1]["eligible"] is False
    assert "review_fixture_correct_count" in rows[1]["failed_gates"]
    assert "full_pipeline_accepted_count" in rows[1]["failed_gates"]


def test_timeout_and_incomplete_tokens_cannot_be_hidden_by_other_counts():
    generation = [
        {
            "case_id": case,
            "model": "g",
            "call": _call(3),
            "selected_structurally_valid": True,
            "selected_mechanism_allowed": True,
        }
        for case in ("c1", "c2")
    ]
    generation[1]["call"] = {
        "completed": False,
        "json_parse_success": False,
        "wall_seconds": 45,
        "error_type": "TimeoutError",
    }
    fixtures = [
        {"case_id": f"f{i}", "model": "r", "call": _call(),
         "correct": True, "accepted": i < 2}
        for i in range(4)
    ]
    full = [
        {"case_id": "c1", "generator_model": "g", "model": "r",
         "call": _call(4), "accepted": True, "source_exact": True,
         "natural_japanese": True}
    ]

    row = m.summarize_arms({**deepcopy(CONTRACT), "arms": [CONTRACT["arms"][0]]},
                           generation, fixtures, full)[0]

    assert row["eligible"] is False
    assert "generation_json_parse_success_count" in row["failed_gates"]
    assert "full_pipeline_accepted_count" in row["failed_gates"]
    assert "token_accounting_complete" in row["failed_gates"]
