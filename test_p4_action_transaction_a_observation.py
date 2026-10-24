"""Zero-call fake M51/M46 packets for A raw-to-normalized reconstruction."""

from copy import deepcopy
import json

import pytest

import p4_action_transaction_a_observation as a
import p4_action_transaction_scoring as tx
import uruha_actionable_help_delivery_m45 as m45
import uruha_goal_progress_delivery_m46 as m46
import uruha_semantic_persona_surface_m39 as m39
import uruha_state_changing_candidates_m51 as m51


RAW = "机に赤い紙と青い紙が混ざってる。色ごとに分けたい。"


def _case():
    return tx.prepare_source_case({
        "case_id": "fake_a", "language": "ja",
        "sources": [{"id": "current:fake_a", "kind": "current_user", "text": RAW}],
    })


def _batch(case):
    source = case["sources"][0]
    return {
        "sid": source["id"], "span": source["text"],
        "goal": "紙を色ごとに分ける", "unknown": "紙の枚数は不明",
        "items": [
            {
                "mechanism": "group_by_rule", "object": "赤い紙と青い紙", "verb": "置く",
                "effect": "紙が左右の二群になる", "stop": "全部置いたら止める",
                "instruction": "まず、赤い紙と青い紙を赤は左、青は右に置いて、全部置いたら止めよ。",
            },
            {
                "mechanism": "same_task_smaller_unit", "object": "紙", "verb": "分ける",
                "effect": "紙が分かれる", "stop": "分けたら止める",
                "instruction": "まず、紙を分けて、一枚分けたら止めよ。",
            },
        ],
    }


def _review(case, *, false_content=None, false_surface=None):
    source = case["sources"][0]
    content = {key: True for key in m46.CONTENT_CHECKS}
    surface = {key: True for key in m46.SURFACE_CHECKS}
    if false_content:
        content[false_content] = False
    if false_surface:
        surface[false_surface] = False
    return {
        "source_id": source["id"], "source_span": source["text"],
        "counterfactual_before_jp": "赤と青の紙が混ざっている",
        "counterfactual_after_jp": "紙が左右の二群に分かれている",
        "observed_progress_mechanism": "group_by_rule",
        "content_checks": content, "surface_checks": surface,
    }


def _json(value):
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def _stage(value, stage, *, content=None):
    return {
        "stage": stage,
        "raw_content": _json(value) if content is None else content,
        "prompt_tokens": 120 if stage == "M51" else 90,
        "completion_tokens": 170 if stage == "M51" else 110,
        "options": {"seed": 20260830 if stage == "M51" else 20260829,
                    "num_predict": 360 if stage == "M51" else 320},
        "request_body": {"model": "fake", "messages": [
            {"role": "system", "content": "frozen fake prompt"},
            {"role": "user", "content": "source-only fake payload"}],
            "format": {"type": "object"}},
        "wall_seconds": 2.0,
        "model_digest": "fake-model-digest",
        "http_identity": {"endpoint": "fake-local-transport", "model": "fake"},
        "transport_metadata": {"http_status": 200},
    }


def _build(case, batch, review=None, *, generator_content=None, reviewer_content=None):
    gen = _stage(batch, "M51", content=generator_content)
    rev = (_stage(review, "M46", content=reviewer_content)
           if review is not None or reviewer_content is not None else None)
    return a.build_a_observation(case, gen, reviewer_stage_record=rev,
                                 full_turn_seconds=4.0)


