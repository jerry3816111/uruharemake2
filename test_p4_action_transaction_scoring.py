"""Zero-call fake-contract tests; no model quality is claimed by these fixtures."""

from copy import deepcopy
import json

import pytest

import p4_action_transaction_scoring as tx
import uruha_actionable_help_delivery_m45 as m45


SOURCE = {
    "id": "current:fake:clause:0",
    "kind": "current_user",
    "text": "我的植物觀察表已經有逐週紀錄，欄位上方還是空白。先給我一個能整理這張表的小動作；觀察數值不要補寫。",
}
RAW = SOURCE["text"]
CASE = {"case_id": "fake_valid", "language": "zh-TW",
        "sources": [SOURCE], "raw_user_input": RAW}


def _action():
    return {
        "status": "action",
        "task_source_id": SOURCE["id"],
        "task_source_span": SOURCE["text"],
        "task_target_quote": "整理這張表的小動作",
        "forbidden_source_id": SOURCE["id"],
        "forbidden_quote": "觀察數值不要補寫",
        "actor": "user",
        "receipt": None,
        "prerequisite_status": "user_can_inspect",
        "task_goal_jp": "植物観察表を整理しやすくする",
        "progress_mechanism": "structure_scaffold",
        "action_object_jp": "観察表の欄見出し二つ",
        "action_verb_jp": "書く",
        "expected_state_change_jp": "観察表の空欄に見出しが二つ加わった状態",
        "completion_jp": "見出しを二つ書いたら終わり",
        "instruction_jp": "まず観察表の欄見出し二つだけ書いてみて。書けたらそこで終わり。",
        "reason_code": "none",
    }


def _abstain(case=CASE, reason="ambiguous_or_unsupported", *, empty_target=False):
    value = {key: "" for key in tx.ACTION_FIELDS}
    value.update({
        "status": "abstain",
        "task_source_id": case["sources"][0]["id"],
        "task_source_span": case["sources"][0]["text"],
        "task_target_quote": "" if empty_target else case["sources"][0]["text"],
        "forbidden_source_id": None,
        "forbidden_quote": None,
        "actor": "unknown",
        "receipt": None,
        "prerequisite_status": "unknown",
        "reason_code": reason,
    })
    return value


def _raw(value):
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def _b(case, value, *, seconds=2.0):
    return tx.build_b_observation(case, _raw(value), prompt_tokens=120,
                                  completion_tokens=170, full_turn_seconds=seconds,
                                  fallback_kind="unavailable" if value["status"] == "abstain" else None)


def _a(decision="action", reason="none", *, seconds=3.0):
    return {
        "arm": "A_two_stage", "decision": decision,
        "failure_stage": "none" if decision == "action" else "review_reject",
        "reason_code": reason, "json_ok": True, "json_contract_ok": True,
        "source_exact": True,
        "tokens_complete": True, "token_budget_ok": True, "prompt_tokens": 150,
        "completion_tokens": 200, "retries": 0,
        "full_turn_seconds": seconds, "guard_violations": [],
        "instruction_jp": _action()["instruction_jp"] if decision == "action" else None,
        "fallback_kind": "unavailable" if decision == "abstain" else None,
        "fallback_reply_jp": m45.UNAVAILABLE if decision == "abstain" else None,
    }


def _gold(case, decision, reason="none"):
    return {
        "case_id": case["case_id"], "decision": decision,
        "expected_reason_code": reason,
        "acceptable_reason_codes": [reason],
        "acceptable_task_source_ids": [case["sources"][0]["id"]],
        "task_target_quotes": [case["sources"][0]["text"]],
        "forbidden": None,
    }


def _adjudication(case, arm, observation, all_pass=True):
    axes = {axis: "pass" for axis in tx.SEMANTIC_AXES}
    if not all_pass:
        axes["task_alignment"] = "fail"
    return {"output_locked_before_annotation": True, "axes": axes,
            "case_id": case["case_id"], "arm": arm,
            "raw_lock_commit": "a" * 40,
            "output_digest": tx.output_evidence_digest(case["case_id"], arm, observation)}


