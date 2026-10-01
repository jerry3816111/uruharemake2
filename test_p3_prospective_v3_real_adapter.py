from __future__ import annotations

import io
import json
from pathlib import Path
from types import SimpleNamespace
import urllib.request

import pytest

from p3_product_comparison import P3ContractError, load_design
import p3_product_worker as worker
import p3_prospective_v3_real_adapter as adapter


ROOT = Path(__file__).resolve().parent
DESIGN = load_design(ROOT / "configs/p3_product_comparison_v1.json")
RUN_SHA = "a" * 64
MESSAGES = [{"role": "user", "content": "checkpoint-secret-input"}]


class SimulatedPowerLoss(BaseException):
    pass


def token_counter(messages):
    assert list(messages)
    return 11


def openai_payload(request):
    return {
        "model": request["model"],
        "choices": [{"message": {"content": "分かった。"}}],
        "usage": {"prompt_tokens": 11, "completion_tokens": 4},
    }


def native_payload(request):
    return {
        "model": request["model"],
        "message": {"role": "assistant", "content": "そうだな。"},
        "prompt_eval_count": 11,
        "eval_count": 5,
        "done": True,
        "done_reason": "stop",
    }


def gate(root, step, *, hook=None):
    journal = adapter.ProviderCallJournal(root, RUN_SHA, after_intent_hook=hook)
    return adapter.CheckpointedProductTransportGate(
        DESIGN, token_counter, allow_real_transport=True,
        provider_binding_verified=True, journal=journal, logical_step_id=step,
    )


def test_openai_complete_checkpoint_reconstructs_without_second_transport(tmp_path):
    calls = {"count": 0}

    def transport(request):
        calls["count"] += 1
        return openai_payload(request)

    request = worker.build_openai_call(DESIGN, MESSAGES, 32)
    first_gate = gate(tmp_path, "case01-u1-product")
    first = first_gate.intercept_openai(
        stage="product_openai_1", call_kwargs=request, transport=transport
    )
    second_gate = gate(tmp_path, "case01-u1-product")
    second = second_gate.intercept_openai(
        stage="product_openai_1", call_kwargs=request, transport=transport
    )
    assert calls["count"] == 1
    assert first["content"] == second["content"] == "分かった。"
    assert first_gate.interceptions[0]["checkpoint_reused"] is False
    assert second_gate.interceptions[0]["checkpoint_reused"] is True
    assert second_gate.interceptions[0]["network_calls"] == 0
    assert second_gate.interceptions[0]["real_model_calls"] == 0
    serialized = "\n".join(path.read_text(encoding="utf-8") for path in tmp_path.rglob("*.json"))
    assert "checkpoint-secret-input" not in serialized


def test_native_complete_checkpoint_reconstructs_without_second_transport(tmp_path):
    calls = {"count": 0}

    def transport(request):
        calls["count"] += 1
        return native_payload(request)

    request = worker.build_native_call(DESIGN, MESSAGES, 32)
    first_gate = gate(tmp_path, "case01-u2-product")
    first = first_gate.intercept_native(
        stage="product_native_1", request_body=request, transport=transport
    )
    second_gate = gate(tmp_path, "case01-u2-product")
    second = second_gate.intercept_native(
        stage="product_native_1", request_body=request, transport=transport
    )
    assert calls["count"] == 1
    assert first["content"] == second["content"] == "そうだな。"
    assert second_gate.interceptions[0]["checkpoint_reused"] is True


def test_intent_only_and_transport_failure_are_terminal(tmp_path):
    calls = {"count": 0}

    def stop_after_intent(_call_id):
        raise SimulatedPowerLoss()

    request = worker.build_openai_call(DESIGN, MESSAGES, 32)
    first_gate = gate(tmp_path / "intent", "case01-u1-product", hook=stop_after_intent)
    with pytest.raises(SimulatedPowerLoss):
        first_gate.intercept_openai(
            stage="product_openai_1", call_kwargs=request, transport=lambda value: openai_payload(value)
        )
    second_gate = gate(tmp_path / "intent", "case01-u1-product")
    with pytest.raises(P3ContractError, match="p3_b46_intent_without_complete_no_retry"):
        second_gate.intercept_openai(
            stage="product_openai_1", call_kwargs=request, transport=lambda value: openai_payload(value)
        )

    def failed_transport(_request):
        calls["count"] += 1
        raise RuntimeError("simulated failure")

    failed_gate = gate(tmp_path / "failure", "case01-u1-product")
    with pytest.raises(P3ContractError, match="p3_b46_transport_failure_no_retry"):
        failed_gate.intercept_openai(
            stage="product_openai_1", call_kwargs=request, transport=failed_transport
        )
    retry_gate = gate(tmp_path / "failure", "case01-u1-product")
    with pytest.raises(P3ContractError, match="p3_b46_terminal_provider_failure_no_retry"):
        retry_gate.intercept_openai(
            stage="product_openai_1", call_kwargs=request, transport=failed_transport
        )
    assert calls["count"] == 1


