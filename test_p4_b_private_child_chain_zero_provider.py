"""One-process B child chain with a real SDK and fake HTTP transport.

No controller Popen, real Ollama, model generation, Safari, or formal DB is used.
The separate controller contract tests cover its final environment and Popen.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
from types import SimpleNamespace

import p4_preference_fallback_detached_control as control


def _child(root: Path, *, controller_issued: bool = False) -> int:
    import httpx
    from openai import OpenAI

    import uruha_p4_b_private_endpoint_binding as identity

    private = (Path(os.environ["URUHA_P4_B_MODEL_ROOT"])
               if controller_issued else (root / "private-model").resolve())
    runtime = (Path(os.environ["HOME"])
               if controller_issued else (root / "runtime").resolve())
    if not controller_issued:
        private.mkdir(mode=0o700)
        runtime.mkdir(mode=0o700)
        for name in ("memory_db", "session_db", "web_logs"):
            (runtime / name).mkdir(mode=0o700)
    entry = Path(identity.__file__).resolve().with_name(
        "uruha_web_ui_product_p4_preference_fallback.py")
    os_python = str(Path("/bin/sleep").resolve(strict=True))
    inprocess_python = str(Path(sys.executable).resolve(strict=True))
    assert os_python != inprocess_python
    sys.argv = [str(entry)]
    # This is a child-side fake identity, not a substitute for actual daemon
    # and runner verification in a future real product acceptance.
    identity._inspect_live_identity = lambda _binding: None
    binding = identity.PrivateEndpointBinding(
        run_id="fake-chain-run", private_root=private,
        shared_models=(root / "shared-models").resolve(),
        receipt_path=private / "p4_b_private_endpoint_launch_receipt.json",
        receipt_sha256="0" * 64, base_url="http://127.0.0.1:11455/v1",
        daemon_pid=101, runner_pid=102, daemon_port=11455, runner_port=55132,
        daemon_process_start="Sun Oct 25 01:02:03 2026",
        runner_process_start="Sun Oct 25 01:02:04 2026",
        daemon_raw_generation=(101, 1, 1792890123, 123456),
        runner_raw_generation=(102, 101, 1792890124, 654321),
        daemon_argv_sha256="a" * 64,
        runner_argv_sha256="b" * 64,
        operator_source_sha256=identity.private_child_source_digests(entry)[
            "operator_source_sha256"],
        daemon_binary=private / "ollama", runner_binary=private / "runner",
    )
    env = {
        "URUHA_P4_B_PRIVATE_CHILD": "1", "URUHA_P4_B_RUN_ID": binding.run_id,
        "URUHA_P4_B_MODEL_ROOT": str(private),
        "URUHA_P4_B_RECEIPT": str(binding.receipt_path),
        "URUHA_WEB_COMPUTE_LEDGER": "1", "URUHA_P4_COMPACT_JSON_SCHEMA": "1",
        "OLLAMA_NO_CLOUD": "1", "HOME": str(runtime), "TMPDIR": str(runtime),
        "URUHA_MEMORY_DB_PATH": str(runtime / "memory_db"),
        "URUHA_WEB_SESSION_DB_PATH": str(runtime / "session_db"),
        "URUHA_WEB_LOG_JSONL_PATH": str(runtime / "web_logs/conversation.jsonl"),
        "URUHA_WEB_LOG_TXT_PATH": str(runtime / "web_logs/conversation.txt"),
        "URUHA_WEB_HOST": "127.0.0.1", "URUHA_WEB_PORT": "7894",
    }
    if not controller_issued:
        for key in list(os.environ):
            if key.lower().endswith("_proxy") or key.upper().startswith("URUHA_P4_B_"):
                os.environ.pop(key)
        os.environ.update(env)
        identity.issue_private_child_receipt(
            binding=binding, runtime_root=runtime, environ=os.environ,
            entrypoint=entry, expected_final_argv=[os_python, str(entry)],
            expected_inprocess_python_argv=[inprocess_python, str(entry)],
        )
    receipt = json.loads(binding.receipt_path.read_bytes())
    assert receipt["schema"] == "p4_b_private_endpoint_launch_receipt_v5"
    source = identity.private_child_source_digests(entry)
    assert receipt["product_source_manifest_sha256"] == source[
        "product_source_manifest_sha256"]
    assert receipt["product_manifest_module_sha256"] == source[
        "product_manifest_module_sha256"]

    def no_socket(*_args, **_kwargs):
        raise AssertionError("real socket forbidden")

    socket.socket.connect = no_socket
    socket.socket.connect_ex = no_socket
    import uruha_p4_b_private_child_bootstrap as boot
    # This fake child is a test-file subprocess, not the fixed product entry.
    # Inject only the OS argv observer; production still queries its own PID.
    boot._self_os_argv = lambda: (os_python, [os_python, str(entry)])
    import uruha_web_ui_product_p4_preference_fallback as product
    import uruha_web_ui as web
    import uruha_brain_mac as brain

    state = boot.get_private_child_boot_state()
    assert state is not None
    assert product.RUNTIME is web.RUNTIME
    assert product.RUNTIME._compute_ledger is state.compute_ledger
    assert state.resource_gate is state.compute_ledger.p4_b_resource_gate

    requests = []
    def reply(request):
        requests.append((request.method, str(request.url)))
        return httpx.Response(200, json={
            "object": "list", "data": [{"id": "qwen2.5:7b", "object": "model"}],
        })

    def real_sdk_fake_transport(**kwargs):
        assert kwargs["base_url"] == "http://127.0.0.1:11455/v1"
        assert kwargs["http_client"]._trust_env is False
        assert kwargs["http_client"].follow_redirects is False
        kwargs["http_client"]._transport = httpx.MockTransport(reply)
        return OpenAI(**kwargs)

    brain.OpenAI = real_sdk_fake_transport
    brain.MemoryManager = lambda *, compute_ledger: SimpleNamespace(
        compute_ledger=compute_ledger,
    )
    brain.LeftBrain = lambda _client, **_kwargs: SimpleNamespace()
    brain.RightBrain = lambda **_kwargs: SimpleNamespace()
    brain._resolve_right_brain_model_loading = lambda _value: False
    brain.uapm.load_model = lambda _: ({}, {})
    created = product.RUNTIME.get_brain()
    assert created.compute_ledger is state.compute_ledger
    assert created.p4_b_private_target.base_url == "http://127.0.0.1:11455/v1"
    assert requests == [("GET", "http://127.0.0.1:11455/v1/models")]
    # A would-be completion stays closed without the exact transformed-request
    # prompt-token oracle; even the fake transport must see zero POST calls.
    from uruha_compact_planner_p2 import _REQUIRED_JSON_SCHEMA_FORMAT
    request = {
        "model": "qwen2.5:7b",
        "messages": [
            {"role": "system", "content": "You are the Left Brain Planner for a dual-brain character system."},
            {"role": "user", "content": "User Input: isolated fake child"},
        ],
        "temperature": 0.1, "timeout": 20.0, "max_tokens": 256,
        "response_format": _REQUIRED_JSON_SCHEMA_FORMAT,
    }
    try:
        with state.compute_ledger.stage("leftbrain_general_plan"):
            created.client_logic.chat.completions.create(**request)
    except Exception:
        pass
    else:
        raise AssertionError("B gate unexpectedly allowed a completion")
    assert requests == [("GET", "http://127.0.0.1:11455/v1/models")]
    assert state.resource_gate.snapshot()["terminal_reason"] == "prompt_upper_bound_unavailable"
    print(json.dumps({
        "ok": True, "same_ledger": True, "private_models_get": 1,
        "provider_completions": 0, "b_send_authorized": False,
    }))
    return 0


def test_fresh_fake_child_entry_to_brain_to_real_sdk_transport(tmp_path):
    result = subprocess.run(
        [sys.executable, str(Path(__file__).resolve()), "--child", str(tmp_path)],
        cwd=Path(__file__).resolve().parent, text=True,
        capture_output=True, timeout=60, check=False,
        env={key: value for key, value in os.environ.items()
             if not key.upper().startswith("URUHA_P4_B_")},
    )
    assert result.returncode == 0, (result.stdout[-1500:], result.stderr[-1500:])
    observed = json.loads(result.stdout.strip().splitlines()[-1])
    assert observed == {
        "ok": True, "same_ledger": True, "private_models_get": 1,
        "provider_completions": 0, "b_send_authorized": False,
    }


def test_controller_final_env_to_same_fake_child_chain(tmp_path, monkeypatch):
    """Controller signs one env; the separate child consumes that exact receipt.

    The Popen target is intentionally a fake child script, not the sandboxed
    product server or an HTTP-ready/Safari acceptance.
    """
    import uruha_p4_b_private_endpoint_binding as identity

    private = (tmp_path / "controller-private-model").resolve()
    private.mkdir(mode=0o700)
    entry = Path(identity.__file__).resolve().with_name(
        "uruha_web_ui_product_p4_preference_fallback.py")
    operator_sha = identity.private_child_source_digests(entry)[
        "operator_source_sha256"]
    descriptor = private / control.B_DESCRIPTOR_NAME
    descriptor.write_text(json.dumps({
        "schema": "p4_b_private_endpoint_descriptor_v2",
        "private_root": str(private), "shared_models": str((tmp_path / "shared").resolve()),
        "daemon_pid": 101, "runner_pid": 102,
        "daemon_port": 11455, "runner_port": 55132,
        "daemon_process_start": "Sun Oct 25 01:02:03 2026",
        "runner_process_start": "Sun Oct 25 01:02:04 2026",
        "daemon_raw_generation": [101, 1, 1792890123, 123456],
        "runner_raw_generation": [102, 101, 1792890124, 654321],
        "daemon_argv_sha256": "a" * 64,
        "runner_argv_sha256": "b" * 64,
        "operator_source_sha256": operator_sha,
        "daemon_binary": str(private / "ollama"),
        "runner_binary": str(private / "runner"),
    }))
    descriptor.chmod(0o600)
    prepared = Path(control.prepare()["runtime_root"])
    spawned = []
    popen_env = []
    real_popen = subprocess.Popen

    def profile(runtime_root):
        path = runtime_root / "product-write-isolation.sb"
        path.write_text("(version 1)\n(allow default)\n")
        path.chmod(0o600)
        return path

    def fake_popen(_command, **kwargs):
        assert _command[-2:] == [sys.executable, str(control.ENTRYPOINT)]
        popen_env.append(kwargs["env"].copy())
        process = real_popen(
            [sys.executable, str(Path(__file__).resolve()),
             "--child-controller", str(prepared)],
            cwd=Path(__file__).resolve().parent, env=kwargs["env"],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        )
        spawned.append(process)
        return process

    def fake_identity(pid):
        return {
            "pid": pid, "uid": os.getuid(), "pgid": pid,
            "lstart": "Sun Oct 25 01:00:00 2026",
            "command": f"{Path('/bin/sleep').resolve(strict=True)} {control.ENTRYPOINT}",
        }

    monkeypatch.setattr(control, "_validate_prepared_cache", lambda _root: None)
    monkeypatch.setattr(control, "_require_vacant", lambda: None)
    monkeypatch.setattr(control, "_b_committed_source_snapshot", lambda: {
        name: (operator_sha if name == "p4_b_private_zero_turn_operator.py"
               else "a" * 64) for name in control.B_COMMITTED_SOURCES
    })
    monkeypatch.setattr(control, "_b_controller_witness", lambda _binding: None)
    monkeypatch.setattr(control.sandbox, "write_sandbox_profile", profile)
    monkeypatch.setattr(control, "_calibrate_python_command", lambda *_args, **_kwargs: {
        "python_ps_executable": str(Path("/bin/sleep").resolve(strict=True)),
        "python_sys_executable": sys.executable,
        "identity": {"synthetic": True},
    })
    monkeypatch.setattr(control, "_identity", fake_identity)
    monkeypatch.setattr(control.subprocess, "Popen", fake_popen)
    monkeypatch.setattr(identity, "_inspect_live_identity", lambda _binding: None)
    try:
        launched = control.start(
            mode="product", python=sys.executable,
            prepared_runtime_root=str(prepared), p4_b_private=True,
            p4_b_private_descriptor=str(descriptor),
        )
        assert launched["ready"] is False
        assert len(spawned) == len(popen_env) == 1
        stdout, stderr = spawned[0].communicate(timeout=60)
        assert spawned[0].returncode == 0, (stdout[-1500:], stderr[-1500:])
        observed = json.loads(stdout.strip().splitlines()[-1])
        assert observed["same_ledger"] is True
        assert observed["provider_completions"] == 0
        _, metadata = control._root(str(prepared))
        assert metadata["final_command"] == (
            f"{Path('/bin/sleep').resolve(strict=True)} {control.ENTRYPOINT}"
        )
        assert metadata["calibration"]["python_sys_executable"] == sys.executable
        assert popen_env[0]["URUHA_P4_B_RUN_ID"] == launched["run_id"]
        assert popen_env[0]["URUHA_P4_B_RECEIPT"] == str(
            private / "p4_b_private_endpoint_launch_receipt.json")
    finally:
        if spawned and spawned[0].poll() is None:
            spawned[0].terminate()
            spawned[0].wait(timeout=5)
        shutil.rmtree(prepared)


if __name__ == "__main__":
    if len(sys.argv) != 3 or sys.argv[1] not in ("--child", "--child-controller"):
        raise SystemExit(2)
    raise SystemExit(_child(
        Path(sys.argv[2]), controller_issued=sys.argv[1] == "--child-controller",
    ))
