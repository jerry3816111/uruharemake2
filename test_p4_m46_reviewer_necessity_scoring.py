"""Pure fake-packet M46 ablation scoring tests; no generator or reviewer calls."""

from copy import deepcopy

import pytest

import p4_m46_reviewer_necessity_scoring as scoring
import uruha_actionable_help_delivery_m45 as m45
import uruha_goal_progress_delivery_m46 as m46
import uruha_state_changing_candidates_m51 as m51


SOURCE = {
    "id": "current:4", "kind": "current_user",
    "text": "机に赤い紙と青い紙が混ざってる。色ごとに分ける手順を一つだけ教えて。",
}


def _batch(*, unsupported_label=False, wrong_task=False, source_span=None):
    obj = "「重要」な紙" if unsupported_label else "赤い紙と青い紙"
    instruction = (
        "まず、「重要」な紙を左に置いて、一枚置いたら止めよ。" if unsupported_label
        else "まず、赤い紙と青い紙を大きさ順に置いて、全部置いたら止めよ。" if wrong_task
        else "まず、赤い紙と青い紙を赤は左、青は右に置いて、全部置いたら止めよ。"
    )
    candidate = {
        "mechanism": "group_by_rule", "object": obj, "verb": "置く",
        "effect": "紙が左右の二群になる", "stop": "全部置いたら止める",
        "instruction": instruction,
    }
    second = {
        "mechanism": "same_task_smaller_unit", "object": "紙", "verb": "分ける",
        "effect": "紙が分かれる", "stop": "分けたら止める",
        "instruction": "まず、紙を分けて、一枚分けたら止めよ。",
    }
    return {
        "sid": SOURCE["id"], "span": SOURCE["text"] if source_span is None else source_span,
        "goal": "紙を色ごとに分ける", "unknown": "紙の枚数は不明",
        "items": [candidate, second],
    }


def _fake_review(*, source_id=None, content_fail=None):
    content = {key: True for key in m46.CONTENT_CHECKS}
    if content_fail:
        content[content_fail] = False
    return {
        "source_id": SOURCE["id"] if source_id is None else source_id,
        "source_span": SOURCE["text"],
        "counterfactual_before_jp": "赤と青の紙が混ざっている",
        "counterfactual_after_jp": "紙が左右の二群に分かれている",
        "observed_progress_mechanism": "group_by_rule",
        "content_checks": content,
        "surface_checks": {key: True for key in m46.SURFACE_CHECKS},
    }


def test_wrong_task_passes_shared_structure_but_fake_review_rejects_semantics():
    result = scoring.score_packet(SOURCE, _batch(wrong_task=True),
                                  _fake_review(content_fail="goal_matches_source"), False)
    assert result["guard_violations"] == []
    assert result["selection_guard_parity"] is True
    assert result["arms"]["B_deterministic_only"]["would_deliver"] is True
    assert result["arms"]["B_deterministic_only"]["false_action"] is True
    assert result["arms"]["B_deterministic_only"]["valid_retained"] is False
    assert result["arms"]["A_model_review"]["would_deliver"] is False
    assert "goal_matches_source" in result["review_audit"]["content_violations"]
    assert result["selected_plan_digest"] == m45.digest(result["selected_plan"])


def test_guard_blocks_unsupported_label_in_both_arms():
    result = scoring.score_packet(SOURCE, _batch(unsupported_label=True), _fake_review(), False)
    assert "unsupported_concrete_scaffold_label_m53" in result["guard_violations"]
    assert result["label_authorization"]["unsupported_count"] == 1
    assert result["arms"]["A_model_review"]["would_deliver"] is False
    assert result["arms"]["B_deterministic_only"]["would_deliver"] is False


def test_m53_aware_selection_difference_fails_closed_instead_of_switching_plan():
    batch = _batch(unsupported_label=True)
    batch["items"][1] = deepcopy(_batch()["items"][0])
    result = scoring.score_packet(SOURCE, batch, _fake_review(), True)
    assert result["selected_index"] == 0
    assert result["m53_aware_selected_index"] == 1
    assert result["selection_guard_parity"] is False
    assert "selection_guard_parity_mismatch" in result["guard_violations"]
    assert result["arms"]["A_model_review"]["would_deliver"] is False
    assert result["arms"]["B_deterministic_only"]["would_deliver"] is False


