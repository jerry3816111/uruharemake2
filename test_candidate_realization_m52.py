from copy import deepcopy

import uruha_actionable_help_delivery_m45 as action45
import uruha_candidate_realization_m52 as m52
import uruha_current_task_source_bundle_m50 as m50
import uruha_goal_progress_delivery_m46 as m46
import uruha_state_changing_candidates_m51 as m51
from test_actionable_help_delivery_m45 import help_logic
from uruha_memory_observatory import collect_cognitive_graph


REPORT = "To create three section headings, give me one practical step."


def sources(text=REPORT):
    return [{"id": "current:4", "kind": "current_user", "text": text}]


def report_batch(source_id="current:4", source_span=REPORT):
    item = {
        "mechanism": "structure_scaffold",
        "object": "「導入」「本論」「結論」という三つのテーマに基づいて見出しを配置する",
        "verb": "作成する",
        "effect": "三つの見出しが文書に並ぶ",
        "stop": "三つ目の見出しが追加されたら停止する",
        "instruction": "「導入」「本論」「結論」という三つのテーマに基づいて、それぞれに対応する見出しを順次作成し、三つ目が完了したら停止する",
    }
    other = {
        "mechanism": "structure_scaffold",
        "object": "三つの見出し",
        "verb": "並べる",
        "effect": "三つの見出し枠が文書にできる",
        "stop": "三つの枠ができたら停止する",
        "instruction": "三つの見出しを上から順に並べる。三つの枠ができたら停止する。",
    }
    return {"sid": source_id, "span": source_span, "goal": "三つの見出しを作る",
            "unknown": "見出しの具体的な内容は不明", "items": [item, other]}


def review(content_pass=True, surface_pass=True, source_id="current:4", source_span=REPORT):
    content = {key: True for key in m46.CONTENT_CHECKS}
    surface = {key: True for key in m46.SURFACE_CHECKS}
    if not content_pass:
        content["criterion_advances_goal"] = False
    if not surface_pass:
        surface["casual_japanese"] = False
    return {"source_id": source_id, "source_span": source_span,
            "counterfactual_before_jp": "見出しがまだない",
            "counterfactual_after_jp": "三つの見出し枠が文書にある",
            "observed_progress_mechanism": "structure_scaffold",
            "content_checks": content, "surface_checks": surface}


def test_object_can_only_shorten_to_text_visible_in_both_generated_fields():
    original = report_batch()["items"][0]
    realized, trace = m52.realize_candidate_m52(original)
    assert realized["object"] == "見出し"
    assert realized["object"] in original["object"] and realized["object"] in realized["instruction"]
    assert trace["object_alignment"] == "shared_visible_substring"
    assert trace["raw_candidate_text_persisted"] is False


def test_goal_effect_stop_and_mechanism_are_byte_for_byte_preserved():
    batch = report_batch(); before = deepcopy(batch)
    plan, state = m52.select_candidate_batch_m52(batch, sources())
    assert state[m52.LABEL]["semantic_fields_unchanged"] is True
    for key in ("sid", "span", "goal", "unknown"):
        assert batch[key] == before[key]
    for index in range(2):
        for key in ("mechanism", "effect", "stop"):
            assert batch["items"][index][key] == before["items"][index][key]
    assert plan["action_object_jp"] in plan["instruction_jp"]
    assert "止めよ" in plan["instruction_jp"]
    assert m46.structural_plan_violations(plan, sources()) == []


def test_no_shared_visible_object_fails_closed_without_inventing_one():
    candidate = report_batch()["items"][0]
    candidate["object"] = "全く別の対象"
    realized, trace = m52.realize_candidate_m52(candidate)
    assert trace["status"] == "blocked" and trace["reason"] == "no_shared_visible_object"
    assert realized == candidate


def test_specification_endings_become_bounded_casual_surface():
    text = "三つのカテゴリを設定し、それぞれの見出し枠を表示させる。三つ目が表示されたら停止する。"
    realized = m52._casualize_instruction(text)
    assert "表示させてみよ" in realized
    assert "表示されたら、そこで止めよ" in realized
    assert "停止する" not in realized


