"""Zero-call B raw-stage/accounting tests; fake transport is not model evidence."""

from copy import deepcopy
import json

import p4_action_transaction_b_observation as b_raw
import p4_action_transaction_scoring as tx


def _case():
    return tx.prepare_source_case({
        "case_id": "fake_b", "language": "ja",
        "sources": [{"id": "current:fake_b", "kind": "current_user",
                     "text": "机の赤い紙と青い紙を色ごとに分けたい"}],
    })


def _transaction(case, *, abstain=False):
    source = case["sources"][0]
    value = {
        "status": "abstain" if abstain else "action",
        "task_source_id": source["id"], "task_source_span": source["text"],
        "task_target_quote": "色ごとに分けたい",
        "forbidden_source_id": None, "forbidden_quote": None,
        "actor": "user", "receipt": None,
        "prerequisite_status": "user_can_inspect",
        "task_goal_jp": "赤い紙と青い紙を色ごとに分ける",
        "progress_mechanism": "group_by_rule",
        "action_object_jp": "赤い紙と青い紙",
        "action_verb_jp": "置く",
        "expected_state_change_jp": "赤い紙と青い紙が左右に分かれた状態",
        "completion_jp": "二色の紙を置いたら終わり",
        "instruction_jp": "まず赤い紙と青い紙を赤は左、青は右に置いてみて。置いたらそこで終わり。",
        "reason_code": "none",
    }
    if abstain:
        for field in tx.ACTION_FIELDS:
            value[field] = ""
        value["reason_code"] = "ambiguous_or_unsupported"
    return value


def _stage(case, value):
    body = {
        "model": "qwen3.5:9b",
        "messages": [
            {"role": "system", "content": tx.TRANSACTION_SYSTEM},
            {"role": "user", "content": json.dumps(
                tx.transaction_payload(case["sources"]), ensure_ascii=False)},
        ],
        "format": tx.transaction_schema(case["sources"]),
        "stream": False, "think": False,
        "options": {"temperature": 0, "seed": 20260830,
                    "num_ctx": 4096, "num_predict": 680},
    }
    return {
        "stage": "B_transaction", "raw_content": json.dumps(value, ensure_ascii=False),
        "prompt_tokens": 250, "completion_tokens": 190,
        "request_body": body, "options": deepcopy(body["options"]),
        "wall_seconds": 2.0, "model_digest": "a" * 64,
        "http_identity": {"endpoint": "http://127.0.0.1:11434/api/chat",
                          "model": "qwen3.5:9b"},
        "transport_metadata": {"http_status": 200},
    }


def _build(case, stage, *, seconds=2.5):
    return b_raw.build_b_observation_from_stage(
        case, stage, full_turn_seconds=seconds,
        fallback_kind="unavailable")


def test_valid_raw_stage_reconstructs_action_and_is_score_integrity_evidence():
    case = _case()
    stage = _stage(case, _transaction(case))
    original = deepcopy(stage)
    observed = _build(case, stage)
    assert stage == original
    assert observed["decision"] == "action"
    assert observed["json_contract_ok"] is True
    assert observed["raw_stage_complete"] is True
    assert observed["metadata_complete"] is True
    assert observed["accounting_complete"] is True
    assert observed["frozen_request_verified_by_builder"] is False
    assert observed["transport_identity_verified_by_builder"] is False
    assert observed["raw_stage_record"] == stage
    arms = {"A_two_stage": {}, "B_transaction": observed}
    gold = {"case_id": case["case_id"], "decision": "action",
            "expected_reason_code": "none", "acceptable_reason_codes": ["none"],
            "acceptable_task_source_ids": [case["sources"][0]["id"]],
            "task_target_quotes": ["色ごとに分けたい"], "forbidden": None}
    row = tx.score_case(case, gold, arms)["arms"]["B_transaction"]
    assert row["observation_integrity"] is True
    assert row["raw_stage_complete"] is True
    assert row["valid_action_pass"] is False  # no raw lock or semantic annotation


def test_missing_request_or_wrong_claimed_identity_fails_closed():
    case = _case()
    stage = _stage(case, _transaction(case))
    del stage["request_body"]
    observed = _build(case, stage)
    assert observed["decision"] == "abstain"
    assert observed["raw_stage_complete"] is False
    assert "request_body_incomplete" in observed["guard_violations"]
    stage = _stage(case, _transaction(case))
    stage["http_identity"]["endpoint"] = "https://example.com/api/chat"
    observed = _build(case, stage)
    assert observed["decision"] == "abstain"
    assert observed["localhost_http_identity_claimed"] is False
    stage = _stage(case, _transaction(case))
    stage["options"]["seed"] = 7
    observed = _build(case, stage)
    assert observed["decision"] == "abstain"
    assert observed["request_options_consistent"] is False


def test_zero_or_over_budget_tokens_and_inconsistent_wall_fail_closed():
    case = _case()
    for prompt, completion, wall, total in ((0, 0, 2.0, 2.5),
                                            (250, 681, 2.0, 2.5),
                                            (250, 190, 3.0, 2.5),
                                            (250, 190, 2.0, 20.1)):
        stage = _stage(case, _transaction(case))
        stage["prompt_tokens"] = prompt
        stage["completion_tokens"] = completion
        stage["wall_seconds"] = wall
        observed = _build(case, stage, seconds=total)
        assert observed["decision"] == "abstain"
        assert observed["accounting_complete"] is False


def test_abstain_stage_is_rebuilt_from_raw_not_forged_delivery_flag():
    case = _case()
    stage = _stage(case, _transaction(case, abstain=True))
    stage.update(decision="action", json_ok=True, accepted=True)
    observed = _build(case, stage)
    assert observed["decision"] == "abstain"
    assert observed["raw_transaction_failure_stage"] == "model_abstain"
    assert observed["raw_stage_complete"] is True
    assert observed["instruction_jp"] is None
