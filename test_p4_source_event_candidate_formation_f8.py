"""Zero-provider contract for the opt-in P4 f8 compact candidate prompt.

The frozen developer probes are source-only diagnostics, not a model-quality
result or a substitute for the separately gated planner/Safari comparison.
"""

from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

import uruha_compact_planner_p2 as compact
import p4_direct_reply_act_m29_priority_detached_control as controller
from test_p4_source_event_core_utility_f7 import _handoff
from test_p4_direct_reply_act_m29_priority import _isolated
from uruha_source_event_candidate_formation_p4 import build_source_event_constraint_p4
from uruha_source_event_core_utility_p4 import _source_event


DATA = json.loads(
    (Path(__file__).parent / "datasets/p4_source_event_candidate_formation_f8_probe_2026-10-24.json").read_text()
)
POSITIVE = [
    ("planner-comparison", DATA["planner_comparison_source"]),
    ("safari-confirmation", DATA["safari_confirmation_source"]),
    *[(row["id"], row["source"]) for row in DATA["contract_sources"] if row["prompt_injection_expected"]],
]
NEGATIVE = [
    (row["id"], row["source"])
    for row in DATA["contract_sources"] if not row["prompt_injection_expected"]
]


def _sha(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _request(source: str) -> dict:
    return {
        "model": "qwen2.5:7b",
        "temperature": 0.1,
        "timeout": 20,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are the Left Brain Planner for a dual-brain character system.\n"
                    "[Memory] same frozen initial memory\n"
                    "[Hard rules] keep facts bounded\n"
                    "[Output JSON schema]old verbose schema"
                ),
            },
            {"role": "user", "content": f"User Input: {source}"},
        ],
    }


def _event_relation(source: str, handoff: dict) -> tuple[str, str]:
    parsed = _source_event(source, handoff["cue_span"][0])
    assert parsed is not None
    sentence, obj, action = parsed
    return sentence, obj + "を" + action


def _assert_raw_free(receipt: dict, source: str, *, sentence: str | None = None,
                     relation: str | None = None) -> None:
    serialized = json.dumps(receipt, ensure_ascii=False, sort_keys=True)
    assert source not in serialized
    if sentence:
        assert sentence not in serialized
    if relation:
        assert relation not in serialized
    assert receipt.get("raw_dialogue_persisted") is not True


def test_frozen_probe_has_five_eligible_and_seven_ineligible_sources():
    assert len(POSITIVE) == 5 and len(NEGATIVE) == 7
    assert len({source for _, source in POSITIVE + NEGATIVE}) == 12
    assert {case_id for case_id, _ in NEGATIVE} == {
        "boundary-21", "third-party", "quoted", "negated",
        "two-sentences", "english", "too-long",
    }


@pytest.mark.parametrize(("case_id", "source"), POSITIVE, ids=[case_id for case_id, _ in POSITIVE])
def test_frozen_eligible_source_builds_only_its_observed_event_constraint(case_id, source):
    handoff = _handoff(source)
    assert handoff is not None
    before_handoff = deepcopy(handoff)
    sentence, relation = _event_relation(source, handoff)

    segment, receipt = build_source_event_constraint_p4(source, handoff)

    assert isinstance(segment, str) and segment.strip()
    assert relation in segment, case_id
    assert source not in segment  # Constraint uses the event, never the whole request.
    assert "今は一言だけ" not in segment
    assert ("初めて" in segment) is source.startswith("初めて")
    assert receipt["status"] == "authorized"
    assert receipt["prompt_injected"] is False  # Only the real request can attest injection.
    assert receipt["input_sha256"] == _sha(source)
    assert receipt["event_sha256"] == _sha(sentence)
    assert receipt["first_time_observed"] is source.startswith("初めて")
    assert receipt["relation_codepoints"] == len(relation) <= 20
    assert receipt["schema"] and receipt["reason"]
    _assert_raw_free(receipt, source, sentence=sentence, relation=relation)
    assert handoff == before_handoff


