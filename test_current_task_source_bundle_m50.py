from copy import deepcopy
import json

import uruha_crosslingual_help_routing_m47 as m47
import uruha_route_qualified_task_handoff_m49 as m49
import uruha_current_task_source_bundle_m50 as m50
import uruha_goal_progress_delivery_m46 as m46
import uruha_actionable_help_delivery_m45 as action45
from test_actionable_help_delivery_m45 import help_logic
from uruha_memory_observatory import collect_cognitive_graph


m47.install_m47_crosslingual_help_routing()
m49.install_m49_route_qualified_task_handoff()
# Direct M50 unit tests call the overlay explicitly. Do not install it for the
# whole pytest process, because that would rewrite M49's frozen integration
# contract while its own tests are collected in the same run.
m50._PREVIOUS_TASK_SOURCES = m49.task_sources_m49

REPORT = "レポートが白紙。見出しを三つ作るために、今できる一歩を教えて。"
COLOR = "机に赤い紙と青い紙が混ざってる。色ごとに分ける手順を一つだけ教えて。"


def packet(text, source_id="current:4"):
    return [{"id": source_id, "kind": "current_user", "text": text}]


def test_report_fragments_become_one_exact_component_bundle():
    kept, gate = m50.task_sources_m50(packet(REPORT))
    assert len(kept) == 1
    assert kept[0]["id"] == "current:4:m50:bundle"
    assert kept[0]["text"] == "レポートが白紙。\n見出しを三つ作るために"
    state = gate[m50.LABEL]
    assert state["status"] == "bundled" and state["bundle_count"] == 1
    assert state["final_source_count"] == 1
    origin = state["bundles"][0]["origin"]
    assert [row["span_start"] for row in origin["components"]] == [0, 8]
    assert REPORT not in json.dumps(state, ensure_ascii=False)


def test_color_bundle_is_the_only_m46_goal_source_option():
    kept, gate = m50.task_sources_m50(packet(COLOR))
    assert kept[0]["text"] == "机に赤い紙と青い紙が混ざってる。\n色ごとに分ける"
    schema = m46.plan_schema(kept)
    assert schema["properties"]["goal_source_id"]["enum"] == ["current:4:m50:bundle"]
    assert schema["properties"]["goal_source_span"]["enum"] == [kept[0]["text"]]
    assert gate[m50.LABEL]["semantic_compatibility_proven"] is False


def test_single_source_and_nonhelp_boundaries_are_not_forced_into_bundle():
    cases = (
        "To create three section headings, give me one practical step.",
        "Give me one practical step.",
        "方法はいらない。ただ聞いてほしい。",
        "You misunderstood; give me a method.",
    )
    for text in cases:
        kept, gate = m50.task_sources_m50(packet(text))
        assert gate[m50.LABEL]["bundle_count"] == 0
        assert all(row.get("source_role") != "current_task_bundle_m50" for row in kept)


def test_linked_previous_source_is_never_bundled_with_current_turn():
    sources = packet(REPORT) + [{
        "id": "prior:3", "kind": "linked_previous_user", "text": "昨日のレポートが白紙。"
    }]
    kept, gate = m50.task_sources_m50(sources)
    assert any(row["kind"] == "linked_previous_user" for row in kept)
    bundle = next(row for row in kept if row.get("source_role") == "current_task_bundle_m50")
    assert "昨日" not in bundle["text"] and gate[m50.LABEL]["bundle_count"] == 1


def test_tampered_component_origin_fails_closed(monkeypatch):
    previous = m50._PREVIOUS_TASK_SOURCES
    def tampered(sources):
        kept, gate = previous(sources)
        kept = deepcopy(kept)
        kept[0]["origin"]["span_digest"] = "tampered"
        return kept, gate
    monkeypatch.setattr(m50, "_PREVIOUS_TASK_SOURCES", tampered)
    kept, gate = m50.task_sources_m50(packet(REPORT))
    assert gate[m50.LABEL]["bundle_count"] == 0
    assert "component_origin_mismatch" in {row["reason"] for row in gate[m50.LABEL]["rejected"]}
    assert all(row.get("source_role") != "current_task_bundle_m50" for row in kept)


