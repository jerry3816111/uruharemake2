import json

import uruha_adaptive_person_model as adaptive
import uruha_crosslingual_help_routing_m47 as m47
from test_personhood_loop_v2_13 import _IsolatedContractBrain
from uruha_memory_observatory import collect_cognitive_graph


m47.install_m47_crosslingual_help_routing()


def test_crosslingual_positive_and_negative_scope_is_explicit():
    cases = {
        "本棚が散らかってる。今できる手順を一つだけ教えて。":
            ("practical_help_authorized", "solve_regulation", "ja"),
        "抽屜裡有信件和收據，現在混在一起。給我一個現在能做的步驟。":
            ("practical_help_authorized", "solve_regulation", "zh"),
        "The report is blank. Give me one practical step.":
            ("practical_help_authorized", "solve_regulation", "en"),
        "方法はいらない。ただ聞いてほしい。":
            ("practical_help_forbidden", "listen_presence", "ja"),
        "不要給我方法，我只是在抱怨。":
            ("practical_help_forbidden", None, "zh"),
        "I don't want advice. Just listen to me.":
            ("practical_help_forbidden", "listen_presence", "en"),
    }
    for text, (status, selected, language) in cases.items():
        result = adaptive.classify_explicit_desired_response_m25(text)
        route = result[m47.LABEL]
        assert route["status"] == status
        assert route["language"] == language
        assert result["selected_policy"] == selected
        if status == "practical_help_forbidden":
            assert "solve_regulation" in result["negated_policies"]
        else:
            assert "solve_regulation" not in result["negated_policies"]


def test_negative_scope_does_not_consume_later_replacement_request():
    text = "不要給我泛泛的方法，給我一個現在能做的步驟。"
    route = m47.classify_help_route_m47(text)
    assert route["status"] == "practical_help_authorized"
    ref = route["desired_response_span"]
    assert text[ref["start"]:ref["end"]] == "給我一個現在能做的步驟"
    assert route["candidate_evidence"][0]["kind"] == "forbid"
    assert route["candidate_evidence"][-1]["kind"] == "authorize"
    assert not route["task_spans"]


def test_method_noun_mention_is_not_rewritten_as_a_solution_request():
    text = "我昨天看過這個方法，但還沒決定。"
    contract = adaptive.classify_explicit_desired_response_m25(text)
    atoms = adaptive._explicit_atom_assignments(text)
    assert contract[m47.LABEL]["status"] == "no_explicit_help_route"
    assert contract["selected_policy"] is None
    assert "solution_request" not in atoms


def test_exact_geometry_is_recoverable_but_raw_dialogue_is_not_duplicated():
    text = "本棚が散らかってる。今できる手順を一つだけ教えて。"
    route = m47.classify_help_route_m47(text)
    desired = route["desired_response_span"]
    task = route["task_spans"][0]
    assert text[desired["start"]:desired["end"]] == "今できる手順を一つだけ教えて"
    assert text[task["start"]:task["end"]] == "本棚が散らかってる"
    assert text not in json.dumps(route, ensure_ascii=False)
    assert route["raw_dialogue_persisted"] is False
    assert route["long_term_memory_write"] is False


def test_runtime_policy_obeys_authorize_forbid_and_nonrequest():
    cases = {
        "本棚が散らかってる。今できる手順を一つだけ教えて。": "solve_regulation",
        "不要給我方法，我只是在抱怨。": None,
        "我昨天看過這個方法，但還沒決定。": None,
    }
    for text, expected in cases.items():
        turn = _IsolatedContractBrain().run_turn_debug(text)
        route = turn["logic"]["explicit_desired_response_m25"][m47.LABEL]
        selected = turn["logic"].get("desired_response_policy_m18")
        assert route["status"] in {
            "practical_help_authorized", "practical_help_forbidden", "no_explicit_help_route"
        }
        if expected is not None:
            assert selected == expected
        else:
            assert selected != "solve_regulation"


def test_m47_node_is_unique_connected_and_card_separates_route_from_delivery():
    text = "本棚が散らかってる。今できる手順を一つだけ教えて。"
    route = m47.classify_help_route_m47(text)
    result = {
        "logic": {
            "explicit_desired_response_m25": {m47.LABEL: route},
            "desired_response_policy_m18": "solve_regulation",
            "actionable_help_delivery_m45": {
                "status": "withheld_goal_plan_failed",
                "goal_progress_delivery_m46": {"status": "plan_rejected"},
            },
        },
        "runtime_trace": {
            "cycle_index": 1,
            "blackboard": [{"label": "utterance", "stage": "speak", "payload": {"reply": "確認する。"}}],
        },
        "runtime_state": {"recent_turn_traces": [{"cycle_index": 1}]},
    }
    m47.materialize_trace_m47(result)
    m47.materialize_trace_m47(result)
    graph = collect_cognitive_graph(result)
    nodes = [node for node in graph["nodes"] if node.get("label") == m47.LABEL]
    assert len(nodes) == 1
    assert any(edge["source"] == nodes[0]["id"] or edge["target"] == nodes[0]["id"]
               for edge in graph["edges"])
    state = result["logic"][m47.LABEL]
    assert state["route_consistent"] is True
    assert state["m46_should_intervene"] is True
    assert state["m46_did_intervene"] is True
    html = m47.render_m47(result)
    for phrase in ("這次是要方法，還是不要方法", "這張卡只證明路由", "M46 行動生成", "路由一致"):
        assert phrase in html


def test_risk_route_is_not_overridden_by_m47():
    text = "死にたい。方法を一つ教えて。"
    result = adaptive.classify_explicit_desired_response_m25(text)
    assert result[m47.LABEL]["status"] == "practical_help_authorized"
    assert result["authority"] == "protected_risk_route"
    assert result["status"] == "blocked_by_protected_risk_cue"
