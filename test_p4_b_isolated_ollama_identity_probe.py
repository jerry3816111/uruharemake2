"""P4 B private Ollama identity probe contracts; no real network or generation."""

import hashlib
import json
import os
from dataclasses import replace
from pathlib import Path

import pytest

import p4_b_isolated_ollama_identity_probe as probe


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _private_store(tmp_path: Path):
    private_root = tmp_path / "private"
    models = private_root / "models"
    shared_models = tmp_path / "shared" / "models"
    manifest_rel = Path("manifests/registry.ollama.ai/library/qwen2.5/7b")
    for base in (models, shared_models):
        (base / "blobs").mkdir(parents=True)
        (base / manifest_rel.parent).mkdir(parents=True)
    # Every private ancestor is checked; permissions below must be explicit.
    for directory in (private_root, models, models / "blobs", models / "manifests",
                      models / "manifests/registry.ollama.ai",
                      models / "manifests/registry.ollama.ai/library",
                      models / manifest_rel.parent):
        directory.chmod(0o700)
    payloads = [b"config", b"gguf", b"system", b"license", b"template"]
    hashes = tuple(_sha(payload) for payload in payloads)
    entries = [{"digest": f"sha256:{digest}", "size": len(payload)}
               for digest, payload in zip(hashes, payloads, strict=True)]
    manifest = json.dumps({"config": entries[0], "layers": entries[1:]},
                          separators=(",", ":")).encode()
    for base in (models, shared_models):
        (base / manifest_rel).write_bytes(manifest)
        for digest, payload in zip(hashes, payloads, strict=True):
            (base / "blobs" / f"sha256-{digest}").write_bytes(payload)
    expected = probe.ExpectedModel(manifest_sha256=_sha(manifest), blob_sha256s=hashes,
                                   daemon_sha256="0" * 64, gguf_sha256=hashes[1],
                                   template_sha256=hashes[4], system_sha256=hashes[2])
    return private_root, shared_models, expected


def test_private_store_accepts_distinct_verified_files_only(tmp_path):
    private_root, shared_models, expected = _private_store(tmp_path)
    models, identity = probe._model_store(private_root, shared_models, expected)
    assert models == private_root / "models"
    assert len(identity) == 6


@pytest.mark.parametrize("tamper", ["hardlink", "symlink", "digest", "permissions"])
def test_private_store_fails_closed_on_clone_identity_drift(tmp_path, tamper):
    private_root, shared_models, expected = _private_store(tmp_path)
    blob = private_root / "models/blobs" / f"sha256-{expected.gguf_sha256}"
    if tamper == "hardlink":
        blob.unlink()
        os.link(shared_models / "blobs" / blob.name, blob)
    elif tamper == "symlink":
        blob.unlink()
        blob.symlink_to(shared_models / "blobs" / blob.name)
    elif tamper == "digest":
        blob.write_bytes(b"wrong")
    else:
        (private_root / "models/blobs").chmod(0o755)
    with pytest.raises(probe.ProbeError):
        probe._model_store(private_root, shared_models, expected)


def _mock_probe(monkeypatch, tmp_path):
    models = tmp_path / "models"
    blobs = models / "blobs"
    blobs.mkdir(parents=True)
    (blobs / f"sha256-{probe.TEMPLATE_SHA256}").write_text("template", encoding="utf-8")
    (blobs / f"sha256-{probe.SYSTEM_SHA256}").write_text("system", encoding="utf-8")
    identity = {"file": (1, 2, 3, 4, 5)}
    state = {"calls": [], "model_checks": 0, "process_checks": 0, "drift": None}
    rendered = "<|im_start|>system\n<|im_start|>user\nUser Input: Tokenizer fixture only."
    replies = {
        "/api/version": {"version": probe.VERSION},
        "/api/tags": {"models": [{"name": probe.MODEL, "digest": probe.FROZEN_MANIFEST_SHA256}]},
        "/api/show": {"template": "template", "system": "system"},
        "/v1/chat/completions": {
            "model": probe.MODEL, "_debug_info": {"rendered_template": rendered},
            "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
            "choices": [{"message": {"content": ""}}],
        },
        "/tokenize": {"tokens": [1, 2, 3]},
    }

    def fake_model_store(*args, **kwargs):
        state["model_checks"] += 1
        if state["drift"] == "model" and state["model_checks"] == 2:
            return models, {"file": (1, 2, 3, 4, 6)}
        return models, identity

    def fake_process_identity(**kwargs):
        state["process_checks"] += 1
        if state["drift"] == "process" and state["process_checks"] == 2:
            raise probe.ProbeError("process_endpoint_or_model_drift")
        return {"daemon_binary_sha256": probe.FROZEN_DAEMON_SHA256,
                "runner_binary_sha256": "a" * 64}

    def fake_http_json(url, payload=None):
        state["calls"].append((url, payload))
        path = "/" + url.split("/", 3)[-1]
        assert path in replies, "No unexpected generation endpoint is allowed"
        return replies[path]

    monkeypatch.setattr(probe, "_model_store", fake_model_store)
    monkeypatch.setattr(probe, "_process_identity", fake_process_identity)
    monkeypatch.setattr(probe, "_http_json", fake_http_json)
    kwargs = dict(private_root=tmp_path / "private", shared_models=tmp_path / "shared",
                  daemon_pid=123, runner_pid=124, daemon_port=11455, runner_port=51234,
                  daemon_binary=tmp_path / "ollama", runner_binary=tmp_path / "llama-server")
    return kwargs, state, replies


