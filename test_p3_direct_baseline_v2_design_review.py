from __future__ import annotations

import json
from pathlib import Path

import pytest

import p3_direct_baseline_v2_design_review as review_module
from p3_direct_baseline_v2_design_review import build_acceptance, load_review
from p3_product_comparison import P3ContractError, shared_visible_surface_contract


ROOT = Path(__file__).resolve().parent
REVIEW = ROOT / "configs/p3_direct_baseline_v2_design_review_v1.json"


def test_review_retires_failed_deliberate_without_changing_v1():
    review = load_review(REVIEW)

    assert review["decision"]["comparison_v1_immutable"] is True
    assert review["decision"]["retire_from_v2"] == ["full_history_deliberate"]
    assert review["v2_conditions"] == ["full_history_direct", "product_system"]
    assert review["direct_baseline"]["instruction"] != review["_design"]["baselines"][
        "direct_instruction"
    ]
    assert "自然な日本語" in review["direct_baseline"]["instruction"]
    assert all(shared_visible_surface_contract(review["_direct_candidate_text"]).values())


def test_review_preserves_fair_resource_and_data_boundary():
    review = load_review(REVIEW)

    assert review["generation"]["aggregate_completion_tokens_max_per_condition"] == 768
    assert review["direct_baseline"]["completion_tokens_max"] == 768
    assert review["fairness"]["same_raw_visible_history"] is True
    assert review["fairness"]["same_shared_persona_contract"] is True
    assert review["fairness"]["actual_prompt_completion_tokens_and_latency_reported_separately"] is True
    assert review["direct_baseline"]["private_product_state"] is False
    assert review["execution_boundary"]["real_model_calls_authorized_by_this_review"] is False


def test_review_selects_unexecuted_case_three_first_turn_without_annotation_access():
    review = load_review(REVIEW)

    assert review["next_canary"]["case_id"] == "p3-smoke-emotional-bid-ja"
    assert review["next_canary"]["turn_id"] == "p3-smoke-03-u1"
    assert review["next_canary"]["future_turn_access_during_canary"] is False
    assert review["next_canary"]["annotation_access_before_all_case_outputs_locked"] is False


def test_review_rejects_attempt_to_keep_failed_deliberate(tmp_path, monkeypatch):
    raw = json.loads(REVIEW.read_text(encoding="utf-8"))
    raw["v2_conditions"].insert(1, "full_history_deliberate")
    path = tmp_path / "configs" / REVIEW.name
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps(raw, ensure_ascii=False), encoding="utf-8")
    monkeypatch.setattr(
        review_module,
        "_ref",
        lambda _repo, _value, expected, _code: ROOT / expected["path"],
    )

    with pytest.raises(P3ContractError) as error:
        load_review(path)

    assert error.value.code == "p3_b14_condition_mismatch"


def test_review_acceptance_is_zero_call_and_ready_for_implementation():
    result = build_acceptance(REVIEW)

    assert result["status"] == "ready_for_direct_v2_canary_implementation"
    assert result["real_model_calls"] == result["network_calls"] == 0
    assert result["annotations_accessed"] == result["confirmation_accessed"] == 0
    assert result["production_database_accessed"] is False
    assert all(result["checks"].values())
