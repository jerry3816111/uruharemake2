from copy import deepcopy
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

import uruha_actionable_help_delivery_m45 as action45
import uruha_crosslingual_help_routing_m47 as m47
import uruha_current_request_authority_p2 as authority
import uruha_task_evidence_authorization_m45_1 as task_gate
from test_actionable_help_delivery_m45 import help_logic
from uruha_task_evidence_authorization_m45_1 import (
    deliver_with_task_evidence,
)


@pytest.fixture(autouse=True)
def isolated_overlay():
    route = m47.classify_help_route_m47
    materialize = action45.materialize_trace_m45
    task_sources = task_gate.task_sources
    assert authority.install_current_request_authority_p2()
    try:
        yield
    finally:
        m47.classify_help_route_m47 = route
        action45.materialize_trace_m45 = materialize
        task_gate.task_sources = task_sources
        authority._ORIGINAL_ROUTE = None
        authority._ORIGINAL_MATERIALIZE = None
        authority._ORIGINAL_TASK_SOURCES = None
        authority._INSTALLED = False


@pytest.mark.parametrize(
    "text,language",
    [
        ("謝謝。不過現在請幫我想一個做法。", "zh"),
        ("那可以幫我找個辦法嗎？", "zh"),
        ("Now help me come up with one approach.", "en"),
        ("Could you help me decide on the next step?", "en"),
        ("じゃあ、方法を一緒に考えてほしい。", "ja"),
        ("次の一歩を決めてくれない？", "ja"),
    ],
)
def test_natural_request_families_authorize_current_help(text, language):
    route = m47.classify_help_route_m47(text)
    assert route["status"] == "practical_help_authorized"
    assert route["selected_policy"] == "solve_regulation"
    assert route["language"] == language
    assert route[authority.LABEL]["status"] == "natural_help_request_authorized"
    ref = route["desired_response_span"]
    assert authority.m47._digest(text[ref["start"] : ref["end"]]) == ref["span_digest"]
    assert text not in json.dumps(route, ensure_ascii=False)
    assert route[authority.LABEL]["model_call_added"] is False
    assert route[authority.LABEL]["long_term_memory_write"] is False


def test_negative_scope_and_nonrequests_do_not_become_authority():
    negatives = (
        "不要幫我想辦法，我只是說說。",
        "Don't help me come up with a method; just listen.",
        "方法は一緒に考えなくていい。ただ聞いて。",
    )
    for text in negatives:
        route = m47.classify_help_route_m47(text)
        assert route["status"] == "practical_help_forbidden"
        assert route["selected_policy"] is None
    for text in (
        "我昨天幫我弟想了一個辦法。",
        "I helped my friend come up with a method.",
        "昨日は方法を一緒に考えていた。",
    ):
        route = m47.classify_help_route_m47(text)
        assert route["status"] == "no_explicit_help_route"
        assert authority.LABEL not in route


def test_existing_m47_routes_remain_byte_identical():
    cases = (
        "給我一個現在能做的步驟。",
        "方法はいらない。ただ聞いてほしい。",
        "我昨天看過這個方法，但還沒決定。",
    )
    for text in cases:
        expected = authority._ORIGINAL_ROUTE(text)
        actual = m47.classify_help_route_m47(text)
        assert actual == expected


def test_later_natural_request_can_replace_earlier_negative_scope():
    text = "不要給我泛泛的方法。但是現在請幫我想一個做法。"
    route = m47.classify_help_route_m47(text)
    assert route["status"] == "practical_help_authorized"
    assert route["candidate_evidence"][-1]["kind"] == "authorize"
    ref = route["desired_response_span"]
    assert "幫我想一個做法" in text[ref["start"] : ref["end"]]


def test_materialized_node_is_unique_connected_and_raw_free(monkeypatch):
    monkeypatch.setattr(authority, "_ORIGINAL_MATERIALIZE", lambda result, feedback=None: None)
    text = "請幫我想一個做法。"
    route = m47.classify_help_route_m47(text)
    result = {
        "reply": "どの作業について考えればいい？",
        "logic": {
            "desired_response_policy_m18": "solve_regulation",
            "explicit_desired_response_m25": {m47.LABEL: route},
        },
        "runtime_trace": {
            "blackboard": [
                {"stage": "route", "label": m47.LABEL, "payload": deepcopy(route)},
                {"stage": "speak", "label": "utterance", "payload": {}},
            ]
        },
    }
    authority.materialize_current_request_trace_p2(result)
    authority.materialize_current_request_trace_p2(result)
    rows = [row for row in result["runtime_trace"]["blackboard"] if row["label"] == authority.LABEL]
    assert len(rows) == 1
    assert text not in json.dumps(rows[0], ensure_ascii=False)
    assert rows[0]["payload"]["actual_selected_policy"] == "solve_regulation"


