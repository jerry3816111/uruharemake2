"""Offline fake-contract tests for the prospective M46 decision interface.

Fixtures are deliberately synthetic reviewer outputs.  They test contract and
scoring behavior only; no model is called and no model quality is inferred.
"""

from copy import deepcopy
import json
from pathlib import Path

import pytest

import p4_m46_decision_interface_scoring as scoring
import p4_m46_reviewer_necessity_scoring as legacy
import uruha_actionable_help_delivery_m45 as m45
import uruha_candidate_realization_m52 as m52
import uruha_goal_progress_delivery_m46 as m46
import uruha_state_changing_candidates_m51 as m51


DATASET = json.loads(
    (Path(__file__).resolve().parent / "datasets/p4_m46_decision_interface_v1.json")
    .read_text(encoding="utf-8")
)
PACKETS = {row["category"]: row for row in DATASET["challenge_packets"]}
INVALID_AXIS = {
    "wrong_task": "task_alignment",
    "unsupported_specificity": "source_grounding",
    "private_inference": "private_claim",
    "non_action": "state_change",
    "actor_surface": "actor_capability",
    "invented_prerequisite": "prerequisites",
    "unnatural_surface": "natural_japanese",
}
OLD_REASON_FIELD = {
    "task_alignment": "content_checks.goal_matches_source",
    "source_grounding": "content_checks.no_invented_facts",
    "private_claim": "content_checks.goal_matches_source",
    "state_change": "content_checks.action_changes_task_state",
    "actor_capability": "surface_checks.no_identity_or_role_error",
    "prerequisites": "content_checks.no_unknown_prerequisites",
    "natural_japanese": "surface_checks.casual_japanese",
}
ANCHORED_REASON = {
    "wrong_task": "「要約原稿」は依頼された質問一覧と違う。",
    "unsupported_specificity": "「一日八キロワット時」は原文にない数値だよ。",
    "private_inference": "「不安を減らすために」は本人が述べていない。",
    "non_action": "「考えてみて」だけでは資料が変わらない。",
    "actor_surface": "「うちが閉じておく」は操作権限がないよ。",
    "invented_prerequisite": "「専用アプリにログイン」は必要だと示されていない。",
    "unnatural_surface": "「引く行為を実行せよ」は硬い命令だよ。",
}


def _selected_plan(packet):
    plan, _ = m52.select_candidate_batch_m52(
        deepcopy(packet["batch"]), [deepcopy(packet["source"])]
    )
    return plan


def _old_review(packet, plan, *, failed_field=None, mechanism=None):
    review = {
        "source_id": packet["source"]["id"],
        "source_span": packet["source"]["text"],
        "counterfactual_before_jp": "作業はまだ始まっていない。",
        "counterfactual_after_jp": "作業を一つ進めた状態。",
        "observed_progress_mechanism": mechanism or plan["progress_mechanism"],
        "content_checks": {key: True for key in m46.CONTENT_CHECKS},
        "surface_checks": {key: True for key in m46.SURFACE_CHECKS},
    }
    if failed_field:
        group, key = failed_field.split(".")
        review[group][key] = False
    return review


def _new_review(packet, plan, *, failed_axis=None, value="fail", mechanism=None):
    review = {
        "source_id": packet["source"]["id"],
        "source_span": packet["source"]["text"],
        "before_jp": "作業はまだ始まっていない。",
        "after_jp": "作業を一つ進めた状態。",
        "observed_progress_mechanism": mechanism or plan["progress_mechanism"],
        "checks": {axis: "pass" for axis in scoring.AXES},
        "primary_failure": failed_axis or "none",
        "evidence_jp": ANCHORED_REASON.get(
            packet["category"], "「まず」の動作を確認した。"
        ),
    }
    if failed_axis:
        review["checks"][failed_axis] = value
    return review


def _score(packet, old_review=None, new_review=None, *, gold_label=None, axis=None):
    gold = packet["gold"]
    return scoring.score_packet(
        packet["source"], packet["batch"], old_review, new_review,
        gold["label"] if gold_label is None else gold_label,
        gold["expected_failed_axis"] if axis is None else axis,
    )