def test_request_or_complete_mutation_fails_closed(tmp_path):
    request = worker.build_openai_call(DESIGN, MESSAGES, 32)
    first_gate = gate(tmp_path / "request", "case01-u1-product")
    first_gate.intercept_openai(
        stage="product_openai_1", call_kwargs=request, transport=openai_payload
    )
    changed = worker.build_openai_call(
        DESIGN, [{"role": "user", "content": "different input"}], 32
    )
    second_gate = gate(tmp_path / "request", "case01-u1-product")
    with pytest.raises(P3ContractError, match="p3_b46_complete_checkpoint_source_mismatch"):
        second_gate.intercept_openai(
            stage="product_openai_1", call_kwargs=changed, transport=openai_payload
        )

    root = tmp_path / "mutated"
    first_gate = gate(root, "case01-u1-product")
    first_gate.intercept_openai(
        stage="product_openai_1", call_kwargs=request, transport=openai_payload
    )
    complete = next(root.rglob("complete.json"))
    value = json.loads(complete.read_text(encoding="utf-8"))
    value["result"]["content"] = "changed"
    complete.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
    with pytest.raises(P3ContractError, match="p3_b46_complete_checkpoint_drift"):
        gate(root, "case01-u1-product").intercept_openai(
            stage="product_openai_1", call_kwargs=request, transport=openai_payload
        )


class FakeCompletions:
    def __init__(self, counter):
        self.counter = counter

    def create(self, **kwargs):
        self.counter["openai"] += 1
        mapped = openai_payload(kwargs)
        return SimpleNamespace(
            model=mapped["model"],
            choices=[SimpleNamespace(message=SimpleNamespace(content="分かった。"))],
            usage=SimpleNamespace(prompt_tokens=11, completion_tokens=4),
        )


class FakeOpenAI:
    def __init__(self, counter):
        self.chat = SimpleNamespace(completions=FakeCompletions(counter))
        self.models = SimpleNamespace(list=lambda: {"data": []})


class FakeHTTPResponse:
    def __init__(self, value):
        self.buffer = io.BytesIO(json.dumps(value, ensure_ascii=False).encode("utf-8"))

    def read(self):
        return self.buffer.read()

    def close(self):
        self.buffer.close()


def brain_module(counter):
    def openai_factory(*_args, **_kwargs):
        return FakeOpenAI(counter)

    def native_urlopen(request, **_kwargs):
        counter["native"] += 1
        body = json.loads(request.data.decode("utf-8"))
        return FakeHTTPResponse(native_payload(body))

    return SimpleNamespace(
        M31_SEMANTIC_VERIFIER_MODEL="qwen2.5:7b",
        M31_SEMANTIC_VERIFIER_URL="http://127.0.0.1:11434/api/chat",
        OpenAI=openai_factory,
        urllib=SimpleNamespace(request=SimpleNamespace(urlopen=native_urlopen)),
    )


def test_installed_gate_returns_sdk_and_native_shapes_on_fresh_and_reuse(tmp_path):
    counter = {"openai": 0, "native": 0}
    openai_request = worker.build_openai_call(DESIGN, MESSAGES, 32)
    native_request = worker.build_native_call(DESIGN, MESSAGES, 32)

    first_module = brain_module(counter)
    first_gate = gate(tmp_path, "case01-u1-product")
    installed = adapter.install_checkpointed_product_transport_gate(first_module, first_gate)
    response = first_module.OpenAI().chat.completions.create(**openai_request)
    assert response.choices[0].message.content == "分かった。"
    request = urllib.request.Request(
        first_module.M31_SEMANTIC_VERIFIER_URL,
        data=json.dumps(native_request).encode("utf-8"), method="POST",
    )
    native = json.loads(first_module.urllib.request.urlopen(request).read().decode("utf-8"))
    assert native["message"]["content"] == "そうだな。"
    assert all(installed.values())

    second_module = brain_module(counter)
    second_gate = gate(tmp_path, "case01-u1-product")
    adapter.install_checkpointed_product_transport_gate(second_module, second_gate)
    response = second_module.OpenAI().chat.completions.create(**openai_request)
    assert response.usage.prompt_tokens == 11
    request = urllib.request.Request(
        second_module.M31_SEMANTIC_VERIFIER_URL,
        data=json.dumps(native_request).encode("utf-8"), method="POST",
    )
    native = json.loads(second_module.urllib.request.urlopen(request).read().decode("utf-8"))
    assert native["eval_count"] == 5
    assert counter == {"openai": 1, "native": 1}

