"""P4 B constructor/transport seam contracts; no real socket, model, Web, or DB."""

import os
import socket
from types import SimpleNamespace

import httpx
from openai import OpenAI
import pytest

_prior_skip_auto_venv = os.environ.get("URUHA_SKIP_AUTO_VENV")
os.environ["URUHA_SKIP_AUTO_VENV"] = "1"
try:
    import uruha_brain_mac as brain
finally:
    if _prior_skip_auto_venv is None:
        os.environ.pop("URUHA_SKIP_AUTO_VENV", None)
    else:
        os.environ["URUHA_SKIP_AUTO_VENV"] = _prior_skip_auto_venv
from uruha_compute_ledger import ComputeLedger
from uruha_p4_b_resource_gate import P4BResourceGate, P4BResourceGateError


def _target(port):
    return SimpleNamespace(
        base_url=f"http://127.0.0.1:{port}/v1",
        native_url=f"http://127.0.0.1:{port}/api/chat",
    )


def _stub_non_network_brain_parts(monkeypatch):
    observed = {"memory_ledgers": [], "left": [], "right": []}

    def memory(*, compute_ledger):
        observed["memory_ledgers"].append(compute_ledger)
        return SimpleNamespace()

    def left(client, **kwargs):
        observed["left"].append((client, kwargs))
        return SimpleNamespace()

    def right(**kwargs):
        observed["right"].append(kwargs)
        return SimpleNamespace()

    monkeypatch.setattr(brain, "MemoryManager", memory)
    monkeypatch.setattr(brain, "LeftBrain", left)
    monkeypatch.setattr(brain, "RightBrain", right)
    monkeypatch.setattr(brain, "_resolve_right_brain_model_loading", lambda _: False)
    monkeypatch.setattr(brain.uapm, "load_model", lambda _: ({}, {}))
    return observed


def _no_socket(monkeypatch):
    def fail(*_args, **_kwargs):
        raise AssertionError("unexpected real socket")

    monkeypatch.setattr(socket.socket, "connect", fail)
    monkeypatch.setattr(socket.socket, "connect_ex", fail)


def test_invalid_private_binding_fails_before_client_models_and_memory(monkeypatch):
    events = []

    def invalid(*_args, **_kwargs):
        events.append("validation")
        raise brain.up4bpeb.PrivateEndpointBindingError("unreviewed_binding")

    monkeypatch.setattr(brain.up4bpeb, "validate_private_endpoint_binding", invalid)
    monkeypatch.setattr(brain, "OpenAI", lambda **_: events.append("client"))
    monkeypatch.setattr(brain, "MemoryManager", lambda **_: events.append("memory"))
    _no_socket(monkeypatch)
    with pytest.raises(brain.up4bpeb.PrivateEndpointBindingError, match="unreviewed_binding"):
        brain.UruhaBrainV4_Mac(
            p4_b_private_mode=True,
            p4_b_private_binding=object(),
            p4_b_run_id="run-1",
        )
    assert events == ["validation"]


def test_private_constructor_uses_real_sdk_only_at_private_models_path_without_proxy(monkeypatch):
    _no_socket(monkeypatch)
    monkeypatch.setenv("HTTP_PROXY", "http://127.0.0.1:11434")
    monkeypatch.setenv("HTTPS_PROXY", "http://127.0.0.1:11434")
    monkeypatch.setenv("ALL_PROXY", "http://127.0.0.1:11434")
    monkeypatch.setenv("NO_PROXY", "")
    ledger = ComputeLedger(p4_b_resource_gate=P4BResourceGate())
    target = _target(11455)
    marker = object()
    monkeypatch.setattr(
        brain.up4bpeb,
        "validate_private_endpoint_binding",
        lambda binding, *, compute_ledger, run_id: (
            target if binding is marker and compute_ledger is ledger and run_id == "run-1"
            else (_ for _ in ()).throw(AssertionError("wrong binding"))
        ),
    )
    observed = _stub_non_network_brain_parts(monkeypatch)
    requests = []
    clients = []

    def reply(request):
        requests.append((request.method, str(request.url)))
        return httpx.Response(200, json={
            "object": "list", "data": [{"id": "qwen2.5:7b", "object": "model"}],
        })

    def actual_sdk(**kwargs):
        assert kwargs["base_url"] == target.base_url
        assert kwargs["max_retries"] == 0
        http_client = kwargs["http_client"]
        clients.append(http_client)
        assert http_client._trust_env is False
        assert http_client.follow_redirects is False
        assert http_client._mounts == {}
        http_client._transport = httpx.MockTransport(reply)
        return OpenAI(**kwargs)

    monkeypatch.setattr(brain, "OpenAI", actual_sdk)
    created = brain.UruhaBrainV4_Mac(
        load_right_brain_model=False,
        compute_ledger=ledger,
        p4_b_private_mode=True,
        p4_b_private_binding=marker,
        p4_b_run_id="run-1",
    )
    try:
        assert requests == [("GET", "http://127.0.0.1:11455/v1/models")]
        assert observed["memory_ledgers"] == [ledger]
        assert observed["left"][0][1]["compute_ledger"] is ledger
        assert observed["left"][0][1]["native_semantic_verifier_url"] == target.native_url
        assert observed["right"][0]["compute_ledger"] is ledger
        assert created.compute_ledger is ledger
        assert created.p4_b_private_target is target
        assert ledger.p4_b_resource_gate.snapshot()["attempted_provider_calls"] == 0
    finally:
        for client in clients:
            client.close()


