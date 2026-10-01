from copy import deepcopy
import json

import uruha_crosslingual_help_routing_m47 as m47
import uruha_route_qualified_task_handoff_m49 as m49
import uruha_goal_progress_delivery_m46 as m46
import uruha_actionable_help_delivery_m45 as action45
from test_actionable_help_delivery_m45 import help_logic
from uruha_memory_observatory import collect_cognitive_graph


m47.install_m47_crosslingual_help_routing()
m49.install_m49_route_qualified_task_handoff()

REPORT_TEXT = "レポートが白紙。見出しを三つ作るために、今できる一歩を教えて。"
COLOR_TEXT = "机に赤い紙と青い紙が混ざってる。色ごとに分ける手順を一つだけ教えて。"


def packet(text, source_id="current:4"):
    return [{"id": source_id, "kind": "current_user", "text": text}]


def test_embedded_task_prefix_is_added_without_duplicating_independent_clause():
    kept, gate = m49.task_sources_m49(packet(REPORT_TEXT))
    assert [(row["id"], row["text"]) for row in kept] == [
        ("current:4:clause:0", "レポートが白紙。"),
        ("current:4:m49:1", "見出しを三つ作るために"),
    ]
    state = gate[m49.LABEL]
    assert state["base_allowed_count"] == 1
    assert state["added_count"] == 1
    assert state["final_allowed_count"] == 2
    assert state["added_sources"][0]["origin"]["span_start"] == 8
    assert REPORT_TEXT not in json.dumps(state, ensure_ascii=False)


def test_grouping_rule_inside_request_clause_reaches_m46_source_schema():
    kept, gate = m49.task_sources_m49(packet(COLOR_TEXT))
    assert kept[-1]["text"] == "色ごとに分ける"
    assert kept[-1]["source_role"] == "route_qualified_task_span_m49"
    schema = m46.plan_schema(kept)
    assert "current:4:m49:1" in schema["properties"]["goal_source_id"]["enum"]
    assert "色ごとに分ける" in schema["properties"]["goal_source_span"]["enum"]
    assert gate[m49.LABEL]["added_count"] == 1


def test_pure_request_negative_and_method_mention_add_no_task_source():
    cases = (
        "Give me one practical step.",
        "方法はいらない。ただ聞いてほしい。",
        "我昨天看過這個方法，但還沒決定。",
    )
    for text in cases:
        kept, gate = m49.task_sources_m49(packet(text))
        assert gate[m49.LABEL]["added_count"] == 0
        assert all(row.get("source_role") != "route_qualified_task_span_m49" for row in kept)


def test_meta_correction_prefix_is_not_promoted_to_task_evidence():
    kept, gate = m49.task_sources_m49(packet("You misunderstood; give me a method."))
    assert kept == []
    state = gate[m49.LABEL]
    assert state["added_count"] == 0
    assert "isolated_response_or_correction_span" in {
        row["reason"] for row in state["rejected"]
    }


def test_tampered_digest_and_response_overlap_fail_closed(monkeypatch):
    original = m49.m47.classify_help_route_m47
    def tampered(text):
        result = deepcopy(original(text))
        result["task_spans"] = [
            {"role": "task_clause_prefix", "start": 8, "end": 20,
             "span_digest": "tampered"},
            {"role": "task_clause_prefix", "start": 20, "end": 30,
             "span_digest": action45.digest(text[20:30])},
        ]
        return result
    monkeypatch.setattr(m49.m47, "classify_help_route_m47", tampered)
    kept, gate = m49.task_sources_m49(packet(REPORT_TEXT))
    assert not any(row.get("source_role") == "route_qualified_task_span_m49" for row in kept)
    reasons = {row["reason"] for row in gate[m49.LABEL]["rejected"]}
    assert "m47_span_digest_mismatch" in reasons
    assert "overlaps_response_form_evidence" in reasons


def valid_plan_for_added_source():
    return {
        "status": "action",
        "goal_source_id": "current:4:m49:1",
        "goal_source_span": "見出しを三つ作るために",
        "task_goal_jp": "見出しを三つ作る",
        "criterion_basis": "direct_from_source",
        "progress_criterion_jp": "見出しが三つ並んでいる状態",
        "progress_mechanism": "structure_scaffold",
        "action_object_jp": "見出しを三つ",
        "action_verb_jp": "書く",
        "action_step_jp": "見出しを三つだけ書く",
        "expected_state_change_jp": "レポートに三つの構成位置ができる",
        "completion_jp": "見出しを三つ書いたら止める",
        "unknown_constraint_jp": "見出しの内容は未定",
        "instruction_jp": "まず見出しを三つだけ書いて、そこで止めよ。",
    }


def valid_review_for_added_source():
    return {
        "source_id": "current:4:m49:1",
        "source_span": "見出しを三つ作るために",
        "counterfactual_before_jp": "レポートに見出しがない状態",
        "counterfactual_after_jp": "見出しが三つ並んでいる状態",
        "observed_progress_mechanism": "structure_scaffold",
        "content_checks": {key: True for key in m46.CONTENT_CHECKS},
        "surface_checks": {key: True for key in m46.SURFACE_CHECKS},
    }


def test_m46_can_bind_goal_and_review_to_added_exact_task_span():
    calls = []
    def caller(system, payload, schema, deadline, metrics):
        calls.append((deepcopy(payload), deepcopy(schema)))
        metrics["model_calls_attempted"] += 1
        metrics["model_calls_completed"] += 1
        return valid_plan_for_added_source() if len(calls) == 1 else valid_review_for_added_source()
    reply, trace = m46.deliver_goal_progress(
        REPORT_TEXT, "元。", help_logic(), packet(REPORT_TEXT), caller
    )
    assert trace["delivered"] and "見出しを三つ" in reply
    assert calls[0][0]["user_sources"][-1]["text"] == "見出しを三つ作るために"
    state = trace[m49.task_gate.LABEL][m49.LABEL]
    assert state["added_count"] == 1


def test_m49_node_is_unique_connected_and_card_does_not_claim_plan_use():
    calls = []
    def caller(system, payload, schema, deadline, metrics):
        calls.append(1)
        metrics["model_calls_attempted"] += 1
        metrics["model_calls_completed"] += 1
        return valid_plan_for_added_source() if len(calls) == 1 else valid_review_for_added_source()
    reply, trace = m46.deliver_goal_progress(REPORT_TEXT, "元。", help_logic(), packet(REPORT_TEXT), caller)
    result = {
        "logic": {action45.LABEL: trace},
        "runtime_trace": {"cycle_index": 4, "blackboard": [
            {"label": "utterance", "stage": "speak", "payload": {"reply": reply}}]},
        "runtime_state": {"recent_turn_traces": [{"cycle_index": 4}]},
    }
    m49.materialize_trace_m49(result)
    m49.materialize_trace_m49(result)
    graph = collect_cognitive_graph(result)
    nodes = [node for node in graph["nodes"] if node.get("label") == m49.LABEL]
    assert len(nodes) == 1
    assert any(edge["source"] == nodes[0]["id"] or edge["target"] == nodes[0]["id"]
               for edge in graph["edges"])
    state = result["logic"][m49.LABEL]
    assert state["goal_selected_added_span"] is True
    html = m49.render_m49(result)
    for phrase in ("任務內容有沒有在進 planner 前消失", "送達不等於模型有遵守", "planner goal 綁到新增 span"):
        assert phrase in html
