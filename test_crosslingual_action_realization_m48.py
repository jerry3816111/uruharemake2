from copy import deepcopy

import uruha_crosslingual_action_realization_m48 as m48
import uruha_goal_progress_delivery_m46 as m46
import uruha_actionable_help_delivery_m45 as action45
from test_goal_progress_delivery_m46 import (
    SOURCE_TEXT,
    fake_calls,
    sources,
    valid_plan,
    valid_review,
)
from test_actionable_help_delivery_m45 import help_logic
from uruha_memory_observatory import collect_cognitive_graph


m48.install_m48_crosslingual_action_realization()


def missing_object_and_stop_plan():
    plan = valid_plan()
    plan["instruction_jp"] = "まず見出しを書いてみよ。"
    return plan


def filtered_sources():
    return m46.task_gate.task_sources(sources())[0]


def test_missing_object_and_stop_are_realized_from_existing_fields_only():
    plan = missing_object_and_stop_plan()
    semantic_before = {key: deepcopy(plan[key]) for key in (
        "task_goal_jp", "progress_criterion_jp", "progress_mechanism",
        "action_object_jp", "action_verb_jp", "action_step_jp",
        "expected_state_change_jp", "completion_jp",
    )}
    violations = m48.structural_plan_violations_m48(plan, filtered_sources())
    state = m48._state_for(plan)
    assert violations == []
    assert state["status"] == "repaired"
    assert state["semantic_fields_changed"] is False
    assert state["object_visible"] and state["operation_visible"] and state["stop_visible"]
    assert "見出しを三つ" in plan["instruction_jp"]
    assert "書いてみよ" in plan["instruction_jp"]
    assert "そこで止めよ" in plan["instruction_jp"]
    assert semantic_before == {key: plan[key] for key in semantic_before}


def test_repaired_surface_still_requires_independent_m46_review():
    plan = missing_object_and_stop_plan()
    review = valid_review()
    review["content_checks"]["criterion_advances_goal"] = False
    reply, trace = m46.deliver_goal_progress(
        SOURCE_TEXT, "元。", help_logic(), sources(), fake_calls(plan, review)
    )
    assert reply == action45.UNAVAILABLE
    assert trace["status"] == "withheld_progress_review_failed"
    state = trace[m46.LABEL][m48.LABEL]
    assert state["status"] == "repaired"
    assert state["m46_content_passed"] is False


def test_valid_repair_can_be_delivered_after_review_and_is_not_sent_to_reviewer():
    plan = missing_object_and_stop_plan()
    caller = fake_calls(plan, valid_review())
    reply, trace = m46.deliver_goal_progress(
        SOURCE_TEXT, "元。", help_logic(), sources(), caller
    )
    assert trace["delivered"] and "そこで止めよ" in reply
    assert m48.LABEL not in caller.calls[1][1]["plan"]
    state = trace[m46.LABEL][m48.LABEL]
    assert state["m46_content_passed"] and state["m46_surface_passed"]


def test_nonprogress_mechanism_is_never_repaired_as_a_surface_problem():
    plan = missing_object_and_stop_plan()
    original = plan["instruction_jp"]
    plan["progress_mechanism"] = "same_task_smaller_unit"
    violations = m48.structural_plan_violations_m48(plan, filtered_sources())
    state = m48._state_for(plan)
    assert "nonprogress_or_unknown_mechanism" in violations
    assert state["status"] == "blocked_by_nonrealization_violation"
    assert plan["instruction_jp"] == original


def test_missing_internal_object_binding_fails_closed():
    plan = missing_object_and_stop_plan()
    plan["action_step_jp"] = "紙に三つだけ書く"
    violations = m48.structural_plan_violations_m48(plan, filtered_sources())
    state = m48._state_for(plan)
    assert violations
    assert state["status"] == "repair_failed_closed"
    assert state["reason"] == "action_step_does_not_contain_declared_object"


def test_already_valid_surface_is_not_rewritten():
    plan = valid_plan()
    original = plan["instruction_jp"]
    assert m48.structural_plan_violations_m48(plan, filtered_sources()) == []
    assert plan["instruction_jp"] == original
    assert m48._state_for(plan)["status"] == "not_needed"


def test_bounded_japanese_inflections_cover_current_action_families():
    assert m48._te_form("書く") == "書いて"
    assert m48._te_form("分ける") == "分けて"
    assert m48._te_form("作成する") == "作成して"
    assert m48._te_form("取る") == "取って"
    assert m48._te_form("行く") == "行って"


def test_already_realized_short_command_is_preserved_and_gets_a_stop():
    plan = valid_plan()
    plan.update(
        action_object_jp="手紙と領収書",
        action_verb_jp="分けよ",
        action_step_jp="手紙と領収書を二つに分けよ",
        instruction_jp="まず手前のものを分けよ。",
    )
    assert m48.structural_plan_violations_m48(plan, filtered_sources()) == []
    assert plan["instruction_jp"] == "手紙と領収書を二つに分けよ。それができたら、そこで止めよ。"
    assert m48._state_for(plan)["status"] == "repaired"


def test_m48_node_is_unique_connected_and_card_keeps_review_boundary():
    plan = missing_object_and_stop_plan()
    reply, trace = m46.deliver_goal_progress(
        SOURCE_TEXT, "元。", help_logic(), sources(), fake_calls(plan, valid_review())
    )
    result = {
        "logic": {action45.LABEL: trace},
        "runtime_trace": {
            "cycle_index": 4,
            "blackboard": [{"label": "utterance", "stage": "speak", "payload": {"reply": reply}}],
        },
        "runtime_state": {"recent_turn_traces": [{"cycle_index": 4}]},
    }
    m48.materialize_trace_m48(result)
    m48.materialize_trace_m48(result)
    graph = collect_cognitive_graph(result)
    nodes = [node for node in graph["nodes"] if node.get("label") == m48.LABEL]
    assert len(nodes) == 1
    assert any(edge["source"] == nodes[0]["id"] or edge["target"] == nodes[0]["id"]
               for edge in graph["edges"])
    html = m48.render_m48(result)
    for phrase in ("內部動作有沒有真的落到最後一句", "不能補任務內容", "M46 的有用性審核"):
        assert phrase in html