def test_request_without_task_fails_closed_before_any_action_model_call():
    text = "謝謝。不過現在請幫我想一個做法。"
    route = m47.classify_help_route_m47(text)
    logic = help_logic()
    logic["desired_response_policy_m18"] = "solve_regulation"
    logic["explicit_desired_response_m25"] = {m47.LABEL: route}

    def forbidden(*_args):
        raise AssertionError("missing task must not reach an action model")

    reply, audit = deliver_with_task_evidence(
        text,
        "元の返事。",
        logic,
        action45.source_packet(text),
        forbidden,
    )
    assert audit["status"] == "awaiting_context"
    assert audit["model_calls_attempted"] == 0
    assert "どの作業" in reply
    source_audit = audit[task_gate.LABEL][authority.LABEL]
    assert source_audit["final_allowed_count"] == 0
    assert "current_request_discourse_ack_not_task" in {
        row["reason"] for row in source_audit["removed"]
    }
    assert any(
        "response_form" in row["reason"]
        for row in audit[task_gate.LABEL]["excluded"]
    )


def test_request_with_independent_task_keeps_only_task_evidence():
    text = "桌上的信件和收據混在一起，請幫我想一個做法。"
    route = m47.classify_help_route_m47(text)
    assert route["status"] == "practical_help_authorized"
    sources, gate = task_gate.task_sources(action45.source_packet(text))
    assert len(sources) == 1
    assert sources[0]["text"].rstrip("，,") == "桌上的信件和收據混在一起"
    assert sources[0]["origin"]["span_digest"] == authority.m47._digest(sources[0]["text"])
    assert gate["status"] == "content_available"
    assert gate[authority.LABEL]["final_allowed_count"] == 1
    assert text not in json.dumps(gate, ensure_ascii=False)


def test_unrelated_source_gate_is_byte_identical():
    packet = action45.source_packet("桌上的信件和收據混在一起。")
    expected = authority._ORIGINAL_TASK_SOURCES(packet)
    actual = task_gate.task_sources(packet)
    assert actual == expected


def test_product_runtime_current_request_overrides_listening_without_task_invention(tmp_path):
    program = r'''
import json, os
from pathlib import Path
root=Path(os.environ["P2_AUTH_ROOT"])
os.environ["URUHA_ADAPTIVE_PERSON_MODEL_PATH"]=str(root/"adaptive.json")
os.environ["URUHA_MEMORY_DB_PATH"]=str(root/"memory")
os.environ["URUHA_WEB_PREWARM_BRAIN"]="0"
os.environ["URUHA_IDLE_VISIBLE_PROACTIVE_ENABLED"]="false"
os.environ["GRADIO_ANALYTICS_ENABLED"]="false"
import project_paths
project_paths.WEB_LOG_DIR=str(root/"web")
project_paths.WEB_CONVERSATION_LOG_JSONL_PATH=str(root/"web/turns.jsonl")
project_paths.WEB_CONVERSATION_LOG_TXT_PATH=str(root/"web/turns.txt")
import uruha_web_ui_product
import uruha_actionable_help_delivery_m45 as action45
import uruha_current_request_authority_p2 as authority
from test_personhood_loop_v2_13 import _IsolatedContractBrain
b=_IsolatedContractBrain()
b.run_turn_debug("今日はただ聞いてほしい。")
r=b.run_turn_debug("謝謝。不過現在請幫我想一個做法。")
assert r["logic"]["desired_response_policy_m18"]=="solve_regulation",r["logic"]
assert r["logic"][authority.LABEL]["actual_selected_policy"]=="solve_regulation"
assert any(row["label"]==authority.LABEL for row in r["runtime_trace"]["blackboard"])
ledger=b.runtime.adaptive_person_model["outcome_calibration_ledger_m27"]
assert ledger[0]["result_status"]=="uncertain",ledger
print(json.dumps({"reply":r["reply"],"policy":r["logic"]["desired_response_policy_m18"],"route":r["logic"][authority.LABEL]["status"]},ensure_ascii=False))
'''
    env = {**os.environ, "P2_AUTH_ROOT": str(tmp_path)}
    result = subprocess.run(
        [sys.executable, "-c", program],
        env=env,
        check=True,
        capture_output=True,
        text=True,
        timeout=90,
    )
    assert "solve_regulation" in result.stdout
