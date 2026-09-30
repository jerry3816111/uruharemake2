"""Focused zero-model regressions for the P4-C failure truth overlay."""

from copy import deepcopy
import json
import threading

import uruha_product_function_calling_p4 as product
import uruha_product_tool_failure_truth_p4 as overlay
import uruha_read_only_function_calling_p4 as core
from uruha_memory_observatory import collect_cognitive_graph, render_memory_observatory


EXPLICIT = "Please check the current UruhaBrain runtime status."
FAILURE_REPLY = "今の状態確認は取れなかった。動かしたとは言わないでおく。"
FAILURE_ACT = "read_only_status_failed_closed"
FAILURE_GROUNDING = {
    "source": "failed_closed_read_only_status_attempt",
    "status": "failed_closed",
    "validated_tool_result": False,
}


class FakeProvider:
    def __init__(self, calls=None):
        self.calls = calls if calls is not None else [
            {"type": "function", "function": {"name": core.TOOL_NAME, "arguments": {}}}
        ]
        self.invocations = []

    def invoke(self, **kwargs):
        self.invocations.append(deepcopy(kwargs))
        return {
            "model": kwargs["model"],
            "message": {"content": "", "tool_calls": deepcopy(self.calls)},
            "done": True,
            "prompt_eval_count": 40,
            "eval_count": 8,
        }


class FakeRuntime:
    def __init__(self):
        self._brain = object()
        self._turn_index = 4
        self._lock = threading.Lock()
        self.activity_count = 0

    def mark_activity(self):
        self.activity_count += 1

    def get_brain(self):
        raise AssertionError("status reader must not initialize the brain")


class FakeBase:
    def __init__(self):
        self.RUNTIME = FakeRuntime()
        self.ordinary_result = {"source": "existing_chat"}
        self.ordinary_calls = []
        self.rendered = []
        self.graphs = []
        self.state_rendered = []

    def _run_turn(self, *args, **kwargs):
        self.ordinary_calls.append((args, kwargs))
        return self.ordinary_result

    @staticmethod
    def _extract_trace_payload(turn):
        return {
            "surface_act": turn["logic"]["surface_act"],
            "grounding": turn["logic"].get("grounding"),
            "runtime_trace": turn["runtime_trace"],
            "runtime_state": turn["runtime_state"],
            "memory_runtime": turn["memory_runtime"],
        }

    @staticmethod
    def _extract_memory_payload(turn):
        return deepcopy(turn.get("memory_data") or {})

    def _render_flow_html(self, observatory):
        self.rendered.append(deepcopy(observatory))
        self.graphs.append(collect_cognitive_graph(observatory))
        return render_memory_observatory(observatory)

    def _render_state_diff_html(self, observatory):
        self.state_rendered.append(deepcopy(observatory))
        return "state:" + str(observatory["logic"].get("surface_act"))


def _installed_base(monkeypatch, provider):
    monkeypatch.setenv("URUHA_PRODUCT_WRITE_SANDBOX", "1")
    monkeypatch.setenv("URUHA_MEMORY_DB_PATH", "/tmp/isolate/memory")
    monkeypatch.setenv("URUHA_WEB_SESSION_DB_PATH", "/tmp/isolate/session")
    monkeypatch.setenv("URUHA_WEB_LOG_JSONL_PATH", "/tmp/isolate/log.jsonl")
    monkeypatch.setenv("URUHA_WEB_LOG_TXT_PATH", "/tmp/isolate/log.txt")
    monkeypatch.setattr(product, "_INSTALLED", False)
    monkeypatch.setattr(product, "_ORIGINAL_RUN_TURN", None)
    monkeypatch.setattr(product, "_PROVIDER_FACTORY", None)
    base = FakeBase()
    assert product.install_product_function_calling_p4(
        base, provider_factory=lambda: provider
    ) is True
    assert overlay.install_product_tool_failure_truth_p4(base) is True
    return base


def _nodes(result):
    return result["cognition_trace"]["runtime_trace"]["blackboard"]


def _assert_failure_projection(result, base):
    assert result["reply"] == FAILURE_REPLY
    assert result["logic"][product.LABEL]["status"] == "failed_closed"
    assert result["logic"]["surface_act"] == FAILURE_ACT
    assert result["logic"]["grounding"] == FAILURE_GROUNDING
    assert result["debug"]["surface_act"] == FAILURE_ACT
    assert result["debug"]["grounding"] == FAILURE_GROUNDING
    assert result["debug"]["core_message_jp"] == FAILURE_REPLY
    assert result["cognition_trace"]["surface_act"] == FAILURE_ACT
    assert result["cognition_trace"]["grounding"] == FAILURE_GROUNDING
    assert len(base.rendered) == len(base.state_rendered) == 2
    assert base.rendered[-1]["logic"]["surface_act"] == FAILURE_ACT
    assert base.rendered[-1]["runtime_trace"]["blackboard"] == _nodes(result)
    assert result["state_html"] == "state:" + FAILURE_ACT
    assert "failed_closed" in result["flow_html"]
    serialized = json.dumps(result, ensure_ascii=False)
    assert "read_only_status_report" not in serialized
    assert "validated_read_only_tool_result" not in serialized


