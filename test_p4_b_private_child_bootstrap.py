"""Zero-provider contracts for P4 B's pre-Web receipt and child bootstrap."""

import builtins
import json
import os
from pathlib import Path
import struct
import sys
import time

import pytest

import uruha_p4_b_private_child_bootstrap as child
import uruha_p4_b_private_endpoint_binding as identity
from uruha_p4_b_resource_gate import P4BResourceGate

_REAL_INSPECT = identity._inspect_live_identity


def _procargs(*, argc=2, executable=b"/bin/sleep",
              argv=(b"/bin/sleep", b"/fixed/entry.py"),
              tail=b"\xffPRIVATE_ENV_MUST_NOT_BE_PARSED=1\0"):
    return (struct.pack("=i", argc) + executable + b"\0\0\0"
            + b"".join(part + b"\0" for part in argv) + tail)


def test_procargs_parser_only_reads_exact_two_argv_not_environment():
    assert child._parse_self_procargs(_procargs()) == (
        "/bin/sleep", ["/bin/sleep", "/fixed/entry.py"])


@pytest.mark.parametrize("raw", [
    "not bytes", b"", b"\0" * 7, b"\0" * ((1 << 20) + 1),
    _procargs(argc=0), _procargs(argc=3),
    _procargs(executable=b""), _procargs(executable=b"\xff"),
    _procargs(argv=(b"", b"/fixed/entry.py")),
    _procargs(argv=(b"/bin/echo", b"/fixed/entry.py")),
    _procargs(argv=(b"/bin/sleep", b"\xff")),
    _procargs(argv=(b"/bin/sleep",)),
    struct.pack("=i", 2) + b"/bin/sleep",  # no exec NUL terminator
    struct.pack("=i", 2) + b"/bin/sleep\0\0/bin/sleep\0/entry",  # truncated argv
])
def test_procargs_parser_rejects_ambiguous_or_malformed_buffers(raw):
    with pytest.raises(identity.PrivateEndpointBindingError,
                       match="private_child_os_argv_"):
        child._parse_self_procargs(raw)


def test_self_os_argv_fails_closed_when_kernel_interface_unavailable(monkeypatch):
    monkeypatch.setattr(child.sys, "platform", "not-darwin")
    with pytest.raises(identity.PrivateEndpointBindingError,
                       match="private_child_os_argv_unavailable"):
        child._self_os_argv()


@pytest.mark.parametrize("failure", [
    "first_syscall", "oversize", "second_syscall", "returned_oversize",
])
def test_self_os_argv_refuses_kernel_errors_and_bad_lengths(monkeypatch, failure):
    monkeypatch.setattr(child.sys, "platform", "darwin")

    class FakeSysctl:
        def __init__(self):
            self.calls = 0

        def __call__(self, _mib, _mib_length, buffer, size_pointer, _new, _new_size):
            self.calls += 1
            size = child.ctypes.cast(
                size_pointer, child.ctypes.POINTER(child.ctypes.c_size_t))
            if self.calls == 1:
                size.contents.value = ((1 << 20) + 1 if failure == "oversize" else 64)
                return -1 if failure == "first_syscall" else 0
            assert buffer is not None
            size.contents.value = 65 if failure == "returned_oversize" else 64
            return -1 if failure == "second_syscall" else 0

    class FakeLibc:
        sysctl = FakeSysctl()

    fake = FakeLibc()
    monkeypatch.setattr(child.ctypes, "CDLL", lambda *_args, **_kwargs: fake)
    with pytest.raises(identity.PrivateEndpointBindingError,
                       match="private_child_os_argv_unavailable"):
        child._self_os_argv()
    assert fake.sysctl.calls == (1 if failure in ("first_syscall", "oversize") else 2)