@pytest.mark.parametrize(("case_id", "source"), NEGATIVE, ids=[case_id for case_id, _ in NEGATIVE])
def test_frozen_ineligible_sources_never_build_a_prompt_segment(case_id, source):
    handoff = _handoff(source)
    before_handoff = deepcopy(handoff)
    segment, receipt = build_source_event_constraint_p4(source, handoff)
    assert segment is None, case_id
    assert receipt["status"] == "abstained"
    assert receipt["prompt_injected"] is False
    assert receipt["input_sha256"] == _sha(source)
    assert receipt["schema"] and receipt["reason"]
    _assert_raw_free(receipt, source)
    assert handoff == before_handoff


def test_exact_unicode_relation_budget_is_20_in_and_21_out():
    rows = {row["id"]: row["source"] for row in DATA["contract_sources"]}
    twenty, twenty_one = rows["boundary-20"], rows["boundary-21"]
    for source, expected_length, expected_status in (
        (twenty, 20, "authorized"),
        (twenty_one, 21, "abstained"),
    ):
        handoff = _handoff(source)
        assert handoff is not None
        _, relation = _event_relation(source, handoff)
        segment, receipt = build_source_event_constraint_p4(source, handoff)
        assert len(relation) == expected_length
        assert receipt["relation_codepoints"] == expected_length
        assert receipt["status"] == expected_status
        assert (segment is not None) is (expected_length == 20)


@pytest.mark.parametrize(("field", "value"), [
    ("schema", "forged"),
    ("input_sha256", "0" * 64),
    ("cue_sha256", "0" * 64),
    ("cue_span", [0, 2]),
    ("requested_act", "other"),
    ("source_kind", "reported_or_non_user_text"),
    ("m29_status", "literal_topic_projection_required"),
    ("m33_status", "source_atoms_extracted"),
    ("raw_dialogue_persisted", True),
])
def test_forged_or_stale_handoff_cannot_license_source_event(field, value):
    source = DATA["planner_comparison_source"]
    handoff = _handoff(source)
    assert handoff is not None
    handoff[field] = value
    segment, receipt = build_source_event_constraint_p4(source, handoff)
    assert segment is None
    assert receipt["status"] == "abstained"
    assert receipt["prompt_injected"] is False
    _assert_raw_free(receipt, source)


def test_handoff_from_a_prior_turn_cannot_license_current_event():
    source = DATA["planner_comparison_source"]
    stale = _handoff(DATA["safari_confirmation_source"])
    segment, receipt = build_source_event_constraint_p4(source, stale)
    assert segment is None and receipt["status"] == "abstained"
    assert receipt["prompt_injected"] is False


def test_compact_off_is_byte_equal_and_on_changes_only_appended_system_suffix(monkeypatch):
    source = DATA["planner_comparison_source"]
    handoff = _handoff(source)
    segment, receipt = build_source_event_constraint_p4(source, handoff)
    assert segment is not None
    original = _request(source)
    before = deepcopy(original)
    context = {"segment": segment, "receipt": receipt}
    before_context = deepcopy(context)
    monkeypatch.setenv(compact._SCHEMA_ARM_ENV, "1")
    monkeypatch.delenv("URUHA_P4_SOURCE_EVENT_CANDIDATE_PROMPT", raising=False)
    baseline = compact.compact_request(original)
    assert baseline is not None
    token = compact._SOURCE_EVENT_CONSTRAINT.set(context)
    try:
        off = compact.compact_request(original)
        assert json.dumps(off, ensure_ascii=False).encode() == json.dumps(baseline, ensure_ascii=False).encode()
        monkeypatch.setenv("URUHA_P4_SOURCE_EVENT_CANDIDATE_PROMPT", "1")
        on = compact.compact_request(original)
    finally:
        compact._SOURCE_EVENT_CONSTRAINT.reset(token)

    assert original == before and context == before_context
    assert on is not None
    assert on["messages"][0]["content"] == baseline["messages"][0]["content"] + segment
    assert on["messages"][0]["content"].startswith(original["messages"][0]["content"].split("[Output JSON schema]")[0] + compact._FORMAT)
    assert {**on, "messages": [{**on["messages"][0], "content": baseline["messages"][0]["content"]}, *on["messages"][1:]]} == baseline
    assert on["messages"][1] == original["messages"][1]
    assert on["response_format"] == baseline["response_format"]
    assert on["model"] == baseline["model"] and on["temperature"] == baseline["temperature"]