def test_wrong_tool_failure_keeps_failed_graph_and_attempt_count(monkeypatch):
    provider = FakeProvider(
        [{"function": {"name": "write_file", "arguments": {"path": "/private/secret"}}}]
    )
    base = _installed_base(monkeypatch, provider)

    result = base._run_turn(EXPLICIT, False)

    _assert_failure_projection(result, base)
    assert len(provider.invocations) == 1
    assert base.RUNTIME.activity_count == 1
    assert base.ordinary_calls == []
    assert result["logic"][product.LABEL]["model_call_count"] == 1
    assert result["logic"][product.LABEL]["tool_execution_count"] == 0
    assert [row["label"] for row in _nodes(result)][:3] == [
        "function_request_p4_c",
        "function_model_decision_p4_c",
        "function_surface_p4_c",
    ]
    assert _nodes(result)[1]["payload"]["status"] == "failed_closed"
    assert _nodes(result)[2]["payload"]["claimed_status_read"] is False
    assert not any(row["label"] == "function_tool_result_p4_c" for row in _nodes(result))
    assert any(
        node["label"] == "function_model_decision_p4_c"
        and "failed_closed" in node["detail"]
        for node in base.graphs[-1]["nodes"]
    )
    assert "/private/secret" not in json.dumps(result, ensure_ascii=False)


def test_reader_exception_keeps_validated_attempt_but_no_result_claim(monkeypatch):
    provider = FakeProvider()
    base = _installed_base(monkeypatch, provider)
    reader_calls = []

    def broken_reader(runtime):
        reader_calls.append(runtime)
        raise RuntimeError("private-reader-path:/sensitive/status.json")

    monkeypatch.setattr(product, "read_product_runtime_status", broken_reader)
    result = base._run_turn(EXPLICIT, False)

    _assert_failure_projection(result, base)
    assert len(provider.invocations) == 1
    assert reader_calls == [base.RUNTIME]
    assert result["logic"][product.LABEL]["model_call_count"] == 1
    assert result["logic"][product.LABEL]["tool_execution_count"] == 1
    labels = [row["label"] for row in _nodes(result)]
    assert labels[:5] == list(core.TRACE_LABELS)
    tool_node = next(row for row in _nodes(result) if row["label"] == "function_tool_result_p4_c")
    assert tool_node["payload"]["status"] == "failed_closed"
    assert tool_node["payload"]["result_exposed"] is False
    assert _nodes(result)[-2]["payload"]["claimed_status_read"] is False
    assert "/sensitive/status.json" not in json.dumps(result, ensure_ascii=False)


def test_success_status_turn_is_not_rewritten_or_rerendered(monkeypatch):
    provider = FakeProvider()
    base = _installed_base(monkeypatch, provider)

    result = base._run_turn(EXPLICIT, False)

    assert len(provider.invocations) == 1
    assert result["logic"][product.LABEL]["status"] == "tool_call_complete"
    assert result["logic"]["surface_act"] == "read_only_status_report"
    assert "grounding" not in result["logic"]
    assert result["debug"]["grounding"] == {"source": "validated_read_only_tool_result"}
    assert result["cognition_trace"]["surface_act"] == "read_only_status_report"
    assert len(base.rendered) == len(base.state_rendered) == 1
    assert result["logic"][product.LABEL]["tool_execution_count"] == 1
    assert any(
        row["label"] == "function_tool_result_p4_c"
        and row["payload"]["status"] == "read_complete"
        for row in _nodes(result)
    )


def test_ordinary_chat_falls_through_with_same_object_and_arguments(monkeypatch):
    provider = FakeProvider()
    base = _installed_base(monkeypatch, provider)

    result = base._run_turn(
        "今日は疲れた。少しだけ聞いて。",
        False,
        input_mode="text",
        acoustic_summary=None,
        frontend_enqueue_started=1.0,
        handler_started=2.0,
    )

    assert result is base.ordinary_result
    assert len(base.ordinary_calls) == 1
    assert base.ordinary_calls[0][0] == ("今日は疲れた。少しだけ聞いて。", False)
    assert base.ordinary_calls[0][1]["frontend_enqueue_started"] == 1.0
    assert provider.invocations == []
    assert base.RUNTIME.activity_count == 0
    assert base.rendered == base.state_rendered == []


def test_installation_is_idempotent_and_delegates_one_turn_once(monkeypatch):
    provider = FakeProvider(
        [{"function": {"name": "write_file", "arguments": {}}}]
    )
    base = _installed_base(monkeypatch, provider)
    current_run_turn = base._run_turn

    assert overlay.install_product_tool_failure_truth_p4(base) is False
    assert base._run_turn is current_run_turn
    result = base._run_turn(EXPLICIT, False)

    _assert_failure_projection(result, base)
    assert len(provider.invocations) == 1
    assert base.ordinary_calls == []


def test_repair_ignores_failed_summary_on_other_route(monkeypatch):
    base = FakeBase()
    result = {
        "logic": {
            "routing_path": "ordinary_chat",
            product.LABEL: {"status": "failed_closed"},
            "surface_act": "existing_act",
        },
        "debug": {"surface_act": "existing_act"},
        "cognition_trace": {"surface_act": "existing_act"},
    }

    assert overlay.repair_product_tool_failure_truth_p4(base, result) is result
    assert result["logic"]["surface_act"] == "existing_act"
    assert base.rendered == []
