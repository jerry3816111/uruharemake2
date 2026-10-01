import json
from types import SimpleNamespace

import pytest
import uruha_compact_planner_p2 as compact


def request():
    return {"model": "qwen2.5:7b", "temperature": 0.1, "timeout": 20,
            "messages": [{"role": "system", "content": "You are the Left Brain Planner for a dual-brain character system.\n[Memory] source reference\n[Hard rules] keep facts bounded\n[Output JSON schema]old verbose schema"},
                         {"role": "user", "content": "user text unchanged"}]}


def response_content():
    return {"plans": [{"scene": "casual", "core_message_jp": text, "response_mode": "direct_answer"}
                      for text in ("うん。", "そっか。", "それでいこう。") ]}


def test_preserves_model_memory_rules_input_temperature_and_budget():
    before = request()
    after = compact.compact_request(before)
    for key in ("model", "temperature", "timeout"):
        assert after[key] == before[key]
    assert after["messages"][1] == before["messages"][1]
    prefix = before["messages"][0]["content"].split("[Output JSON schema]")[0]
    assert after["messages"][0]["content"].startswith(prefix)
    assert after["max_tokens"] == 256
    assert before["messages"][0]["content"].endswith("old verbose schema")
    other = request(); other["messages"][0]["content"] = "Other module"
    assert compact.compact_request(other) is None


def test_product_budget_is_explicit_and_bounded():
    assert compact.product_planner_budget() == 20
    assert compact.product_planner_budget("8") == 8
    for value in ("nan", "inf", "0", "46", "invalid"):
        with pytest.raises(ValueError):
            compact.product_planner_budget(value)


@pytest.mark.parametrize("case", ["truncated", "fewer", "duplicate", "extra", "too_long", "invalid_scene"])
def test_rejects_incomplete_or_invalid_candidates_without_synthesizing(case):
    value = response_content()
    finish = "stop"
    if case == "truncated": finish = "length"
    if case == "fewer": value["plans"].pop()
    if case == "duplicate": value["plans"][1] = value["plans"][0]
    if case == "extra": value["invented_field"] = True
    if case == "too_long": value["plans"][0]["core_message_jp"] = "あ" * 33
    if case == "invalid_scene": value["plans"][0]["scene"] = "unknown"
    with pytest.raises(ValueError):
        compact.expand_compact_response(json.dumps(value), finish)


def test_actual_client_records_compact_response_before_internal_expansion():
    seen = []
    original = SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=json.dumps(response_content())), finish_reason="stop")])
    def create(**kwargs):
        seen.append(kwargs)
        return original
    client = compact._Proxy(SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create))))
    audit = {}
    token = compact._CALL.set(audit)
    try:
        returned = client.chat.completions.create(**request())
    finally:
        compact._CALL.reset(token)
    assert seen[0]["max_tokens"] == 256
    assert "plans" in json.loads(original.choices[0].message.content)
    assert len(json.loads(returned.choices[0].message.content)["candidate_plans"]) == 3
    assert audit["completed"] and audit["candidate_count"] == 3


def test_no_context_means_no_interception_and_exception_is_not_retried():
    calls = []
    def fail(**kwargs):
        calls.append(kwargs)
        raise TimeoutError("test-only transport")
    client = compact._Proxy(SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=fail))))
    with pytest.raises(TimeoutError): client.chat.completions.create(**request())
    assert calls[0] == request()
    audit = {}; token = compact._CALL.set(audit)
    try:
        with pytest.raises(TimeoutError): client.chat.completions.create(**request())
    finally: compact._CALL.reset(token)
    assert len(calls) == 2 and not audit["completed"] and audit["failure_type"] == "TimeoutError"


def test_compact_graph_node_is_connected_idempotent_and_absent_on_non_model_turn():
    from uruha_memory_observatory import collect_cognitive_graph
    audit = {"schema": "uruha_compact_general_plan_p2", "completed": True, "candidate_count": 3}
    result = {"logic": {"bounded_slow_path_m21": {"compact_general_plan_p2": audit}},
              "runtime_trace": {"blackboard": [{"label": "selected_plan", "stage": "select", "payload": {}},
                                                 {"label": "utterance", "stage": "speak", "payload": {}}]}}
    compact.materialize_compact_trace(result); compact.materialize_compact_trace(result)
    graph = collect_cognitive_graph(result)
    nodes = [n for n in graph["nodes"] if n["label"] == "compact_general_plan_p2"]
    assert len(nodes) == 1
    assert any(e["source"] == nodes[0]["id"] or e["target"] == nodes[0]["id"] for e in graph["edges"])
    result["logic"] = {}
    compact.materialize_compact_trace(result)
    assert not any(row["label"] == "compact_general_plan_p2" for row in result["runtime_trace"]["blackboard"])