def test_compact_rejects_valid_context_bound_to_a_different_user_turn(monkeypatch):
    source = DATA["planner_comparison_source"]
    next_source = DATA["safari_confirmation_source"]
    segment, receipt = build_source_event_constraint_p4(source, _handoff(source))
    assert segment is not None
    monkeypatch.setenv("URUHA_P4_SOURCE_EVENT_CANDIDATE_PROMPT", "1")
    request = _request(next_source)
    baseline = compact.compact_request(request)
    token = compact._SOURCE_EVENT_CONSTRAINT.set({"segment": segment, "receipt": receipt})
    try:
        transformed = compact.compact_request(request)
    finally:
        compact._SOURCE_EVENT_CONSTRAINT.reset(token)
    assert transformed == baseline
    assert segment not in transformed["messages"][0]["content"]


def test_transport_and_graph_project_raw_free_receipt_even_with_extra_context_fields(monkeypatch):
    source = DATA["planner_comparison_source"]
    segment, receipt = build_source_event_constraint_p4(source, _handoff(source))
    assert segment is not None
    poisoned = {**receipt, "raw_source": source, "nested_private_state": {"claim": source}}
    poisoned["reason"] = [source]
    poisoned["status"] = [source]
    monkeypatch.setenv("URUHA_P4_SOURCE_EVENT_CANDIDATE_PROMPT", "1")
    calls = []

    def fake_create(**kwargs):
        calls.append(kwargs)
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(
            content=json.dumps({"plans": [
                {"scene": "support", "core_message_jp": core, "response_mode": "direct_answer"}
                for core in ("いいね。", "そうなんだ。", "やったな。")
            ]}, ensure_ascii=False),
        ), finish_reason="stop")])

    audit = {}
    client = compact._Proxy(SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=fake_create))))
    call_token = compact._CALL.set(audit)
    event_token = compact._SOURCE_EVENT_CONSTRAINT.set({"segment": segment, "receipt": poisoned})
    try:
        client.chat.completions.create(**_request(source))
    finally:
        compact._SOURCE_EVENT_CONSTRAINT.reset(event_token)
        compact._CALL.reset(call_token)
    assert len(calls) == 1
    safe = audit["source_event_candidate_prompt_p4"]
    assert safe["prompt_injected"] is True
    assert "raw_source" not in safe and "nested_private_state" not in safe
    _assert_raw_free(safe, source)
    result = {"logic": {"bounded_slow_path_m21": {"compact_general_plan_p2": audit}},
              "runtime_trace": {"blackboard": []}}
    compact.materialize_compact_trace(result)
    serialized = json.dumps(result["runtime_trace"], ensure_ascii=False)
    assert source not in serialized
    assert "raw_source" not in serialized and "nested_private_state" not in serialized


def test_forged_receipt_schema_cannot_inject_prompt(monkeypatch):
    source = DATA["planner_comparison_source"]
    segment, receipt = build_source_event_constraint_p4(source, _handoff(source))
    assert segment is not None
    monkeypatch.setenv("URUHA_P4_SOURCE_EVENT_CANDIDATE_PROMPT", "1")
    original = _request(source)
    baseline = compact.compact_request(original)
    token = compact._SOURCE_EVENT_CONSTRAINT.set({
        "segment": segment, "receipt": {**receipt, "schema": "forged"},
    })
    try:
        actual = compact.compact_request(original)
    finally:
        compact._SOURCE_EVENT_CONSTRAINT.reset(token)
    assert actual == baseline


