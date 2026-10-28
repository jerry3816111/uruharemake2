"""Product-only first-step route; frozen M47 evidence remains unchanged."""

import json
import subprocess
import sys
import textwrap

import pytest

import uruha_crosslingual_help_routing_m47 as m47
import uruha_explicit_first_step_route_p4 as firststep
from uruha_explicit_first_step_route_p4 import (
    classify_first_step_route_p4,
)


POSITIVES = (
    ("桌上有兩本筆記本，我現在只想先整理一件東西。你會叫我先做什麼？", "zh"),
    ("我要開始寫報告，現在還是空白的。我該先做什麼？", "zh"),
    ("ノートを整理したい。まず何をすればいい？", "ja"),
    ("我想整理練習題。你會叫我先做什麼？", "zh"),
    ("例題を整理したい。まず何をすればいい？", "ja"),
)
NEGATIVES = (
    "我該先做什麼？",
    "先做什麼只是標題。",
    "朋友問我：「我該先做什麼？」",
    "朋友問我該先做什麼。",
    "朋友問我該先做什麼？",
    "我想整理筆記本。弟弟說我該先做什麼？",
    "我想整理筆記本。例句：'我該先做什麼？",
    "我想整理筆記本。這是練習題：我該先做什麼？",
    "我想整理筆記本。標題是我該先做什麼？",
    "我想整理筆記本，但我不想真的聽建議。我該先做什麼？",
    "我要整理筆記本，不要回答。我該先做什麼？",
    "友達が「まず何をすればいい？」と言った。",
    "不要給我方法，我只是在抱怨。",
    "我不想要建議。報告還是空白的。我該先做什麼？",
    "死にたい。まず何をすればいい？",
    "ノートを整理したい。まず何をすればいい？　彼女が聞いてた。",
)


@pytest.mark.parametrize("source,language", POSITIVES)
def test_explicit_current_user_first_step_has_exact_task_and_cue(source, language):
    old = firststep._PRIOR_CLASSIFIER(source)
    assert old["status"] == "no_explicit_help_route"
    route = classify_first_step_route_p4(source)
    assert route["schema"] == m47.SCHEMA
    assert route["status"] == "practical_help_authorized"
    assert route["direction"] == "authorize"
    assert route["language"] == language
    assert route["selected_policy"] == "solve_regulation"
    assert route["negated_policy"] is None
    assert route["detected"] is True
    assert route["input_digest"] == m47._digest(source)
    assert route["cue_id"].startswith(f"solve_regulation:{language}:p4:first_step:")
    cue = route["desired_response_span"]
    assert cue["source"] == "current_user_input"
    assert cue["role"] == "desired_response_clause"
    assert cue["span_digest"] == m47._digest(source[cue["start"]:cue["end"]])
    assert route["task_spans"]
    assert all(
        row["role"] in {"task_clause", "task_clause_prefix"}
        and row["source"] == "current_user_input"
        and row["end"] <= cue["start"]
        and row["span_digest"] == m47._digest(source[row["start"]:row["end"]])
        for row in route["task_spans"]
    )
    assert route["raw_dialogue_persisted"] is False
    assert route["long_term_memory_write"] is False
    assert route["classifier_model_call_added"] is False
    assert source not in json.dumps(route, ensure_ascii=False)


@pytest.mark.parametrize("source", NEGATIVES)
def test_existing_forbid_or_unverified_cases_are_not_promoted(source):
    previous = firststep._PRIOR_CLASSIFIER(source)
    assert classify_first_step_route_p4(source) == previous
    assert previous["status"] != "practical_help_authorized"


def test_existing_english_route_is_byte_for_byte_unchanged():
    source = "There are two notebooks. What should I do first?"
    previous = firststep._PRIOR_CLASSIFIER(source)
    assert previous["status"] == "practical_help_authorized"
    assert classify_first_step_route_p4(source) == previous


def test_product_overlay_reuses_m47_policy_atoms_and_graph_without_reply_claim():
    script = textwrap.dedent("""
        import json
        import uruha_adaptive_person_model as adaptive
        import uruha_crosslingual_help_routing_m47 as m47
        import uruha_explicit_first_step_route_p4 as firststep
        from uruha_memory_observatory import collect_cognitive_graph

        m47.install_m47_crosslingual_help_routing()
        assert firststep.install_explicit_first_step_route_p4() is True
        assert firststep.install_explicit_first_step_route_p4() is False
        source = "桌上有兩本筆記本，我現在只想先整理一件東西。你會叫我先做什麼？"
        explicit = adaptive.classify_explicit_desired_response_m25(source)
        route = explicit[m47.LABEL]
        assert route["status"] == "practical_help_authorized"
        assert explicit["selected_policy"] == "solve_regulation"
        assert explicit["authority"] == "current_explicit_desired_response"
        assignments = adaptive._explicit_atom_assignments(source)
        assert assignments["solution_request"][0] == 0.99
        result = {
            "logic": {
                "explicit_desired_response_m25": explicit,
                "desired_response_policy_m18": "solve_regulation",
                "actionable_help_delivery_m45": {
                    "status": "withheld_goal_plan_failed",
                    "goal_progress_delivery_m46": {"status": "plan_rejected"},
                },
            },
            "runtime_trace": {
                "cycle_index": 1,
                "blackboard": [
                    {"label": "utterance", "stage": "speak", "payload": {"reply": "まだ答えられない。"}}
                ],
            },
            "runtime_state": {"recent_turn_traces": [{"cycle_index": 1}]},
        }
        m47.materialize_trace_m47(result)
        graph = collect_cognitive_graph(result)
        assert result["logic"][m47.LABEL]["route_consistent"] is True
        assert result["logic"][m47.LABEL]["m46_should_intervene"] is True
        assert result["logic"][m47.LABEL]["m46_did_intervene"] is True
        labels = {node["label"] for node in graph["nodes"]}
        assert m47.LABEL in labels and "utterance" in labels
        assert result["logic"][m47.LABEL]["m46_delivery_status"] == "withheld_goal_plan_failed"
        print(json.dumps({"status": "ok"}))
    """)
    completed = subprocess.run(
        [sys.executable, "-c", script], capture_output=True, text=True,
        check=False, timeout=30,
    )
    assert completed.returncode == 0, completed.stderr
    assert json.loads(completed.stdout.splitlines()[-1]) == {"status": "ok"}