def _fake_raw_lock(case, observations):
    return {"commit_sha": "a" * 40, "output_digests": {
        case["case_id"]: {arm: tx.output_evidence_digest(case["case_id"], arm, observations[arm])
                          for arm in tx.ARMS}}}


def _frozen_fake_summary(rows):
    """Synthetic test-only identity map; formal runner uses hash-checked files."""
    return tx.summarize_scores(
        rows,
        expected_case_order=[row["case_id"] for row in rows],
        expected_source_digests={row["case_id"]: row["source_digest"] for row in rows},
        expected_gold_digests={row["case_id"]: row["gold_digest"] for row in rows},
    )


def test_17_field_schema_and_payload_are_source_only_and_pure():
    sources = [dict(SOURCE, origin={"private_metadata": "do not send"})]
    before = deepcopy(sources)
    schema = tx.transaction_schema(sources)
    payload = tx.transaction_payload(sources)
    assert len(tx.TRANSACTION_FIELDS) == 17
    assert tuple(schema["required"]) == tx.TRANSACTION_FIELDS
    assert set(schema["properties"]) == set(tx.TRANSACTION_FIELDS)
    assert schema["additionalProperties"] is False
    assert schema["properties"]["receipt"] == {"type": "null"}
    assert schema["properties"]["task_source_id"]["enum"] == [SOURCE["id"]]
    assert payload == {"user_sources": [SOURCE]}
    assert "gold" not in _raw(payload) and "case_id" not in _raw(payload)
    assert sources == before
    assert "valid_zh" not in tx.TRANSACTION_SYSTEM


def test_good_action_preserves_source_forbidden_actor_stop_and_common_guards():
    value = _action()
    audit = tx.inspect_transaction(value, CASE["sources"], raw_user_input=RAW)
    assert audit["valid_transaction"] is True
    assert audit["would_deliver"] is True
    assert audit["source_exact"] is True
    assert audit["m53_label_audit"]["unsupported_count"] == 0
    assert audit["m39_surface_trace"]["action"] == "accept"
    assert audit["semantic_gold_checked"] is False
    assert audit["human_validated"] is False


def test_model_supplied_exact_evidence_does_not_self_certify_wrong_task():
    wrong_case = {
        "case_id": "wrong_task", "language": "zh-TW",
        "raw_user_input": "我正在整理讀書會的提問清單，摘要稿先不要改。只要一個整理提問的小步驟。",
        "sources": [{"id": "current:wrong:clause:0", "kind": "current_user",
                     "text": "我正在整理讀書會的提問清單，摘要稿先不要改。只要一個整理提問的小步驟。"}],
    }
    value = _action()
    value.update({
        "task_source_id": wrong_case["sources"][0]["id"],
        "task_source_span": wrong_case["sources"][0]["text"],
        "task_target_quote": "提問清單",
        "forbidden_source_id": wrong_case["sources"][0]["id"],
        "forbidden_quote": "摘要稿先不要改",
        "task_goal_jp": "読書会の質問一覧を整理する",
        "action_object_jp": "要約原稿の小見出し一つ",
        "expected_state_change_jp": "要約原稿に小見出しが一つ増えた状態",
        "completion_jp": "小見出しを一つ書いたら終わり",
        "instruction_jp": "まず要約原稿の小見出し一つだけ書いてみて。書けたらそこで終わり。",
    })
    audit = tx.inspect_transaction(value, wrong_case["sources"],
                                   raw_user_input=wrong_case["raw_user_input"])
    assert audit["source_exact"] is True
    # The mechanical guard is intentionally not an independent semantic judge.
    assert audit["would_deliver"] is True
    observed = {"A_two_stage": _a(), "B_transaction": _b(wrong_case, value)}
    adjudications = {arm: _adjudication(wrong_case, arm, observed[arm], False)
                     for arm in tx.ARMS}
    scored = tx.score_case(wrong_case, _gold(wrong_case, "abstain", "wrong_task"),
                           observed, adjudications, _fake_raw_lock(wrong_case, observed))
    assert scored["arms"]["B_transaction"]["false_action"] is True
    assert scored["arms"]["B_transaction"]["reason_code_hit"] is False