def test_private_models_redirect_is_terminal_and_not_followed(monkeypatch):
    _no_socket(monkeypatch)
    target = _target(11456)
    monkeypatch.setattr(
        brain.up4bpeb,
        "validate_private_endpoint_binding",
        lambda *_args, **_kwargs: target,
    )
    memory_calls = []
    monkeypatch.setattr(brain, "MemoryManager", lambda **_: memory_calls.append(True))
    seen = []

    def redirect(request):
        seen.append(str(request.url))
        return httpx.Response(302, headers={"location": "http://127.0.0.1:11434/v1/models"})

    def actual_sdk(**kwargs):
        kwargs["http_client"]._transport = httpx.MockTransport(redirect)
        return OpenAI(**kwargs)

    monkeypatch.setattr(brain, "OpenAI", actual_sdk)
    with pytest.raises(brain.up4bpeb.PrivateEndpointBindingError, match="private_models_list_unavailable"):
        brain.UruhaBrainV4_Mac(
            compute_ledger=ComputeLedger(p4_b_resource_gate=P4BResourceGate()),
            p4_b_private_mode=True,
            p4_b_private_binding=object(),
            p4_b_run_id="run-2",
        )
    assert seen == ["http://127.0.0.1:11456/v1/models"]
    assert memory_calls == []


def test_private_models_listing_drift_fails_before_memory(monkeypatch):
    _no_socket(monkeypatch)
    target = _target(11456)
    monkeypatch.setattr(brain.up4bpeb, "validate_private_endpoint_binding",
                        lambda *_args, **_kwargs: target)
    memory_calls = []
    monkeypatch.setattr(brain, "MemoryManager", lambda **_: memory_calls.append(True))
    seen = []

    def wrong_model(request):
        seen.append(str(request.url))
        return httpx.Response(200, json={
            "object": "list", "data": [{"id": "some-other-model", "object": "model"}],
        })

    def actual_sdk(**kwargs):
        kwargs["http_client"]._transport = httpx.MockTransport(wrong_model)
        return OpenAI(**kwargs)

    monkeypatch.setattr(brain, "OpenAI", actual_sdk)
    with pytest.raises(brain.up4bpeb.PrivateEndpointBindingError,
                       match="private_model_listing_drift"):
        brain.UruhaBrainV4_Mac(
            compute_ledger=ComputeLedger(p4_b_resource_gate=P4BResourceGate()),
            p4_b_private_mode=True,
            p4_b_private_binding=object(),
            p4_b_run_id="run-2",
        )
    assert seen == ["http://127.0.0.1:11456/v1/models"]
    assert memory_calls == []


def test_default_private_private_default_instances_do_not_mutate_module_target(monkeypatch):
    _no_socket(monkeypatch)
    observed = _stub_non_network_brain_parts(monkeypatch)
    old_default = brain.OLLAMA_URL
    old_native = brain.M31_SEMANTIC_VERIFIER_URL
    bindings = {"first": _target(11455), "second": _target(11456)}
    monkeypatch.setattr(
        brain.up4bpeb,
        "validate_private_endpoint_binding",
        lambda binding, *, compute_ledger, run_id: bindings[binding],
    )
    calls = []

    def fake_sdk(**kwargs):
        calls.append(kwargs)
        return SimpleNamespace(
            models=SimpleNamespace(list=lambda: SimpleNamespace(
                data=[SimpleNamespace(id="qwen2.5:7b")],
            )),
            chat=SimpleNamespace(completions=SimpleNamespace(create=lambda **_: None)),
        )

    monkeypatch.setattr(brain, "OpenAI", fake_sdk)
    ordinary_1 = brain.UruhaBrainV4_Mac(load_right_brain_model=False)
    first = brain.UruhaBrainV4_Mac(
        load_right_brain_model=False,
        compute_ledger=ComputeLedger(p4_b_resource_gate=P4BResourceGate()),
        p4_b_private_mode=True, p4_b_private_binding="first", p4_b_run_id="run-1",
    )
    second = brain.UruhaBrainV4_Mac(
        load_right_brain_model=False,
        compute_ledger=ComputeLedger(p4_b_resource_gate=P4BResourceGate()),
        p4_b_private_mode=True, p4_b_private_binding="second", p4_b_run_id="run-2",
    )
    ordinary_2 = brain.UruhaBrainV4_Mac(load_right_brain_model=False)
    assert [call["base_url"] for call in calls] == [
        old_default, bindings["first"].base_url, bindings["second"].base_url, old_default,
    ]
    assert "http_client" not in calls[0] and "http_client" not in calls[3]
    assert calls[0]["max_retries"] == calls[3]["max_retries"] == 0
    assert brain.OLLAMA_URL == old_default
    assert brain.M31_SEMANTIC_VERIFIER_URL == old_native
    assert ordinary_1.p4_b_private_target is ordinary_2.p4_b_private_target is None
    assert first.p4_b_private_target is bindings["first"]
    assert second.p4_b_private_target is bindings["second"]
    assert [row[1].get("native_semantic_verifier_url") for row in observed["left"]] == [
        None, bindings["first"].native_url, bindings["second"].native_url, None,
    ]
    for call in calls:
        if "http_client" in call:
            call["http_client"].close()


def test_private_native_m31_still_denies_before_any_urlopen(monkeypatch):
    opened = []
    monkeypatch.setattr(brain.urllib.request, "urlopen", lambda *_args, **_kwargs: opened.append(True))
    ledger = ComputeLedger(p4_b_resource_gate=P4BResourceGate())
    left = brain.LeftBrain(
        client_logic=SimpleNamespace(),
        compute_ledger=ledger,
        native_semantic_verifier_url="http://127.0.0.1:11455/api/chat",
    )
    with pytest.raises(P4BResourceGateError, match="unexpected_generation_backend"):
        left._native_semantic_authorizer_m31("safe fixture")
    assert opened == []