def test_probe_uses_only_five_fixed_diagnostic_calls_and_never_authorizes_b(monkeypatch, tmp_path):
    kwargs, state, replies = _mock_probe(monkeypatch, tmp_path)
    report = probe.probe(**kwargs)
    paths = ["/" + url.split("/", 3)[-1] for url, _ in state["calls"]]
    assert paths == ["/api/version", "/api/tags", "/api/show",
                     "/v1/chat/completions", "/tokenize"]
    rendered_request = state["calls"][3][1]
    assert rendered_request == probe._fixed_request()
    assert rendered_request["_debug_render_only"] is True
    assert "stream" not in rendered_request
    assert state["calls"][4][1] == {
        "content": replies["/v1/chat/completions"]["_debug_info"]["rendered_template"],
        "add_special": False, "parse_special": True,
    }
    assert report["diagnostic_http_calls"] == 5
    assert report["runner_token_count"] == 3
    assert report["generated_completions"] == 0
    assert report["raw_rendered_prompt_or_reply_in_result"] is False
    assert report["b_prompt_upper_bound_proven"] is False
    assert report["b_safari_send_authorized"] is False
    assert report["rendered_prompt_sha256"] == _sha(state["calls"][4][1]["content"].encode())
    assert probe.FIXTURE not in json.dumps(report)
    assert state["model_checks"] == state["process_checks"] == 2


@pytest.mark.parametrize("drift", ["version", "tag", "show", "nonempty_content",
                                    "usage", "render_branch", "token_shape", "model", "process"])
def test_probe_fails_closed_without_generation_on_diagnostic_or_identity_drift(
        monkeypatch, tmp_path, drift):
    kwargs, state, replies = _mock_probe(monkeypatch, tmp_path)
    if drift == "version":
        replies["/api/version"]["version"] = "0.0.0"
    elif drift == "tag":
        replies["/api/tags"]["models"][0]["digest"] = "wrong"
    elif drift == "show":
        replies["/api/show"]["template"] = "wrong"
    elif drift == "nonempty_content":
        replies["/v1/chat/completions"]["choices"][0]["message"]["content"] = "generated"
    elif drift == "usage":
        replies["/v1/chat/completions"]["usage"]["completion_tokens"] = 1
    elif drift == "render_branch":
        replies["/v1/chat/completions"]["_debug_info"]["rendered_template"] = "other"
    elif drift == "token_shape":
        replies["/tokenize"]["tokens"] = [True]
    else:
        state["drift"] = drift
    with pytest.raises(probe.ProbeError):
        probe.probe(**kwargs)
    assert all(payload is None or payload.get("_debug_render_only") is True
               or "/v1/chat/completions" not in url
               for url, payload in state["calls"])


def test_probe_rejects_shared_or_invalid_endpoint_before_any_diagnostic(monkeypatch, tmp_path):
    kwargs, state, _ = _mock_probe(monkeypatch, tmp_path)
    kwargs["daemon_port"] = 11434
    with pytest.raises(probe.ProbeError, match="private_endpoint_invalid"):
        probe.probe(**kwargs)
    assert state["calls"] == []
    assert state["model_checks"] == state["process_checks"] == 0


def test_process_identity_freezes_both_daemon_and_runner_binary_hashes(monkeypatch, tmp_path):
    daemon = tmp_path / "ollama"
    runner = tmp_path / "llama-server"
    model_blob = tmp_path / "private-gguf"
    daemon.write_bytes(b"daemon")
    runner.write_bytes(b"runner")
    model_blob.write_bytes(b"model")
    commands = {
        123: (1, [str(daemon), "serve"]),
        124: (123, [str(runner), "--model", str(model_blob), "--port", "51234",
                    "--host", "127.0.0.1", "--offline", "--no-jinja",
                    "--chat-template", "chatml"]),
    }
    monkeypatch.setattr(probe, "_process", lambda pid: commands[pid])
    monkeypatch.setattr(probe, "_owns_loopback_port", lambda pid, port: (pid, port) in {(123, 11455), (124, 51234)})
    expected = replace(probe.FROZEN_MODEL, daemon_sha256=_sha(b"daemon"), runner_sha256=_sha(b"runner"))
    kwargs = dict(daemon_pid=123, runner_pid=124, daemon_port=11455, runner_port=51234,
                  daemon_binary=daemon, runner_binary=runner, model_blob=model_blob)
    assert probe._process_identity(**kwargs, expected=expected) == {
        "daemon_binary_sha256": _sha(b"daemon"), "runner_binary_sha256": _sha(b"runner")}
    with pytest.raises(probe.ProbeError, match="runner_binary_digest_drift"):
        probe._process_identity(**kwargs, expected=replace(expected, runner_sha256="0" * 64))