def test_assistant_without_trusted_receipt_and_fake_receipt_are_blocked():
    assistant = _action()
    assistant["actor"] = "assistant"
    audit = tx.inspect_transaction(assistant, CASE["sources"], raw_user_input=RAW)
    assert audit["would_deliver"] is False
    assert "assistant_without_trusted_receipt" in audit["guard_violations"]
    assert _b(CASE, assistant)["reason_code"] == "actor_capability"
    assistant["receipt"] = {"model_says": "I did it"}
    audit = tx.inspect_transaction(assistant, CASE["sources"], raw_user_input=RAW)
    assert "untrusted_model_receipt" in audit["guard_violations"]
    assert audit["receipt_trusted"] is False


def test_wrong_source_quote_pair_and_unknown_prerequisite_fail_closed():
    wrong = _action()
    wrong["task_source_id"] = "current:other"
    audit = tx.inspect_transaction(wrong, CASE["sources"], raw_user_input=RAW)
    assert "invalid_exact_task_source" in audit["guard_violations"]
    assert audit["source_exact"] is False
    wrong = _action()
    wrong["forbidden_quote"] = "モデルが作った禁止文"
    assert "forbidden_quote_not_source_anchored" in tx.inspect_transaction(
        wrong, CASE["sources"], raw_user_input=RAW)["guard_violations"]
    wrong = _action()
    wrong["prerequisite_status"] = "unknown"
    assert "unknown_action_prerequisite" in tx.inspect_transaction(
        wrong, CASE["sources"], raw_user_input=RAW)["guard_violations"]


def test_conservative_abstain_allows_empty_target_without_inventing_task():
    value = _abstain(empty_target=True)
    audit = tx.inspect_transaction(value, CASE["sources"], raw_user_input=RAW)
    assert audit["valid_transaction"] is True
    assert audit["source_exact"] is True
    assert audit["would_deliver"] is False
    assert audit["guard_violations"] == []
    assert audit["m39_surface_trace"] is None
    observed = _b(CASE, value)
    assert observed["instruction_jp"] is None
    assert observed["fallback_kind"] == "unavailable"
    assert observed["fallback_reply_jp"] == m45.UNAVAILABLE
    value["instruction_jp"] = "勝手にやってみて。"
    assert "abstain_has_action_payload" in tx.inspect_transaction(
        value, CASE["sources"], raw_user_input=RAW)["guard_violations"]


def test_abstain_reason_label_without_gold_task_anchor_is_not_source_bound():
    value = _abstain(empty_target=True)
    observed = tx.build_b_observation(
        CASE, _raw(value), prompt_tokens=10, completion_tokens=10,
        full_turn_seconds=1, fallback_kind="unavailable")
    scored = tx.score_case(
        CASE, _gold(CASE, "abstain", "ambiguous_or_unsupported"),
        {"A_two_stage": _a("abstain", "ambiguous_or_unsupported"),
         "B_transaction": observed})
    row = scored["arms"]["B_transaction"]
    assert row["reason_label_hit"] is True
    assert row["source_bound_reason_hit"] is False
    assert row["abstain_pass"] is False


def test_abstain_reason_cannot_pass_without_raw_commit_binding():
    observed = _b(CASE, _abstain())
    arms = {"A_two_stage": _a("abstain", "ambiguous_or_unsupported"),
            "B_transaction": observed}
    scored = tx.score_case(CASE, _gold(CASE, "abstain", "ambiguous_or_unsupported"),
                           arms)
    row = scored["arms"]["B_transaction"]
    assert row["reason_label_hit"] is True
    assert row["source_bound_reason_hit"] is True
    assert row["raw_lock_bound"] is False
    assert row["abstain_pass"] is False
    assert scored["raw_lock_binding_checked"] is False


