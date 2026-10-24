from copy import deepcopy
import json

import uruha_goal_progress_delivery_m46 as m
import uruha_actionable_help_delivery_m45 as base
from test_actionable_help_delivery_m45 import help_logic
from uruha_memory_observatory import collect_cognitive_graph


SOURCE_TEXT = "The report is still blank. Give me one practical step."
TASK_SPAN = "The report is still blank."


def sources(text=SOURCE_TEXT):
    return [{"id": "current:4", "kind": "current_user", "text": text}]


def valid_plan(text=SOURCE_TEXT):
    return {"status": "action", "goal_source_id": "current:4:clause:0", "goal_source_span": TASK_SPAN,
            "task_goal_jp": "報告書の作成を進める",
            "criterion_basis": "safe_proposed_criterion",
            "progress_criterion_jp": "見出しが三つ書かれた状態",
            "progress_mechanism": "structure_scaffold",
            "action_object_jp": "見出しを三つ", "action_verb_jp": "書く",
            "action_step_jp": "紙かメモに見出しを三つだけ書く",
            "expected_state_change_jp": "空白の状態から構成の骨組みが一つできる",
            "completion_jp": "見出しを三つ書いたら止める", "unknown_constraint_jp": "詳しい提出条件は不明",
            "instruction_jp": "まず紙かメモに見出しを三つだけ書いて、そこで止めよ。"}


def valid_review(text=SOURCE_TEXT):
    return {"source_id": "current:4:clause:0", "source_span": TASK_SPAN,
            "counterfactual_before_jp": "報告書に構成の手掛かりがない状態",
            "counterfactual_after_jp": "見出しが三つあり次に書く場所が見える状態",
            "observed_progress_mechanism": "structure_scaffold",
            "content_checks": {key: True for key in m.CONTENT_CHECKS},
            "surface_checks": {key: True for key in m.SURFACE_CHECKS}}


def fake_calls(plan=None, review=None):
    plan, review = deepcopy(plan or valid_plan()), deepcopy(review or valid_review())
    calls = []
    def call(system, payload, schema, deadline, metrics):
        calls.append((system, deepcopy(payload), deepcopy(schema)))
        metrics["model_calls_attempted"] += 1
        metrics["model_calls_completed"] += 1
        if len(calls) == 1:
            assert list(schema["properties"])[-1] == "instruction_jp"
            assert "user_sources" in payload
            return deepcopy(plan)
        assert "progress_mechanism" not in payload["plan"] and payload["planned_payload_digest"]
        return deepcopy(review)
    call.calls = calls
    return call


def test_dynamic_schemas_only_allow_exact_user_task_sources():
    packet = sources()
    ps, rs = m.plan_schema(packet), m.review_schema(packet)
    assert ps["properties"]["goal_source_id"]["enum"] == ["current:4"]
    assert ps["properties"]["goal_source_span"]["enum"] == [SOURCE_TEXT]
    assert rs["properties"]["source_span"]["enum"] == [SOURCE_TEXT]
    assert "enum" not in ps["properties"]["task_goal_jp"]
    filtered, _ = m.task_gate.task_sources(packet)
    fixed = m.review_schema(filtered, valid_plan())
    assert fixed["properties"]["source_id"]["enum"] == ["current:4:clause:0"]
    assert fixed["properties"]["source_span"]["enum"] == [TASK_SPAN]


def test_valid_goal_criterion_action_effect_delivers_in_two_calls():
    call = fake_calls()
    reply, trace = m.deliver_goal_progress(SOURCE_TEXT, "一緒に考えよ。", help_logic(), sources(), call)
    assert reply == valid_plan()["instruction_jp"] and trace["delivered"]
    assert trace["model_calls_completed"] == 2
    state = trace[m.LABEL]
    assert state["formed_before_surface"] and state["content_passed"] and state["surface_passed"]
    assert state["progress_criterion"] == "見出しが三つ書かれた状態"
    assert state["counterfactual"]["before_jp"] != state["counterfactual"]["after_jp"]
    assert state["long_term_memory_write"] is False


def test_random_action_is_content_failure_even_when_surface_passes(monkeypatch):
    plan = valid_plan()
    plan.update(task_goal_jp="本棚を整理する", progress_criterion_jp="本棚が整理された状態",
                progress_mechanism="group_by_rule",
                action_object_jp="本", action_verb_jp="入れ替える",
                action_step_jp="隣り合う本を入れ替える",
                expected_state_change_jp="二冊の位置が逆になる",
                completion_jp="二冊を入れ替えたら止める",
                instruction_jp="隣り合う本を一冊ずつ入れ替えて、そこで止めよ。")
    review = valid_review()
    review["content_checks"]["criterion_advances_goal"] = False
    review["content_checks"]["not_random_or_task_relabeling"] = False
    review["observed_progress_mechanism"] = "random_rearrangement"
    monkeypatch.setenv("URUHA_M46_ISOLATED_DIAGNOSTIC", "1")
    reply, trace = m.deliver_goal_progress(SOURCE_TEXT, "元の返事。", help_logic(), sources(), fake_calls(plan, review))
    assert reply == base.UNAVAILABLE and not trace["delivered"]
    assert trace["status"] == "withheld_progress_review_failed"
    assert trace[m.LABEL]["surface_passed"] and not trace[m.LABEL]["content_passed"]
    assert trace[m.LABEL]["diagnostic"]["rejected_candidate_jp"] == plan["instruction_jp"]
    assert trace[m.LABEL]["diagnostic"]["long_term_memory_write"] is False