def test_p4_av_neutral_operational_role_remains_guard_eligible():
    batch = _batch()
    batch["items"][0].update(
        mechanism="structure_scaffold", object="「今扱う項目」", verb="書く",
        effect="項目が一つ書かれる",
        instruction="まず、「今扱う項目」を一つ書いて、そこで止めよ。",
    )
    result = scoring.score_packet(SOURCE, batch, None, False)
    assert result["label_authorization"]["unsupported_count"] == 0
    assert result["label_authorization"]["neutral_role_count"] == 1
    assert result["guard_violations"] == []
    assert result["arms"]["B_deterministic_only"]["false_action"] is True


def test_exact_source_mismatch_blocks_both_arms_even_with_all_true_fake_review():
    result = scoring.score_packet(SOURCE, _batch(source_span="別の原文"), _fake_review(), False)
    assert "invalid_exact_goal_source" in result["guard_violations"]
    assert result["arms"]["A_model_review"]["would_deliver"] is False
    assert result["arms"]["B_deterministic_only"]["would_deliver"] is False


def test_missing_review_cannot_count_as_a_pass_and_identical_plan_is_shared():
    result = scoring.score_packet(SOURCE, _batch(), None, True)
    assert result["deterministic_eligible"] is True
    assert result["review_supplied"] is False
    assert result["review_audit"] is None
    assert result["arms"]["A_model_review"]["valid_retained"] is False
    assert result["arms"]["B_deterministic_only"]["valid_retained"] is True
    assert "selected_plan" in result and "selected_fingerprint" in result
    assert result["model_calls_by_scorer"] == 0


def test_synthetic_all_true_review_only_checks_contract_wiring_not_model_quality():
    result = scoring.score_packet(SOURCE, _batch(), _fake_review(), True)
    assert result["arms"]["A_model_review"]["valid_retained"] is True
    assert result["arms"]["B_deterministic_only"]["valid_retained"] is True
    assert result["arms"]["A_model_review"]["false_action"] is False


def test_m39_repair_blocks_both_arms_even_when_reviewer_fixture_accepts():
    batch = _batch()
    batch["items"][0]["instruction"] = (
        "まず、朝から赤い紙と青い紙を赤は左、青は右に置いて、全部置いたら止めよ。"
    )
    result = scoring.score_packet(SOURCE, batch, _fake_review(), "invalid")
    assert "m39_surface_not_exactly_accepted" in result["guard_violations"]
    assert result["m39_surface_trace"]["action"] == "repair"
    assert result["m39_final_byte_identical"] is False
    assert result["arms"]["A_model_review"]["would_deliver"] is False
    assert result["arms"]["B_deterministic_only"]["would_deliver"] is False


def test_uncertain_label_is_risk_not_valid_retention():
    result = scoring.score_packet(SOURCE, _batch(), _fake_review(), "uncertain")
    assert result["guard_violations"] == []
    assert result["gold_label"] == "uncertain"
    for arm in result["arms"].values():
        assert arm["would_deliver"] is True
        assert arm["false_action"] is True
        assert arm["uncertain_action_risk"] is True
        assert arm["valid_retention_denominator"] is False
        assert arm["valid_retained"] is False


def test_scorer_does_not_mutate_packet_or_call_model(monkeypatch):
    def forbidden(*_args, **_kwargs):
        pytest.fail("model transport called by pure offline scorer")

    monkeypatch.setattr(m45, "_native_json", forbidden)
    monkeypatch.setattr(m51, "_native_candidates", forbidden)
    source, batch, review = deepcopy(SOURCE), _batch(), _fake_review()
    before = deepcopy((source, batch, review))
    result = scoring.score_packet(source, batch, review, True)
    assert (source, batch, review) == before
    assert result["model_calls_by_scorer"] == 0


def test_non_boolean_gold_and_non_dict_review_are_not_silently_coerced():
    with pytest.raises(TypeError, match="independent string label"):
        scoring.score_packet(SOURCE, _batch(), None, 1)
    with pytest.raises(ValueError, match="valid, invalid, or uncertain"):
        scoring.score_packet(SOURCE, _batch(), None, "maybe")
    with pytest.raises(TypeError, match="review must"):
        scoring.score_packet(SOURCE, _batch(), "accepted", True)