def test_strict_single_json_and_observation_integrity():
    assert tx.parse_transaction_json('{"x":1,"x":2}') is None
    assert tx.parse_transaction_json('{"x":NaN}') is None
    assert tx.parse_transaction_json('{"x":1} trailing') is None
    assert tx.parse_transaction_json('[1]') is None
    good = _b(CASE, _action())
    forged = deepcopy(good)
    forged["source_exact"] = False
    observations = {"A_two_stage": _a(), "B_transaction": forged}
    scored = tx.score_case(CASE, _gold(CASE, "action"), observations,
                           {arm: _adjudication(CASE, arm, observations[arm]) for arm in tx.ARMS},
                           _fake_raw_lock(CASE, observations))
    assert scored["arms"]["B_transaction"]["observation_integrity"] is False
    assert scored["arms"]["B_transaction"]["valid_action_pass"] is False


def test_malformed_abstain_and_oversized_action_cannot_count_as_complete_json():
    missing = _abstain()
    del missing["task_goal_jp"]
    observed = tx.build_b_observation(
        CASE, _raw(missing), prompt_tokens=10, completion_tokens=10,
        full_turn_seconds=1, fallback_kind="unavailable")
    assert observed["json_ok"] is True
    assert observed["json_contract_ok"] is False
    score = tx.score_case(
        CASE, _gold(CASE, "abstain", "ambiguous_or_unsupported"),
        {"A_two_stage": _a("abstain", "ambiguous_or_unsupported"),
         "B_transaction": observed})
    assert score["arms"]["B_transaction"]["parse_source_accounting_complete"] is False
    assert score["arms"]["B_transaction"]["abstain_pass"] is False


def test_completion_budget_and_malformed_annotation_lock_fail_closed():
    observed = tx.build_b_observation(
        CASE, _raw(_action()), prompt_tokens=10, completion_tokens=681,
        full_turn_seconds=1)
    arms = {"A_two_stage": _a(), "B_transaction": observed}
    annotation = _adjudication(CASE, "B_transaction", observed)
    assert tx.score_case(CASE, _gold(CASE, "action"), arms,
                         {"B_transaction": annotation},
                         {"commit_sha": "a" * 40, "output_digests": []})["arms"]["B_transaction"]["semantic_action_valid"] is None
    scored = tx.score_case(CASE, _gold(CASE, "action"), arms,
                           {"B_transaction": annotation},
                           _fake_raw_lock(CASE, arms))
    assert scored["arms"]["B_transaction"]["token_budget_ok"] is False
    assert scored["arms"]["B_transaction"]["valid_action_pass"] is False


def test_raw_lock_prevents_posthoc_latency_and_token_relabeling():
    slow = _b(CASE, _action(), seconds=25.0)
    arms = {"A_two_stage": _a(), "B_transaction": slow}
    locked = _fake_raw_lock(CASE, arms)
    annotation = _adjudication(CASE, "B_transaction", slow)
    assert tx.score_case(CASE, _gold(CASE, "action"), arms,
                         {"B_transaction": annotation}, locked)["arms"]["B_transaction"][
                             "latency_within_budget"] is False
    relabeled = deepcopy(slow)
    relabeled.update(full_turn_seconds=2.0, prompt_tokens=0,
                     completion_tokens=0)
    arms["B_transaction"] = relabeled
    row = tx.score_case(CASE, _gold(CASE, "action"), arms,
                        {"B_transaction": annotation}, locked)["arms"]["B_transaction"]
    assert row["observation_integrity"] is False  # zero-token relabel also fails accounting
    assert row["semantic_action_valid"] is None  # but raw lock no longer matches
    assert row["valid_action_pass"] is False

    oversized = _action()
    oversized["actor"] = "assistant"
    oversized["action_object_jp"] = "観察表" * 30
    observed = tx.build_b_observation(
        CASE, _raw(oversized), prompt_tokens=10, completion_tokens=10,
        full_turn_seconds=1, fallback_kind="unavailable")
    assert observed["reason_code"] == "actor_capability"
    assert observed["json_contract_ok"] is False
    score = tx.score_case(
        CASE, _gold(CASE, "abstain", "actor_capability"),
        {"A_two_stage": _a("abstain", "actor_capability"),
         "B_transaction": observed})
    assert score["arms"]["B_transaction"]["abstain_pass"] is False