def test_source_exact_schema_and_payload_hide_gold_and_plan_mechanism():
    packet = PACKETS["valid"]
    source, plan = packet["source"], _selected_plan(packet)
    schema = scoring.decision_review_schema(source, plan)
    assert schema["properties"]["source_id"] == {"type": "string", "enum": [source["id"]]}
    assert schema["properties"]["source_span"] == {"type": "string", "enum": [source["text"]]}
    assert schema["additionalProperties"] is False
    assert schema["properties"]["checks"]["additionalProperties"] is False
    assert set(schema["required"]) == set(scoring.REVIEW_FIELDS)
    assert set(schema["properties"]["checks"]["required"]) == set(scoring.AXES)
    assert schema["properties"]["checks"]["properties"]["actor_capability"]["enum"] == [
        "pass", "fail", "uncertain"
    ]

    payload = scoring.decision_review_payload(source, plan)
    assert payload["sources"] == [source]
    assert payload["plan"] == {key: value for key, value in plan.items()
                               if key != "progress_mechanism"}
    assert "progress_mechanism" not in payload["plan"]
    assert payload["planned_payload_digest"] == m45.digest({"sources": [source], "plan": plan})
    assert "gold" not in payload and "category" not in payload
    assert "expected_failed_axis" not in json.dumps(payload, ensure_ascii=False)
    assert plan["progress_mechanism"] == _selected_plan(packet)["progress_mechanism"]

    wrong_plan = deepcopy(plan)
    wrong_plan["goal_source_span"] = "別の原文"
    with pytest.raises(ValueError, match="Plan source is not an allowed user source"):
        scoring.decision_review_schema(source, wrong_plan)
    with pytest.raises(ValueError, match="Plan source is not an allowed user source"):
        scoring.decision_review_payload(source, wrong_plan)


def test_dataset_preflight_and_common_deterministic_selection_for_all_packets():
    rows = DATASET["challenge_packets"]
    assert len(rows) == 11
    assert sum(row["gold"]["label"] == "valid" for row in rows) == 3
    assert sum(row["gold"]["label"] == "invalid" for row in rows) == 8
    assert len(INVALID_AXIS) == 7
    assert set(PACKETS) == {"valid", *INVALID_AXIS, "guard_control"}
    assert DATASET["scored_packet_count"] == 10
    assert DATASET["guard_control_count"] == 1
    assert DATASET["maximum_paired_review_calls"] == 20

    for packet in rows:
        source, batch, gold = packet["source"], packet["batch"], packet["gold"]
        expected = packet["expected_deterministic_guard"]
        assert batch["sid"] == source["id"] and batch["span"] == source["text"]
        assert len(batch["items"]) == 2
        assert gold["rationale_zh"]
        if packet["category"] in INVALID_AXIS:
            assert gold["label"] == "invalid"
            assert gold["expected_failed_axis"] == INVALID_AXIS[packet["category"]]
        elif packet["category"] == "valid":
            assert gold["label"] == "valid" and gold["expected_failed_axis"] is None
        else:
            assert packet["category"] == "guard_control"

        paired = _score(packet)
        old = legacy.score_packet(source, batch, None, gold["label"])
        assert paired["selected_plan"] == old["selected_plan"]
        assert paired["selected_plan_digest"] == old["selected_plan_digest"]
        assert paired["selected_fingerprint"] == old["selected_fingerprint"]
        assert paired["selected_index"] == old["selected_index"] == expected["selected_index"]
        assert paired["selection_guard_parity"] is old["selection_guard_parity"] is True
        assert paired["guard_violations"] == old["guard_violations"]
        assert paired["deterministic_eligible"] is expected["review_eligible"]
        assert paired["model_calls_by_scorer"] == old["model_calls_by_scorer"] == 0
        assert paired["product_runtime_changed"] is False
        assert old["m39_final_byte_identical"] is expected["m39_exact_accept"]
        assert old["review_audit"] is None
        if packet["category"] == "guard_control":
            assert expected["selected_structural_pass"] is False
            assert paired["deterministic_eligible"] is False
            assert "nonprogress_or_unknown_mechanism" in paired["guard_violations"]
        else:
            assert expected["selected_structural_pass"] is True
            assert paired["deterministic_eligible"] is True
            assert paired["guard_violations"] == []