def test_existing_stop_field_is_surfaced_when_instruction_only_contains_a_count():
    candidate = report_batch()["items"][0]
    candidate["stop"] = "三つ目の見出し枠に移動した時"
    candidate["instruction"] = "三つの見出し枠を配置する。"
    candidate["object"] = "三つの見出し枠"
    realized, trace = m52.realize_candidate_m52(candidate)
    assert "三つ目の見出し枠に移動した時、そこで止めよ" in realized["instruction"]
    assert trace["stop_surface_added"] is True and trace["stop_visible_after"] is True
    assert realized["stop"] == candidate["stop"]


def test_m46_content_review_still_blocks_a_realized_candidate(monkeypatch):
    monkeypatch.setattr(m51.m46.task_gate, "task_sources", m50.task_sources_m50)
    monkeypatch.setattr(m51, "select_candidate_batch", m52.select_candidate_batch_m52)
    calls = []
    def caller(system, payload, schema, deadline, metrics):
        calls.append(1); metrics["model_calls_attempted"] += 1; metrics["model_calls_completed"] += 1
        if len(calls) == 1:
            source = payload["user_sources"][0]
            return report_batch(source["id"], source["text"])
        source = payload["sources"][0]
        return review(content_pass=False, source_id=source["id"], source_span=source["text"])
    _, trace = m51.deliver_m51(REPORT, "元。", help_logic(), sources(), caller)
    assert len(calls) == 2
    assert trace["status"] == "withheld_progress_review_failed"
    assert trace[m51.LABEL][m52.LABEL]["added_model_calls"] == 0
    assert trace["delivered"] is False


def test_valid_realization_can_reach_delivery_without_an_extra_model_call(monkeypatch):
    monkeypatch.setattr(m51.m46.task_gate, "task_sources", m50.task_sources_m50)
    monkeypatch.setattr(m51, "select_candidate_batch", m52.select_candidate_batch_m52)
    calls = []
    def caller(system, payload, schema, deadline, metrics):
        calls.append(1); metrics["model_calls_attempted"] += 1; metrics["model_calls_completed"] += 1
        if len(calls) == 1:
            source = payload["user_sources"][0]
            return report_batch(source["id"], source["text"])
        source = payload["sources"][0]
        return review(source_id=source["id"], source_span=source["text"])
    reply, trace = m51.deliver_m51(REPORT, "元。", help_logic(), sources(), caller)
    assert len(calls) == 2 and trace["delivered"] is True
    assert "見出し" in reply and "止めよ" in reply
    assert trace[m51.LABEL][m52.LABEL]["source_goal_unknown_unchanged"] is True


def test_m52_node_is_unique_connected_and_card_states_authority(monkeypatch):
    monkeypatch.setattr(m51.m46.task_gate, "task_sources", m50.task_sources_m50)
    monkeypatch.setattr(m51, "select_candidate_batch", m52.select_candidate_batch_m52)
    calls = []
    def caller(system, payload, schema, deadline, metrics):
        calls.append(1); metrics["model_calls_attempted"] += 1; metrics["model_calls_completed"] += 1
        if len(calls) == 1:
            source = payload["user_sources"][0]
            return report_batch(source["id"], source["text"])
        source = payload["sources"][0]
        return review(source_id=source["id"], source_span=source["text"])
    reply, trace = m51.deliver_m51(REPORT, "元。", help_logic(), sources(), caller)
    result = {"logic": {action45.LABEL: trace}, "runtime_trace": {"cycle_index": 5,
              "blackboard": [{"label": "utterance", "stage": "speak", "payload": {"reply": reply}}]},
              "runtime_state": {"recent_turn_traces": [{"cycle_index": 5}]}}
    monkeypatch.setattr(m52, "_PREVIOUS_MATERIALIZE", m51.materialize_trace_m51)
    m52.materialize_trace_m52(result); m52.materialize_trace_m52(result)
    graph = collect_cognitive_graph(result)
    nodes = [node for node in graph["nodes"] if node.get("label") == m52.LABEL]
    assert len(nodes) == 1
    assert any(edge["source"] == nodes[0]["id"] or edge["target"] == nodes[0]["id"] for edge in graph["edges"])
    html = m52.render_m52(result)
    for phrase in ("操作欄位有沒有真的說成自然日文", "goal、effect、stop 不准改", "M46 仍決定"):
        assert phrase in html
