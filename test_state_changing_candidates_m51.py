from copy import deepcopy
import json

import uruha_crosslingual_help_routing_m47 as m47
import uruha_route_qualified_task_handoff_m49 as m49
import uruha_current_task_source_bundle_m50 as m50
import uruha_state_changing_candidates_m51 as m51
import uruha_goal_progress_delivery_m46 as m46
import uruha_actionable_help_delivery_m45 as action45
from test_actionable_help_delivery_m45 import help_logic
from uruha_memory_observatory import collect_cognitive_graph


m47.install_m47_crosslingual_help_routing(); m49.install_m49_route_qualified_task_handoff()
m50._PREVIOUS_TASK_SOURCES = m49.task_sources_m49
COLOR = "机に赤い紙と青い紙が混ざってる。色ごとに分ける手順を一つだけ教えて。"


def packet(text=COLOR): return [{"id": "current:4", "kind": "current_user", "text": text}]


def candidate_batch(source_id, source_span, duplicate=False):
    good = {"mechanism": "group_by_rule", "object": "赤い紙と青い紙", "verb": "置く",
            "effect": "紙が赤と青の二群になる", "stop": "全部置いたら止める",
            "instruction": "赤い紙と青い紙を赤は左、青は右に置いて、全部置いたら止めよ。"}
    bad = {"mechanism": "same_task_smaller_unit", "object": "紙", "verb": "分ける",
           "effect": "紙が分かれる", "stop": "分けたら止める",
           "instruction": "紙を分けて、分けたら止めよ。"}
    return {"sid": source_id, "span": source_span, "goal": "紙を色ごとに分ける",
            "unknown": "", "items": [good, deepcopy(good) if duplicate else bad]}


def review(source_id, source_span):
    return {"source_id": source_id, "source_span": source_span,
            "counterfactual_before_jp": "赤い紙と青い紙が混ざっている",
            "counterfactual_after_jp": "赤と青が左右に分かれている",
            "observed_progress_mechanism": "group_by_rule",
            "content_checks": {key: True for key in m46.CONTENT_CHECKS},
            "surface_checks": {key: True for key in m46.SURFACE_CHECKS}}


def test_distinct_batch_selects_structurally_valid_candidate_without_raw_trace():
    sources, _ = m50.task_sources_m50(packet()); source = sources[0]
    plan, state = m51.select_candidate_batch(candidate_batch(source["id"], source["text"]), sources)
    assert state["candidate_count"] == 2 and state["unique_candidate_count"] == 2
    assert state["structurally_valid_count"] == 1 and state["selected_index"] == 0
    assert not m46.structural_plan_violations(plan, sources)
    assert COLOR not in json.dumps(state, ensure_ascii=False)
    assert state["raw_candidate_text_persisted"] is False


def test_duplicate_candidate_gets_no_second_credit():
    sources, _ = m50.task_sources_m50(packet()); source = sources[0]
    _, state = m51.select_candidate_batch(candidate_batch(source["id"], source["text"], True), sources)
    assert state["candidate_count"] == 2 and state["unique_candidate_count"] == 1
    assert state["structurally_valid_count"] == 1
    assert "duplicate_candidate" in state["candidates"][1]["violations"]


def test_compound_verb_field_only_keeps_trailing_realized_dictionary_verb():
    instruction = "見出しを三つのカテゴリに分けてリスト化する。三つ揃ったら止めよ。"
    assert m51._single_realized_verb("分類してリスト化する", instruction) == "リスト化する"
    assert m51._single_realized_verb("分類して要約する", instruction) == "分類して要約する"


def test_m51_candidate_then_original_m46_review_can_deliver(monkeypatch):
    monkeypatch.setattr(m51.m46.task_gate, "task_sources", m50.task_sources_m50)
    sources, _ = m50.task_sources_m50(packet()); source = sources[0]; calls = []
    def caller(system, payload, schema, deadline, metrics):
        calls.append((system, deepcopy(payload), deepcopy(schema)))
        metrics["model_calls_attempted"] += 1; metrics["model_calls_completed"] += 1
        return candidate_batch(source["id"], source["text"]) if len(calls) == 1 else review(source["id"], source["text"])
    final, trace = m51.deliver_m51(COLOR, "元。", help_logic(), packet(), caller)
    assert trace["delivered"] and "赤は左" in final
    state = trace[m51.LABEL]
    assert state["candidate_count"] == 2 and state["selected_structurally_valid"] is True
    assert state["m46_status"] == "verified"


def test_missing_task_does_not_invoke_candidate_model(monkeypatch):
    monkeypatch.setattr(m51.m46.task_gate, "task_sources", m50.task_sources_m50)
    def forbidden(*args): raise AssertionError("candidate model must not run")
    final, trace = m51.deliver_m51("Give me one practical step.", "元。", help_logic(), packet("Give me one practical step."), forbidden)
    assert trace["status"] == "awaiting_context" and trace["model_calls_attempted"] == 0
    assert trace[m51.LABEL]["status"] == "not_invoked" and "どの作業" in final


def test_nonhelp_boundary_does_not_invoke_candidates():
    logic = dict(help_logic(), desired_response_policy_m18="listen_presence")
    def forbidden(*args): raise AssertionError("candidate model must not run")
    final, trace = m51.deliver_m51("方法はいらない。", "ここにいる。", logic, packet("方法はいらない。"), forbidden)
    assert final == "ここにいる。" and trace["status"] == "not_applicable"
    assert trace[m51.LABEL]["candidate_count"] == 0


def test_m51_node_and_card_show_candidates_without_claiming_usefulness(monkeypatch):
    monkeypatch.setattr(m51.m46.task_gate, "task_sources", m50.task_sources_m50)
    sources, _ = m50.task_sources_m50(packet()); source = sources[0]; calls = []
    def caller(system, payload, schema, deadline, metrics):
        calls.append(1); metrics["model_calls_attempted"] += 1; metrics["model_calls_completed"] += 1
        return candidate_batch(source["id"], source["text"]) if len(calls) == 1 else review(source["id"], source["text"])
    final, trace = m51.deliver_m51(COLOR, "元。", help_logic(), packet(), caller)
    result = {"logic": {action45.LABEL: trace}, "runtime_trace": {"cycle_index": 4, "blackboard": [
        {"label": "utterance", "stage": "speak", "payload": {"reply": final}}]},
        "runtime_state": {"recent_turn_traces": [{"cycle_index": 4}]}}
    m51.materialize_trace_m51(result); m51.materialize_trace_m51(result)
    graph = collect_cognitive_graph(result); nodes = [n for n in graph["nodes"] if n.get("label") == m51.LABEL]
    assert len(nodes) == 1 and any(e["source"] == nodes[0]["id"] or e["target"] == nodes[0]["id"] for e in graph["edges"])
    html = m51.render_m51(result)
    for phrase in ("比原任務更具體的狀態改變", "候選存在不等於有用", "原 M46 counterfactual review"):
        assert phrase in html