def test_broad_task_rephrased_as_first_part_is_not_operational_method():
    review = valid_review()
    review["content_checks"]["action_is_operationally_specific"] = False
    reply, trace = m.deliver_goal_progress(SOURCE_TEXT, "元。", help_logic(), sources(),
                                           fake_calls(review=review))
    assert reply == base.UNAVAILABLE and not trace["delivered"]
    assert "content_action_is_operationally_specific_not_passed" in trace["violations"]


def test_two_allowed_mechanism_labels_are_visible_ambiguity_not_false_failure():
    review = valid_review()
    review["observed_progress_mechanism"] = "direct_atomic_completion"
    reply, trace = m.deliver_goal_progress(SOURCE_TEXT, "元。", help_logic(), sources(),
                                           fake_calls(review=review))
    assert trace["delivered"] and reply == valid_plan()["instruction_jp"]
    assert trace[m.LABEL]["mechanism_exact_agreement"] is False


def test_content_and_surface_failures_are_not_collapsed(monkeypatch):
    review = valid_review()
    review["surface_checks"]["casual_japanese"] = False
    monkeypatch.setenv("URUHA_M46_ISOLATED_DIAGNOSTIC", "1")
    _, trace = m.deliver_goal_progress(SOURCE_TEXT, "元の返事。", help_logic(), sources(), fake_calls(review=review))
    assert trace["status"] == "withheld_surface_review_failed"
    assert trace[m.LABEL]["content_passed"] and not trace[m.LABEL]["surface_passed"]
    assert trace[m.LABEL]["content_violations"] == []
    assert "casual_japanese" in trace[m.LABEL]["surface_violations"]


def test_missing_task_forms_no_goal_and_makes_zero_model_calls():
    def forbidden(*args):
        raise AssertionError("No task evidence means no model call")
    text = "Give me one practical step."
    reply, trace = m.deliver_goal_progress(text, "何かしよ。", help_logic(),
                                           base.source_packet(text), forbidden)
    assert "どの作業" in reply and trace["model_calls_attempted"] == 0
    assert trace[m.LABEL]["status"] == "awaiting_task"
    assert trace[m.LABEL]["formed_before_surface"] is False


def test_model_needs_context_uses_canonical_visible_spacing():
    plan = valid_plan()
    plan["status"] = "needs_context"
    call = fake_calls(plan)
    reply, trace = m.deliver_goal_progress(SOURCE_TEXT, "元。", help_logic(), sources(), call)
    assert reply == base.CLARIFY.replace("\u3000", " ")
    assert "\u3000" not in reply and trace["status"] == "awaiting_context"
    assert trace["model_calls_completed"] == 1


def test_invalid_goal_source_and_task_relabel_are_rejected_before_review():
    for update in ({"goal_source_span": "invented"},
                   {"progress_criterion_jp": "報告書の作成を進める"}):
        plan = valid_plan(); plan.update(update)
        call = fake_calls(plan)
        _, trace = m.deliver_goal_progress(SOURCE_TEXT, "元。", help_logic(), sources(), call)
        assert trace["status"] == "withheld_goal_plan_failed"
        assert trace["model_calls_completed"] == 1 and len(call.calls) == 1


def test_rejected_candidate_is_digest_only_outside_isolated_diagnostic(monkeypatch):
    monkeypatch.delenv("URUHA_M46_ISOLATED_DIAGNOSTIC", raising=False)
    review = valid_review(); review["content_checks"]["action_changes_task_state"] = False
    _, trace = m.deliver_goal_progress(SOURCE_TEXT, "元。", help_logic(), sources(), fake_calls(review=review))
    diagnostic = trace[m.LABEL]["diagnostic"]
    assert "rejected_candidate_jp" not in diagnostic and diagnostic["candidate_digest"]
    assert SOURCE_TEXT not in json.dumps(trace, ensure_ascii=False)


def test_m46_runtime_node_is_unique_connected_and_card_explains_flow():
    _, trace = m.deliver_goal_progress(SOURCE_TEXT, "元。", help_logic(), sources(), fake_calls())
    result = {"logic": {base.LABEL: trace},
              "runtime_trace": {"cycle_index": 4, "blackboard": [
                  {"label": "utterance", "stage": "speak", "payload": {"reply": valid_plan()["instruction_jp"]}}]},
              "runtime_state": {"recent_turn_traces": [{"cycle_index": 4}]}}
    m.materialize_trace_m46(result)
    m.materialize_trace_m46(result)
    graph = collect_cognitive_graph(result)
    nodes = [node for node in graph["nodes"] if node.get("label") == m.LABEL]
    assert len(nodes) == 1
    assert any(edge["source"] == nodes[0]["id"] or edge["target"] == nodes[0]["id"]
               for edge in graph["edges"])
    assert result["runtime_state"]["recent_turn_traces"][-1][m.LABEL]["long_term_memory_write"] is False
    html = m.render_m46(result)
    for phrase in ("真正要前進的任務", "什麼狀態算有前進", "做完應改變什麼", "不是讀心"):
        assert phrase in html


def test_nonhelp_policy_remains_unchanged_and_zero_call(monkeypatch):
    def forbidden(*args):
        raise AssertionError("Non-help must not call M46")
    logic = dict(help_logic(), desired_response_policy_m18="listen_presence")
    reply, trace = m.deliver_goal_progress("今日は疲れた。", "ここにいる。", logic, [], forbidden)
    assert reply == "ここにいる。" and trace["status"] == "not_applicable"
    assert trace["model_calls_attempted"] == 0