def _fixture(tmp_path, monkeypatch):
    private = (tmp_path / "private").resolve()
    runtime = (tmp_path / "runtime").resolve()
    private.mkdir(mode=0o700)
    runtime.mkdir(mode=0o700)
    for directory in (private, runtime):
        directory.chmod(0o700)
    for name in ("memory_db", "session_db", "web_logs"):
        (runtime / name).mkdir(mode=0o700)
        (runtime / name).chmod(0o700)
    entry = Path(identity.__file__).resolve().with_name(
        "uruha_web_ui_product_p4_preference_fallback.py")
    os_python = str(Path("/bin/sleep").resolve(strict=True))
    inprocess_python = str(Path(sys.executable).resolve(strict=True))
    assert os_python != inprocess_python
    os_argv = [os_python, str(entry)]
    monkeypatch.setattr(child, "_BOOT_STATE", None)
    monkeypatch.setattr(sys, "argv", [str(entry)])
    monkeypatch.setattr(child, "_self_os_argv", lambda: (os_python, os_argv))
    monkeypatch.setattr(identity, "_inspect_live_identity", lambda _: None)
    binding = identity.PrivateEndpointBinding(
        run_id="b-test-123", private_root=private,
        shared_models=(tmp_path / "shared_models").resolve(),
        receipt_path=private / "p4_b_private_endpoint_launch_receipt.json",
        receipt_sha256="0" * 64, base_url="http://127.0.0.1:11455/v1",
        daemon_pid=101, runner_pid=102, daemon_port=11455, runner_port=55132,
        daemon_process_start="Sat Oct 24 12:00:00 2026",
        runner_process_start="Sat Oct 24 12:00:01 2026",
        daemon_binary=private / "ollama", runner_binary=private / "llama-server",
    )
    env = {
        "URUHA_P4_B_PRIVATE_CHILD": "1", "URUHA_P4_B_RUN_ID": binding.run_id,
        "URUHA_P4_B_MODEL_ROOT": str(private),
        "URUHA_P4_B_RECEIPT": str(binding.receipt_path),
        "URUHA_WEB_COMPUTE_LEDGER": "1",
        "URUHA_P4_COMPACT_JSON_SCHEMA": "1", "OLLAMA_NO_CLOUD": "1",
        "HOME": str(runtime), "TMPDIR": str(runtime),
        "URUHA_MEMORY_DB_PATH": str(runtime / "memory_db"),
        "URUHA_WEB_SESSION_DB_PATH": str(runtime / "session_db"),
        "URUHA_WEB_LOG_JSONL_PATH": str(runtime / "web_logs/conversation.jsonl"),
        "URUHA_WEB_LOG_TXT_PATH": str(runtime / "web_logs/conversation.txt"),
        "URUHA_WEB_HOST": "127.0.0.1", "URUHA_WEB_PORT": "7894",
    }
    issued = identity.issue_private_child_receipt(
        binding=binding, runtime_root=runtime, environ=env,
        entrypoint=entry, expected_final_argv=os_argv,
        expected_inprocess_python_argv=[inprocess_python, str(entry)],
    )
    return issued, runtime, env


def _rewrite(binding, **updates):
    receipt = json.loads(binding.receipt_path.read_bytes())
    receipt.update(updates)
    return _write_receipt_data(binding, receipt)


def _write_receipt_data(binding, receipt):
    raw = (json.dumps(receipt, sort_keys=True, separators=(",", ":")) + "\n").encode()
    binding.receipt_path.write_bytes(raw)
    binding.receipt_path.chmod(0o600)
    return receipt


def test_valid_bootstrap_is_pre_web_zero_provider_and_reuses_closed_ledger(
        tmp_path, monkeypatch):
    binding, runtime, env = _fixture(tmp_path, monkeypatch)
    receipt = json.loads(binding.receipt_path.read_bytes())
    assert receipt["schema"] == "p4_b_private_endpoint_launch_receipt_v3"
    assert receipt["expected_os_final_argv"][0] != str(Path(sys.executable).resolve())
    assert receipt["expected_final_argv_sha256"] == identity._final_argv_digest(
        receipt["expected_os_final_argv"]
    )
    assert receipt["expected_inprocess_python_argv_sha256"] == identity._final_argv_digest(
        [sys.executable, sys.argv[0]]
    )
    imports = []
    old_import = builtins.__import__

    def track_import(name, *args, **kwargs):
        if name.startswith("uruha_web_ui"):
            imports.append(name)
            raise AssertionError("Web import before bootstrap completed")
        return old_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", track_import)
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    state = child.bootstrap_private_child()
    assert state is child.get_private_child_boot_state()
    assert state.binding.receipt_sha256 == binding.receipt_sha256
    assert state.runtime_root == runtime
    assert state.compute_ledger.p4_b_resource_gate.snapshot()["attempted_provider_calls"] == 0
    assert state.compute_ledger.p4_b_resource_gate._prompt_token_upper_bound is None
    child.revalidate_private_child_before_create(state)
    assert imports == []