def bundle_plan(text):
    return {
        "status": "action", "goal_source_id": "current:4:m50:bundle",
        "goal_source_span": text, "task_goal_jp": "紙を色ごとに分ける",
        "criterion_basis": "direct_from_source", "progress_criterion_jp": "赤と青の二群になる",
        "progress_mechanism": "group_by_rule", "action_object_jp": "赤い紙と青い紙",
        "action_verb_jp": "分ける", "action_step_jp": "赤い紙と青い紙を色ごとに分ける",
        "expected_state_change_jp": "紙が赤と青の二群になる", "completion_jp": "全部分けたら止める",
        "unknown_constraint_jp": "", "instruction_jp": "赤い紙と青い紙を色ごとに分けて、全部分けたら止めよ。",
    }


def bundle_review(text):
    return {
        "source_id": "current:4:m50:bundle", "source_span": text,
        "counterfactual_before_jp": "赤い紙と青い紙が混ざっている",
        "counterfactual_after_jp": "赤と青の二群に分かれている",
        "observed_progress_mechanism": "group_by_rule",
        "content_checks": {key: True for key in m46.CONTENT_CHECKS},
        "surface_checks": {key: True for key in m46.SURFACE_CHECKS},
    }


def test_m46_plan_and_review_are_bound_to_complete_bundle(monkeypatch):
    monkeypatch.setattr(m50.task_gate, "task_sources", m50.task_sources_m50)
    kept, _ = m50.task_sources_m50(packet(COLOR))
    text = kept[0]["text"]
    calls = []
    def caller(system, payload, schema, deadline, metrics):
        calls.append(deepcopy(payload)); metrics["model_calls_attempted"] += 1; metrics["model_calls_completed"] += 1
        return bundle_plan(text) if len(calls) == 1 else bundle_review(text)
    reply, trace = m46.deliver_goal_progress(COLOR, "元。", help_logic(), packet(COLOR), caller)
    assert trace["delivered"] and "色ごと" in reply
    assert calls[0]["user_sources"] == kept
    assert trace[m50.task_gate.LABEL][m50.LABEL]["bundle_count"] == 1


def test_m50_node_is_unique_connected_and_card_separates_bundle_from_use(monkeypatch):
    monkeypatch.setattr(m50.task_gate, "task_sources", m50.task_sources_m50)
    kept, _ = m50.task_sources_m50(packet(COLOR)); text = kept[0]["text"]; calls = []
    def caller(system, payload, schema, deadline, metrics):
        calls.append(1); metrics["model_calls_attempted"] += 1; metrics["model_calls_completed"] += 1
        return bundle_plan(text) if len(calls) == 1 else bundle_review(text)
    reply, trace = m46.deliver_goal_progress(COLOR, "元。", help_logic(), packet(COLOR), caller)
    result = {"logic": {action45.LABEL: trace}, "runtime_trace": {"cycle_index": 4, "blackboard": [
        {"label": "utterance", "stage": "speak", "payload": {"reply": reply}}]},
        "runtime_state": {"recent_turn_traces": [{"cycle_index": 4}]}}
    m50.materialize_trace_m50(result); m50.materialize_trace_m50(result)
    graph = collect_cognitive_graph(result)
    nodes = [node for node in graph["nodes"] if node.get("label") == m50.LABEL]
    assert len(nodes) == 1 and any(edge["source"] == nodes[0]["id"] or edge["target"] == nodes[0]["id"] for edge in graph["edges"])
    assert result["logic"][m50.LABEL]["goal_selected_bundle"] is True
    html = m50.render_m50(result)
    for phrase in ("完整任務有沒有被拆成只能任選一段", "結構共現不等於已證明語意相容", "goal 使用完整 bundle"):
        assert phrase in html