def test_action_quality_requires_separate_output_locked_adjudication():
    observations = {"A_two_stage": _a(), "B_transaction": _b(CASE, _action())}
    scored = tx.score_case(CASE, _gold(CASE, "action"), observations)
    assert scored["arms"]["B_transaction"]["semantic_action_valid"] is None
    assert scored["arms"]["B_transaction"]["false_action"] is None
    assert scored["arms"]["B_transaction"]["valid_action_pass"] is False
    scored = tx.score_case(
        CASE, _gold(CASE, "action"), observations,
        {arm: _adjudication(CASE, arm, observations[arm]) for arm in tx.ARMS},
        _fake_raw_lock(CASE, observations))
    assert scored["arms"]["B_transaction"]["semantic_action_valid"] is True
    assert scored["arms"]["B_transaction"]["valid_action_pass"] is False
    assert scored["arms"]["B_transaction"]["raw_stage_complete"] is False


def test_uncertain_semantic_annotation_is_not_mislabeled_as_false_action():
    from test_p4_action_transaction_b_observation import (
        _case as b_case, _transaction as b_transaction,
        _stage as b_stage, _build as b_build,
    )
    case = b_case()
    observed_b = b_build(case, b_stage(case, b_transaction(case)))
    arms = {"A_two_stage": _a(), "B_transaction": observed_b}
    annotation = _adjudication(case, "B_transaction", observed_b)
    annotation["axes"]["task_alignment"] = "uncertain"
    gold = _gold(case, "action")
    gold["task_target_quotes"] = ["色ごとに分けたい"]
    row = tx.score_case(case, gold, arms,
                        {"B_transaction": annotation},
                        _fake_raw_lock(case, arms))["arms"]["B_transaction"]
    assert row["semantic_action_valid"] is None
    assert row["false_action"] is None
    assert row["valid_action_pass"] is False


def test_all_reject_fails_absolute_valid_retention_despite_zero_false_actions():
    from test_p4_action_transaction_b_observation import (
        _case as b_case, _transaction as b_transaction,
        _stage as b_stage, _build as b_build,
    )
    rows = []
    for index in range(18):
        case = dict(b_case(), case_id=f"fake_{index}")
        gold = (_gold(case, "action") if index < 9 else
                _gold(case, "abstain", "ambiguous_or_unsupported"))
        gold["task_target_quotes"] = ["色ごとに分けたい"]
        observations = {
            "A_two_stage": _a("abstain", "ambiguous_or_unsupported"),
            "B_transaction": b_build(case, b_stage(case, b_transaction(case, abstain=True))),
        }
        rows.append(tx.score_case(case, gold, observations,
                                  raw_lock=_fake_raw_lock(case, observations)))
    table = _frozen_fake_summary(rows)
    score = table["arms"]["B_transaction"]
    assert score["valid_action"] == 0
    assert score["correct_abstain_with_reason"] == 9
    assert score["false_action"] == 0
    assert score["parse_source_accounting_complete"] == 18
    assert score["absolute_gate_passed"] is False
    # A's old normalized-only fake is deliberately not raw-locked evidence.
    assert table["arms"]["A_two_stage"]["parse_source_accounting_complete"] == 0