@pytest.mark.parametrize("mutation", [
    "missing_marker", "marker_zero", "missing_run", "missing_receipt",
    "lowercase_marker", "wrong_root", "env_drift", "proxy_upper",
    "proxy_mixed", "unknown_b_key", "old_v2", "source_drift",
    "web_source_drift", "ledger_source_drift",
])
def test_bad_intent_or_receipt_refused_before_web_or_provider(
        tmp_path, monkeypatch, mutation):
    binding, _runtime, env = _fixture(tmp_path, monkeypatch)
    if mutation == "missing_marker":
        env.pop("URUHA_P4_B_PRIVATE_CHILD")
    elif mutation == "marker_zero":
        env["URUHA_P4_B_PRIVATE_CHILD"] = "0"
    elif mutation == "missing_run":
        env.pop("URUHA_P4_B_RUN_ID")
    elif mutation == "missing_receipt":
        env.pop("URUHA_P4_B_RECEIPT")
    elif mutation == "lowercase_marker":
        env.pop("URUHA_P4_B_PRIVATE_CHILD")
        env["uruha_p4_b_private_child"] = "1"
    elif mutation == "wrong_root":
        env["URUHA_P4_B_MODEL_ROOT"] = str(tmp_path / "wrong")
    elif mutation == "env_drift":
        env["URUHA_WEB_PORT"] = "7895"
    elif mutation == "proxy_upper":
        env["HTTPS_PROXY"] = "http://proxy.invalid"
    elif mutation == "proxy_mixed":
        env["Https_Proxy"] = "http://proxy.invalid"
    elif mutation == "unknown_b_key":
        env["URUHA_P4_B_OVERRIDE"] = "untrusted"
    elif mutation == "old_v2":
        receipt = json.loads(binding.receipt_path.read_bytes())
        receipt["schema"] = "p4_b_private_endpoint_launch_receipt_v2"
        receipt.pop("expected_os_final_argv")
        receipt.pop("expected_inprocess_python_argv_sha256")
        _write_receipt_data(binding, receipt)
    elif mutation == "source_drift":
        _rewrite(binding, entrypoint_sha256="0" * 64)
    elif mutation == "web_source_drift":
        _rewrite(binding, web_source_sha256="0" * 64)
    elif mutation == "ledger_source_drift":
        _rewrite(binding, ledger_source_sha256="0" * 64)
    with pytest.raises(identity.PrivateEndpointBindingError):
        child.bootstrap_private_child(env)
    assert child._BOOT_STATE is None


@pytest.mark.parametrize("mutation", [
    "os_wrong_executable", "os_argv0_mismatch", "os_appended_argument",
    "os_unavailable",
    "inprocess_executable", "inprocess_argv0", "inprocess_extra_argument",
    "receipt_os_argv", "receipt_os_digest", "receipt_inprocess_digest",
    "receipt_missing_os_argv", "receipt_missing_inprocess_digest",
])
def test_independent_argv_tamper_fails_before_web_or_provider(
        tmp_path, monkeypatch, mutation):
    binding, _runtime, env = _fixture(tmp_path, monkeypatch)
    entry = str(child._ENTRYPOINT)
    os_python = str(Path("/bin/sleep").resolve(strict=True))
    other_python = str(Path("/bin/echo").resolve(strict=True))
    assert os_python != other_python
    reached_identity = []
    monkeypatch.setattr(identity, "_inspect_live_identity",
                        lambda value: reached_identity.append(value))
    if mutation == "os_wrong_executable":
        monkeypatch.setattr(child, "_self_os_argv", lambda: (
            other_python, [other_python, entry]))
    elif mutation == "os_argv0_mismatch":
        monkeypatch.setattr(child, "_self_os_argv", lambda: (
            os_python, [other_python, entry]))
    elif mutation == "os_appended_argument":
        monkeypatch.setattr(child, "_self_os_argv", lambda: (
            os_python, [os_python, entry, "--extra"]))
    elif mutation == "os_unavailable":
        def unavailable():
            raise identity.PrivateEndpointBindingError("private_child_os_argv_unavailable")
        monkeypatch.setattr(child, "_self_os_argv", unavailable)
    elif mutation == "inprocess_executable":
        monkeypatch.setattr(sys, "executable", other_python)
    elif mutation == "inprocess_argv0":
        monkeypatch.setattr(sys, "argv", [str(Path(identity.__file__).resolve())])
    elif mutation == "inprocess_extra_argument":
        monkeypatch.setattr(sys, "argv", [entry, "--extra"])
    elif mutation == "receipt_os_argv":
        changed = [other_python, entry]
        _rewrite(binding, expected_os_final_argv=changed,
                 expected_final_argv_sha256=identity._final_argv_digest(changed))
    elif mutation == "receipt_os_digest":
        _rewrite(binding, expected_final_argv_sha256="0" * 64)
    elif mutation == "receipt_inprocess_digest":
        _rewrite(binding, expected_inprocess_python_argv_sha256=(
            identity._final_argv_digest([other_python, entry])
        ))
    elif mutation == "receipt_missing_os_argv":
        receipt = json.loads(binding.receipt_path.read_bytes())
        receipt.pop("expected_os_final_argv")
        _write_receipt_data(binding, receipt)
    else:
        receipt = json.loads(binding.receipt_path.read_bytes())
        receipt.pop("expected_inprocess_python_argv_sha256")
        _write_receipt_data(binding, receipt)
    with pytest.raises(identity.PrivateEndpointBindingError):
        child.bootstrap_private_child(env)
    assert child._BOOT_STATE is None
    assert reached_identity == []