@pytest.mark.parametrize("packet_id", [
    row["packet_id"] for row in DATASET["challenge_packets"]
    if row["gold"]["label"] == "valid"
])
def test_three_fake_pass_reviews_retain_valid_packets(packet_id):
    packet = next(row for row in DATASET["challenge_packets"] if row["packet_id"] == packet_id)
    plan = _selected_plan(packet)
    result = _score(packet, _old_review(packet, plan), _new_review(packet, plan))
    assert result["new_review_audit"]["schema_passed"] is True
    assert result["new_review_audit"]["accepted"] is True
    assert result["old_review_audit"]["content_passed"] is True
    assert result["old_review_audit"]["surface_passed"] is True
    for arm in result["arms"].values():
        assert arm["would_deliver"] is True
        assert arm["valid_retained"] is True
        assert arm["false_action"] is False


@pytest.mark.parametrize("category,axis", list(INVALID_AXIS.items()))
def test_seven_fake_fail_reviews_block_and_hit_preregistered_reason(category, axis):
    packet = PACKETS[category]
    plan = _selected_plan(packet)
    result = _score(
        packet, _old_review(packet, plan, failed_field=OLD_REASON_FIELD[axis]),
        _new_review(packet, plan, failed_axis=axis),
    )
    assert result["deterministic_eligible"] is True
    assert result["new_review_audit"]["schema_passed"] is True
    assert result["new_review_audit"]["accepted"] is False
    assert result["new_review_audit"]["failed_or_uncertain_axes"] == [axis]
    assert result["new_review_audit"]["primary_failure"] == axis
    assert result["new_category_reason_hit"] is True
    assert result["old_category_reason_hit"] is True
    for arm in result["arms"].values():
        assert arm["would_deliver"] is False
        assert arm["false_action"] is False
        assert arm["valid_retention_denominator"] is False


def test_rejection_without_relevant_reason_cannot_count_as_category_hit():
    packet = PACKETS["actor_surface"]
    plan = _selected_plan(packet)
    result = _score(
        packet,
        _old_review(packet, plan, failed_field="content_checks.no_invented_facts"),
        _new_review(packet, plan, failed_axis="source_grounding"),
    )
    assert result["arms"]["old_contract"]["would_deliver"] is False
    assert result["arms"]["new_contract"]["would_deliver"] is False
    assert result["old_category_reason_hit"] is False
    assert result["new_category_reason_hit"] is False


def test_uncertain_review_and_uncertain_gold_are_fail_closed_and_not_valid_retention():
    packet = PACKETS["actor_surface"]
    plan = _selected_plan(packet)
    uncertain = _new_review(packet, plan, failed_axis="actor_capability", value="uncertain")
    blocked = _score(packet, None, uncertain)
    assert blocked["new_review_audit"]["schema_passed"] is True
    assert blocked["new_review_audit"]["failed_or_uncertain_axes"] == ["actor_capability"]
    assert blocked["new_category_reason_hit"] is False
    assert blocked["arms"]["new_contract"]["would_deliver"] is False

    valid = PACKETS["valid"]
    valid_plan = _selected_plan(valid)
    all_pass = scoring.score_packet(
        valid["source"], valid["batch"], _old_review(valid, valid_plan),
        _new_review(valid, valid_plan), "uncertain",
    )
    for arm in all_pass["arms"].values():
        assert arm["would_deliver"] is True
        assert arm["false_action"] is True
        assert arm["uncertain_action_risk"] is True
        assert arm["valid_retention_denominator"] is False
        assert arm["valid_retained"] is False


@pytest.mark.parametrize("mutation,violation", [
    ("source_id", "review_source_mismatch"),
    ("source_span", "review_source_mismatch"),
    ("evidence_jp", "evidence_not_source_or_instruction_anchored"),
])
def test_source_and_evidence_mismatches_fail_closed(mutation, violation):
    packet = PACKETS["valid"]
    plan = _selected_plan(packet)
    review = _new_review(packet, plan)
    review[mutation] = "「無関係」について確認した。" if mutation == "evidence_jp" else "別の原文"
    result = _score(packet, _old_review(packet, plan), review)
    audit = result["new_review_audit"]
    assert audit["schema_passed"] is False
    assert audit["accepted"] is False
    assert violation in audit["violations"]
    assert result["arms"]["old_contract"]["valid_retained"] is True
    assert result["arms"]["new_contract"]["valid_retained"] is False