def test_18_case_b_fake_pass_and_single_cost_failure_are_separate():
    from test_p4_action_transaction_b_observation import (
        _case as b_case, _transaction as b_transaction,
        _stage as b_stage, _build as b_build,
    )
    rows = []
    for index in range(18):
        case = dict(b_case(), case_id=f"pass_{index}")
        positive = index < 9
        gold = (_gold(case, "action") if positive else
                _gold(case, "abstain", "ambiguous_or_unsupported"))
        gold["task_target_quotes"] = ["色ごとに分けたい"]
        observations = {
            "A_two_stage": _a() if positive else _a("abstain", "ambiguous_or_unsupported"),
            "B_transaction": b_build(case, b_stage(case, b_transaction(case, abstain=not positive))),
        }
        adjudications = ({arm: _adjudication(case, arm, observations[arm]) for arm in tx.ARMS}
                         if positive else None)
        rows.append(tx.score_case(case, gold, observations, adjudications,
                                  _fake_raw_lock(case, observations)))
    table = _frozen_fake_summary(rows)
    assert table["arms"]["A_two_stage"]["absolute_gate_passed"] is False
    assert table["arms"]["B_transaction"]["absolute_gate_passed"] is True
    slow_rows = deepcopy(rows)
    slow_rows[0]["arms"]["B_transaction"]["full_turn_seconds"] = 20.01
    slow_rows[0]["arms"]["B_transaction"]["latency_within_budget"] = False
    assert _frozen_fake_summary(slow_rows)["arms"]["B_transaction"]["absolute_gate_passed"] is False
    assert tx.summarize_scores(rows)["frozen_case_identity_match"] is False
    tampered = deepcopy(rows)
    tampered[0]["source_digest"] = "0" * 64
    expected = {row["case_id"]: row["source_digest"] for row in rows}
    assert tx.summarize_scores(
        tampered, expected_case_order=[row["case_id"] for row in rows],
        expected_source_digests=expected,
        expected_gold_digests={row["case_id"]: row["gold_digest"] for row in rows},
    )["frozen_case_identity_match"] is False


def test_a_score_is_rebuilt_from_raw_stages_and_rejects_relabeling():
    import p4_action_transaction_a_observation as a_raw
    from test_p4_action_transaction_a_observation import (
        _case as a_case, _batch as a_batch, _review as a_review,
        _stage as a_stage,
    )

    case = a_case()
    observed_a = a_raw.build_a_observation(
        case, a_stage(a_batch(case), "M51"),
        reviewer_stage_record=a_stage(a_review(case), "M46"),
        full_turn_seconds=4.0)
    arms = {"A_two_stage": observed_a,
            "B_transaction": _b(case, _abstain(case))}
    scored = tx.score_case(
        case, _gold(case, "action"), arms,
        {"A_two_stage": _adjudication(case, "A_two_stage", observed_a)},
        _fake_raw_lock(case, arms))
    assert scored["arms"]["A_two_stage"]["observation_integrity"] is True
    assert scored["arms"]["A_two_stage"]["valid_action_pass"] is True
    forged = deepcopy(observed_a)
    forged["decision"] = "abstain"
    forged["instruction_jp"] = None
    forged["fallback_kind"] = "unavailable"
    forged["fallback_reply_jp"] = m45.UNAVAILABLE
    arms["A_two_stage"] = forged
    scored = tx.score_case(case, _gold(case, "action"), arms)
    assert scored["arms"]["A_two_stage"]["observation_integrity"] is False
    assert scored["arms"]["A_two_stage"]["decision"] == "action"
    assert scored["arms"]["A_two_stage"]["valid_action_pass"] is False


def test_source_and_raw_input_are_distinct_and_required():
    with pytest.raises(ValueError, match="complete original"):
        tx.inspect_transaction(_action(), CASE["sources"], raw_user_input="")
    with pytest.raises(ValueError, match="prefiltered"):
        tx.transaction_payload([{"id": "assistant:0", "kind": "assistant", "text": "fake"}])