@pytest.mark.parametrize(("case_id", "source"), NEGATIVE, ids=[case_id for case_id, _ in NEGATIVE])
def test_flag_on_does_not_inject_any_frozen_negative_even_with_context(monkeypatch, case_id, source):
    segment, receipt = build_source_event_constraint_p4(source, _handoff(source))
    assert segment is None and receipt["status"] == "abstained"
    monkeypatch.setenv("URUHA_P4_SOURCE_EVENT_CANDIDATE_PROMPT", "1")
    request = _request(source)
    baseline = compact.compact_request(request)
    token = compact._SOURCE_EVENT_CONSTRAINT.set({"segment": segment, "receipt": receipt})
    try:
        actual = compact.compact_request(request)
    finally:
        compact._SOURCE_EVENT_CONSTRAINT.reset(token)
    assert actual == baseline, case_id


def test_real_compact_proxy_keeps_one_fake_model_call_and_three_actual_candidates(monkeypatch):
    source = DATA["planner_comparison_source"]
    segment, receipt = build_source_event_constraint_p4(source, _handoff(source))
    assert segment is not None
    plans = [
        {"scene": "support", "core_message_jp": "おめでとう、いいじゃん！", "response_mode": "direct_answer"},
        {"scene": "support", "core_message_jp": "夜の星を撮ったんだ、いいね。", "response_mode": "direct_answer"},
        {"scene": "support", "core_message_jp": "頑張ったね、応援してる。", "response_mode": "direct_answer"},
    ]
    calls = []

    def fake_create(**kwargs):
        calls.append(kwargs)
        return SimpleNamespace(choices=[SimpleNamespace(
            message=SimpleNamespace(content=json.dumps({"plans": plans}, ensure_ascii=False)),
            finish_reason="stop",
        )])

    client = compact._Proxy(SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=fake_create))))
    audit = {}
    monkeypatch.setenv("URUHA_P4_SOURCE_EVENT_CANDIDATE_PROMPT", "1")
    token_call = compact._CALL.set(audit)
    token_source = compact._SOURCE_EVENT_CONSTRAINT.set({"segment": segment, "receipt": receipt})
    try:
        returned = client.chat.completions.create(**_request(source))
    finally:
        compact._SOURCE_EVENT_CONSTRAINT.reset(token_source)
        compact._CALL.reset(token_call)
    assert len(calls) == 1
    assert calls[0]["messages"][0]["content"].endswith(segment)
    assert json.loads(returned.choices[0].message.content)["candidate_plans"] == plans
    assert audit["completed"] is True and audit["candidate_count"] == 3
    prompt_receipt = audit["source_event_candidate_prompt_p4"]
    assert prompt_receipt["status"] == "prompt_injected"
    assert prompt_receipt["prompt_injected"] is True
    _assert_raw_free(prompt_receipt, source, sentence=source.split("。", 1)[0] + "。", relation="夜の星を撮った")