def test_exact_english_source_quote_is_allowed_only_inside_japanese_explanation():
    packet = next(row for row in DATASET["challenge_packets"]
                  if row["packet_id"] == "p4_m46_di_valid_en_001")
    plan = _selected_plan(packet)
    review = _new_review(packet, plan)
    review["evidence_jp"] = "「The delivery slips」の記載を確認した。"
    accepted = _score(packet, _old_review(packet, plan), review)
    assert accepted["new_review_audit"]["evidence_anchored"] is True
    assert accepted["arms"]["new_contract"]["valid_retained"] is True

    review["evidence_jp"] = "「The delivery slip Z」の記載を確認した。"
    unanchored = _score(packet, None, review)
    assert unanchored["new_review_audit"]["evidence_anchored"] is False
    assert unanchored["arms"]["new_contract"]["would_deliver"] is False

    review["evidence_jp"] = "「The delivery slips」is confirmed。"
    non_japanese_explanation = _score(packet, None, review)
    assert non_japanese_explanation["new_review_audit"]["evidence_anchored"] is False
    assert non_japanese_explanation["arms"]["new_contract"]["would_deliver"] is False


def test_guard_control_blocks_both_contracts_despite_fake_pass_reviews():
    packet = PACKETS["guard_control"]
    plan = _selected_plan(packet)
    old = _old_review(packet, plan, mechanism="structure_scaffold")
    new = _new_review(packet, plan, mechanism="structure_scaffold")
    result = _score(packet, old, new)
    assert result["deterministic_eligible"] is False
    assert result["new_review_audit"]["accepted"] is True
    assert "nonprogress_or_unknown_mechanism" in result["guard_violations"]
    assert result["arms"]["old_contract"]["would_deliver"] is False
    assert result["arms"]["new_contract"]["would_deliver"] is False
    assert result["old_category_reason_hit"] is False
    assert result["new_category_reason_hit"] is False


@pytest.mark.parametrize("mutation,violation", [
    ("missing_axis", "checks_fields_mismatch"),
    ("invalid_value", "invalid_check_values"),
    ("wrong_primary", "primary_failure_without_failed_axis"),
    ("same_state", "unchanged_before_after_state"),
])
def test_malformed_decision_review_never_passes(mutation, violation):
    packet = PACKETS["valid"]
    plan = _selected_plan(packet)
    review = _new_review(packet, plan)
    if mutation == "missing_axis":
        del review["checks"]["stop_visible"]
    elif mutation == "invalid_value":
        review["checks"]["stop_visible"] = True
    elif mutation == "wrong_primary":
        review["primary_failure"] = "task_alignment"
    else:
        review["after_jp"] = review["before_jp"]
    result = _score(packet, None, review)
    assert violation in result["new_review_audit"]["violations"]
    assert result["arms"]["new_contract"]["would_deliver"] is False


def test_gold_and_axis_contract_rejects_invalid_labels():
    packet = PACKETS["valid"]
    for label in (True, "maybe", 1):
        with pytest.raises(ValueError, match="gold_label"):
            scoring.score_packet(packet["source"], packet["batch"], None, None, label)
    with pytest.raises(ValueError, match="expected_failed_axis"):
        _score(packet, axis="made_up_axis")
    with pytest.raises(ValueError, match="valid gold cannot expect"):
        _score(packet, axis="task_alignment")


def test_offline_scorer_does_not_mutate_inputs_or_call_model(monkeypatch):
    def forbidden(*_args, **_kwargs):
        pytest.fail("model transport called by offline scorer")

    monkeypatch.setattr(m45, "_native_json", forbidden)
    monkeypatch.setattr(m51, "_native_candidates", forbidden)
    packet = PACKETS["valid"]
    source, batch = deepcopy(packet["source"]), deepcopy(packet["batch"])
    plan = _selected_plan(packet)
    old, new = _old_review(packet, plan), _new_review(packet, plan)
    before = deepcopy((source, batch, old, new))
    schema = scoring.decision_review_schema(source, plan)
    payload = scoring.decision_review_payload(source, plan)
    result = scoring.score_packet(source, batch, old, new, "valid")
    assert (source, batch, old, new) == before
    assert schema["properties"]["source_span"]["enum"] == [source["text"]]
    assert payload["sources"][0] == source
    assert result["model_calls_by_scorer"] == 0
    assert result["product_runtime_changed"] is False