def test_valid_review_uses_exact_raw_selected_plan_and_full_stage_records(monkeypatch):
    case = _case()
    batch = _batch(case)
    review = _review(case)
    seen = []
    original = m39.verify_and_repair_surface_m39

    def capture(raw, instruction, logic):
        seen.append(raw)
        return original(raw, instruction, logic)

    monkeypatch.setattr(m39, "verify_and_repair_surface_m39", capture)
    before = deepcopy((case, batch, review))
    observed = _build(case, batch, review)
    assert (case, batch, review) == before
    assert seen == [case["raw_user_input"]]
    assert observed["decision"] == "action"
    assert observed["failure_stage"] == "none"
    assert observed["reason_code"] == "none"
    assert observed["json_contract_ok"] is True
    assert observed["source_exact"] is True
    assert observed["guard_violations"] == []
    assert observed["m52_selection"]["selected_index"] == 0
    assert observed["selected_plan_digest"] == m45.digest(observed["selected_plan"])
    assert observed["review_audit"]["content_passed"] is True
    assert observed["review_audit"]["surface_passed"] is True
    assert observed["prompt_tokens"] == 210
    assert observed["completion_tokens"] == 280
    assert observed["token_budget_ok"] is True
    assert observed["stage_wall_complete"] is True
    assert observed["stage_wall_within_full_turn"] is True
    assert observed["raw_stage_records"]["generator"]["raw_content"] == _json(batch)
    assert observed["raw_stage_records"]["reviewer"]["raw_content"] == _json(review)
    assert observed["raw_stage_records"]["reviewer"]["options"]["num_predict"] == 320
    assert observed["raw_stage_records"]["reviewer"]["request_body"]["messages"][0]["role"] == "system"
    assert observed["raw_stage_records"]["reviewer"]["http_identity"]["model"] == "fake"
    assert observed["raw_stage_records_digest"] == m45.digest(observed["raw_stage_records"])
    assert observed["model_calls_by_builder"] == 0
    assert observed["semantic_gold_checked"] is False


def test_forged_stage_flags_cannot_turn_reviewer_reject_into_action():
    case = _case()
    gen = _stage(_batch(case), "M51")
    rev = _stage(_review(case, false_surface="no_identity_or_role_error"), "M46")
    for record in (gen, rev):
        record.update(decision="action", accepted=True, source_exact=True,
                      json_contract_ok=True, reviewer_passed=True,
                      guard_violations=[])
    observed = a.build_a_observation(case, gen, reviewer_stage_record=rev,
                                     full_turn_seconds=4.0)
    assert observed["decision"] == "abstain"
    assert observed["failure_stage"] == "review_reject"
    assert observed["reason_code"] == "actor_capability"
    assert observed["json_contract_ok"] is True
    assert observed["instruction_jp"] is None
    assert observed["fallback_reply_jp"] == m45.UNAVAILABLE


def test_truncated_generator_is_quality_failure_and_does_not_require_review():
    case = _case()
    truncated = '{"sid":"' + case["sources"][0]["id"] + '","items":[{'
    observed = _build(case, _batch(case), generator_content=truncated)
    assert observed["decision"] == "abstain"
    assert observed["failure_stage"] == "generator_parse"
    assert observed["json_ok"] is False
    assert observed["json_contract_ok"] is False
    assert observed["tokens_complete"] is True
    assert observed["raw_stage_records"]["reviewer"] is None
    assert observed["selected_plan"] is None
    assert observed["reason_code"] == "unknown_reason"
    # A caller cannot attach a synthetic successful review after the failed
    # generator stage and wash this into a passing observation.
    forged = _build(case, _batch(case), _review(case), generator_content=truncated)
    assert forged["decision"] == "abstain"
    assert "unexpected_reviewer_after_upstream_failure" in forged["guard_violations"]


def test_generation_and_review_source_mismatch_fail_even_with_all_true_checks():
    case = _case()
    batch = _batch(case)
    batch["span"] = "來源不是這一段"
    observed = _build(case, batch, _review(case))
    assert observed["decision"] == "abstain"
    assert observed["failure_stage"] == "generator_source"
    assert observed["source_exact"] is False
    assert observed["json_contract_ok"] is False
    assert observed["reason_code"] == "source_grounding"
    assert "unexpected_reviewer_after_upstream_failure" in observed["guard_violations"]
    batch = _batch(case)
    review = _review(case)
    review["source_span"] = "來源不是這一段"
    observed = _build(case, batch, review)
    assert observed["decision"] == "abstain"
    assert observed["failure_stage"] == "review_source"
    assert observed["source_exact"] is False
    assert observed["json_contract_ok"] is False
    assert observed["reason_code"] == "source_grounding"


def test_missing_review_and_duplicate_json_keys_cannot_pass():
    case = _case()
    observed = _build(case, _batch(case))
    assert observed["failure_stage"] == "review_missing"
    assert observed["decision"] == "abstain"
    assert observed["json_contract_ok"] is False
    duplicate = _json(_review(case)).replace('"source_id":', '"source_id":"forged", "source_id":', 1)
    observed = _build(case, _batch(case), reviewer_content=duplicate)
    assert observed["failure_stage"] == "review_parse"
    assert observed["json_ok"] is False
    assert observed["decision"] == "abstain"