@pytest.mark.parametrize("drift", [
    "os_wrong_executable", "os_appended_argument", "os_unavailable",
    "inprocess_executable", "inprocess_argv0", "receipt_revoked",
])
def test_booted_child_rechecks_both_argv_identities_before_create(
        tmp_path, monkeypatch, drift):
    binding, _runtime, env = _fixture(tmp_path, monkeypatch)
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    state = child.bootstrap_private_child()
    entry = str(child._ENTRYPOINT)
    if drift == "os_wrong_executable":
        other_python = str(Path("/bin/echo").resolve(strict=True))
        monkeypatch.setattr(child, "_self_os_argv", lambda: (
            other_python, [other_python, entry]))
    elif drift == "os_appended_argument":
        os_python = str(Path("/bin/sleep").resolve(strict=True))
        monkeypatch.setattr(child, "_self_os_argv", lambda: (
            os_python, [os_python, entry, "--extra"]))
    elif drift == "os_unavailable":
        def unavailable():
            raise identity.PrivateEndpointBindingError("private_child_os_argv_unavailable")
        monkeypatch.setattr(child, "_self_os_argv", unavailable)
    elif drift == "inprocess_executable":
        monkeypatch.setattr(sys, "executable", str(Path("/bin/echo").resolve(strict=True)))
    elif drift == "inprocess_argv0":
        monkeypatch.setattr(sys, "argv", [str(Path(identity.__file__).resolve())])
    else:
        binding.receipt_path.unlink()
    with pytest.raises(identity.PrivateEndpointBindingError):
        child.get_private_child_boot_state()
    with pytest.raises(identity.PrivateEndpointBindingError):
        child.revalidate_private_child_before_create(state)


def test_wrong_shared_store_path_reaches_real_inspector_and_refuses(tmp_path, monkeypatch):
    binding, _runtime, env = _fixture(tmp_path, monkeypatch)
    _rewrite(binding, shared_models=str(tmp_path / "wrong-shared"))
    monkeypatch.setattr(identity, "_inspect_live_identity", _REAL_INSPECT)
    monkeypatch.setattr(identity, "_process_start", lambda pid: (
        binding.daemon_process_start if pid == binding.daemon_pid
        else binding.runner_process_start
    ))
    monkeypatch.setattr(identity, "_daemon_environment", lambda *args: None)
    def store(private_root, shared_models, expected):
        if shared_models != binding.shared_models:
            raise identity.ProbeError("shared_model_file_invalid")
        return private_root / "models", {"model": (1, 2, 3)}
    monkeypatch.setattr(identity, "_model_store", store)
    monkeypatch.setattr(identity, "_process_identity", lambda **kwargs: {
        "daemon_binary_sha256": identity.FROZEN_DAEMON_SHA256,
        "runner_binary_sha256": identity.FROZEN_RUNNER_SHA256,
    })
    with pytest.raises(identity.PrivateEndpointBindingError,
                       match="private_ollama_identity_drift"):
        child.bootstrap_private_child(env)
    assert child._BOOT_STATE is None


