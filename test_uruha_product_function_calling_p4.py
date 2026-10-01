from copy import deepcopy
import json
from pathlib import Path
import threading
from types import SimpleNamespace

import uruha_product_function_calling_p4 as product
import uruha_read_only_function_calling_p4 as core


ROOT = Path(__file__).resolve().parent
EXPLICIT = "Please check the current UruhaBrain runtime status."


class FakeProvider:
    def __init__(self, calls=None):
        self.invocations = []
        self.calls = calls if calls is not None else [
            {
                "type": "function",
                "function": {"name": core.TOOL_NAME, "arguments": {}},
            }
        ]

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
    def __init__(self, *, loaded=True, turn_index=4):
        self._brain = object() if loaded else None
        self._turn_index = turn_index
        self._lock = threading.Lock()
        self.activity_count = 0

    def mark_activity(self):
        self.activity_count += 1

    def get_brain(self):
        raise AssertionError("status tool must not initialize or inspect the brain")


class FakeBase:
    def __init__(self, runtime):
        self.RUNTIME = runtime
        self.rendered = []

    @staticmethod
    def _extract_trace_payload(turn):
        return {
            "runtime_trace": deepcopy(turn["runtime_trace"]),
            "runtime_state": deepcopy(turn["runtime_state"]),
            "memory_runtime": deepcopy(turn["memory_runtime"]),
        }

    @staticmethod
    def _extract_memory_payload(turn):
        return deepcopy(turn.get("memory_data") or {})

    def _render_flow_html(self, turn):
        labels = [row["label"] for row in turn["runtime_trace"]["blackboard"]]
        self.rendered.append(labels)
        return "flow:" + "->".join(labels)

    @staticmethod
    def _render_state_diff_html(turn):
        return "state:no_mutation"


def _isolated_environment(monkeypatch):
    monkeypatch.setenv("URUHA_PRODUCT_WRITE_SANDBOX", "1")
    monkeypatch.setenv("URUHA_MEMORY_DB_PATH", "/tmp/isolate/memory")
    monkeypatch.setenv("URUHA_WEB_SESSION_DB_PATH", "/tmp/isolate/session")
    monkeypatch.setenv("URUHA_WEB_LOG_JSONL_PATH", "/tmp/isolate/log.jsonl")
    monkeypatch.setenv("URUHA_WEB_LOG_TXT_PATH", "/tmp/isolate/log.txt")


def test_live_status_reader_never_initializes_brain_or_returns_paths(monkeypatch):
    _isolated_environment(monkeypatch)
    runtime = FakeRuntime(loaded=True, turn_index=4)
    status = product.read_product_runtime_status(runtime)
    assert status == {
        "schema": "uruha_p4_c_runtime_status_result_v1",
        "brain_loaded": True,
        "turn_count": 4,
        "memory_isolation": "isolated",
        "tool_capability": "get_runtime_status_only",
    }
    serialized = json.dumps(status, ensure_ascii=False)
    assert "/tmp/" not in serialized
    assert "session" not in serialized.lower()


def test_isolation_is_unknown_without_launcher_sandbox(monkeypatch):
    monkeypatch.delenv("URUHA_PRODUCT_WRITE_SANDBOX", raising=False)
    assert product._memory_isolation_from_environment({}) == "unknown"


def test_nonselected_chat_uses_existing_turn_unchanged_and_never_builds_provider(monkeypatch):
    _isolated_environment(monkeypatch)
    runtime = FakeRuntime()
    base = FakeBase(runtime)
    calls = []

    def original(*args, **kwargs):
        calls.append((args, kwargs))
        return {"source": "existing_chat", "args": args, "kwargs": kwargs}

    provider = FakeProvider()
    result = product.run_product_turn_p4_c(
        base,
        original,
        "今日は疲れた。少しだけ聞いて。",
        False,
        input_mode="text",
        acoustic_summary=None,
        frontend_enqueue_started=1.0,
        handler_started=2.0,
        provider=provider,
    )
    assert result["source"] == "existing_chat"
    assert len(calls) == 1
    assert provider.invocations == []
    assert runtime.activity_count == 0


def test_explicit_status_request_uses_live_bounded_status_and_same_turn_graph(monkeypatch):
    _isolated_environment(monkeypatch)
    runtime = FakeRuntime(loaded=True, turn_index=4)
    base = FakeBase(runtime)
    original_calls = []
    provider = FakeProvider()
    result = product.run_product_turn_p4_c(
        base,
        lambda *args, **kwargs: original_calls.append((args, kwargs)),
        EXPLICIT,
        False,
        provider=provider,
    )
    assert original_calls == []
    assert len(provider.invocations) == 1
    assert runtime.activity_count == 1
    assert result["reply"] == "うん、脳は起動済み。記録は4ターン、記憶は隔離環境。今使えるのは読み取り専用の状態確認だけ。"
    labels = [
        row["label"]
        for row in result["cognition_trace"]["runtime_trace"]["blackboard"]
    ]
    assert labels[:5] == list(core.TRACE_LABELS)
    assert labels[-1] == "runtime_latency_m19"
    assert base.rendered == [labels]
    assert "function_tool_result_p4_c" in result["flow_html"]
    assert result["logic"][product.LABEL]["tool_execution_count"] == 1
    assert result["memory_snapshot"] == {}
    assert result["cognition_trace"]["memory_runtime"]["memory_content_read_count"] == 0
    serialized = json.dumps(result, ensure_ascii=False)
    assert "/tmp/isolate" not in serialized


def test_invalid_provider_call_surfaces_failure_without_claiming_tool_result(monkeypatch):
    _isolated_environment(monkeypatch)
    runtime = FakeRuntime()
    base = FakeBase(runtime)
    provider = FakeProvider(
        [{"function": {"name": "write_file", "arguments": {"path": "x"}}}]
    )
    result = product.run_product_turn_p4_c(
        base,
        lambda *args, **kwargs: None,
        EXPLICIT,
        False,
        provider=provider,
    )
    assert result["reply"] == "今の状態確認は取れなかった。動かしたとは言わないでおく。"
    assert result["logic"][product.LABEL]["tool_execution_count"] == 0
    labels = [
        row["label"]
        for row in result["cognition_trace"]["runtime_trace"]["blackboard"]
    ]
    assert "function_validated_call_p4_c" not in labels
    assert "function_tool_result_p4_c" not in labels
    assert "function_surface_p4_c" in labels


def test_product_entry_installs_adapter_after_existing_product_layers():
    source = (ROOT / "uruha_web_ui_product.py").read_text(encoding="utf-8")
    assert "from uruha_product_function_calling_p4 import install_product_function_calling_p4" in source
    assert "install_product_function_calling_p4(_base)" in source
    assert source.index("install_wait_and_see_authority_p3()") < source.index(
        "install_product_function_calling_p4(_base)"
    )