def test_schema_extra_fields_and_nonboolean_reviewer_checks_fail_closed():
    case = _case()
    batch = _batch(case)
    batch["accepted"] = True
    observed = _build(case, batch)
    assert observed["failure_stage"] == "generator_contract"
    assert observed["json_ok"] is True
    assert observed["json_contract_ok"] is False
    assert observed["decision"] == "abstain"
    review = _review(case)
    review["content_checks"]["goal_matches_source"] = "true"
    observed = _build(case, _batch(case), review)
    assert observed["failure_stage"] == "review_contract"
    assert observed["json_ok"] is True
    assert observed["json_contract_ok"] is False
    assert observed["decision"] == "abstain"


@pytest.mark.parametrize("stage,completion_tokens", [("generator", 361), ("reviewer", 321)])
def test_frozen_stage_completion_budget_is_measured_and_blocks_action(stage, completion_tokens):
    case = _case()
    gen = _stage(_batch(case), "M51")
    rev = _stage(_review(case), "M46")
    target = gen if stage == "generator" else rev
    target["completion_tokens"] = completion_tokens
    observed = a.build_a_observation(case, gen, reviewer_stage_record=rev,
                                     full_turn_seconds=4.0)
    assert observed["tokens_complete"] is True
    assert observed["token_budget_ok"] is False
    assert observed["decision"] == "abstain"
    assert observed["failure_stage"] == "accounting_guard"
    assert "stage_completion_token_budget_exceeded" in observed["guard_violations"]


def test_stage_wall_cannot_exceed_measured_full_turn():
    case = _case()
    gen = _stage(_batch(case), "M51")
    rev = _stage(_review(case), "M46")
    rev["wall_seconds"] = 4.1
    observed = a.build_a_observation(case, gen, reviewer_stage_record=rev,
                                     full_turn_seconds=4.0)
    assert observed["stage_wall_complete"] is True
    assert observed["stage_wall_within_full_turn"] is False
    assert observed["decision"] == "abstain"
    assert observed["failure_stage"] == "accounting_guard"
    assert "stage_wall_not_within_full_turn" in observed["guard_violations"]


def test_guard_parity_and_complete_raw_m39_repair_fail_closed():
    case = _case()
    batch = _batch(case)
    batch["items"][0]["object"] = "「重要」な紙"
    batch["items"][0]["instruction"] = "まず、「重要」な紙を左に置いて、一枚置いたら止めよ。"
    batch["items"][1] = deepcopy(_batch(case)["items"][0])
    observed = _build(case, batch)
    assert observed["decision"] == "abstain"
    assert "selection_guard_parity_mismatch" in observed["guard_violations"]
    batch = _batch(case)
    batch["items"][0]["instruction"] = (
        "まず、朝から赤い紙と青い紙を赤は左、青は右に置いて、全部置いたら止めよ。")
    observed = _build(case, batch)
    assert observed["decision"] == "abstain"
    assert "m39_surface_not_exactly_accepted" in observed["guard_violations"]
    assert observed["m39_surface_trace"]["action"] == "repair"
    assert observed["m39_final_byte_identical"] is False


def test_review_reason_mapping_is_conservative_and_never_reads_gold():
    case = _case()
    review = _review(case, false_content="no_invented_facts")
    observed = _build(case, _batch(case), review)
    assert observed["decision"] == "abstain"
    assert observed["reason_code"] == "source_grounding"
    review = _review(case, false_content="low_risk_reversible")
    observed = _build(case, _batch(case), review)
    assert observed["reason_code"] == "unknown_reason"
    review = _review(case, false_content="goal_matches_source")
    review["surface_checks"]["casual_japanese"] = False
    observed = _build(case, _batch(case), review)
    assert observed["reason_code"] == "unknown_reason"
    case["gold"] = {"decision": "action", "expected_reason_code": "none"}
    assert _build(case, _batch(case), _review(case, false_content="no_invented_facts"))[
        "reason_code"] == "source_grounding"


def test_prepared_sources_must_be_exact_slices_of_full_input_and_no_model_call(monkeypatch):
    case = _case()
    case["sources"][0]["text"] = "偽の出典"
    with pytest.raises(ValueError, match="exact in the complete raw input"):
        _build(case, _batch(_case()), _review(_case()))
    case = _case()

    def forbidden(*_args, **_kwargs):
        pytest.fail("offline A builder called a model")

    monkeypatch.setattr(m51, "_native_candidates", forbidden)
    monkeypatch.setattr(m45, "_native_json", forbidden)
    assert _build(case, _batch(case), _review(case))["decision"] == "action"