def test_full_turn_uses_f7_on_real_three_candidate_path_and_exposes_raw_free_f8_receipt(tmp_path):
    observed = _isolated(tmp_path, """
        import hashlib
        import json
        import os
        from types import SimpleNamespace

        import uruha_brain_mac as runtime
        import uruha_compact_planner_p2 as compact
        import uruha_contextual_expression_commit_p2 as expression
        import uruha_web_ui_product_p4_direct_reply_act_m29_priority as product_entry
        from uruha_brain_mac import LeftBrain, RightBrain
        from test_personhood_loop_v2_13 import _IsolatedContractBrain

        source = json.load(open("datasets/p4_source_event_candidate_formation_f8_probe_2026-10-24.json"))["planner_comparison_source"]
        runtime.LEFT_BRAIN_SLOW_PATH_BUDGET_SECONDS = 20.0
        compact.install_compact_planner_p2()
        expression.install_contextual_expression_commit_p2()
        product_entry.install_product_chain()
        os.environ["URUHA_P4_DIRECT_REPLY_ACT_HANDOFF_ARM"] = "control"
        os.environ[compact._SCHEMA_ARM_ENV] = "1"
        os.environ["URUHA_P4_REPAIR_CUE_BOUNDARY"] = "1"
        os.environ["URUHA_P4_SOURCE_EVENT_CORE_UTILITY"] = "1"
        plans = [
            {"scene": "support", "core_message_jp": "おめでとう、いいじゃん！", "response_mode": "direct_answer"},
            {"scene": "support", "core_message_jp": "夜の星を撮ったんだ、いいね。", "response_mode": "direct_answer"},
            {"scene": "support", "core_message_jp": "頑張ったね、応援してる。", "response_mode": "direct_answer"},
        ]
        rows = []
        for enabled in (False, True):
            if enabled:
                os.environ["URUHA_P4_SOURCE_EVENT_CANDIDATE_PROMPT"] = "1"
            else:
                os.environ.pop("URUHA_P4_SOURCE_EVENT_CANDIDATE_PROMPT", None)
            calls = []
            def fake_create(**kwargs):
                calls.append(kwargs)
                return SimpleNamespace(choices=[SimpleNamespace(
                    message=SimpleNamespace(content=json.dumps({"plans": plans}, ensure_ascii=False)),
                    finish_reason="stop",
                )])
            brain = _IsolatedContractBrain()
            left = LeftBrain(SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=fake_create))))
            def fit(plan, *_args):
                return 1.0 if plan.get("core_message_jp") == plans[0]["core_message_jp"] else 0.75
            for name in ("_persona_fit_score", "_psyche_fit_score", "_continuity_fit_score",
                         "_human_fit_score", "_belief_gap_fit_score", "_procedural_fit_score"):
                setattr(left, name, fit)
            left._critique_plan = lambda *_args: {"needs_revision": False, "issues": [], "internal_note": ""}
            brain.left_brain = left
            brain.right_brain = RightBrain(load_model=False)
            result = brain.run_turn_debug(source)
            logic = result["logic"]
            m21 = logic.get("bounded_slow_path_m21") or {}
            compact_audit = m21.get("compact_general_plan_p2") or {}
            graph_rows = [row for row in result["runtime_trace"]["blackboard"]
                          if row.get("label") == "source_event_candidate_prompt_p4"]
            rows.append({
                "enabled": enabled,
                "calls": len(calls),
                "prompt": calls[0]["messages"][0]["content"] if calls else None,
                "user_message": calls[0]["messages"][1]["content"] if calls else None,
                "response_format": calls[0]["response_format"] if calls else None,
                "candidate_count": compact_audit.get("candidate_count"),
                "compact_completed": compact_audit.get("completed"),
                "prompt_receipt": compact_audit.get("source_event_candidate_prompt_p4"),
                "graph_receipts": [row.get("payload") for row in graph_rows],
                "route": m21.get("route"),
                "status": m21.get("status"),
                "fallback": m21.get("fallback_used"),
                "revision": logic.get("planner_repair_applied"),
                "f7": logic.get("source_event_core_utility_p4"),
                "core": logic.get("core_message_jp"),
                "episode_match": result["reply"] == brain.memory.saved_episodes[-1]["reply"],
            })
        print(json.dumps(rows, ensure_ascii=False))
    """)
    off, on = observed
    source = DATA["planner_comparison_source"]
    segment, _ = build_source_event_constraint_p4(source, _handoff(source))
    assert segment is not None
    assert off["calls"] == on["calls"] == 1
    assert off["prompt"] + segment == on["prompt"]
    assert off["user_message"] == on["user_message"] == f"User Input: {source}"
    assert off["response_format"] == on["response_format"]
    for row in (off, on):
        assert row["route"] == "full_planner" and row["status"] == "completed_within_budget"
        assert row["fallback"] is False and row["revision"] is False
        assert row["compact_completed"] is True and row["candidate_count"] == 3
        assert row["f7"]["eligible"] is True
        assert [candidate["grounded"] for candidate in row["f7"]["candidate_coverage"]] == [False, True, False]
        assert row["f7"]["final_core_matches_winner"] is True
        assert row["core"] == "夜の星を撮ったんだ、いいね。"
        assert row["episode_match"] is True
    assert off["prompt_receipt"] is None and off["graph_receipts"] == []
    assert on["prompt_receipt"]["prompt_injected"] is True
    assert on["prompt_receipt"]["status"] == "prompt_injected"
    assert on["graph_receipts"] == [on["prompt_receipt"]]
    _assert_raw_free(on["prompt_receipt"], source, sentence="初めて自分で夜の星を撮った。", relation="夜の星を撮った")
    _assert_raw_free(on["graph_receipts"][0], source, sentence="初めて自分で夜の星を撮った。", relation="夜の星を撮った")