def test_receipt_revoke_or_environment_drift_blocks_precreate(tmp_path, monkeypatch):
    binding, _runtime, env = _fixture(tmp_path, monkeypatch)
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    state = child.bootstrap_private_child()
    monkeypatch.setenv("URUHA_WEB_PORT", "7895")
    with pytest.raises(identity.PrivateEndpointBindingError):
        child.get_private_child_boot_state()
    with pytest.raises(identity.PrivateEndpointBindingError):
        child.revalidate_private_child_before_create(state)
    monkeypatch.setenv("URUHA_WEB_PORT", "7894")
    _rewrite(binding, expires_at_epoch=time.time() - 1)
    with pytest.raises(identity.PrivateEndpointBindingError):
        child.revalidate_private_child_before_create(state)


def test_original_resource_gate_identity_cannot_be_swapped(tmp_path, monkeypatch):
    _binding, _runtime, env = _fixture(tmp_path, monkeypatch)
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    state = child.bootstrap_private_child()
    state.compute_ledger.p4_b_resource_gate = P4BResourceGate()
    with pytest.raises(identity.PrivateEndpointBindingError,
                       match="private_child_resource_gate_changed"):
        child.get_private_child_boot_state()
    with pytest.raises(identity.PrivateEndpointBindingError,
                       match="private_child_resource_gate_changed"):
        child.revalidate_private_child_before_create(state)


@pytest.mark.parametrize("issued,expires,now,valid", [
    (700.0, 1000.0, 1000.0, False),
    (700.0, 1000.0, 999.999, True),
    (699.999, 1000.0, 1000.0, False),
    (1002.0, 1003.0, 1000.0, True),
    (1002.001, 1003.0, 1000.0, False),
    (900.0, 1200.001, 1000.0, False),
    (900.0, 900.0, 1000.0, False),
    (True, 1001.0, 1000.0, False),
    (900.0, float("nan"), 1000.0, False),
    (10 ** 1000, 10 ** 1001, 1000.0, False),
])
def test_v3_receipt_time_contract(monkeypatch, issued, expires, now, valid):
    monkeypatch.setattr(identity.time, "time", lambda: now)
    receipt = {"issued_at_epoch": issued, "expires_at_epoch": expires}
    if valid:
        assert identity._valid_receipt_time(receipt) == expires
    else:
        with pytest.raises(identity.PrivateEndpointBindingError,
                           match="receipt_expired_or_invalid"):
            identity._valid_receipt_time(receipt)


def test_receipt_expiry_during_live_inspection_refused(tmp_path, monkeypatch):
    binding, _runtime, env = _fixture(tmp_path, monkeypatch)
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    now = time.time()
    _rewrite(binding, issued_at_epoch=now - 2, expires_at_epoch=now + 1)
    def expire_during_inspection(_):
        monkeypatch.setattr(identity.time, "time", lambda: now + 2)
    monkeypatch.setattr(identity, "_inspect_live_identity", expire_during_inspection)
    with pytest.raises(identity.PrivateEndpointBindingError):
        child.bootstrap_private_child()
    assert child._BOOT_STATE is None


def test_no_b_intent_remains_default_without_boot_state(tmp_path, monkeypatch):
    monkeypatch.setattr(child, "_BOOT_STATE", None)
    assert child.bootstrap_private_child({"HOME": str(tmp_path)}) is None


def _run_self_os_argv_probe() -> int:
    """No-service actual-script probe for the frozen sandbox profile."""
    try:
        script = str(Path(__file__).resolve(strict=True))
        os_python, os_argv = child._self_os_argv()
        if (os_argv != [os_python, script]
                or str(Path(os_python).resolve(strict=True)) != os_python):
            raise ValueError("os_argv_shape")
        inprocess_python = sys.executable
        if os_python == inprocess_python:
            raise ValueError("executables_not_distinct")
        os_digest = identity._final_argv_digest([os_python, str(child._ENTRYPOINT)])
        inprocess_digest = identity._final_argv_digest([
            inprocess_python, str(child._ENTRYPOINT),
        ])
        if os_digest == inprocess_digest:
            raise ValueError("digests_not_distinct")
    except (OSError, ValueError, identity.PrivateEndpointBindingError) as exc:
        print(json.dumps({"ok": False, "reason": str(exc) if isinstance(exc, ValueError)
                          else "os_argv_or_digest_unavailable"}))
        return 1
    print(json.dumps({
        "ok": True,
        "os_argv_sha256": os_digest,
        "inprocess_argv_sha256": inprocess_digest,
        "distinct_executables": True,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 1:
        raise SystemExit(2)
    raise SystemExit(_run_self_os_argv_probe())
