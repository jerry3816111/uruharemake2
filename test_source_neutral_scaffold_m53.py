from copy import deepcopy
import json

import uruha_actionable_help_delivery_m45 as action45
import uruha_candidate_realization_m52 as m52
import uruha_current_task_source_bundle_m50 as m50
import uruha_goal_progress_delivery_m46 as m46
import uruha_source_neutral_scaffold_m53 as m53
import uruha_state_changing_candidates_m51 as m51
from test_actionable_help_delivery_m45 import help_logic
from test_candidate_realization_m52 import REPORT, report_batch, review, sources
from uruha_memory_observatory import collect_cognitive_graph


def invented_plan():
    batch = report_batch()
    item = batch["items"][0]
    item.update(
        object="「環境」「経済」「社会」の三つのカテゴリ",
        verb="設定する",
        effect="三つのカテゴリに対応する見出し枠ができる",
        stop="三つ目のカテゴリ枠が表示されたら停止する",
        instruction="「環境」「経済」「社会」の三つのカテゴリを設定し、それぞれに対応する見出しの枠を表示させる。三つ目のカテゴリ枠が表示されたら停止する。",
    )
    batch["items"][1] = deepcopy(item)
    batch["items"][1]["instruction"] = "「環境」「経済」「社会」の三つのカテゴリを設定し、三つの見出し枠を並べる。三つ並んだら停止する。"
    return m52.select_candidate_batch_m52(batch, sources())[0]


def neutral_plan():
    return m52.select_candidate_batch_m52(report_batch(), sources())[0]


def test_unsupported_concrete_quoted_labels_are_blocked_without_plan_rewrite():
    plan = invented_plan(); before = deepcopy(plan)
    violations = m53.structural_plan_violations_m53(plan, sources())
    state = m53._state_for(plan)
    assert "unsupported_concrete_scaffold_label_m53" in violations
    assert state["status"] == "blocked" and state["unsupported_count"] == 3
    assert plan == before and state["plan_changed"] is False
    payload = json.dumps(state, ensure_ascii=False)
    for label in ("環境", "経済", "社会"):
        assert label not in payload


def test_neutral_scaffold_roles_are_authorized_without_source_claim():
    plan = neutral_plan()
    assert m53.structural_plan_violations_m53(plan, sources()) == []
    state = m53._state_for(plan)
    assert state["status"] == "authorized"
    assert state["neutral_role_count"] == 3 and state["exact_source_count"] == 0


def test_exact_source_quoted_labels_are_authorized():
    text = "レポートは「環境」「経済」「社会」の三部構成にする。見出しを三つ作る手順を教えて。"
    packet = [{"id": "current:4", "kind": "current_user", "text": text}]
    plan = invented_plan(); plan["goal_source_id"] = "current:4"; plan["goal_source_span"] = text
    assert m53.structural_plan_violations_m53(plan, packet) == []
    state = m53._state_for(plan)
    assert state["exact_source_count"] == 3 and state["unsupported_count"] == 0


def test_unquoted_color_grouping_does_not_get_false_blocked():
    text = "赤い紙と青い紙を色ごとに分ける手順を一つ教えて。"
    packet = [{"id": "current:4", "kind": "current_user", "text": text}]
    plan = neutral_plan(); plan.update(
        goal_source_id="current:4", goal_source_span=text, task_goal_jp="紙を色ごとに分ける",
        progress_criterion_jp="紙が赤と青の二群になる", progress_mechanism="group_by_rule",
        action_object_jp="赤い紙と青い紙", action_verb_jp="置く",
        action_step_jp="赤い紙と青い紙を赤は左、青は右に置く",
        expected_state_change_jp="紙が赤と青の二群になる", completion_jp="全部置いたら停止する",
        unknown_constraint_jp="", instruction_jp="赤い紙と青い紙を赤は左、青は右に置いてみよ。全部置いたら止めよ。",
    )
    assert m53.structural_plan_violations_m53(plan, packet) == []
    assert m53._state_for(plan)["status"] == "no_named_labels"


def test_same_model_all_true_review_cannot_override_unsupported_labels(monkeypatch):
    monkeypatch.setattr(m51.m46.task_gate, "task_sources", m50.task_sources_m50)
    monkeypatch.setattr(m51, "select_candidate_batch", m52.select_candidate_batch_m52)
    monkeypatch.setattr(m46, "structural_plan_violations", m53.structural_plan_violations_m53)
    calls = []
    def caller(system, payload, schema, deadline, metrics):
        calls.append(1); metrics["model_calls_attempted"] += 1; metrics["model_calls_completed"] += 1
        source = payload["user_sources"][0]
        batch = report_batch(source["id"], source["text"])
        for item in batch["items"]:
            item.update(object="「環境」「経済」「社会」の三つのカテゴリ", verb="設定する",
                        effect="三つのカテゴリに対応する見出し枠ができる",
                        stop="三つ目のカテゴリ枠が表示されたら停止する",
                        instruction="「環境」「経済」「社会」の三つのカテゴリを設定し、見出し枠を表示させる。三つ目が表示されたら停止する。")
        return batch
    _, trace = m51.deliver_m51(REPORT, "元。", help_logic(), sources(), caller)
    assert len(calls) == 1 and trace["delivered"] is False
    assert "unsupported_concrete_scaffold_label_m53" in trace["violations"]


def test_m53_node_is_unique_connected_and_card_has_honest_boundary(monkeypatch):
    state = m53.authorize_named_scaffold_m53(invented_plan(), sources())
    result = {"logic": {m46.LABEL: {m53.LABEL: state}}, "runtime_trace": {"cycle_index": 6,
              "blackboard": [{"label": "utterance", "stage": "speak", "payload": {"reply": "保留。"}}]},
              "runtime_state": {"recent_turn_traces": [{"cycle_index": 6}]}}
    monkeypatch.setattr(m53, "_PREVIOUS_MATERIALIZE", lambda result, feedback=None: None)
    m53.materialize_trace_m53(result); m53.materialize_trace_m53(result)
    graph = collect_cognitive_graph(result)
    nodes = [node for node in graph["nodes"] if node.get("label") == m53.LABEL]
    assert len(nodes) == 1
    assert any(edge["source"] == nodes[0]["id"] or edge["target"] == nodes[0]["id"] for edge in graph["edges"])
    html = m53.render_m53(result)
    for phrase in ("來源給的，還是系統自己編的", "無來源的具體主題直接阻擋", "不是通用幻覺偵測"):
        assert phrase in html