def test_f8_controller_flag_is_child_only_and_requires_f7_control_compact(monkeypatch, tmp_path):
    layout = {
        "runtime_root": tmp_path,
        "memory_db": tmp_path / "memory_db",
        "session_db": tmp_path / "session_db",
        "web_logs": tmp_path / "web_logs",
        "jsonl_log": tmp_path / "web_logs/conversation.jsonl",
        "text_log": tmp_path / "web_logs/conversation.txt",
    }
    observed = []

    def preflight(**kwargs):
        return {}, dict(kwargs["environ"]), layout, False, None

    def no_launch(argv):
        base = controller.launchd._isolated_env(layout, port=None)
        child = controller.launchd._isolated_env(layout, port=7938)
        if argv[0] == "start" and "product" in argv:
            _, final, _, _, _ = controller.product_launcher.preflight_preference_fallback(
                environ=base, prewarm=False
            )
            observed.append((base, child, final))
        else:
            observed.append((base, child, None))
        return 0

    monkeypatch.setattr(controller.product_launcher, "preflight_preference_fallback", preflight)
    monkeypatch.setattr(controller.prior.base_controller, "main", no_launch)
    monkeypatch.setenv("URUHA_P4_SOURCE_EVENT_CANDIDATE_PROMPT", "1")
    assert controller.main(["prepare"]) == 0
    assert "URUHA_P4_SOURCE_EVENT_CANDIDATE_PROMPT" not in observed[-1][1]
    assert controller.main([
        "--source-event-core-utility", "--compact-json-schema",
        "start", "--mode", "product",
    ]) == 0
    assert "URUHA_P4_SOURCE_EVENT_CANDIDATE_PROMPT" not in observed[-1][1]

    assert controller.main([
        "--source-event-candidate-prompt", "--source-event-core-utility",
        "--compact-json-schema", "--direct-act-arm", "control", "--product-port", "7938",
        "start", "--mode", "product",
    ]) == 0
    base, child, final = observed[-1]
    assert "URUHA_P4_SOURCE_EVENT_CANDIDATE_PROMPT" not in base
    assert child["URUHA_P4_SOURCE_EVENT_CANDIDATE_PROMPT"] == "1"
    assert final["URUHA_P4_SOURCE_EVENT_CANDIDATE_PROMPT"] == "1"
    for rejected in (
        ["--source-event-candidate-prompt", "prepare"],
        ["--source-event-candidate-prompt", "start", "--mode", "inert"],
        ["--source-event-candidate-prompt", "start", "--mode", "product"],
        ["--source-event-candidate-prompt", "--compact-json-schema", "start", "--mode", "product"],
        ["--source-event-candidate-prompt", "--source-event-core-utility", "--compact-json-schema",
         "--direct-act-arm", "treatment", "start", "--mode", "product"],
    ):
        before = len(observed)
        with pytest.raises(SystemExit):
            controller.main(rejected)
        assert len(observed) == before
