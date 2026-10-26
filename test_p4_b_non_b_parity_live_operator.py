"""Fake-only contract for the one-use non-B parity live operator.

No test starts Ollama, opens HTTP or uses a real model. The process-watchdog
slice signals only its own short-lived synthetic fork children.
"""

from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import mmap
import os
from pathlib import Path
import select
import signal
import socket
import stat
import sys
import tempfile
import time
import urllib.request

import pytest

import p4_b_non_b_parity_live_operator as live
import p4_b_non_b_usage_parity as parity
from p4_b_isolated_ollama_identity_probe import (
    FROZEN_DAEMON_SHA256, FROZEN_MANIFEST_SHA256, FROZEN_RUNNER_SHA256,
    GGUF_SHA256,
)


CANARY = "RAW_LIVE_OPERATOR_CANARY_MUST_NOT_ESCAPE"
STAGES = (
    "before_metadata", "after_render", "before_tokenize_true",
    "before_tokenize_default", "before_completion", "after_completion",
)
OPERATIONS = (
    ("GET", "/api/version"),
    ("GET", "/api/tags"),
    ("POST", "/api/show"),
    ("POST", "/v1/chat/completions"),
    ("POST", "/tokenize"),
    ("POST", "/tokenize"),
    ("POST", "/v1/chat/completions"),
)
WORKER = {"pid": 202, "ppid": 101, "start_sec": 1000, "start_usec": 12}


_DARWIN_FORK = pytest.mark.skipif(
    sys.platform != "darwin" or not hasattr(os, "fork"),
    reason="the synthetic raw-generation watcher uses macOS libproc/fork",
)


def _canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")


def _ack(_grant):
    """Explicit fake ACK callback; return is not worker-delivery proof."""
    return None


def _read_only_journal(run_dir: Path) -> tuple[Path, dict]:
    """Inspect committed state; a failed update may leave a private intent."""
    journal = run_dir / "journal.json"
    assert journal.is_file()
    assert stat.S_IMODE(journal.stat().st_mode) == 0o600
    raw = journal.read_bytes()
    assert raw == _canonical(json.loads(raw))
    assert CANARY.encode() not in raw
    return journal, json.loads(raw)


def _grant_fields(ordinal: int, *, run_id="synthetic-run") -> dict:
    method, path = OPERATIONS[ordinal - 1]
    role = "runner" if ordinal in (5, 6) else "daemon"
    return {
        "run_id": run_id, "worker": dict(WORKER), "ordinal": ordinal,
        "target_role": role, "port": 55132 if role == "runner" else 11455,
        "method": method, "path": path,
        "payload_sha256": (None if method == "GET" else
                           hashlib.sha256(f"payload-{ordinal}".encode()).hexdigest()),
        "expires_at": 180.0,
    }


def _reserve_first(journal, n: int):
    return [journal.reserve(_grant_fields(ordinal), ack=_ack)
            for ordinal in range(1, n + 1)]


def _worker_harness(monkeypatch, tmp_path):
    """One fully injected seven-call worker; private blobs are never read."""
    template = "synthetic template, not a private model blob"
    system = "synthetic system, not a private model blob"
    monkeypatch.setattr(live, "TEMPLATE_SHA256", hashlib.sha256(template.encode()).hexdigest())
    monkeypatch.setattr(live, "SYSTEM_SHA256", hashlib.sha256(system.encode()).hexdigest())
    request = parity.fixed_transformed_request()
    rendered = ("<|im_start|>system\n" + request["messages"][0]["content"]
                + "<|im_end|>\n<|im_start|>user\n"
                + request["messages"][1]["content"]
                + "<|im_end|>\n<|im_start|>assistant\n")
    daemon_argv = ["ollama", "serve"]
    runner_argv = ["ollama_llama_server", "--no-jinja", "--chat-template",
                   "chatml", "-c", "32768", "-np", "4"]
    daemon = {
        "pid": 101, "ppid": 1, "raw_generation": [101, 1, 1000, 12],
        "pgid": 101, "port": 11455,
        "argv_sha256": hashlib.sha256(_canonical(daemon_argv)).hexdigest(),
        "binary_sha256": FROZEN_DAEMON_SHA256,
        "manifest_sha256": FROZEN_MANIFEST_SHA256,
        "template_sha256": live.TEMPLATE_SHA256,
        "system_sha256": live.SYSTEM_SHA256,
        "gguf_sha256": GGUF_SHA256,
    }
    runner = {
        "pid": 102, "ppid": 101, "raw_generation": [102, 101, 1001, 13],
        "pgid": 102, "port": 55132,
        "argv_sha256": hashlib.sha256(_canonical(runner_argv)).hexdigest(),
        "binary_sha256": FROZEN_RUNNER_SHA256,
        "gguf_sha256": GGUF_SHA256,
    }
    source = {
        "source_revision": "v0.34.4", "version": "0.34.4",
        "renderer": None, "parser": None, "messages": [],
        "manifest_messages": [], "daemon_argv": daemon_argv,
        "runner_argv": runner_argv, "gguf_pre": "qwen2",
        "gguf_model": "gpt2", "gguf_add_bos_token": False,
        "model_num_ctx": 8192, "daemon_default_num_ctx": 8192,
        "normal_request_options": {}, "render_request_options": {},
    }
    binding = {"run_id": "synthetic-run", "daemon": daemon,
               "worker": dict(WORKER), "source": source,
               "t0": 100.0, "work_stop_at": 180.0}
    journal = live.DurableJournal.create(tmp_path / "run", "synthetic-run")
    state = {
        "time": 100.0, "stages": [], "specs": [], "calls": [],
        "tokens_true": [1, 2, 3], "tokens_default": [1, 2, 3],
        "usage": {"prompt_tokens": 3, "completion_tokens": 2,
                  "total_tokens": 5},
        "block_http": None, "body_change": None, "grant_change": None,
        "transport_change": None, "http_grant_change": None,
        "after_http": None, "minted_grants": [],
        "daemon": daemon, "runner": runner,
    }

    def observe_identity(stage):
        state["stages"].append(stage)
        return {"run_id": binding["run_id"], "identity_http_calls": 0,
                "daemon": deepcopy(daemon),
                "runner": None if stage == "before_metadata" else deepcopy(runner)}

    def authorize_call(spec):
        state["specs"].append(deepcopy(spec))
        grant = journal.reserve(spec, ack=_ack)
        state["minted_grants"].append(deepcopy(grant))
        if state["grant_change"] is not None:
            state["grant_change"](grant, state)
        return grant

    def http_call(method, url, payload, remaining, grant):
        index = len(state["calls"]) + 1
        state["calls"].append((method, url, deepcopy(payload), remaining,
                               deepcopy(grant)))
        assert 0 < remaining <= 80
        journal.mark_worker_issued(index, grant["nonce"])
        if state["block_http"] == index:
            raise RuntimeError(CANARY)
        if index == 1:
            body = {"version": "0.34.4"}
        elif index == 2:
            body = {"models": [{"name": "qwen2.5:7b",
                                "digest": FROZEN_MANIFEST_SHA256}]}
        elif index == 3:
            body = {"template": template, "system": system}
        elif index == 4:
            body = {"model": "qwen2.5:7b",
                    "_debug_info": {"rendered_template": rendered},
                    "usage": {"prompt_tokens": 0, "completion_tokens": 0,
                              "total_tokens": 0},
                    "choices": [{"message": {"content": ""}}]}
        elif index in (5, 6):
            body = {"tokens": deepcopy(state["tokens_true"] if index == 5
                                       else state["tokens_default"])}
        elif index == 7:
            body = {"model": "qwen2.5:7b", "usage": deepcopy(state["usage"]),
                    "choices": [{"message": {"content": CANARY}}]}
        else:
            pytest.fail("an eighth external HTTP operation was attempted")
        if state["body_change"] is not None:
            state["body_change"](body, index)
        result = {"requested_url": url, "effective_url": url,
                  "proxy_used": False, "redirected": False, "status": 200,
                  "body": _canonical(body)}
        if state["transport_change"] is not None:
            state["transport_change"](result, index)
        if (set(result) == {"requested_url", "effective_url", "proxy_used",
                            "redirected", "status", "body"}
                and result["requested_url"] == url
                and result["effective_url"] == url
                and result["proxy_used"] is False
                and result["redirected"] is False
                and type(result["status"]) is int
                and result["status"] == 200
                and type(result["body"]) is bytes
                and len(result["body"]) <= 2 * 1024 * 1024):
            journal.mark_on_wire(index, grant["nonce"])
        if state["http_grant_change"] is not None:
            state["http_grant_change"](grant, index)
        if state["after_http"] is not None:
            state["after_http"](state, index)
        return result

    kwargs = {"binding": binding, "clock": lambda: state["time"],
              "observe_identity": observe_identity,
              "authorize_call": authorize_call, "http_call": http_call}
    return kwargs, state, journal, rendered


def test_frame_is_length_prefixed_canonical_utf8_and_bounded():
    value = {"z": "日本語", "a": 7}
    frame = live.encode_frame(value)
    body = _canonical(value)
    assert frame == len(body).to_bytes(4, "big") + body
    assert live.decode_frame(frame, keys={"a", "z"}) == value
    with pytest.raises(Exception):
        live.encode_frame({"huge": "x" * 4096})


@pytest.mark.parametrize("frame", [
    b"", b"\x00\x00\x00", b"\x00\x00\x00\x02{}x",
    b"\x00\x00\x00\x09" + b'{"x": 1}',  # noncanonical space
    b"\x00\x00\x00\x0d" + b'{"x":1,"x":2}',
    b"\x00\x00\x00\x03" + b"NaN",
])
def test_frame_rejects_malformed_noncanonical_or_duplicate_input(frame):
    with pytest.raises(Exception):
        live.decode_frame(frame)


def test_frame_rejects_unknown_field_even_if_canonical():
    with pytest.raises(Exception):
        live.decode_frame(live.encode_frame({"run_id": "r", "raw": CANARY}),
                          keys={"run_id"})


def test_bounded_pipe_reader_accepts_exact_max_frame_only_after_eof():
    value = {"a": "x" * (live.FRAME_LIMIT - len(_canonical({"a": ""})))}
    frame = live.encode_frame(value)
    assert len(frame) == live.FRAME_LIMIT + 4
    for trailing, expected in ((b"", value), (b"x", None)):
        read_fd, write_fd = os.pipe()
        try:
            os.write(write_fd, frame + trailing)
            os.close(write_fd)
            write_fd = -1
            observed = live._fake_read_bounded(
                read_fd, time.monotonic() + 0.2, framed=True, keys={"a"})
            assert observed == expected
        finally:
            os.close(read_fd)
            if write_fd >= 0:
                os.close(write_fd)


def test_initial_journal_is_exclusive_durable_zero_count_and_0600(tmp_path):
    run_dir = tmp_path / "new-run"
    assert not run_dir.exists()
    journal = live.DurableJournal.create(run_dir, "synthetic-run")
    assert stat.S_IMODE(run_dir.stat().st_mode) == 0o700
    _, disk = _read_only_journal(run_dir)
    assert [path.name for path in run_dir.iterdir()] == ["journal.json"]
    snapshot = journal.snapshot()
    assert snapshot["run_id"] == disk["run_id"] == "synthetic-run"
    assert snapshot["reserved"] == disk["reserved"] == 0
    assert snapshot["granted"] == disk["granted"] == 0
    assert snapshot["ack_callback_returned"] == disk["ack_callback_returned"] == 0
    assert snapshot["ack_failed_terminal"] == disk["ack_failed_terminal"] == 0
    assert snapshot["completion_attempt_spent"] == 0
    assert disk["completion_attempt_spent"] == 0


@pytest.mark.parametrize("preexisting", ["directory", "file"])
def test_existing_run_refused_without_resume_or_mutation(tmp_path, preexisting):
    run_dir = tmp_path / "existing-run"
    if preexisting == "directory":
        run_dir.mkdir()
        marker = run_dir / "marker"
        marker.write_text(CANARY)
    else:
        run_dir.write_text(CANARY)
        marker = run_dir
    old = marker.read_bytes()
    with pytest.raises(Exception):
        live.DurableJournal.create(run_dir, "synthetic-run")
    assert marker.read_bytes() == old


@pytest.mark.parametrize("ack", [None, object()])
def test_missing_or_noncallable_ack_cannot_mint_usable_grant(tmp_path, ack):
    journal = live.DurableJournal.create(tmp_path / "run", "synthetic-run")
    before = journal.snapshot()
    with pytest.raises(live.LiveOperatorError, match="^grant_ack_required$"):
        journal.reserve(_grant_fields(1), ack=ack)
    assert journal.snapshot() == before
    _, disk = _read_only_journal(journal.run_dir)
    assert disk == before


def test_journal_op7_spent_is_durable_before_ack_and_ack_loss_never_refunds(tmp_path):
    run_dir = tmp_path / "run"
    journal = live.DurableJournal.create(run_dir, "synthetic-run")
    grants = _reserve_first(journal, 6)
    assert [grant["ordinal"] for grant in grants] == list(range(1, 7))
    assert len({grant["nonce"] for grant in grants}) == 6

    seen = []

    def lost_ack(grant):
        assert grant["ordinal"] == 7
        assert grant["run_id"] == "synthetic-run"
        assert grant["worker"] == WORKER
        assert grant["nonce"] not in {older["nonce"] for older in grants}
        _, disk = _read_only_journal(run_dir)
        assert disk["reserved"] == disk["granted"] == 7
        assert disk["ack_callback_returned"] == 6
        assert disk["completion_attempt_spent"] == 1
        assert disk["operations"][-1]["ordinal"] == 7
        assert disk["operations"][-1]["on_wire"] == "unknown"
        seen.append(disk)
        raise RuntimeError(CANARY)

    with pytest.raises(live.LiveOperatorError) as caught:
        journal.reserve(_grant_fields(7), ack=lost_ack)
    assert str(caught.value) == "grant_ack_failed"
    assert CANARY not in repr(caught.value)
    assert caught.value.__cause__ is None
    assert caught.value.__context__ is None
    assert len(seen) == 1
    snap = journal.snapshot()
    assert snap["reserved"] == snap["granted"] == 7
    assert snap["ack_callback_returned"] == 6
    assert snap["operations"][-1]["ack_callback_returned"] == 0
    assert snap["completion_attempt_spent"] == 1
    assert snap["operations"][-1]["on_wire"] == "unknown"
    with pytest.raises(live.LiveOperatorError):
        journal.reserve(_grant_fields(7), ack=_ack)
    with pytest.raises(live.LiveOperatorError):
        journal.reserve({**_grant_fields(7), "ordinal": 8}, ack=_ack)
    assert journal.snapshot() == snap


def test_op1_ack_loss_makes_op2_terminal_without_refund(tmp_path):
    journal = live.DurableJournal.create(tmp_path / "run", "synthetic-run")

    def lost_ack(_grant):
        raise RuntimeError(CANARY)

    with pytest.raises(live.LiveOperatorError, match="^grant_ack_failed$"):
        journal.reserve(_grant_fields(1), ack=lost_ack)
    snap = journal.snapshot()
    assert snap["reserved"] == snap["granted"] == 1
    assert snap["ack_callback_returned"] == 0
    assert snap["ack_failed_terminal"] == 1
    assert snap["operations"][0]["on_wire"] == "unknown"
    with pytest.raises(live.LiveOperatorError, match="^grant_ack_terminal$"):
        journal.reserve(_grant_fields(2), ack=_ack)
    assert journal.snapshot() == snap
    _, disk = _read_only_journal(journal.run_dir)
    assert disk == snap


def test_journal_rejects_out_of_order_and_replayed_worker_nonce(tmp_path):
    journal = live.DurableJournal.create(tmp_path / "run", "synthetic-run")
    with pytest.raises(live.LiveOperatorError):
        journal.reserve(_grant_fields(2), ack=_ack)
    grant = journal.reserve(_grant_fields(1), ack=_ack)
    assert journal.snapshot()["reserved"] == 1
    with pytest.raises(live.LiveOperatorError):
        journal.reserve(_grant_fields(1), ack=_ack)
    with pytest.raises(live.LiveOperatorError):
        journal.mark_worker_issued(1, "wrong-nonce")
    assert journal.snapshot()["worker_issued"] == 0
    journal.mark_worker_issued(1, grant["nonce"])
    assert journal.snapshot()["worker_issued"] == 1
    with pytest.raises(live.LiveOperatorError):
        journal.mark_worker_issued(1, grant["nonce"])
    journal.mark_on_wire(1, grant["nonce"])
    assert journal.snapshot()["operations"][0]["on_wire"] == "yes"
    with pytest.raises(live.LiveOperatorError):
        journal.mark_on_wire(1, grant["nonce"])
    mismatched_worker = _grant_fields(2)
    mismatched_worker["worker"] = {**WORKER, "start_usec": 13}
    with pytest.raises(live.LiveOperatorError):
        journal.reserve(mismatched_worker, ack=_ack)
    assert journal.snapshot()["reserved"] == 1


@pytest.mark.parametrize("field,replacement", [
    ("run_id", "wrong-run"),
    ("worker", {**WORKER, "pid": True}),
    ("target_role", "runner"),
    ("port", 11434),
    ("method", "POST"),
    ("path", "/v1/chat/completions"),
    ("payload_sha256", "0" * 64),
    ("expires_at", -1.0),
])
def test_journal_rejects_mismatched_or_expired_first_grant_without_state_change(
        tmp_path, field, replacement):
    journal = live.DurableJournal.create(tmp_path / "run", "synthetic-run")
    before = journal.snapshot()
    bad = _grant_fields(1)
    bad[field] = replacement
    with pytest.raises(live.LiveOperatorError):
        journal.reserve(bad, ack=_ack)
    assert journal.snapshot() == before


def test_huge_json_integer_expiry_fails_fixed_and_raw_free_before_reservation(
        tmp_path):
    journal = live.DurableJournal.create(tmp_path / "run", "synthetic-run")
    before = journal.snapshot()
    fields = _grant_fields(1)
    fields["expires_at"] = 10 ** 5000
    with pytest.raises(live.LiveOperatorError) as caught:
        journal.reserve(fields, ack=_ack)
    assert str(caught.value) in {"grant_invalid", "ipc_invalid"}
    assert caught.value.__cause__ is None
    assert caught.value.__context__ is None
    assert journal.snapshot() == before


def test_worker_positive_exact_seven_calls_six_os_observations_and_raw_free_summary(
        monkeypatch, tmp_path):
    kwargs, state, journal, rendered = _worker_harness(monkeypatch, tmp_path)
    summary = live.worker_once(**kwargs)
    assert summary["schema"] == "fake_non_b_worker_v1"
    assert summary["status"] == "fake_non_b_parity_pass"
    assert summary["http_calls"] == 7
    assert summary["identity_checks"] == 6
    assert summary["signed_delta"] == 0
    assert summary["provider_usage"] == {
        "prompt_tokens": 3, "completion_tokens": 2, "total_tokens": 5}
    assert summary["b_upper_bound_proven"] is False
    assert summary["b_send_authorized"] is False
    assert state["stages"] == list(STAGES)
    assert [(method, url) for method, url, _, _, _ in state["calls"]] == [
        ("GET", "http://127.0.0.1:11455/api/version"),
        ("GET", "http://127.0.0.1:11455/api/tags"),
        ("POST", "http://127.0.0.1:11455/api/show"),
        ("POST", "http://127.0.0.1:11455/v1/chat/completions"),
        ("POST", "http://127.0.0.1:55132/tokenize"),
        ("POST", "http://127.0.0.1:55132/tokenize"),
        ("POST", "http://127.0.0.1:11455/v1/chat/completions"),
    ]
    request = parity.fixed_transformed_request()
    normal = deepcopy(request)
    del normal["timeout"]
    assert [call[2] for call in state["calls"][:3]] == [
        None, None, {"model": "qwen2.5:7b"}]
    assert state["calls"][3][2] == {**normal, "_debug_render_only": True}
    assert state["calls"][4][2] == {
        "content": rendered, "add_special": False, "parse_special": True}
    assert state["calls"][5][2] == {
        "content": rendered, "add_special": False}
    assert state["calls"][6][2] == normal
    assert [spec["ordinal"] for spec in state["specs"]] == list(range(1, 8))
    assert all(spec["run_id"] == kwargs["binding"]["run_id"]
               and spec["worker"] == WORKER for spec in state["specs"])
    for index, (method, path) in enumerate(OPERATIONS, 1):
        spec = state["specs"][index - 1]
        grant = state["calls"][index - 1][4]
        assert (spec["method"], spec["path"]) == (method, path)
        assert {key: grant[key] for key in spec} == spec
        assert grant["payload_sha256"] == (
            None if method == "GET" else
            hashlib.sha256(_canonical(state["calls"][index - 1][2])).hexdigest())
    snap = journal.snapshot()
    assert (snap["reserved"], snap["granted"], snap["ack_callback_returned"],
            snap["worker_issued"]) == (7, 7, 7, 7)
    assert snap["completion_attempt_spent"] == 1
    assert [op["on_wire"] for op in snap["operations"]] == ["yes"] * 7
    encoded = live.encode_frame(summary)
    assert live.decode_frame(encoded, keys=set(summary)) == summary
    assert CANARY.encode() not in encoded
    assert rendered.encode() not in encoded
    assert CANARY not in json.dumps(snap)


@pytest.mark.parametrize("blocked_ordinal", range(1, 8))
def test_blocked_http_at_each_ordinal_stops_without_retry_or_raw_leak(
        monkeypatch, tmp_path, blocked_ordinal):
    kwargs, state, journal, _ = _worker_harness(monkeypatch, tmp_path)
    state["block_http"] = blocked_ordinal
    with pytest.raises(live.LiveOperatorError) as caught:
        live.worker_once(**kwargs)
    assert CANARY not in repr(caught.value)
    assert caught.value.__cause__ is None
    assert caught.value.__context__ is None
    assert len(state["specs"]) == len(state["calls"]) == blocked_ordinal
    snap = journal.snapshot()
    assert snap["reserved"] == snap["granted"] == blocked_ordinal
    assert snap["completion_attempt_spent"] == int(blocked_ordinal == 7)
    assert snap["operations"][-1]["on_wire"] == "unknown"
    assert [op["on_wire"] for op in snap["operations"][:-1]] == [
        "yes"] * (blocked_ordinal - 1)


@pytest.mark.parametrize("field,replacement", [
    ("port", 11456),  # a different private port, not just forbidden 11434
    ("port", 11434),
    ("run_id", "wrong-run"),
    ("worker", {**WORKER, "pid": 203}),
    ("ordinal", 2),
    ("target_role", "runner"),
    ("method", "POST"),
    ("path", "/api/tags"),
    ("payload_sha256", "0" * 64),
    ("nonce", "not-a-nonce"),
])
def test_worker_rejects_tampered_grant_before_transport_send(
        monkeypatch, tmp_path, field, replacement):
    kwargs, state, journal, _ = _worker_harness(monkeypatch, tmp_path)
    state["grant_change"] = lambda grant, _state: grant.update({field: replacement})
    with pytest.raises(live.LiveOperatorError):
        live.worker_once(**kwargs)
    assert len(state["specs"]) == 1
    assert state["calls"] == []
    snap = journal.snapshot()
    assert snap["reserved"] == 1
    assert snap["worker_issued"] == 0
    assert snap["operations"][0]["on_wire"] == "unknown"


@pytest.mark.parametrize("field", ["ppid", "raw_generation_ppid"])
def test_daemon_boolean_equal_to_integer_is_still_identity_drift(
        monkeypatch, tmp_path, field):
    kwargs, state, journal, _ = _worker_harness(monkeypatch, tmp_path)
    original = kwargs["observe_identity"]

    def boolean_witness(stage):
        observation = original(stage)
        if stage == "before_metadata":
            if field == "ppid":
                observation["daemon"]["ppid"] = True
            else:
                observation["daemon"]["raw_generation"][1] = True
        return observation

    kwargs["observe_identity"] = boolean_witness
    with pytest.raises(live.LiveOperatorError, match="^identity_drift$"):
        live.worker_once(**kwargs)
    assert state["stages"] == ["before_metadata"]
    assert state["specs"] == state["calls"] == []
    assert journal.snapshot()["reserved"] == 0


def test_http_callback_in_place_grant_mutation_cannot_fake_pass(
        monkeypatch, tmp_path):
    kwargs, state, journal, _ = _worker_harness(monkeypatch, tmp_path)
    state["http_grant_change"] = lambda grant, index: (
        grant.update(port=11456) if index == 1 else None)
    with pytest.raises(live.LiveOperatorError, match="^grant_mutated$"):
        live.worker_once(**kwargs)
    assert len(state["specs"]) == len(state["calls"]) == 1
    assert journal.snapshot()["reserved"] == 1
    assert journal.snapshot()["operations"][0]["on_wire"] == "yes"


def test_missing_grant_or_replayed_nonce_stops_before_second_transport(
        monkeypatch, tmp_path):
    kwargs, state, journal, _ = _worker_harness(monkeypatch, tmp_path)
    state["grant_change"] = lambda grant, _state: grant.pop("nonce")
    with pytest.raises(live.LiveOperatorError):
        live.worker_once(**kwargs)
    assert state["calls"] == []
    assert journal.snapshot()["operations"][0]["on_wire"] == "unknown"

    second = tmp_path / "second"
    second.mkdir()
    kwargs, state, journal, _ = _worker_harness(monkeypatch, second)

    def replay(grant, state):
        if grant["ordinal"] == 2:
            grant["nonce"] = state["minted_grants"][0]["nonce"]

    state["grant_change"] = replay
    with pytest.raises(live.LiveOperatorError):
        live.worker_once(**kwargs)
    assert len(state["calls"]) == 1
    assert journal.snapshot()["reserved"] == 2
    assert journal.snapshot()["operations"][1]["on_wire"] == "unknown"


def test_expired_grant_is_never_sent_even_when_ack_arrived(monkeypatch, tmp_path):
    kwargs, state, journal, _ = _worker_harness(monkeypatch, tmp_path)
    state["grant_change"] = lambda grant, state: state.update(
        time=grant["expires_at"])
    with pytest.raises(live.LiveOperatorError):
        live.worker_once(**kwargs)
    assert len(state["specs"]) == 1
    assert state["calls"] == []
    snap = journal.snapshot()
    assert snap["reserved"] == snap["granted"] == 1
    assert snap["worker_issued"] == 0
    assert snap["operations"][0]["on_wire"] == "unknown"


def test_worker_inherits_parent_work_deadline_not_fresh_eighty_seconds(
        monkeypatch, tmp_path):
    kwargs, state, journal, _ = _worker_harness(monkeypatch, tmp_path)
    state["time"] = 179.5
    summary = live.worker_once(**kwargs)
    assert summary["http_calls"] == 7
    assert {spec["expires_at"] for spec in state["specs"]} == {180.0}
    assert all(0 < call[3] <= 0.5 for call in state["calls"])
    assert journal.snapshot()["completion_attempt_spent"] == 1

    second = tmp_path / "second"
    second.mkdir()
    kwargs, state, journal, _ = _worker_harness(monkeypatch, second)
    state["time"] = 180.0
    with pytest.raises(live.LiveOperatorError):
        live.worker_once(**kwargs)
    assert state["specs"] == state["calls"] == []
    assert journal.snapshot()["completion_attempt_spent"] == 0


def test_worker_work_stop_after_render_blocks_later_grants_and_completion(
        monkeypatch, tmp_path):
    kwargs, state, journal, _ = _worker_harness(monkeypatch, tmp_path)
    state["after_http"] = lambda state, index: (
        state.update(time=180.0) if index == 4 else None)
    with pytest.raises(live.LiveOperatorError, match="^work_deadline_exceeded$"):
        live.worker_once(**kwargs)
    assert len(state["specs"]) == len(state["calls"]) == 4
    assert journal.snapshot()["completion_attempt_spent"] == 0


@pytest.mark.parametrize("change", [
    lambda result: result.update(effective_url="http://127.0.0.1:11456/api/version"),
    lambda result: result.update(proxy_used=True),
    lambda result: result.update(redirected=True),
    lambda result: result.update(status=302),
    lambda result: result.update(body=b"x" * (2 * 1024 * 1024 + 1)),
])
def test_injected_transport_drift_or_oversize_stops_after_one_spent_grant(
        monkeypatch, tmp_path, change):
    kwargs, state, journal, _ = _worker_harness(monkeypatch, tmp_path)
    state["transport_change"] = lambda result, index: (
        change(result) if index == 1 else None)
    with pytest.raises(live.LiveOperatorError):
        live.worker_once(**kwargs)
    assert len(state["specs"]) == len(state["calls"]) == 1
    assert journal.snapshot()["reserved"] == 1
    assert journal.snapshot()["completion_attempt_spent"] == 0
    assert journal.snapshot()["worker_issued"] == 1
    assert journal.snapshot()["operations"][0]["on_wire"] == "unknown"


@pytest.mark.parametrize("case", [
    "native_renderer", "extra_message", "manifest_extra_message",
    "bos_added", "duplicate_context",
    "numctx_mismatch", "rendered_utf8_not_below_numctx",
])
def test_known_source_condition_failure_refuses_operation_seven(
        monkeypatch, tmp_path, case):
    kwargs, state, journal, rendered = _worker_harness(monkeypatch, tmp_path)
    source = kwargs["binding"]["source"]
    if case == "native_renderer":
        source["renderer"] = "native"
    elif case == "extra_message":
        source["messages"] = [{"role": "system", "content": "extra"}]
    elif case == "manifest_extra_message":
        source["manifest_messages"] = [{"role": "system", "content": "extra"}]
    elif case == "bos_added":
        source["gguf_add_bos_token"] = True
    elif case == "duplicate_context":
        source["runner_argv"] += ["-c", "32768"]
    elif case == "numctx_mismatch":
        source["model_num_ctx"] = 4096
    elif case == "rendered_utf8_not_below_numctx":
        assert len(rendered.encode()) > 1000
        source["runner_argv"][-3:] = ["1000", "-np", "1"]
        source["model_num_ctx"] = source["daemon_default_num_ctx"] = 1000
    if case in ("duplicate_context", "rendered_utf8_not_below_numctx"):
        state["runner"]["argv_sha256"] = hashlib.sha256(
            _canonical(source["runner_argv"])).hexdigest()
    with pytest.raises(live.LiveOperatorError):
        live.worker_once(**kwargs)
    assert len(state["specs"]) <= 6
    assert len(state["calls"]) <= 6
    assert journal.snapshot()["completion_attempt_spent"] == 0


@pytest.mark.parametrize("runner_argv", [
    ["ollama_llama_server", "--no-jinja", "--chat-template", "chatml",
     "--jinja", "-c", "32768", "-np", "4"],
    ["ollama_llama_server", "--no-jinja", "-c", "32768", "-np", "4",
     "--chat-template", "chatml"],
])
def test_contradictory_or_nonadjacent_render_branch_flags_refuse_op7(
        monkeypatch, tmp_path, runner_argv):
    kwargs, state, journal, _ = _worker_harness(monkeypatch, tmp_path)
    kwargs["binding"]["source"]["runner_argv"] = runner_argv
    state["runner"]["argv_sha256"] = hashlib.sha256(
        _canonical(runner_argv)).hexdigest()
    with pytest.raises(live.LiveOperatorError,
                       match="^source_branch_or_bos_unproven$"):
        live.worker_once(**kwargs)
    assert len(state["specs"]) <= 6
    assert len(state["calls"]) <= 6
    assert journal.snapshot()["completion_attempt_spent"] == 0


@pytest.mark.parametrize("digits,code", [
    (100, "source_runner_argv_invalid"),
    (5000, "binding_invalid"),  # bounded parent/worker frame rejects earlier
])
def test_huge_runner_context_decimal_fails_fixed_before_completion(
        monkeypatch, tmp_path, digits, code):
    kwargs, state, journal, _ = _worker_harness(monkeypatch, tmp_path)
    argv = kwargs["binding"]["source"]["runner_argv"]
    argv[-3] = "9" * digits
    state["runner"]["argv_sha256"] = hashlib.sha256(_canonical(argv)).hexdigest()
    with pytest.raises(live.LiveOperatorError) as caught:
        live.worker_once(**kwargs)
    assert str(caught.value) == code
    assert caught.value.__cause__ is None
    assert caught.value.__context__ is None
    assert len(state["specs"]) <= 6
    assert journal.snapshot()["completion_attempt_spent"] == 0


@pytest.mark.parametrize("field,replacement", [
    ("renderer", "native"), ("parser", "native"),
    ("messages", [{"role": "system", "content": "unexpected"}]),
])
def test_same_run_show_conflict_refused_before_render_or_completion(
        monkeypatch, tmp_path, field, replacement):
    kwargs, state, journal, _ = _worker_harness(monkeypatch, tmp_path)
    state["body_change"] = lambda body, index: (
        body.update({field: replacement}) if index == 3 else None)
    with pytest.raises(live.LiveOperatorError):
        live.worker_once(**kwargs)
    assert len(state["specs"]) == len(state["calls"]) == 3
    assert journal.snapshot()["completion_attempt_spent"] == 0


def test_render_with_appended_message_fails_before_tokenizers_or_completion(
        monkeypatch, tmp_path):
    kwargs, state, journal, _ = _worker_harness(monkeypatch, tmp_path)

    def append_message(body, index):
        if index == 4:
            body["_debug_info"]["rendered_template"] += (
                "<|im_end|>\n<|im_start|>system\n" + CANARY)

    state["body_change"] = append_message
    with pytest.raises(live.LiveOperatorError):
        live.worker_once(**kwargs)
    assert len(state["specs"]) == len(state["calls"]) == 4
    assert journal.snapshot()["completion_attempt_spent"] == 0


@pytest.mark.parametrize("bad_choice", [
    [], [{"message": {}}], [{"message": {"content": None}}],
    [{"message": {"content": CANARY}}, {"message": {"content": "extra"}}],
])
def test_valid_usage_without_single_valid_completion_choice_is_spent_failure(
        monkeypatch, tmp_path, bad_choice):
    kwargs, state, journal, _ = _worker_harness(monkeypatch, tmp_path)
    state["body_change"] = lambda body, index: (
        body.update(choices=bad_choice) if index == 7 else None)
    with pytest.raises(live.LiveOperatorError):
        live.worker_once(**kwargs)
    assert len(state["specs"]) == len(state["calls"]) == 7
    assert journal.snapshot()["completion_attempt_spent"] == 1


def test_usage_nonnegative_integer_boundary_is_not_silently_rejected(
        monkeypatch, tmp_path):
    kwargs, state, journal, _ = _worker_harness(monkeypatch, tmp_path)
    state["usage"] = {"prompt_tokens": 0, "completion_tokens": 0,
                      "total_tokens": 0}
    summary = live.worker_once(**kwargs)
    assert summary["status"] == "fake_non_b_parity_mismatch"
    assert summary["signed_delta"] == -3
    assert summary["provider_usage"] == state["usage"]
    assert len(state["calls"]) == 7
    assert journal.snapshot()["completion_attempt_spent"] == 1


@pytest.mark.parametrize("usage", [
    None, {}, {"prompt_tokens": True, "completion_tokens": 2,
               "total_tokens": 3},
    {"prompt_tokens": -1, "completion_tokens": 2, "total_tokens": 1},
    {"prompt_tokens": 3, "completion_tokens": 2, "total_tokens": 6},
])
def test_invalid_usage_after_single_spent_completion_keeps_failure(
        monkeypatch, tmp_path, usage):
    kwargs, state, journal, _ = _worker_harness(monkeypatch, tmp_path)
    state["usage"] = usage
    with pytest.raises(live.LiveOperatorError):
        live.worker_once(**kwargs)
    assert len(state["calls"]) == 7
    assert journal.snapshot()["completion_attempt_spent"] == 1


@pytest.mark.parametrize("failed_effect", ["fsync", "replace"])
def test_failed_journal_durability_never_acks_or_retries(
        monkeypatch, tmp_path, failed_effect):
    journal = live.DurableJournal.create(tmp_path / "run", "synthetic-run")
    ack_calls = []

    def explode(*_args):
        raise RuntimeError(CANARY)

    monkeypatch.setattr(live.os, failed_effect, explode)
    with pytest.raises(live.LiveOperatorError) as caught:
        journal.reserve(_grant_fields(1), ack=ack_calls.append)
    assert str(caught.value) == "journal_commit_failed"
    assert caught.value.__cause__ is None
    assert caught.value.__context__ is None
    assert CANARY not in repr(caught.value)
    assert ack_calls == []
    with pytest.raises(live.LiveOperatorError, match="^journal_unavailable$"):
        journal.reserve(_grant_fields(1), ack=ack_calls.append)
    assert ack_calls == []


def test_post_replace_directory_fsync_failure_refuses_stale_memory_snapshot(
        monkeypatch, tmp_path):
    journal = live.DurableJournal.create(tmp_path / "run", "synthetic-run")
    ack_calls = []

    def fail_directory_fsync(_directory):
        raise RuntimeError(CANARY)

    monkeypatch.setattr(live.DurableJournal, "_sync_directory",
                        staticmethod(fail_directory_fsync))
    with pytest.raises(live.LiveOperatorError, match="^journal_commit_failed$"):
        journal.reserve(_grant_fields(1), ack=ack_calls.append)
    assert ack_calls == []
    _, disk = _read_only_journal(journal.run_dir)
    assert disk["reserved"] == disk["granted"] == 1
    assert disk["operations"][0]["on_wire"] == "unknown"
    with pytest.raises(live.LiveOperatorError, match="^journal_unavailable$"):
        journal.snapshot()
    with pytest.raises(live.LiveOperatorError, match="^journal_unavailable$"):
        journal.reserve(_grant_fields(2), ack=_ack)


def test_post_ack_durability_failure_retains_uncertain_grant_without_refund(
        monkeypatch, tmp_path):
    journal = live.DurableJournal.create(tmp_path / "run", "synthetic-run")
    original = live.os.fsync
    count = 0
    returned = []

    def fail_after_ack(fd):
        nonlocal count
        count += 1
        if count == 3:
            raise RuntimeError(CANARY)
        return original(fd)

    monkeypatch.setattr(live.os, "fsync", fail_after_ack)
    with pytest.raises(live.LiveOperatorError, match="^journal_commit_failed$"):
        journal.reserve(_grant_fields(1), ack=returned.append)
    assert len(returned) == 1
    assert returned[0]["ordinal"] == 1
    _, disk = _read_only_journal(journal.run_dir)
    assert disk["reserved"] == disk["granted"] == 1
    assert disk["ack_callback_returned"] == 0
    assert disk["operations"][0]["on_wire"] == "unknown"
    with pytest.raises(live.LiveOperatorError, match="^journal_unavailable$"):
        journal.snapshot()
    with pytest.raises(live.LiveOperatorError, match="^journal_unavailable$"):
        journal.reserve(_grant_fields(1), ack=_ack)


def test_thread_only_or_unknown_witness_cannot_be_reported_as_physical_stop(
        tmp_path):
    class ThreadOnlyEffects:
        calls = 0

        def __getattr__(self, _name):
            self.calls += 1
            raise AssertionError("not a witnessed process helper")

    effects = ThreadOnlyEffects()
    run_dir = tmp_path / "never-created"
    with pytest.raises(live.LiveOperatorError) as caught:
        live.supervise_once(run_dir=run_dir, model_root=tmp_path / "unused-model",
                            clock=lambda: 100.0, effects=effects)
    assert str(caught.value) == "process_supervisor_not_implemented"
    assert effects.calls == 0
    assert not run_dir.exists()


def _pipe_has_byte(fd):
    ready, _, _ = select.select([fd], [], [], 0)
    return bool(ready and os.read(fd, 1))


@_DARWIN_FORK
def test_fake_process_wrong_but_well_shaped_initial_witness_never_starts_work():
    marker_r, marker_w = os.pipe()
    try:
        def work():
            os.write(marker_w, b"W")

        def wrong_witness(pid):
            value = live._fake_os_witness(pid)
            value["pgid"] += 1
            return value

        result = live._supervise_fake_callback_once(
            work=work, initial_witness=wrong_witness,
            preparation_seconds=0.05, work_seconds=0.05,
            term_grace_seconds=0.02, cleanup_seconds=0.06)
        assert result == {
            "schema": "fake_process_watchdog_partial_v1",
            "status": "fake_partial_initial_witness_unavailable",
            "go_issued": False, "worker_reaped": True,
            "signal_reaped": True, "term": "not_attempted",
            "kill": "not_attempted", "full_gate_pass": False,
        }
        assert not _pipe_has_byte(marker_r)
    finally:
        os.close(marker_r)
        os.close(marker_w)


@_DARWIN_FORK
def test_fake_process_blocked_initial_witness_is_bounded_and_no_callback():
    marker_r, marker_w = os.pipe()
    try:
        def work():
            os.write(marker_w, b"W")

        started = time.monotonic()
        result = live._supervise_fake_callback_once(
            work=work, initial_witness=lambda _pid: time.sleep(2),
            preparation_seconds=0.05, work_seconds=0.05,
            term_grace_seconds=0.02, cleanup_seconds=0.06)
        elapsed = time.monotonic() - started
        assert elapsed < 1.5
        assert result["status"] == "fake_partial_initial_witness_unavailable"
        assert result["go_issued"] is False
        assert result["worker_reaped"] is True
        assert result["term"] == "not_attempted"
        assert result["full_gate_pass"] is False
        assert not _pipe_has_byte(marker_r)
    finally:
        os.close(marker_r)
        os.close(marker_w)


@_DARWIN_FORK
def test_fake_process_blocked_work_is_stopped_by_separate_signal_helper():
    marker_r, marker_w = os.pipe()
    try:
        def blocked_work():
            os.write(marker_w, b"W")
            time.sleep(2)

        started = time.monotonic()
        result = live._supervise_fake_callback_once(
            work=blocked_work, preparation_seconds=0.08,
            work_seconds=0.15, term_grace_seconds=0.03,
            cleanup_seconds=0.15)
        assert time.monotonic() - started < 1.5
        assert _pipe_has_byte(marker_r)  # callback really entered
        assert result["go_issued"] is True
        assert result["term"] == "signal_sent"
        assert result["worker_reaped"] is True
        assert result["signal_reaped"] is True
        assert result["status"] == "fake_partial_witnessed_child_reaped"
        assert result["full_gate_pass"] is False
        assert CANARY not in json.dumps(result)
    finally:
        os.close(marker_r)
        os.close(marker_w)


@_DARWIN_FORK
def test_fake_process_final_observer_drift_does_not_signal(monkeypatch):
    signal_r, signal_w = os.pipe()
    original_kill = os.kill

    def recorded_kill(pid, signum):
        os.write(signal_w, b"S")
        return original_kill(pid, signum)

    monkeypatch.setattr(live.os, "kill", recorded_kill)
    observations = 0

    def drift_on_final(pid):
        nonlocal observations
        observations += 1
        value = live._fake_os_witness(pid)
        if observations == 2:
            value["pgid"] += 1
        return value

    try:
        result = live._supervise_fake_callback_once(
            work=lambda: time.sleep(2), observe=drift_on_final,
            preparation_seconds=0.06, work_seconds=0.05,
            term_grace_seconds=0.02, cleanup_seconds=0.07)
        assert result["term"] == "identity_changed_no_signal"
        assert result["kill"] == "not_attempted"
        assert result["status"] == "fake_partial_physical_stop_unproven"
        assert result["full_gate_pass"] is False
        assert result["worker_reaped"] is True  # self-timeout, not stop proof
        assert result["signal_reaped"] is True
        assert not _pipe_has_byte(signal_r)
    finally:
        os.close(signal_r)
        os.close(signal_w)


@_DARWIN_FORK
def test_fake_process_blocked_cleanup_observer_is_bounded_and_no_signal(
        monkeypatch):
    signal_r, signal_w = os.pipe()
    original_kill = os.kill

    def recorded_kill(pid, signum):
        os.write(signal_w, b"S")
        return original_kill(pid, signum)

    monkeypatch.setattr(live.os, "kill", recorded_kill)
    try:
        started = time.monotonic()
        result = live._supervise_fake_callback_once(
            work=lambda: time.sleep(2), observe=lambda _pid: time.sleep(2),
            preparation_seconds=0.06, work_seconds=0.05,
            term_grace_seconds=0.02, cleanup_seconds=0.07)
        assert time.monotonic() - started < 1.5
        assert result["term"] == "cleanup_observer_timeout"
        assert result["kill"] == "not_attempted"
        assert result["status"] == "fake_partial_physical_stop_unproven"
        assert result["full_gate_pass"] is False
        assert result["worker_reaped"] is True  # child alarm, after gate failure
        assert result["signal_reaped"] is True
        assert not _pipe_has_byte(signal_r)
    finally:
        os.close(signal_r)
        os.close(signal_w)


@_DARWIN_FORK
def test_fake_process_term_ignored_requires_exact_kill_and_reap():
    def armed_initial_witness(pid):
        # Install the disposition before initial ACK/GO. Otherwise a busy
        # machine may send TERM before the work callback can install it.
        signal.signal(signal.SIGTERM, signal.SIG_IGN)
        return live._fake_os_witness(pid)

    result = live._supervise_fake_callback_once(
        work=lambda: time.sleep(2), initial_witness=armed_initial_witness,
        preparation_seconds=0.08,
        work_seconds=0.06, term_grace_seconds=0.03,
        cleanup_seconds=0.16)
    assert result["term"] == "signal_sent"
    assert result["kill"] == "signal_sent"
    assert result["worker_reaped"] is True
    assert result["signal_reaped"] is True
    assert result["status"] == "fake_partial_witnessed_child_reaped"
    assert result["full_gate_pass"] is False


def test_fake_process_missing_waitable_child_is_not_exit_proof(monkeypatch):
    def missing(_pid, _flags):
        raise ChildProcessError("not waitable")

    monkeypatch.setattr(live.os, "waitpid", missing)
    assert live._fake_reap_nonblocking(123456) is False


def test_fake_process_equal_python_values_are_not_equal_identity(monkeypatch):
    initial = {"pid": 123456, "ppid": 1,
               "raw_generation": [123456, 1, 1000, 0], "pgid": 123456}
    signaled = []
    monkeypatch.setattr(live, "_fake_os_witness", lambda _pid: deepcopy(initial))
    monkeypatch.setattr(live.os, "kill",
                        lambda pid, signum: signaled.append((pid, signum)))

    def equal_but_wrong(_pid):
        result = deepcopy(initial)
        result["ppid"] = True  # Python equality would accept True == 1.
        return result

    assert live._fake_exact_signal_transaction(
        initial, equal_but_wrong, signal.SIGTERM) == "identity_changed_no_signal"
    assert signaled == []


@_DARWIN_FORK
def test_fake_process_blocked_signal_helper_initial_witness_never_sends_go():
    marker_r, marker_w = os.pipe()
    try:
        def work():
            os.write(marker_w, b"W")

        result = live._supervise_fake_callback_once(
            work=work, signal_initial_witness=lambda _pid: time.sleep(2),
            preparation_seconds=0.05, work_seconds=0.05,
            term_grace_seconds=0.02, cleanup_seconds=0.06)
        assert result["status"] == "fake_partial_signal_helper_witness_unavailable"
        assert result["go_issued"] is False
        assert result["worker_reaped"] is True
        assert result["signal_reaped"] is True
        assert result["term"] == "not_attempted"
        assert not _pipe_has_byte(marker_r)
    finally:
        os.close(marker_r)
        os.close(marker_w)


@_DARWIN_FORK
def test_fake_process_broken_cleanup_command_is_fixed_fail(monkeypatch):
    original_write = os.write

    def break_term(fd, data):
        if data == b"T":
            raise BrokenPipeError("synthetic pipe close")
        return original_write(fd, data)

    monkeypatch.setattr(live.os, "write", break_term)
    result = live._supervise_fake_callback_once(
        work=lambda: time.sleep(2), preparation_seconds=0.06,
        work_seconds=0.05, term_grace_seconds=0.02,
        cleanup_seconds=0.07)
    assert result["go_issued"] is True
    assert result["term"] == "cleanup_command_unavailable"
    assert result["kill"] == "not_attempted"
    assert result["status"] == "fake_partial_physical_stop_unproven"
    assert result["worker_reaped"] is True  # later self-timeout only
    assert result["signal_reaped"] is True
    assert "synthetic pipe close" not in json.dumps(result)


@_DARWIN_FORK
def test_fake_process_broken_go_is_fixed_fail_without_callback(monkeypatch):
    original_write = os.write
    marker_r, marker_w = os.pipe()

    def break_go(fd, data):
        if data == b"G":
            raise BrokenPipeError("synthetic GO pipe close")
        return original_write(fd, data)

    monkeypatch.setattr(live.os, "write", break_go)
    try:
        def work():
            os.write(marker_w, b"W")

        result = live._supervise_fake_callback_once(
            work=work, preparation_seconds=0.06,
            work_seconds=0.05, term_grace_seconds=0.02,
            cleanup_seconds=0.07)
        assert result["status"] == "fake_partial_go_unavailable"
        assert result["go_issued"] is False
        assert result["worker_reaped"] is True
        assert result["signal_reaped"] is True
        assert result["term"] == "not_attempted"
        assert result["full_gate_pass"] is False
        assert not _pipe_has_byte(marker_r)
        assert "synthetic GO pipe close" not in json.dumps(result)
    finally:
        os.close(marker_r)
        os.close(marker_w)


@_DARWIN_FORK
def test_fake_process_noop_signal_cannot_masquerade_as_stopped(monkeypatch):
    # An injected os.kill that merely returns cannot prove that it stopped
    # the child. The exact waitpid status must be SIGTERM/SIGKILL, not the
    # worker's later self-timeout exit 124.
    monkeypatch.setattr(live.os, "kill", lambda _pid, _signum: None)
    marker_r, marker_w = os.pipe()
    try:
        def blocked_work():
            os.write(marker_w, b"W")
            time.sleep(2)

        result = live._supervise_fake_callback_once(
            work=blocked_work, preparation_seconds=0.06,
            work_seconds=0.15, term_grace_seconds=0.02,
            cleanup_seconds=0.07)
        assert _pipe_has_byte(marker_r)
        assert result["go_issued"] is True
        assert result["term"] == "signal_sent"  # call returned; no effect
        assert result["kill"] == "signal_sent"  # call returned; no effect
        assert result["worker_reaped"] is True
        assert result["signal_reaped"] is True
        assert result["status"] == "fake_partial_physical_stop_unproven"
        assert result["full_gate_pass"] is False
    finally:
        os.close(marker_r)
        os.close(marker_w)


def _op1_without_worker():
    fields = _grant_fields(1)
    fields.pop("worker")
    fields["expires_at"] = time.monotonic() + 10
    return fields


@_DARWIN_FORK
def test_fake_journal_op1_is_child_durable_before_parent_proof(tmp_path):
    run_dir = tmp_path / "isolated-run"
    result = live._supervise_fake_journal_op1_once(
        run_dir=run_dir, grant_without_worker=_op1_without_worker())
    assert result["status"] == "fake_partial_op1_durable_proof"
    assert result["worker_reaped"] is True
    assert result["signal_reaped"] is True
    assert result["zero_ack_received"] is True
    assert result["reserve_command_issued"] is True
    assert result["full_gate_pass"] is False
    assert stat.S_IMODE(run_dir.stat().st_mode) == 0o700
    journal_path, disk = _read_only_journal(run_dir)
    assert hashlib.sha256(journal_path.read_bytes()).hexdigest() == result["journal_sha256"]
    assert disk["reserved"] == disk["granted"] == 1
    assert disk["ack_callback_returned"] == 1  # local callback, not worker delivery
    assert disk["worker_issued"] == disk["completion_attempt_spent"] == 0
    assert disk["operations"][0]["on_wire"] == "unknown"
    assert disk["operations"][0]["worker"]["pid"] > 0
    assert result["on_wire"] == "unknown"
    assert CANARY not in json.dumps(result)


@_DARWIN_FORK
@pytest.mark.parametrize("blocked_effect", ["create_fsync", "create_dir_fsync",
                                             "reserve_fsync", "replace",
                                             "directory_fsync", "post_ack_fsync",
                                             "post_ack_dir_fsync"])
def test_fake_journal_blocked_durability_keeps_parent_bounded_and_no_proof(
        monkeypatch, tmp_path, blocked_effect):
    original_fsync = os.fsync
    original_replace = os.replace
    fsync_calls = 0

    def maybe_block_fsync(fd):
        nonlocal fsync_calls
        fsync_calls += 1
        if ((blocked_effect == "create_fsync" and fsync_calls == 1)
                or (blocked_effect == "create_dir_fsync" and fsync_calls == 2)
                or (blocked_effect == "reserve_fsync" and fsync_calls == 3)
                or (blocked_effect == "directory_fsync" and fsync_calls == 4)
                or (blocked_effect == "post_ack_fsync" and fsync_calls == 5)
                or (blocked_effect == "post_ack_dir_fsync" and fsync_calls == 6)):
            time.sleep(20)
        return original_fsync(fd)

    def maybe_block_replace(*args):
        if blocked_effect == "replace":
            time.sleep(20)
        return original_replace(*args)

    monkeypatch.setattr(live.os, "fsync", maybe_block_fsync)
    monkeypatch.setattr(live.os, "replace", maybe_block_replace)
    started = time.monotonic()
    result = live._supervise_fake_journal_op1_once(
        run_dir=tmp_path / "blocked-run", grant_without_worker=_op1_without_worker(),
        work_seconds=0.15)
    elapsed = time.monotonic() - started
    assert elapsed < 2
    assert result["status"] == "fake_partial_journal_unproven"
    assert result["full_gate_pass"] is False
    assert result["worker_reaped"] is True
    assert result["signal_reaped"] is True
    assert "journal_sha256" not in result
    assert CANARY not in json.dumps(result)


@_DARWIN_FORK
def test_fake_journal_post_replace_failure_and_lost_proof_do_not_refund(
        monkeypatch, tmp_path):
    original_sync_directory = live.DurableJournal._sync_directory
    calls = 0

    def fail_second_directory_sync(directory):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise RuntimeError(CANARY)
        return original_sync_directory(directory)

    monkeypatch.setattr(live.DurableJournal, "_sync_directory",
                        staticmethod(fail_second_directory_sync))
    failed_run = tmp_path / "failed-run"
    result = live._supervise_fake_journal_op1_once(
        run_dir=failed_run, grant_without_worker=_op1_without_worker())
    assert result["status"] == "fake_partial_journal_unproven"
    assert "journal_sha256" not in result
    _, disk = _read_only_journal(failed_run)
    assert disk["reserved"] == disk["granted"] == 1
    assert disk["operations"][0]["on_wire"] == "unknown"
    assert CANARY not in json.dumps(result)

    monkeypatch.setattr(live.DurableJournal, "_sync_directory",
                        staticmethod(original_sync_directory))
    lost_run = tmp_path / "lost-proof-run"
    lost = live._supervise_fake_journal_op1_once(
        run_dir=lost_run, grant_without_worker=_op1_without_worker(),
        crash_after_commit=True)
    assert lost["status"] == "fake_partial_journal_unproven"
    assert "journal_sha256" not in lost
    _, lost_disk = _read_only_journal(lost_run)
    assert lost_disk["reserved"] == lost_disk["granted"] == 1
    assert lost_disk["ack_callback_returned"] == 1
    before_retry = (lost_run / "journal.json").read_bytes()
    refused = live._supervise_fake_journal_op1_once(
        run_dir=lost_run, grant_without_worker=_op1_without_worker())
    assert refused["status"] == "fake_partial_journal_unproven"
    assert (lost_run / "journal.json").read_bytes() == before_retry


@_DARWIN_FORK
def test_fake_journal_existing_run_is_terminal_without_reuse(tmp_path):
    run_dir = tmp_path / "existing-run"
    live.DurableJournal.create(run_dir, "synthetic-run")
    original = (run_dir / "journal.json").read_bytes()
    result = live._supervise_fake_journal_op1_once(
        run_dir=run_dir, grant_without_worker=_op1_without_worker())
    assert result["status"] == "fake_partial_journal_unproven"
    assert "journal_sha256" not in result
    assert (run_dir / "journal.json").read_bytes() == original


@_DARWIN_FORK
def test_fake_journal_worker_grant_must_match_initial_os_witness(
        monkeypatch, tmp_path):
    original_reserve = live.DurableJournal.reserve

    def mint_wrong_worker(self, fields, *, ack):
        altered = deepcopy(fields)
        altered["worker"]["pid"] += 1
        return original_reserve(self, altered, ack=ack)

    monkeypatch.setattr(live.DurableJournal, "reserve", mint_wrong_worker)
    result = live._supervise_fake_journal_op1_once(
        run_dir=tmp_path / "wrong-worker", grant_without_worker=_op1_without_worker())
    assert result["watchdog_status"] == "fake_partial_work_exited"
    assert result["status"] == "fake_partial_journal_unproven"
    assert "journal_sha256" not in result


@_DARWIN_FORK
def test_fake_journal_grant_expiry_must_be_canonical_byte_equal(
        monkeypatch, tmp_path):
    original_reserve = live.DurableJournal.reserve

    def mint_type_drift(self, fields, *, ack):
        altered = deepcopy(fields)
        altered["expires_at"] = 100
        return original_reserve(self, altered, ack=ack)

    monkeypatch.setattr(live.DurableJournal, "reserve", mint_type_drift)
    fields = _op1_without_worker()
    fields["expires_at"] = 100.0  # Python equality would hide this type drift.
    result = live._supervise_fake_journal_op1_once(
        run_dir=tmp_path / "expiry-type-drift", grant_without_worker=fields)
    assert result["watchdog_status"] == "fake_partial_work_exited"
    assert result["status"] == "fake_partial_journal_unproven"
    assert "journal_sha256" not in result


@_DARWIN_FORK
def test_fake_journal_proof_ipc_rejects_nested_raw_before_writing_frame():
    result = live._supervise_fake_callback_once(
        work=lambda: {"grant": {"raw": CANARY},
                      "journal_sha256": hashlib.sha256(b"x").hexdigest()},
        journal_proof=True, work_seconds=0.1)
    assert result["status"] != "fake_partial_work_exited"
    assert result["worker_reaped"] is True
    assert result["signal_reaped"] is True
    assert "work_result" not in result
    assert CANARY not in json.dumps(result)


def test_fake_journal_cannot_claim_proof_with_unreaped_signal_helper(
        monkeypatch, tmp_path):
    def missing_reap(**_kwargs):
        return {"status": "fake_partial_work_exited", "worker_reaped": True,
                "signal_reaped": False, "go_issued": True,
                "term": "not_attempted", "kill": "not_attempted"}

    monkeypatch.setattr(live, "_supervise_fake_callback_once", missing_reap)
    result = live._supervise_fake_journal_op1_once(
        run_dir=tmp_path / "unused", grant_without_worker=_op1_without_worker())
    assert result["status"] == "fake_partial_journal_unproven"
    assert result["signal_reaped"] is False
    assert "journal_sha256" not in result


@_DARWIN_FORK
@pytest.mark.parametrize("broken_zero", ["wrong_run", "wrong_seq", "duplicate",
                                           "split_duplicate", "lost"])
def test_fake_journal_zero_ack_must_validate_before_op1_command(
        monkeypatch, tmp_path, broken_zero):
    original_encode = live.encode_frame
    original_write = os.write
    original_read = os.read

    def break_zero_frame(value):
        if type(value) is dict and value.get("phase") == "zero":
            changed = deepcopy(value)
            if broken_zero == "wrong_run":
                changed["run_id"] = "another-run"
            elif broken_zero == "wrong_seq":
                changed["seq"] = 2
            elif broken_zero in ("duplicate", "split_duplicate"):
                frame = original_encode(value)
                return frame + frame
            return original_encode(changed)
        return original_encode(value)

    def lose_zero_frame(fd, data):
        if broken_zero == "lost" and b'"phase":"zero"' in data:
            return len(data)
        return original_write(fd, data)

    monkeypatch.setattr(live, "encode_frame", break_zero_frame)
    monkeypatch.setattr(live.os, "write", lose_zero_frame)
    if broken_zero == "split_duplicate":
        monkeypatch.setattr(live.os, "read",
                            lambda fd, length: original_read(fd, min(length, 32)))
    run_dir = tmp_path / f"bad-zero-{broken_zero}"
    result = live._supervise_fake_journal_op1_once(
        run_dir=run_dir, grant_without_worker=_op1_without_worker(),
        work_seconds=0.15)
    assert result["status"] == "fake_partial_journal_unproven"
    assert result["zero_ack_received"] is False
    assert result["reserve_command_issued"] is False
    assert "journal_sha256" not in result
    _, disk = _read_only_journal(run_dir)
    assert disk["reserved"] == disk["granted"] == 0
    assert disk["operations"] == []


@_DARWIN_FORK
def test_fake_journal_broken_op1_command_keeps_zero_state(
        monkeypatch, tmp_path):
    original_write = os.write

    def break_reserve_command(fd, data):
        if data == b"R":
            raise BrokenPipeError(CANARY)
        return original_write(fd, data)

    monkeypatch.setattr(live.os, "write", break_reserve_command)
    run_dir = tmp_path / "broken-reserve-command"
    result = live._supervise_fake_journal_op1_once(
        run_dir=run_dir, grant_without_worker=_op1_without_worker(),
        work_seconds=0.15)
    assert result["zero_ack_received"] is True
    assert result["reserve_command_issued"] is False
    assert result["status"] == "fake_partial_journal_unproven"
    _, disk = _read_only_journal(run_dir)
    assert disk["reserved"] == disk["granted"] == 0
    assert CANARY not in json.dumps(result)


@_DARWIN_FORK
@pytest.mark.parametrize("bad_final", ["wrong_seq", "split_duplicate"])
def test_fake_journal_bad_final_frame_keeps_spent_disk_but_no_proof(
        monkeypatch, tmp_path, bad_final):
    original_encode = live.encode_frame
    original_read = os.read

    def stale_final_frame(value):
        if type(value) is dict and value.get("seq") == 2 and "grant" in value:
            if bad_final == "split_duplicate":
                frame = original_encode(value)
                return frame + frame
            changed = deepcopy(value)
            changed["seq"] = 1
            return original_encode(changed)
        return original_encode(value)

    monkeypatch.setattr(live, "encode_frame", stale_final_frame)
    if bad_final == "split_duplicate":
        monkeypatch.setattr(live.os, "read",
                            lambda fd, length: original_read(fd, min(length, 32)))
    run_dir = tmp_path / f"bad-final-{bad_final}"
    result = live._supervise_fake_journal_op1_once(
        run_dir=run_dir, grant_without_worker=_op1_without_worker())
    assert result["zero_ack_received"] is True
    assert result["reserve_command_issued"] is True
    assert result["status"] == "fake_partial_journal_unproven"
    assert "journal_sha256" not in result
    _, disk = _read_only_journal(run_dir)
    assert disk["reserved"] == disk["granted"] == 1


@_DARWIN_FORK
def test_fake_split_op1_requires_both_witnesses_zero_and_worker_received(tmp_path):
    run_dir = tmp_path / "split-success"
    result = live._supervise_fake_split_op1_once(
        run_dir=run_dir, grant_without_worker=_op1_without_worker())
    assert result["status"] == "fake_partial_op1_worker_received"
    assert result["d_reaped"] is result["w_reaped"] is True
    assert result["zero_ack_received"] is True
    assert result["request_accepted"] is True
    assert result["grant_proven"] is True
    assert result["worker_received_proven"] is True
    assert result["durable_reserved"] == 1
    assert result["d_stop"] == result["w_stop"] == "normal_exit"
    assert result["s_d_reaped"] is result["s_w_reaped"] is True
    assert result["on_wire"] == "unknown"
    assert result["full_gate_pass"] is False
    journal, disk = _read_only_journal(run_dir)
    assert stat.S_IMODE(run_dir.stat().st_mode) == 0o700
    assert hashlib.sha256(journal.read_bytes()).hexdigest() == result["journal_sha256"]
    assert disk["reserved"] == disk["granted"] == 1
    assert disk["worker_issued"] == 0  # W only ACKs reception; no HTTP.
    assert disk["operations"][0]["on_wire"] == "unknown"
    assert CANARY not in json.dumps(result)


@_DARWIN_FORK
@pytest.mark.parametrize("fault", ["wrong_run", "wrong_seq", "duplicate",
                                           "split_duplicate", "lost"])
def test_fake_split_bad_or_lost_zero_ack_never_requests_op1(
        monkeypatch, tmp_path, fault):
    original_encode = live.encode_frame
    original_write = os.write
    original_read = os.read

    def bad_zero(value):
        if type(value) is dict and value.get("phase") == "zero":
            altered = deepcopy(value)
            if fault == "wrong_run":
                altered["run_id"] = "wrong-run"
            elif fault == "wrong_seq":
                altered["seq"] = 7
            elif fault in ("duplicate", "split_duplicate"):
                frame = original_encode(value)
                return frame + frame
            return original_encode(altered)
        return original_encode(value)

    def lose_zero(fd, data):
        if fault == "lost" and b'"phase":"zero"' in data:
            return len(data)
        return original_write(fd, data)

    monkeypatch.setattr(live, "encode_frame", bad_zero)
    monkeypatch.setattr(live.os, "write", lose_zero)
    if fault == "split_duplicate":
        monkeypatch.setattr(live.os, "read",
                            lambda fd, size: original_read(fd, min(size, 17)))
    run_dir = tmp_path / f"split-zero-{fault}"
    result = live._supervise_fake_split_op1_once(
        run_dir=run_dir, grant_without_worker=_op1_without_worker(),
        work_seconds=0.15)
    assert result["status"] == "fake_partial_split_unproven"
    assert result["zero_ack_received"] is False
    assert result["request_accepted"] is False
    assert result["grant_proven"] is False
    assert result["worker_received_proven"] is False
    assert result["on_wire"] == "unknown"
    _, disk = _read_only_journal(run_dir)
    assert disk["reserved"] == disk["granted"] == 0


@_DARWIN_FORK
def test_fake_split_worker_request_wrong_initial_witness_never_reserves(
        monkeypatch, tmp_path):
    original = live._split_worker_request

    def wrong_witness(spec, witness):
        request = original(spec, witness)
        request["worker"]["pid"] += 1
        return request

    monkeypatch.setattr(live, "_split_worker_request", wrong_witness)
    run_dir = tmp_path / "split-wrong-worker"
    result = live._supervise_fake_split_op1_once(
        run_dir=run_dir, grant_without_worker=_op1_without_worker())
    assert result["status"] == "fake_partial_split_unproven"
    assert result["zero_ack_received"] is True
    assert result["request_accepted"] is False
    _, disk = _read_only_journal(run_dir)
    assert disk["reserved"] == disk["granted"] == 0


@_DARWIN_FORK
@pytest.mark.parametrize("lost_phase", ["grant_proof", "received"])
def test_fake_split_ack_loss_after_durability_never_refunds(
        monkeypatch, tmp_path, lost_phase):
    original_write = os.write

    def lose_ack(fd, data):
        if f'"phase":"{lost_phase}"'.encode() in data:
            return len(data)
        return original_write(fd, data)

    monkeypatch.setattr(live.os, "write", lose_ack)
    run_dir = tmp_path / f"split-lost-{lost_phase}"
    result = live._supervise_fake_split_op1_once(
        run_dir=run_dir, grant_without_worker=_op1_without_worker(),
        work_seconds=0.15)
    assert result["status"] == "fake_partial_split_unproven"
    assert result["zero_ack_received"] is True
    assert result["request_accepted"] is True
    assert result["worker_received_proven"] is False
    assert result["grant_proven"] is (lost_phase == "received")
    assert result["on_wire"] == "unknown"
    _, disk = _read_only_journal(run_dir)
    assert disk["reserved"] == disk["granted"] == 1
    assert disk["operations"][0]["on_wire"] == "unknown"
    assert CANARY not in json.dumps(result)


@_DARWIN_FORK
def test_fake_split_partial_parent_reserve_write_is_unknown_not_zero(
        monkeypatch, tmp_path):
    original_write = os.write
    partial = False

    def tear_reserve_frame(fd, data):
        nonlocal partial
        if b'"phase":"reserve"' in data and not partial:
            partial = True
            return original_write(fd, data[:7])
        if partial:
            raise BrokenPipeError(CANARY)
        return original_write(fd, data)

    monkeypatch.setattr(live.os, "write", tear_reserve_frame)
    run_dir = tmp_path / "split-partial-reserve"
    result = live._supervise_fake_split_op1_once(
        run_dir=run_dir, grant_without_worker=_op1_without_worker())
    assert result["status"] == "fake_partial_split_unproven"
    assert result["zero_ack_received"] is True
    assert result["request_accepted"] is True
    assert result["durable_reserved"] == "unknown"
    assert result["grant_proven"] is False
    assert result["worker_received_proven"] is False
    assert CANARY not in json.dumps(result)
    _, disk = _read_only_journal(run_dir)
    assert disk["reserved"] == 0


@_DARWIN_FORK
@pytest.mark.parametrize("blocked_stage", ["create", "reserve"])
def test_fake_split_blocked_fsync_keeps_parent_bounded_and_unproven(
        monkeypatch, tmp_path, blocked_stage):
    original_fsync = os.fsync
    calls = 0

    def blocked_fsync(fd):
        nonlocal calls
        calls += 1
        if calls == (1 if blocked_stage == "create" else 3):
            time.sleep(20)
        return original_fsync(fd)

    monkeypatch.setattr(live.os, "fsync", blocked_fsync)
    start = time.monotonic()
    result = live._supervise_fake_split_op1_once(
        run_dir=tmp_path / f"split-blocked-fsync-{blocked_stage}",
        grant_without_worker=_op1_without_worker(), work_seconds=0.12)
    assert time.monotonic() - start < 2
    assert result["status"] == "fake_partial_split_unproven"
    assert result["grant_proven"] is False
    assert result["physical_stop_unproven"] is True
    assert result["on_wire"] == "unknown"


@_DARWIN_FORK
@pytest.mark.parametrize("phase", ["op1_request", "grant_proof", "received"])
def test_fake_split_encoded_raw_canary_is_rejected_before_ipc_write(
        monkeypatch, tmp_path, phase):
    original_encode = live.encode_frame
    original_write = os.write
    marker_r, marker_w = os.pipe()

    def pollute_encoded_frame(value):
        if type(value) is dict and value.get("phase") == phase:
            altered = deepcopy(value)
            altered["raw"] = {"secret": CANARY}
            return original_encode(altered)
        return original_encode(value)

    def record_raw_write(fd, data):
        if CANARY.encode() in data:
            original_write(marker_w, b"X")
        return original_write(fd, data)

    monkeypatch.setattr(live, "encode_frame", pollute_encoded_frame)
    monkeypatch.setattr(live.os, "write", record_raw_write)
    try:
        run_dir = tmp_path / f"split-raw-frame-{phase}"
        result = live._supervise_fake_split_op1_once(
            run_dir=run_dir, grant_without_worker=_op1_without_worker())
        assert result["status"] == "fake_partial_split_unproven"
        assert result["worker_received_proven"] is False
        assert result["on_wire"] == "unknown"
        assert not _pipe_has_byte(marker_r)
        assert CANARY not in json.dumps(result)
        _, disk = _read_only_journal(run_dir)
        assert disk["reserved"] == (0 if phase == "op1_request" else 1)
    finally:
        os.close(marker_r)
        os.close(marker_w)


@_DARWIN_FORK
@pytest.mark.parametrize("fault", ["d_after_zero", "d_after_commit",
                                           "w_after_request"])
def test_fake_split_child_crash_is_terminal_without_refund(tmp_path, fault):
    run_dir = tmp_path / f"split-crash-{fault}"
    result = live._supervise_fake_split_op1_once(
        run_dir=run_dir, grant_without_worker=_op1_without_worker(),
        fault=fault, work_seconds=0.15)
    assert result["status"] == "fake_partial_split_unproven"
    assert result["worker_received_proven"] is False
    assert result["on_wire"] == "unknown"
    _, disk = _read_only_journal(run_dir)
    # W can die just after sending its valid request while D has already
    # committed. The parent must not assume that race refunds the ordinal.
    expected = (0, 1) if fault == "w_after_request" else (
        (1,) if fault == "d_after_commit" else (0,))
    assert disk["reserved"] == disk["granted"]
    assert disk["reserved"] in expected


@_DARWIN_FORK
def test_fake_split_existing_run_is_terminal_and_unchanged(tmp_path):
    run_dir = tmp_path / "split-existing"
    live.DurableJournal.create(run_dir, "synthetic-run")
    old = (run_dir / "journal.json").read_bytes()
    result = live._supervise_fake_split_op1_once(
        run_dir=run_dir, grant_without_worker=_op1_without_worker())
    assert result["status"] == "fake_partial_split_unproven"
    assert result["zero_ack_received"] is False
    assert result["worker_received_proven"] is False
    assert (run_dir / "journal.json").read_bytes() == old


@_DARWIN_FORK
def test_fake_split_raw_canary_in_worker_request_is_rejected_before_ipc(
        monkeypatch, tmp_path):
    original = live._split_worker_request

    def raw_request(spec, witness):
        request = original(spec, witness)
        request["raw"] = {"secret": CANARY}
        return request

    monkeypatch.setattr(live, "_split_worker_request", raw_request)
    run_dir = tmp_path / "split-raw"
    result = live._supervise_fake_split_op1_once(
        run_dir=run_dir, grant_without_worker=_op1_without_worker())
    assert result["status"] == "fake_partial_split_unproven"
    assert result["request_accepted"] is False
    assert CANARY not in json.dumps(result)
    _, disk = _read_only_journal(run_dir)
    assert disk["reserved"] == 0


@_DARWIN_FORK
@pytest.mark.parametrize("blocked", ["D", "W"])
def test_fake_split_blocked_child_requires_witnessed_exact_signal_stop(
        monkeypatch, tmp_path, blocked):
    if blocked == "D":
        original = live.DurableJournal.create.__func__

        def stall_create(cls, *args, **kwargs):
            time.sleep(20)
            return original(cls, *args, **kwargs)

        monkeypatch.setattr(live.DurableJournal, "create", classmethod(stall_create))
    else:
        original = live._split_worker_request

        def stall_request(*args):
            time.sleep(20)
            return original(*args)

        monkeypatch.setattr(live, "_split_worker_request", stall_request)
    start = time.monotonic()
    result = live._supervise_fake_split_op1_once(
        run_dir=tmp_path / f"split-signal-{blocked}",
        grant_without_worker=_op1_without_worker(), work_seconds=0.12)
    assert time.monotonic() - start < 2
    assert result[f"{blocked.lower()}_term"] == "signal_sent"
    assert result[f"{blocked.lower()}_stop"] == "witnessed_term"
    assert result[f"{blocked.lower()}_reaped"] is True
    assert result["physical_stop_unproven"] is True  # no real port/receipt gate
    assert result["full_gate_pass"] is False


@_DARWIN_FORK
def test_fake_split_signal_helper_initial_ack_is_prework_barrier(tmp_path):
    def bad_initial(pid):
        witness = live._fake_os_witness(pid)
        witness["pgid"] += 1
        return witness

    run_dir = tmp_path / "split-bad-signal-initial"
    result = live._supervise_fake_split_op1_once(
        run_dir=run_dir, grant_without_worker=_op1_without_worker(),
        signal_initial_witness=bad_initial)
    assert result["status"] == "fake_partial_split_unproven"
    assert result["failure_code"] == "signal_helper_initial_unavailable"
    assert result["zero_ack_received"] is False
    assert not (run_dir / "journal.json").exists()
    assert result["physical_stop_unproven"] is True


@_DARWIN_FORK
@pytest.mark.parametrize("failure", ["blocked_observer", "drift", "noop_signal"])
def test_fake_split_cleanup_uncertainty_never_becomes_witnessed_stop(
        monkeypatch, tmp_path, failure):
    original_create = live.DurableJournal.create.__func__

    def stall_create(cls, *args, **kwargs):
        time.sleep(20)
        return original_create(cls, *args, **kwargs)

    monkeypatch.setattr(live.DurableJournal, "create", classmethod(stall_create))
    if failure == "blocked_observer":
        def observe(_pid):
            time.sleep(20)
            return None
    elif failure == "drift":
        calls = {}

        def observe(pid):
            witness = live._fake_os_witness(pid)
            calls[pid] = calls.get(pid, 0) + 1
            if calls[pid] % 2 == 0:
                witness["pgid"] += 1
            return witness
    else:
        observe = live._fake_os_witness
        monkeypatch.setattr(live.os, "kill", lambda _pid, _sig: None)
    result = live._supervise_fake_split_op1_once(
        run_dir=tmp_path / f"split-{failure}",
        grant_without_worker=_op1_without_worker(),
        cleanup_observe=observe, work_seconds=0.12)
    assert result["status"] == "fake_partial_split_unproven"
    assert result["d_stop"] != "witnessed_term"
    assert result["d_stop"] != "witnessed_kill"
    assert result["physical_stop_unproven"] is True
    assert result["full_gate_pass"] is False


@_DARWIN_FORK
def test_fake_split_kill_requires_fresh_witness_and_actual_waitpid(
        monkeypatch, tmp_path):
    original_create = live.DurableJournal.create.__func__
    original_kill = os.kill

    def stall_create(cls, *args, **kwargs):
        time.sleep(20)
        return original_create(cls, *args, **kwargs)

    def ignore_term(pid, signum):
        if signum != signal.SIGTERM:
            return original_kill(pid, signum)

    monkeypatch.setattr(live.DurableJournal, "create", classmethod(stall_create))
    monkeypatch.setattr(live.os, "kill", ignore_term)
    result = live._supervise_fake_split_op1_once(
        run_dir=tmp_path / "split-kill", grant_without_worker=_op1_without_worker(),
        work_seconds=0.12)
    assert result["d_term"] == result["d_kill"] == "signal_sent"
    assert result["d_stop"] == "witnessed_kill"
    assert result["d_reaped"] is True
    assert result["full_gate_pass"] is False


@_DARWIN_FORK
@pytest.mark.parametrize("lost", ["command", "response"])
def test_fake_split_cleanup_ipc_loss_cannot_prove_signal_stop(
        monkeypatch, tmp_path, lost):
    original_create = live.DurableJournal.create.__func__
    original_write = os.write

    def stall_create(cls, *args, **kwargs):
        time.sleep(20)
        return original_create(cls, *args, **kwargs)

    def lose_signal_frame(fd, data):
        phase = b'"phase":"signal_term"' if lost == "command" else b'"phase":"signal_result"'
        if phase in data:
            return len(data)
        return original_write(fd, data)

    monkeypatch.setattr(live.DurableJournal, "create", classmethod(stall_create))
    monkeypatch.setattr(live.os, "write", lose_signal_frame)
    result = live._supervise_fake_split_op1_once(
        run_dir=tmp_path / f"split-cleanup-lost-{lost}",
        grant_without_worker=_op1_without_worker(), work_seconds=0.12)
    assert result["status"] == "fake_partial_split_unproven"
    assert result["d_term"] == "cleanup_response_unavailable"
    assert result["d_stop"] == "unproven"
    assert result["physical_stop_unproven"] is True
    assert result["full_gate_pass"] is False


@_DARWIN_FORK
def test_fake_split_blocked_signal_helper_initial_never_starts_d(tmp_path):
    run_dir = tmp_path / "split-blocked-signal-initial"
    result = live._supervise_fake_split_op1_once(
        run_dir=run_dir, grant_without_worker=_op1_without_worker(),
        signal_initial_witness=lambda _pid: time.sleep(20),
        preparation_seconds=0.12, work_seconds=0.12)
    assert result["failure_code"] == "signal_helper_initial_unavailable"
    assert result["zero_ack_received"] is False
    assert not (run_dir / "journal.json").exists()
    assert result["physical_stop_unproven"] is True


@_DARWIN_FORK
def test_fake_split_early_failure_starts_w_cleanup_before_work_deadline(
        monkeypatch, tmp_path):
    original_w = live._split_w_child

    def linger_after_closed_delivery(*args, **kwargs):
        code = original_w(*args, **kwargs)
        time.sleep(20)
        return code

    monkeypatch.setattr(live, "_split_w_child", linger_after_closed_delivery)
    started = time.monotonic()
    result = live._supervise_fake_split_op1_once(
        run_dir=tmp_path / "split-early-failure",
        grant_without_worker=_op1_without_worker(),
        fault="d_after_commit", work_seconds=0.8)
    elapsed = time.monotonic() - started
    assert elapsed < 0.65  # old cleanup deferred TERM until ~0.8 s
    assert result["durable_reserved"] == "unknown"
    assert result["worker_received_proven"] is False
    assert result["w_term"] == "signal_sent"
    assert result["w_stop"] == "witnessed_term"
    assert result["full_gate_pass"] is False


@_DARWIN_FORK
def test_fake_split_blocked_d_cleanup_observer_does_not_hide_w_stop(
        monkeypatch, tmp_path):
    original_create = live.DurableJournal.create.__func__
    original_w = live._split_w_child
    original_signal_child = live._split_signal_child

    def stall_create(cls, *args, **kwargs):
        time.sleep(20)
        return original_create(cls, *args, **kwargs)

    def linger_after_w_go(*args, **kwargs):
        code = original_w(*args, **kwargs)
        time.sleep(20)
        return code

    def d_observer_stalls(*args, **kwargs):
        if kwargs["target_role"] == "D":
            kwargs["observer"] = lambda _pid: time.sleep(20)
        return original_signal_child(*args, **kwargs)

    monkeypatch.setattr(live.DurableJournal, "create", classmethod(stall_create))
    monkeypatch.setattr(live, "_split_w_child", linger_after_w_go)
    monkeypatch.setattr(live, "_split_signal_child", d_observer_stalls)
    result = live._supervise_fake_split_op1_once(
        run_dir=tmp_path / "split-independent-stop",
        grant_without_worker=_op1_without_worker(), work_seconds=0.12)
    assert result["d_stop"] == "unproven"
    assert result["w_term"] == "signal_sent"
    assert result["w_stop"] == "witnessed_term"
    assert result["w_reaped"] is True
    assert result["physical_stop_unproven"] is True
    assert result["full_gate_pass"] is False


@_DARWIN_FORK
def test_fake_split_parent_cleanup_error_is_fixed_code_and_reaps(
        monkeypatch, tmp_path):
    def broken_cleanup(**_kwargs):
        raise OSError("RAW_CANARY_cleanup_exception")

    monkeypatch.setattr(live, "_split_cleanup_children", broken_cleanup)
    result = live._supervise_fake_split_op1_once(
        run_dir=tmp_path / "split-parent-cleanup-error",
        grant_without_worker=_op1_without_worker())
    assert result["status"] == "fake_partial_split_unproven"
    assert result["failure_code"] == "cleanup_unavailable"
    assert result["d_stop"] == result["w_stop"] == "unproven"
    assert result["s_d_reaped"] is result["s_w_reaped"] is True
    assert "RAW_CANARY" not in json.dumps(result)
    assert result["physical_stop_unproven"] is True
    assert result["full_gate_pass"] is False


@_DARWIN_FORK
def test_fake_split_receipt_is_prestarted_durable_raw_free_and_still_partial(tmp_path):
    run_dir = tmp_path / "split-receipt-positive"
    result = live._supervise_fake_split_op1_once(
        run_dir=run_dir, grant_without_worker=_op1_without_worker())
    receipt = run_dir / "receipt.json"
    raw = receipt.read_bytes()
    disk = json.loads(raw)
    assert stat.S_IMODE(receipt.stat().st_mode) == 0o600
    assert stat.S_IMODE(run_dir.stat().st_mode) == 0o700
    assert raw == _canonical(disk)
    assert CANARY.encode() not in raw
    assert disk["schema"] == "fake_split_receipt_v1"
    assert disk["snapshot_phase"] == "after_dw_cleanup_before_r_final_reap"
    assert disk["status"] == "fake_partial_op1_worker_received"
    assert disk["physical_stop_unproven"] is True
    assert disk["full_gate_pass"] is False
    assert disk["b_send_authorized"] is False
    assert result["receipt_durable_proven"] is True
    assert result["receipt_sha256"] == hashlib.sha256(raw).hexdigest()
    assert result["r_reaped"] is result["s_r_reaped"] is True
    assert result["full_gate_pass"] is False


@_DARWIN_FORK
def test_fake_split_existing_receipt_is_never_overwritten(monkeypatch, tmp_path):
    original = live._split_disk_readback

    def plant_existing(journal, state):
        path = journal.run_dir / "receipt.json"
        if not path.exists():
            path.write_bytes(b"existing-user-data")
        return original(journal, state)

    monkeypatch.setattr(live, "_split_disk_readback", plant_existing)
    run_dir = tmp_path / "split-existing-receipt"
    result = live._supervise_fake_split_op1_once(
        run_dir=run_dir, grant_without_worker=_op1_without_worker())
    assert (run_dir / "receipt.json").read_bytes() == b"existing-user-data"
    assert result["zero_ack_received"] is True
    assert result["receipt_preflight_accepted"] is False
    assert result["request_accepted"] is False
    assert result["grant_proven"] is False
    _, disk = _read_only_journal(run_dir)
    assert disk["reserved"] == 0
    assert result["receipt_durable_proven"] is False
    assert result["receipt_failure_code"] == "receipt_unavailable_review_required"
    assert result["full_gate_pass"] is False


@_DARWIN_FORK
def test_fake_split_blocked_receipt_write_keeps_parent_bounded(monkeypatch, tmp_path):
    original = live._split_write_receipt

    def blocked_write(*args, **kwargs):
        time.sleep(20)
        return original(*args, **kwargs)

    monkeypatch.setattr(live, "_split_write_receipt", blocked_write)
    started = time.monotonic()
    result = live._supervise_fake_split_op1_once(
        run_dir=tmp_path / "split-blocked-receipt",
        grant_without_worker=_op1_without_worker())
    assert time.monotonic() - started < 2
    assert result["receipt_durable_proven"] is False
    assert result["receipt_failure_code"] == "receipt_unavailable_review_required"
    assert result["status"] == "fake_partial_split_unproven"
    assert result["failure_code"] == "receipt_unavailable_review_required"
    assert result["worker_received_proven"] is True
    assert result["r_stop"] in ("witnessed_term", "witnessed_kill")
    assert result["r_reaped"] is True
    assert result["physical_stop_unproven"] is True


@_DARWIN_FORK
def test_fake_split_blocked_receipt_directory_fsync_is_witnessed_stopped(
        monkeypatch, tmp_path):
    original_sync = live.DurableJournal._sync_directory

    def stall_receipt_sync(directory):
        if (Path(directory) / "receipt.json").exists():
            time.sleep(20)
        return original_sync(directory)

    monkeypatch.setattr(live.DurableJournal, "_sync_directory",
                        staticmethod(stall_receipt_sync))
    started = time.monotonic()
    result = live._supervise_fake_split_op1_once(
        run_dir=tmp_path / "split-receipt-fsync-stall",
        grant_without_worker=_op1_without_worker())
    assert time.monotonic() - started < 2
    assert result["receipt_durable_proven"] is False
    assert result["receipt_failure_code"] == "receipt_unavailable_review_required"
    assert result["r_stop"] in ("witnessed_term", "witnessed_kill")
    assert result["physical_stop_unproven"] is True


@_DARWIN_FORK
def test_fake_split_receipt_readback_mismatch_cannot_prove_durability(
        monkeypatch, tmp_path):
    original_write_receipt = live._split_write_receipt

    def corrupt_readback(*args, **kwargs):
        original_read = os.read

        def read(fd, size):
            if size == live.FRAME_LIMIT + 1:
                return b"corrupted-readback"
            return original_read(fd, size)

        live.os.read = read  # R-only post-fork injection
        return original_write_receipt(*args, **kwargs)

    monkeypatch.setattr(live, "_split_write_receipt", corrupt_readback)
    run_dir = tmp_path / "split-receipt-readback-mismatch"
    result = live._supervise_fake_split_op1_once(
        run_dir=run_dir, grant_without_worker=_op1_without_worker())
    assert (run_dir / "receipt.json").is_file()  # uncertain parent ACK
    assert result["receipt_durable_proven"] is False
    assert result["receipt_failure_code"] == "receipt_unavailable_review_required"
    assert result["status"] == "fake_partial_split_unproven"
    assert result["failure_code"] == "receipt_unavailable_review_required"
    assert result["full_gate_pass"] is False


@_DARWIN_FORK
@pytest.mark.parametrize("fault", ["r_after_commit", "r_after_proof"])
def test_fake_split_receipt_child_nonzero_exit_never_proves_durability(
        tmp_path, fault):
    run_dir = tmp_path / f"split-receipt-{fault}"
    result = live._supervise_fake_split_op1_once(
        run_dir=run_dir, grant_without_worker=_op1_without_worker(),
        fault=fault)
    assert (run_dir / "receipt.json").is_file()  # disk may be spent
    assert result["receipt_durable_proven"] is False
    assert result["receipt_failure_code"] == "receipt_unavailable_review_required"
    assert result["full_gate_pass"] is False


@_DARWIN_FORK
def test_fake_split_lost_receipt_proof_does_not_assume_disk_failed(
        monkeypatch, tmp_path):
    original_write = os.write

    def lose_receipt_proof(fd, data):
        if b'"phase":"receipt_proof"' in data:
            return len(data)
        return original_write(fd, data)

    monkeypatch.setattr(live.os, "write", lose_receipt_proof)
    run_dir = tmp_path / "split-receipt-lost-proof"
    result = live._supervise_fake_split_op1_once(
        run_dir=run_dir, grant_without_worker=_op1_without_worker())
    assert (run_dir / "receipt.json").is_file()
    assert result["receipt_durable_proven"] is False
    assert result["receipt_failure_code"] == "receipt_unavailable_review_required"
    assert result["full_gate_pass"] is False


@_DARWIN_FORK
def test_fake_split_lost_receipt_command_causes_zero_receipt_write(
        monkeypatch, tmp_path):
    original_write = os.write

    def lose_receipt_command(fd, data):
        if b'"phase":"receipt_write"' in data:
            return len(data)
        return original_write(fd, data)

    monkeypatch.setattr(live.os, "write", lose_receipt_command)
    run_dir = tmp_path / "split-receipt-lost-command"
    result = live._supervise_fake_split_op1_once(
        run_dir=run_dir, grant_without_worker=_op1_without_worker())
    assert not (run_dir / "receipt.json").exists()
    assert result["receipt_durable_proven"] is False
    assert result["receipt_failure_code"] == "receipt_unavailable_review_required"
    assert result["full_gate_pass"] is False


@_DARWIN_FORK
def test_fake_split_receipt_signal_noop_is_not_stop_proof(monkeypatch, tmp_path):
    original = live._split_write_receipt
    original_kill = os.kill

    def blocked_write(*args, **kwargs):
        time.sleep(20)
        return original(*args, **kwargs)

    def ignore_signal(pid, signum):
        if signum in (signal.SIGTERM, signal.SIGKILL):
            return None
        return original_kill(pid, signum)

    monkeypatch.setattr(live, "_split_write_receipt", blocked_write)
    monkeypatch.setattr(live.os, "kill", ignore_signal)
    result = live._supervise_fake_split_op1_once(
        run_dir=tmp_path / "split-receipt-noop-signal",
        grant_without_worker=_op1_without_worker())
    assert result["receipt_durable_proven"] is False
    assert result["r_stop"] == "unproven"
    assert result["physical_stop_unproven"] is True
    assert result["full_gate_pass"] is False


@_DARWIN_FORK
def test_fake_split_raw_receipt_field_cannot_cross_parent_ipc(
        monkeypatch, tmp_path):
    original = live._split_receipt_payload

    def inject_raw(*args, **kwargs):
        return {**original(*args, **kwargs), "raw": CANARY}

    monkeypatch.setattr(live, "_split_receipt_payload", inject_raw)
    run_dir = tmp_path / "split-raw-receipt"
    result = live._supervise_fake_split_op1_once(
        run_dir=run_dir, grant_without_worker=_op1_without_worker())
    assert not (run_dir / "receipt.json").exists()
    assert result["receipt_durable_proven"] is False
    assert CANARY not in json.dumps(result)
    assert result["full_gate_pass"] is False


@_DARWIN_FORK
def test_fake_split_receipt_initial_witness_failure_prevents_d_go(tmp_path):
    def bad_initial(pid):
        value = live._fake_os_witness(pid)
        value["pgid"] += 1
        return value

    run_dir = tmp_path / "split-receipt-initial-bad"
    result = live._supervise_fake_split_op1_once(
        run_dir=run_dir, grant_without_worker=_op1_without_worker(),
        receipt_initial_witness=bad_initial)
    assert not (run_dir / "journal.json").exists()
    assert result["zero_ack_received"] is False
    assert result["receipt_durable_proven"] is False
    assert result["full_gate_pass"] is False


def _seven_fake_inputs(monkeypatch, tmp_path, on_call=None):
    seed = tmp_path / "seven-seed"
    seed.mkdir()
    kwargs, _, _, _ = _worker_harness(monkeypatch, seed)
    binding = deepcopy(kwargs["binding"])
    template = "synthetic template, not a private model blob"
    system = "synthetic system, not a private model blob"

    def fake_http(method, url, payload, remaining, grant):
        assert 0 < remaining <= 2.5
        ordinal = grant["ordinal"]
        if on_call is not None:
            on_call(ordinal)
        if ordinal == 1:
            body = {"version": "0.34.4"}
        elif ordinal == 2:
            body = {"models": [{"name": "qwen2.5:7b",
                                "digest": FROZEN_MANIFEST_SHA256}]}
        elif ordinal == 3:
            body = {"template": template, "system": system}
        elif ordinal == 4:
            request = parity.fixed_transformed_request()
            rendered = ("<|im_start|>system\n" + request["messages"][0]["content"]
                        + "<|im_end|>\n<|im_start|>user\n"
                        + request["messages"][1]["content"]
                        + "<|im_end|>\n<|im_start|>assistant\n")
            body = {"model": "qwen2.5:7b",
                    "_debug_info": {"rendered_template": rendered},
                    "usage": {"prompt_tokens": 0, "completion_tokens": 0,
                              "total_tokens": 0},
                    "choices": [{"message": {"content": ""}}]}
        elif ordinal in (5, 6):
            body = {"tokens": [1, 2, 3]}
        elif ordinal == 7:
            body = {"model": "qwen2.5:7b",
                    "usage": {"prompt_tokens": 3, "completion_tokens": 2,
                              "total_tokens": 5},
                    "choices": [{"message": {"content": CANARY}}]}
        else:
            pytest.fail("eighth injected operation")
        return {"requested_url": url, "effective_url": url,
                "proxy_used": False, "redirected": False, "status": 200,
                "body": _canonical(body)}

    return binding, kwargs["observe_identity"], fake_http


@_DARWIN_FORK
def test_fake_seven_process_loop_commits_every_stage_before_next_grant(
        monkeypatch, tmp_path):
    """A process-backed W/D/R run, not merely worker_once in one process."""
    binding, observer, fake_http = _seven_fake_inputs(monkeypatch, tmp_path)

    run_dir = tmp_path / "seven"
    result = live._supervise_fake_seven_once(
        run_dir=run_dir, binding_template=binding,
        observe_identity=observer, fake_http=fake_http,
        work_seconds=2.0)
    journal_path, disk = _read_only_journal(run_dir)
    assert result["status"] == "fake_seven_process_pass"
    assert result["receipt_durable_proven"] is True
    assert [op["ordinal"] for op in disk["operations"]] == list(range(1, 8))
    assert disk["reserved"] == disk["granted"] == disk["worker_issued"] == 7
    assert disk["completion_attempt_spent"] == 1
    assert all(op["on_wire"] == "yes" for op in disk["operations"])
    assert result["http_calls"] == 7 and result["identity_checks"] == 6
    receipt_path = run_dir / "receipt.json"
    receipt = json.loads(receipt_path.read_bytes())
    assert stat.S_IMODE(run_dir.stat().st_mode) == 0o700
    assert stat.S_IMODE(receipt_path.stat().st_mode) == 0o600
    assert receipt["schema"] == "fake_seven_process_receipt_v1"
    assert receipt["status"] == "fake_seven_process_pending_receipt"
    assert [receipt[key] for key in (
        "reserved", "granted", "worker_issued", "on_wire_yes",
        "http_calls")] == [7] * 5
    assert receipt["identity_checks"] == 6
    assert receipt["completion_attempt_spent"] == 1
    assert receipt["journal_sha256"] == hashlib.sha256(
        journal_path.read_bytes()).hexdigest()
    assert receipt["physical_stop_unproven"] is True
    assert receipt["full_gate_pass"] is False
    assert result["physical_stop_unproven"] is True
    assert result["full_gate_pass"] is False
    assert CANARY not in json.dumps(result)
    assert CANARY not in receipt_path.read_text()


@_DARWIN_FORK
@pytest.mark.parametrize("stage", ["reserve", "issue", "wire"])
def test_fake_seven_durable_stage_crash_never_refunds_or_grants_next(
        monkeypatch, tmp_path, stage):
    binding, observer, fake_http = _seven_fake_inputs(monkeypatch, tmp_path)
    run_dir = tmp_path / f"seven-d-{stage}"
    result = live._supervise_fake_seven_once(
        run_dir=run_dir, binding_template=binding,
        observe_identity=observer, fake_http=fake_http,
        fault=f"d_after_{stage}_3", work_seconds=0.6)
    _, disk = _read_only_journal(run_dir)
    assert result["status"] == "fake_seven_process_unproven"
    assert result["full_gate_pass"] is False
    assert disk["reserved"] == disk["granted"] == 3
    assert disk["worker_issued"] == (2 if stage == "reserve" else 3)
    assert [op["on_wire"] for op in disk["operations"]] == (
        ["yes", "yes", "yes" if stage == "wire" else "unknown"])
    assert disk["completion_attempt_spent"] == 0
    assert not any(op["ordinal"] > 3 for op in disk["operations"])
    assert CANARY not in json.dumps(result)


@_DARWIN_FORK
def test_fake_seven_op7_spent_before_lost_grant_proof(monkeypatch, tmp_path):
    binding, observer, fake_http = _seven_fake_inputs(monkeypatch, tmp_path)
    run_dir = tmp_path / "seven-op7-spent"
    result = live._supervise_fake_seven_once(
        run_dir=run_dir, binding_template=binding,
        observe_identity=observer, fake_http=fake_http,
        fault="d_after_reserve_7", work_seconds=0.8)
    _, disk = _read_only_journal(run_dir)
    assert result["status"] == "fake_seven_process_unproven"
    assert disk["reserved"] == 7 and disk["worker_issued"] == 6
    assert disk["completion_attempt_spent"] == 1
    assert disk["operations"][6]["on_wire"] == "unknown"
    assert result["completion_attempt_spent"] == "unknown"
    assert result["physical_stop_unproven"] is True


@_DARWIN_FORK
@pytest.mark.parametrize("blocked_ordinal", range(1, 8))
def test_fake_seven_blocked_callback_is_bounded_and_not_false_wire(
        monkeypatch, tmp_path, blocked_ordinal):
    def block_on_call(ordinal):
        if ordinal == blocked_ordinal:
            time.sleep(20)

    binding, observer, fake_http = _seven_fake_inputs(
        monkeypatch, tmp_path, on_call=block_on_call)
    run_dir = tmp_path / f"seven-blocked-{blocked_ordinal}"
    started = time.monotonic()
    result = live._supervise_fake_seven_once(
        run_dir=run_dir, binding_template=binding,
        observe_identity=observer, fake_http=fake_http,
        work_seconds=0.55, cleanup_seconds=0.25)
    assert time.monotonic() - started < 3.0
    _, disk = _read_only_journal(run_dir)
    assert result["status"] == "fake_seven_process_unproven"
    assert disk["reserved"] == disk["worker_issued"] == blocked_ordinal
    assert disk["operations"][-1]["on_wire"] == "unknown"
    assert sum(op["on_wire"] == "yes" for op in disk["operations"]) == (
        blocked_ordinal - 1)
    assert disk["completion_attempt_spent"] == int(blocked_ordinal == 7)
    assert result["w_stop"] in ("witnessed_term", "witnessed_kill")
    assert result["physical_stop_unproven"] is True


@_DARWIN_FORK
def test_fake_seven_source_failure_before_op7_keeps_completion_unspent(
        monkeypatch, tmp_path):
    binding, observer, fake_http = _seven_fake_inputs(monkeypatch, tmp_path)
    binding["source"]["model_num_ctx"] = 8193
    run_dir = tmp_path / "seven-source-failure"
    result = live._supervise_fake_seven_once(
        run_dir=run_dir, binding_template=binding,
        observe_identity=observer, fake_http=fake_http,
        work_seconds=0.8)
    _, disk = _read_only_journal(run_dir)
    assert result["status"] == "fake_seven_process_unproven"
    assert disk["reserved"] == disk["worker_issued"] == 6
    assert all(op["on_wire"] == "yes" for op in disk["operations"])
    assert disk["completion_attempt_spent"] == 0
    assert result["full_gate_pass"] is False


@_DARWIN_FORK
def test_fake_seven_wrong_worker_grant_is_rejected_before_callback(
        monkeypatch, tmp_path):
    original = live._seven_child_receive
    called = tmp_path / "callback-called"

    def tamper(pipes, name, *args, **kwargs):
        value = original(pipes, name, *args, **kwargs)
        if name == "w_grant_1" and value is not None:
            value["grant"]["port"] += 1
        return value

    monkeypatch.setattr(live, "_seven_child_receive", tamper)
    binding, observer, fake_http = _seven_fake_inputs(
        monkeypatch, tmp_path, on_call=lambda _: called.write_text("called"))
    run_dir = tmp_path / "seven-tamper"
    result = live._supervise_fake_seven_once(
        run_dir=run_dir, binding_template=binding,
        observe_identity=observer, fake_http=fake_http,
        work_seconds=0.5)
    _, disk = _read_only_journal(run_dir)
    assert not called.exists()
    assert result["status"] == "fake_seven_process_unproven"
    assert disk["reserved"] == 1 and disk["worker_issued"] == 0
    assert disk["operations"][0]["on_wire"] == "unknown"


@_DARWIN_FORK
def test_fake_seven_lost_result_ack_retains_wire_and_never_grants_next(
        monkeypatch, tmp_path):
    original = live._seven_send

    def lose_ack(fd, value, deadline, **validation):
        if value["phase"] == "result_ack" and value["seq"] == 2:
            return False
        return original(fd, value, deadline, **validation)

    monkeypatch.setattr(live, "_seven_send", lose_ack)
    binding, observer, fake_http = _seven_fake_inputs(monkeypatch, tmp_path)
    run_dir = tmp_path / "seven-lost-result-ack"
    result = live._supervise_fake_seven_once(
        run_dir=run_dir, binding_template=binding,
        observe_identity=observer, fake_http=fake_http,
        work_seconds=0.6)
    _, disk = _read_only_journal(run_dir)
    assert result["status"] == "fake_seven_process_unproven"
    assert disk["reserved"] == disk["worker_issued"] == 2
    assert [op["on_wire"] for op in disk["operations"]] == ["yes", "yes"]
    assert disk["completion_attempt_spent"] == 0


@_DARWIN_FORK
def test_fake_seven_duplicate_child_frame_is_not_accepted_as_one_proof(
        monkeypatch, tmp_path):
    original = live._seven_send

    def duplicate_request(fd, value, deadline, **validation):
        if value["phase"] == "request" and value["seq"] == 1:
            frame = live.encode_frame(value)
            return os.write(fd, frame + frame) == len(frame) * 2
        return original(fd, value, deadline, **validation)

    monkeypatch.setattr(live, "_seven_send", duplicate_request)
    binding, observer, fake_http = _seven_fake_inputs(monkeypatch, tmp_path)
    run_dir = tmp_path / "seven-duplicate"
    result = live._supervise_fake_seven_once(
        run_dir=run_dir, binding_template=binding,
        observe_identity=observer, fake_http=fake_http,
        work_seconds=0.5)
    _, disk = _read_only_journal(run_dir)
    assert result["status"] == "fake_seven_process_unproven"
    assert result["failure_code"] == "worker_request_unavailable"
    assert disk["reserved"] == 0


@_DARWIN_FORK
def test_fake_seven_fd_reservation_failure_never_starts_journal(
        monkeypatch, tmp_path):
    original = live.resource.getrlimit
    monkeypatch.setattr(
        live.resource, "getrlimit",
        lambda _: (10, original(live.resource.RLIMIT_NOFILE)[1]))
    binding, observer, fake_http = _seven_fake_inputs(monkeypatch, tmp_path)
    run_dir = tmp_path / "seven-fd-refused"
    result = live._supervise_fake_seven_once(
        run_dir=run_dir, binding_template=binding,
        observe_identity=observer, fake_http=fake_http)
    assert result["status"] == "fake_seven_process_unproven"
    assert result["failure_code"] == "fake_seven_fd_reservation_unavailable"
    assert result["fd_endpoints_reserved"] == 0
    assert not run_dir.exists()


@_DARWIN_FORK
def test_fake_seven_summary_raw_canary_is_not_sent_or_receipted(
        monkeypatch, tmp_path):
    original = live.worker_once

    def poisoned_summary(**kwargs):
        value = original(**kwargs)
        value["source_evidence"]["branch"] = CANARY
        return value

    monkeypatch.setattr(live, "worker_once", poisoned_summary)
    binding, observer, fake_http = _seven_fake_inputs(monkeypatch, tmp_path)
    run_dir = tmp_path / "seven-raw-summary"
    result = live._supervise_fake_seven_once(
        run_dir=run_dir, binding_template=binding,
        observe_identity=observer, fake_http=fake_http,
        work_seconds=0.8)
    _, disk = _read_only_journal(run_dir)
    assert disk["reserved"] == 7 and disk["worker_issued"] == 7
    assert result["status"] == "fake_seven_process_unproven"
    assert CANARY not in json.dumps(result)
    receipt = run_dir / "receipt.json"
    if receipt.exists():
        assert CANARY not in receipt.read_text()


@_DARWIN_FORK
@pytest.mark.parametrize("variant,ordinal", [
    ("wrong_method", 1), ("wrong_port", 1), ("wrong_role", 1),
    ("wrong_path", 1), ("wrong_nonce", 1), ("wrong_worker", 1),
    ("expired", 1), ("wrong_payload", 3),
])
def test_fake_seven_w_local_gate_rejects_tamper_before_fake_callback(
        monkeypatch, tmp_path, variant, ordinal):
    original_worker = live.worker_once
    markers = tmp_path / "fake-callbacks"
    markers.mkdir()

    def corrupted_worker(**kwargs):
        original_http = kwargs["http_call"]
        calls = {"count": 0}

        def corrupt(method, url, payload, remaining, grant):
            calls["count"] += 1
            if calls["count"] == ordinal:
                if variant == "wrong_method":
                    method = "POST"
                elif variant == "wrong_port":
                    url = url.replace(":11455", ":11456")
                elif variant == "wrong_role":
                    grant["target_role"] = "runner"
                elif variant == "wrong_path":
                    grant["path"] = "/api/tags"
                elif variant == "wrong_nonce":
                    grant["nonce"] = "0" * 32
                elif variant == "wrong_worker":
                    grant["worker"]["pid"] += 1
                elif variant == "expired":
                    grant["expires_at"] = time.monotonic() - 1
                elif variant == "wrong_payload":
                    payload = {"model": "wrong"}
            return original_http(method, url, payload, remaining, grant)

        kwargs["http_call"] = corrupt
        return original_worker(**kwargs)

    monkeypatch.setattr(live, "worker_once", corrupted_worker)
    binding, observer, fake_http = _seven_fake_inputs(
        monkeypatch, tmp_path,
        on_call=lambda n: (markers / str(n)).write_text("called"))
    run_dir = tmp_path / f"seven-gate-{variant}"
    result = live._supervise_fake_seven_once(
        run_dir=run_dir, binding_template=binding,
        observe_identity=observer, fake_http=fake_http,
        work_seconds=0.8)
    _, disk = _read_only_journal(run_dir)
    assert result["status"] == "fake_seven_process_unproven"
    assert not (markers / str(ordinal)).exists()
    assert disk["reserved"] == ordinal
    assert disk["worker_issued"] == ordinal - 1
    assert disk["operations"][-1]["on_wire"] == "unknown"
    assert result["physical_stop_unproven"] is True


@_DARWIN_FORK
def test_fake_seven_existing_run_is_terminal_without_resume_or_mutation(
        monkeypatch, tmp_path):
    binding, observer, fake_http = _seven_fake_inputs(monkeypatch, tmp_path)
    run_dir = tmp_path / "seven-existing"
    run_dir.mkdir()
    marker = run_dir / "keep.txt"
    marker.write_text("preexisting")
    result = live._supervise_fake_seven_once(
        run_dir=run_dir, binding_template=binding,
        observe_identity=observer, fake_http=fake_http,
        work_seconds=0.5)
    assert result["status"] == "fake_seven_process_unproven"
    assert result["zero_ack_received"] is False
    assert marker.read_text() == "preexisting"
    assert not (run_dir / "journal.json").exists()


@_DARWIN_FORK
def test_fake_seven_bad_r_initial_witness_prevents_d_go(monkeypatch, tmp_path):
    def wrong(pid):
        observed = live._fake_os_witness(pid)
        observed["pgid"] += 1
        return observed

    binding, observer, fake_http = _seven_fake_inputs(monkeypatch, tmp_path)
    run_dir = tmp_path / "seven-bad-r-initial"
    result = live._supervise_fake_seven_once(
        run_dir=run_dir, binding_template=binding,
        observe_identity=observer, fake_http=fake_http,
        receipt_initial_witness=wrong, work_seconds=0.5)
    assert result["status"] == "fake_seven_process_unproven"
    assert result["zero_ack_received"] is False
    assert not (run_dir / "journal.json").exists()


@_DARWIN_FORK
def test_fake_seven_blocked_d_commit_keeps_parent_bounded(monkeypatch, tmp_path):
    original = live.DurableJournal._commit

    def stall_third_reserve(self, state):
        if (state["reserved"] == 3 and state["worker_issued"] == 2
                and state["operations"][-1]["on_wire"] == "unknown"):
            time.sleep(20)
        return original(self, state)

    monkeypatch.setattr(live.DurableJournal, "_commit", stall_third_reserve)
    binding, observer, fake_http = _seven_fake_inputs(monkeypatch, tmp_path)
    run_dir = tmp_path / "seven-d-commit-stall"
    started = time.monotonic()
    result = live._supervise_fake_seven_once(
        run_dir=run_dir, binding_template=binding,
        observe_identity=observer, fake_http=fake_http,
        work_seconds=0.55, cleanup_seconds=0.25)
    assert time.monotonic() - started < 3.0
    _, disk = _read_only_journal(run_dir)
    assert result["status"] == "fake_seven_process_unproven"
    assert result["d_stop"] in ("witnessed_term", "witnessed_kill")
    assert disk["reserved"] == 2
    assert disk["worker_issued"] == 2
    assert result["full_gate_pass"] is False


@_DARWIN_FORK
def test_fake_seven_raw_extra_field_never_crosses_request_ipc(
        monkeypatch, tmp_path):
    original = live._seven_frame

    def add_raw(run_id, phase, seq, witness, **extra):
        frame = original(run_id, phase, seq, witness, **extra)
        if phase == "request" and seq == 1:
            frame["raw"] = CANARY
        return frame

    monkeypatch.setattr(live, "_seven_frame", add_raw)
    binding, observer, fake_http = _seven_fake_inputs(monkeypatch, tmp_path)
    run_dir = tmp_path / "seven-raw-request"
    result = live._supervise_fake_seven_once(
        run_dir=run_dir, binding_template=binding,
        observe_identity=observer, fake_http=fake_http,
        work_seconds=0.5)
    _, disk = _read_only_journal(run_dir)
    assert disk["reserved"] == 0
    assert result["status"] == "fake_seven_process_unproven"
    assert CANARY not in json.dumps(result)
    receipt = run_dir / "receipt.json"
    if receipt.exists():
        assert CANARY not in receipt.read_text()


@_DARWIN_FORK
def test_fake_seven_injected_raw_exception_cannot_become_public_code(
        monkeypatch, tmp_path):
    original = live._seven_send

    def raw_error(fd, value, deadline, **validation):
        if value["phase"] == "d_go":
            raise live.LiveOperatorError(CANARY)
        return original(fd, value, deadline, **validation)

    monkeypatch.setattr(live, "_seven_send", raw_error)
    binding, observer, fake_http = _seven_fake_inputs(monkeypatch, tmp_path)
    run_dir = tmp_path / "seven-raw-exception"
    result = live._supervise_fake_seven_once(
        run_dir=run_dir, binding_template=binding,
        observe_identity=observer, fake_http=fake_http,
        work_seconds=0.5)
    assert result["status"] == "fake_seven_process_unproven"
    assert result["failure_code"] == "ipc_or_spawn_unavailable"
    assert CANARY not in json.dumps(result)
    assert not run_dir.exists()


@_DARWIN_FORK
@pytest.mark.parametrize("role", ["D", "W", "R"])
def test_fake_seven_signal_helper_nonzero_exit_cannot_be_positive(
        monkeypatch, tmp_path, role):
    original = live._split_signal_child

    def exit_nonzero_after_cleanup(*args, **kwargs):
        code = original(*args, **kwargs)
        if kwargs["target_role"] == role and code == 0:
            return 121
        return code

    monkeypatch.setattr(live, "_split_signal_child",
                        exit_nonzero_after_cleanup)
    binding, observer, fake_http = _seven_fake_inputs(monkeypatch, tmp_path)
    run_dir = tmp_path / f"seven-s-{role.lower()}-nonzero"
    result = live._supervise_fake_seven_once(
        run_dir=run_dir, binding_template=binding,
        observe_identity=observer, fake_http=fake_http)
    _, disk = _read_only_journal(run_dir)
    assert disk["reserved"] == 7 and disk["worker_issued"] == 7
    assert result["status"] == "fake_seven_process_unproven"
    assert result["failure_code"] == "signal_helper_exit_unavailable"
    assert result[f"s_{role.lower()}_reaped"] is True
    assert result[f"s_{role.lower()}_normal_exit"] is False
    assert result["physical_stop_unproven"] is True
    assert result["full_gate_pass"] is False


@_DARWIN_FORK
def test_fake_seven_restrictive_umask_still_commits_exact_0600(
        monkeypatch, tmp_path):
    binding, observer, fake_http = _seven_fake_inputs(monkeypatch, tmp_path)
    run_dir = tmp_path / "seven-umask"
    previous = os.umask(0o777)
    try:
        result = live._supervise_fake_seven_once(
            run_dir=run_dir, binding_template=binding,
            observe_identity=observer, fake_http=fake_http)
    finally:
        os.umask(previous)
    assert result["status"] == "fake_seven_process_pass"
    journal, disk = _read_only_journal(run_dir)
    assert disk["reserved"] == 7
    assert stat.S_IMODE(journal.stat().st_mode) == 0o600
    assert stat.S_IMODE((run_dir / "receipt.json").stat().st_mode) == 0o600


@_DARWIN_FORK
def test_fake_seven_parent_does_not_close_reused_core_fd(
        monkeypatch, tmp_path):
    original = live._seven_send
    original_layout = live._seven_pipe_layout
    core_numbers = set()
    held = []

    def capture_layout():
        layout = original_layout()
        core_numbers.update(fd for pair in layout[0].values() for fd in pair)
        return layout

    def hold_after_last_ack(fd, value, deadline, **validation):
        sent = original(fd, value, deadline, **validation)
        if sent and value["phase"] == "result_ack" and value["seq"] == 7:
            held.append(os.open(tmp_path / "parent-held", os.O_WRONLY
                                | os.O_CREAT | os.O_EXCL, 0o600))
        return sent

    monkeypatch.setattr(live, "_seven_send", hold_after_last_ack)
    monkeypatch.setattr(live, "_seven_pipe_layout", capture_layout)
    binding, observer, fake_http = _seven_fake_inputs(monkeypatch, tmp_path)
    try:
        result = live._supervise_fake_seven_once(
            run_dir=tmp_path / "seven-parent-fd", binding_template=binding,
            observe_identity=observer, fake_http=fake_http)
        assert result["status"] == "fake_seven_process_pass"
        assert len(held) == 1
        assert held[0] in core_numbers
        assert stat.S_ISREG(os.fstat(held[0]).st_mode)
    finally:
        for fd in held:
            try:
                os.close(fd)
            except OSError:
                pass


@_DARWIN_FORK
def test_fake_seven_w_does_not_close_reused_callback_fd(
        monkeypatch, tmp_path):
    original_w = live._seven_w_child
    held = {}

    def check_after_child_returns(*args, **kwargs):
        pipes = args[0]
        held["owned_numbers"] = {
            pipes["w_initial"][1], pipes["w_summary"][1],
            pipes["w_go"][0], pipes["w_finish"][0],
        } | {
            pipes[f"{edge}_{n}"][1] for n in range(1, 8)
            for edge in ("w_request", "w_issue", "w_result")
        } | {
            pipes[f"{edge}_{n}"][0] for n in range(1, 8)
            for edge in ("w_grant", "w_issue_ack", "w_result_ack")
        }
        code = original_w(*args, **kwargs)
        if code == 0:
            try:
                if held["fd"] not in held["owned_numbers"]:
                    return 121
                os.fstat(held["fd"])
            except (KeyError, OSError):
                return 121
        return code

    monkeypatch.setattr(live, "_seven_w_child", check_after_child_returns)
    binding, observer, base_http = _seven_fake_inputs(monkeypatch, tmp_path)

    def fake_http(method, url, payload, remaining, grant):
        if grant["ordinal"] == 7:
            opened = os.open(tmp_path / "w-held", os.O_WRONLY
                             | os.O_CREAT | os.O_EXCL, 0o600)
            target = opened
            if opened not in held["owned_numbers"]:
                for candidate in sorted(held["owned_numbers"]):
                    try:
                        os.fstat(candidate)
                    except OSError:
                        target = candidate
                        break
                if target != opened:
                    os.dup2(opened, target)
                    os.close(opened)
            held["fd"] = target
        return base_http(method, url, payload, remaining, grant)

    result = live._supervise_fake_seven_once(
        run_dir=tmp_path / "seven-w-fd", binding_template=binding,
        observe_identity=observer, fake_http=fake_http)
    assert result["status"] == "fake_seven_process_pass"
    assert (tmp_path / "w-held").exists()


def _fake_seven_port_snapshot(*, phase, daemon_port, runner_port,
                              shared_sha=None, expected_daemon_port=11455):
    """Injected fake OS observation, not an actual lsof or live-port proof."""
    assert daemon_port == expected_daemon_port
    assert runner_port == (None if phase == "pre" else 55132)
    return {
        "schema": "fake_port_snapshot_v1",
        "phase": phase,
        "daemon_port": daemon_port,
        "daemon_vacant": True,
        "runner_port": runner_port,
        "runner_vacant": None if phase == "pre" else True,
        "shared_11434": {
            "state": "listener",
            "listener_sha256": shared_sha or hashlib.sha256(
                b"synthetic pre-existing shared listener").hexdigest(),
        },
    }


@_DARWIN_FORK
def test_fake_seven_port_v2_orders_observer_and_receipts_without_live_http(
        monkeypatch, tmp_path):
    """A v1 URL check is insufficient for the frozen port-vacancy gate."""
    binding, observe_identity, fake_http = _seven_fake_inputs(
        monkeypatch, tmp_path)
    pre_marker = tmp_path / "port-pre-seen"
    calls_marker = tmp_path / "fake-calls-seen"

    def port_observe(phase, daemon_port, runner_port):
        if phase == "pre":
            assert not calls_marker.exists()
            pre_marker.write_text("pre")
        else:
            assert pre_marker.read_text() == "pre"
            assert calls_marker.read_text() == "7"
        return _fake_seven_port_snapshot(
            phase=phase, daemon_port=daemon_port, runner_port=runner_port)

    def counted_fake_http(method, url, payload, remaining, grant):
        assert pre_marker.read_text() == "pre"
        calls_marker.write_text(str(grant["ordinal"]))
        return fake_http(method, url, payload, remaining, grant)

    run_dir = tmp_path / "seven-port-v2"
    result = live._supervise_fake_seven_once(
        run_dir=run_dir, binding_template=binding,
        observe_identity=observe_identity, fake_http=counted_fake_http,
        port_observe=port_observe, work_seconds=2.0)
    assert result["receipt_durable_proven"] is True, json.dumps(result)
    receipt_path = run_dir / "receipt.json"
    receipt = json.loads(receipt_path.read_bytes())
    assert result["schema"] == "fake_seven_process_result_v2"
    assert result["status"] == "fake_seven_process_pass"
    assert result["port_gate_proven"] is True
    assert result["fd_endpoints_reserved"] == 246
    assert result["http_calls"] == 7
    assert result["identity_checks"] == 6
    assert result["receipt_durable_proven"] is True
    assert result["o_stop"] == "normal_exit"
    assert result["o_term"] == "not_attempted"
    assert result["o_kill"] == "not_attempted"
    assert result["s_o_normal_exit"] is True
    assert stat.S_IMODE(receipt_path.stat().st_mode) == 0o600
    assert receipt["schema"] == "fake_seven_process_receipt_v2"
    assert receipt["port_gate_proven"] is True
    for key in ("port_pre_sha256", "port_post_sha256"):
        assert len(result[key]) == 64
        assert receipt[key] == result[key]
    for key in ("daemon_port_vacant_after", "runner_port_vacant_after",
                "shared_11434_unchanged"):
        assert result[key] is True
        assert receipt[key] is True
    assert result["physical_stop_unproven"] is True
    assert result["full_gate_pass"] is False
    assert result["b_send_authorized"] is False
    assert CANARY not in json.dumps(result)
    assert CANARY not in receipt_path.read_text()


@_DARWIN_FORK
@pytest.mark.parametrize("variant", ["pre_occupied", "pre_unknown_shared",
                                     "pre_runner_fabricated",
                                     "post_daemon_occupied",
                                     "post_runner_occupied",
                                     "post_shared_drift", "post_wrong_runner"])
def test_fake_seven_port_v2_rejects_occupied_drift_or_wrong_binding(
        monkeypatch, tmp_path, variant):
    binding, observe_identity, fake_http = _seven_fake_inputs(
        monkeypatch, tmp_path)
    calls_marker = tmp_path / "fake-http-was-called"

    def counted_fake_http(*args):
        calls_marker.write_text("yes")
        return fake_http(*args)

    def port_observe(phase, daemon_port, runner_port):
        value = _fake_seven_port_snapshot(
            phase=phase, daemon_port=daemon_port, runner_port=runner_port)
        if variant == "pre_occupied" and phase == "pre":
            value["daemon_vacant"] = False
        elif variant == "pre_unknown_shared" and phase == "pre":
            value["shared_11434"] = {"state": "unknown",
                                     "listener_sha256": None}
        elif variant == "pre_runner_fabricated" and phase == "pre":
            value["runner_port"] = 55132
            value["runner_vacant"] = True
        elif variant == "post_daemon_occupied" and phase == "post":
            value["daemon_vacant"] = False
        elif variant == "post_runner_occupied" and phase == "post":
            value["runner_vacant"] = False
        elif variant == "post_shared_drift" and phase == "post":
            value["shared_11434"]["listener_sha256"] = hashlib.sha256(
                b"different shared listener").hexdigest()
        elif variant == "post_wrong_runner" and phase == "post":
            value["runner_port"] += 1
        return value

    run_dir = tmp_path / f"seven-port-{variant}"
    result = live._supervise_fake_seven_once(
        run_dir=run_dir, binding_template=binding,
        observe_identity=observe_identity, fake_http=counted_fake_http,
        port_observe=port_observe, work_seconds=2.0)
    assert result["schema"] == "fake_seven_process_result_v2"
    assert result["status"] != "fake_seven_process_pass"
    assert result["port_gate_proven"] is False
    assert result["full_gate_pass"] is False
    assert result["b_send_authorized"] is False
    assert result["receipt_durable_proven"] is True
    receipt = json.loads((run_dir / "receipt.json").read_bytes())
    assert receipt["schema"] == "fake_seven_process_receipt_v2"
    assert receipt["port_gate_proven"] is False
    assert receipt["b_send_authorized"] is False
    if variant.startswith("pre_"):
        assert result["http_calls"] in (0, "unknown")
        assert not calls_marker.exists()


@_DARWIN_FORK
def test_fake_seven_port_v2_accepts_explicit_vacant_shared_11434(
        monkeypatch, tmp_path):
    binding, observe_identity, fake_http = _seven_fake_inputs(
        monkeypatch, tmp_path)

    def port_observe(phase, daemon_port, runner_port):
        value = _fake_seven_port_snapshot(
            phase=phase, daemon_port=daemon_port, runner_port=runner_port)
        value["shared_11434"] = {"state": "vacant", "listener_sha256": None}
        return value

    result = live._supervise_fake_seven_once(
        run_dir=tmp_path / "seven-shared-vacant", binding_template=binding,
        observe_identity=observe_identity, fake_http=fake_http,
        port_observe=port_observe, work_seconds=2.0)
    assert result["status"] == "fake_seven_process_pass", result
    assert result["port_gate_proven"] is True
    assert result["shared_11434_unchanged"] is True
    assert result["physical_stop_unproven"] is True


@_DARWIN_FORK
@pytest.mark.parametrize("phase", ["pre", "post"])
def test_fake_seven_port_v2_blocked_observer_keeps_parent_bounded_and_r_independent(
        monkeypatch, tmp_path, phase):
    binding, observe_identity, fake_http = _seven_fake_inputs(
        monkeypatch, tmp_path)

    def port_observe(current, daemon_port, runner_port):
        if current == phase:
            time.sleep(10)
        return _fake_seven_port_snapshot(
            phase=current, daemon_port=daemon_port, runner_port=runner_port)

    run_dir = tmp_path / f"seven-port-block-{phase}"
    started = time.monotonic()
    result = live._supervise_fake_seven_once(
        run_dir=run_dir, binding_template=binding,
        observe_identity=observe_identity, fake_http=fake_http,
        port_observe=port_observe, work_seconds=0.5,
        preparation_seconds=0.5, cleanup_seconds=0.5)
    assert time.monotonic() - started < 3.0
    assert result["status"] != "fake_seven_process_pass"
    assert result["port_gate_proven"] is False
    assert result["receipt_durable_proven"] is True
    assert result["o_term"] != "not_attempted" or result["o_kill"] != "not_attempted"
    receipt = json.loads((run_dir / "receipt.json").read_bytes())
    assert receipt["schema"] == "fake_seven_process_receipt_v2"
    assert receipt["port_gate_proven"] is False


@_DARWIN_FORK
@pytest.mark.parametrize("variant", ["observer_crash", "final_crash",
                                     "raw_extra_field"])
def test_fake_seven_port_v2_rejects_callback_failure_without_raw_leak(
        monkeypatch, tmp_path, variant):
    binding, observe_identity, fake_http = _seven_fake_inputs(
        monkeypatch, tmp_path)

    def port_observe(phase, daemon_port, runner_port):
        if ((phase == "pre" and variant == "observer_crash")
                or (phase == "post" and variant == "final_crash")):
            raise RuntimeError(CANARY)
        value = _fake_seven_port_snapshot(
            phase=phase, daemon_port=daemon_port, runner_port=runner_port)
        if phase == "pre" and variant == "raw_extra_field":
            value["raw_lsof"] = CANARY
        return value

    run_dir = tmp_path / f"seven-port-raw-{variant}"
    result = live._supervise_fake_seven_once(
        run_dir=run_dir, binding_template=binding,
        observe_identity=observe_identity, fake_http=fake_http,
        port_observe=port_observe, work_seconds=2.0)
    assert result["status"] != "fake_seven_process_pass"
    assert result["port_gate_proven"] is False
    assert result["receipt_durable_proven"] is True
    receipt_path = run_dir / "receipt.json"
    assert CANARY not in json.dumps(result)
    assert CANARY not in receipt_path.read_text()


@_DARWIN_FORK
def test_fake_seven_port_v2_observer_stdio_is_not_public(
        monkeypatch, tmp_path):
    binding, observe_identity, fake_http = _seven_fake_inputs(
        monkeypatch, tmp_path)

    def port_observe(phase, daemon_port, runner_port):
        # The injected callback is untrusted for output privacy: stdout and
        # stderr must not remain attached to the parent terminal/capture.
        assert os.path.samestat(os.fstat(1), os.stat(os.devnull))
        assert os.path.samestat(os.fstat(2), os.stat(os.devnull))
        os.write(1, CANARY.encode())
        os.write(2, CANARY.encode())
        return _fake_seven_port_snapshot(
            phase=phase, daemon_port=daemon_port, runner_port=runner_port)

    result = live._supervise_fake_seven_once(
        run_dir=tmp_path / "seven-port-stdio", binding_template=binding,
        observe_identity=observe_identity, fake_http=fake_http,
        port_observe=port_observe, work_seconds=2.0)
    assert result["status"] == "fake_seven_process_pass", result


@_DARWIN_FORK
def test_fake_seven_port_v2_blocked_fresh_cleanup_witness_is_bounded(
        monkeypatch, tmp_path):
    binding, observe_identity, fake_http = _seven_fake_inputs(
        monkeypatch, tmp_path)
    blocked_pid = tmp_path / "blocked-o-pid"

    def port_observe(phase, daemon_port, runner_port):
        if phase == "post":
            blocked_pid.write_text(str(os.getpid()))
            time.sleep(10)
        return _fake_seven_port_snapshot(
            phase=phase, daemon_port=daemon_port, runner_port=runner_port)

    def cleanup_observe(pid):
        if blocked_pid.exists() and str(pid) == blocked_pid.read_text():
            time.sleep(10)
        return live._fake_os_witness(pid)

    run_dir = tmp_path / "seven-port-cleanup-observer-blocked"
    started = time.monotonic()
    result = live._supervise_fake_seven_once(
        run_dir=run_dir, binding_template=binding,
        observe_identity=observe_identity, fake_http=fake_http,
        port_observe=port_observe, cleanup_observe=cleanup_observe,
        work_seconds=0.5, preparation_seconds=0.5,
        cleanup_seconds=0.5)
    assert time.monotonic() - started < 3.0
    assert result["status"] != "fake_seven_process_pass"
    assert result["port_gate_proven"] is False
    assert result["physical_stop_unproven"] is True
    assert result["receipt_durable_proven"] is True, json.dumps(result)
    assert json.loads((run_dir / "receipt.json").read_bytes())[
        "port_gate_proven"] is False


@_DARWIN_FORK
@pytest.mark.parametrize("variant", ["o_initial_missing", "s_o_initial_missing",
                                     "o_abnormal_exit", "s_o_abnormal_exit"])
def test_fake_seven_port_v2_initial_and_exit_proofs_are_required(
        monkeypatch, tmp_path, variant):
    binding, observe_identity, fake_http = _seven_fake_inputs(
        monkeypatch, tmp_path)
    original_send = live._seven_child_send
    original_o = live._seven_o_child
    original_signal = live._split_signal_child
    port_callback_marker = tmp_path / "port-callback-started"

    def port_observe(phase, daemon_port, runner_port):
        port_callback_marker.write_text(phase)
        return _fake_seven_port_snapshot(
            phase=phase, daemon_port=daemon_port,
            runner_port=runner_port)

    if variant == "o_initial_missing":
        def no_o_initial(*args, **kwargs):
            if args[1] == "o_initial":
                return False
            return original_send(*args, **kwargs)
        monkeypatch.setattr(live, "_seven_child_send", no_o_initial)
    elif variant == "s_o_initial_missing":
        def no_s_o_initial(*args, **kwargs):
            if kwargs.get("target_role") == "O":
                return 125
            return original_signal(*args, **kwargs)
        monkeypatch.setattr(live, "_split_signal_child", no_s_o_initial)
    elif variant == "o_abnormal_exit":
        def bad_o_exit(*args, **kwargs):
            code = original_o(*args, **kwargs)
            return 121 if code == 0 else code
        monkeypatch.setattr(live, "_seven_o_child", bad_o_exit)
    else:
        def bad_s_o_exit(*args, **kwargs):
            code = original_signal(*args, **kwargs)
            return 121 if kwargs.get("target_role") == "O" else code
        monkeypatch.setattr(live, "_split_signal_child", bad_s_o_exit)

    run_dir = tmp_path / f"seven-port-{variant}"
    result = live._supervise_fake_seven_once(
        run_dir=run_dir, binding_template=binding,
        observe_identity=observe_identity, fake_http=fake_http,
        port_observe=port_observe,
        work_seconds=1.0)
    assert result["status"] != "fake_seven_process_pass"
    assert result["port_gate_proven"] is False
    assert result["receipt_durable_proven"] is True
    assert json.loads((run_dir / "receipt.json").read_bytes())[
        "port_gate_proven"] is False
    if variant in ("o_initial_missing", "s_o_initial_missing"):
        assert not port_callback_marker.exists()


@_DARWIN_FORK
def test_fake_seven_port_v2_rejects_runner_port_change_between_ops_5_and_6(
        monkeypatch, tmp_path):
    binding, observe_identity, fake_http = _seven_fake_inputs(
        monkeypatch, tmp_path)
    original = live._seven_frame

    def wrong_runner_port(run_id, phase, seq, witness, **extra):
        frame = original(run_id, phase, seq, witness, **extra)
        if phase == "request" and seq == 6:
            frame["fields"]["port"] += 1
        return frame

    monkeypatch.setattr(live, "_seven_frame", wrong_runner_port)
    run_dir = tmp_path / "seven-runner-port-drift"
    result = live._supervise_fake_seven_once(
        run_dir=run_dir, binding_template=binding,
        observe_identity=observe_identity, fake_http=fake_http,
        port_observe=lambda phase, daemon_port, runner_port:
            _fake_seven_port_snapshot(phase=phase,
                                      daemon_port=daemon_port,
                                      runner_port=runner_port),
        work_seconds=1.0)
    assert result["status"] == "fake_seven_process_unproven"
    assert result["failure_code"] == "runner_port_unavailable"
    assert result["port_gate_proven"] is False
    assert result["receipt_durable_proven"] is True
    assert json.loads((run_dir / "receipt.json").read_bytes())[
        "failure_code"] == "runner_port_unavailable"


@_DARWIN_FORK
def test_fake_seven_port_v2_does_not_claim_gate_when_dw_stop_is_unproven(
        monkeypatch, tmp_path):
    binding, observe_identity, fake_http = _seven_fake_inputs(
        monkeypatch, tmp_path)
    original_d = live._seven_d_child

    def bad_d_exit(*args, **kwargs):
        code = original_d(*args, **kwargs)
        return 121 if code == 0 else code

    monkeypatch.setattr(live, "_seven_d_child", bad_d_exit)
    run_dir = tmp_path / "seven-d-stop-unproven"
    result = live._supervise_fake_seven_once(
        run_dir=run_dir, binding_template=binding,
        observe_identity=observe_identity, fake_http=fake_http,
        port_observe=lambda phase, daemon_port, runner_port:
            _fake_seven_port_snapshot(phase=phase,
                                      daemon_port=daemon_port,
                                      runner_port=runner_port),
        work_seconds=1.0)
    assert result["status"] == "fake_seven_process_unproven"
    assert result["d_stop"] == "unproven"
    assert result["port_post_sha256"] is not None
    assert result["port_gate_proven"] is False
    assert result["receipt_durable_proven"] is True
    receipt = json.loads((run_dir / "receipt.json").read_bytes())
    assert receipt["port_gate_proven"] is False


@_DARWIN_FORK
def test_fake_seven_port_v2_trailing_o_proof_is_not_one_frame(
        monkeypatch, tmp_path):
    binding, observe_identity, fake_http = _seven_fake_inputs(
        monkeypatch, tmp_path)
    original = live._seven_send

    def extra_byte(fd, value, deadline, **validation):
        sent = original(fd, value, deadline, **validation)
        if sent and value["phase"] == "o_pre_proof":
            os.write(fd, b"x")
        return sent

    monkeypatch.setattr(live, "_seven_send", extra_byte)
    run_dir = tmp_path / "seven-port-trailing"
    result = live._supervise_fake_seven_once(
        run_dir=run_dir, binding_template=binding,
        observe_identity=observe_identity, fake_http=fake_http,
        port_observe=lambda phase, daemon_port, runner_port:
            _fake_seven_port_snapshot(phase=phase, daemon_port=daemon_port,
                                      runner_port=runner_port),
        work_seconds=1.0)
    assert result["status"] != "fake_seven_process_pass"
    assert result["failure_code"] == "port_pre_unavailable"
    assert result["receipt_durable_proven"] is True


@_DARWIN_FORK
@pytest.mark.parametrize("phase,variant", [
    ("o_pre_proof", "duplicate"), ("o_pre_proof", "partial"),
    ("o_pre_proof", "stale"), ("o_final_proof", "duplicate"),
    ("o_final_proof", "partial"), ("o_final_proof", "stale"),
])
def test_fake_seven_port_v2_rejects_duplicate_partial_or_stale_o_proof(
        monkeypatch, tmp_path, phase, variant):
    binding, observe_identity, fake_http = _seven_fake_inputs(
        monkeypatch, tmp_path)
    original = live._seven_send

    def malformed(fd, value, deadline, **validation):
        if value["phase"] != phase:
            return original(fd, value, deadline, **validation)
        if variant == "duplicate":
            sent = original(fd, value, deadline, **validation)
            if sent:
                os.write(fd, live.encode_frame(value))
            return sent
        if variant == "partial":
            os.write(fd, b"\0\0\0\x10abc")
            return True
        stale = {**value, "run_id": "stale-port-proof"}
        os.write(fd, live.encode_frame(stale))
        return True

    monkeypatch.setattr(live, "_seven_send", malformed)
    run_dir = tmp_path / f"seven-port-{phase}-{variant}"
    result = live._supervise_fake_seven_once(
        run_dir=run_dir, binding_template=binding,
        observe_identity=observe_identity, fake_http=fake_http,
        port_observe=lambda current, daemon_port, runner_port:
            _fake_seven_port_snapshot(phase=current,
                                      daemon_port=daemon_port,
                                      runner_port=runner_port),
        work_seconds=1.0)
    assert result["status"] != "fake_seven_process_pass"
    assert result["failure_code"] == (
        "port_pre_unavailable" if phase == "o_pre_proof"
        else "port_final_unavailable")
    assert result["port_gate_proven"] is False
    assert result["receipt_durable_proven"] is True


@_DARWIN_FORK
def test_fake_seven_port_v2_fd_cap_fails_before_journal_or_work(
        monkeypatch, tmp_path):
    binding, observe_identity, fake_http = _seven_fake_inputs(
        monkeypatch, tmp_path)
    monkeypatch.setattr(live.resource, "getrlimit", lambda _kind: (245, 245))
    run_dir = tmp_path / "seven-port-fd-cap"
    result = live._supervise_fake_seven_once(
        run_dir=run_dir, binding_template=binding,
        observe_identity=observe_identity, fake_http=fake_http,
        port_observe=lambda phase, daemon_port, runner_port:
            _fake_seven_port_snapshot(phase=phase, daemon_port=daemon_port,
                                      runner_port=runner_port))
    assert result["status"] == "fake_seven_process_unproven"
    assert result["failure_code"] == "fake_seven_fd_reservation_unavailable"
    assert result["fd_endpoints_reserved"] == 0
    assert not run_dir.exists()


@_DARWIN_FORK
def test_fake_split_receipt_signal_helper_bad_initial_prevents_d_go(
        monkeypatch, tmp_path):
    original = live._split_signal_child

    def bad_r_signal_initial(*args, **kwargs):
        if kwargs["target_role"] == "R":
            def wrong(pid):
                value = live._fake_os_witness(pid)
                value["pgid"] += 1
                return value
            kwargs["initial_reader"] = wrong
        return original(*args, **kwargs)

    monkeypatch.setattr(live, "_split_signal_child", bad_r_signal_initial)
    run_dir = tmp_path / "split-receipt-signal-initial-bad"
    result = live._supervise_fake_split_op1_once(
        run_dir=run_dir, grant_without_worker=_op1_without_worker())
    assert not (run_dir / "journal.json").exists()
    assert result["zero_ack_received"] is False
    assert result["receipt_durable_proven"] is False
    assert result["full_gate_pass"] is False


@_DARWIN_FORK
def test_fake_split_blocked_receipt_preflight_never_grants_op1(
        monkeypatch, tmp_path):
    original = live._split_receipt_preflight

    def blocked_preflight(*args, **kwargs):
        time.sleep(20)
        return original(*args, **kwargs)

    monkeypatch.setattr(live, "_split_receipt_preflight", blocked_preflight)
    started = time.monotonic()
    run_dir = tmp_path / "split-receipt-preflight-stall"
    result = live._supervise_fake_split_op1_once(
        run_dir=run_dir, grant_without_worker=_op1_without_worker(),
        work_seconds=0.12)
    assert time.monotonic() - started < 2
    assert result["zero_ack_received"] is True
    assert result["receipt_preflight_accepted"] is False
    assert result["request_accepted"] is False
    assert result["r_stop"] in ("witnessed_term", "witnessed_kill")
    _, disk = _read_only_journal(run_dir)
    assert disk["reserved"] == 0
    assert result["receipt_durable_proven"] is False


@_DARWIN_FORK
def test_fake_split_lost_receipt_preflight_ack_never_grants_op1(
        monkeypatch, tmp_path):
    original_write = os.write

    def lose_preflight_ack(fd, data):
        if b'"phase":"receipt_preflight_ack"' in data:
            return len(data)
        return original_write(fd, data)

    monkeypatch.setattr(live.os, "write", lose_preflight_ack)
    run_dir = tmp_path / "split-receipt-preflight-ack-lost"
    result = live._supervise_fake_split_op1_once(
        run_dir=run_dir, grant_without_worker=_op1_without_worker())
    assert result["zero_ack_received"] is True
    assert result["receipt_preflight_accepted"] is False
    assert result["request_accepted"] is False
    _, disk = _read_only_journal(run_dir)
    assert disk["reserved"] == 0
    assert result["receipt_durable_proven"] is False


@_DARWIN_FORK
def test_fake_split_receipt_preflight_rejects_changed_zero_journal(
        monkeypatch, tmp_path):
    original = live._split_disk_readback

    def alter_after_d_readback(journal, state):
        raw = original(journal, state)
        if state["reserved"] == 0:
            journal.path.write_bytes(b"tampered-after-D-zero-proof")
        return raw

    monkeypatch.setattr(live, "_split_disk_readback", alter_after_d_readback)
    run_dir = tmp_path / "split-receipt-journal-drift"
    result = live._supervise_fake_split_op1_once(
        run_dir=run_dir, grant_without_worker=_op1_without_worker())
    assert result["zero_ack_received"] is True
    assert result["receipt_preflight_accepted"] is False
    assert result["request_accepted"] is False
    assert result["grant_proven"] is False
    assert (run_dir / "journal.json").read_bytes() == b"tampered-after-D-zero-proof"
    assert result["receipt_durable_proven"] is False
    assert result["full_gate_pass"] is False


@_DARWIN_FORK
def test_fake_split_blocked_d_and_ineffective_signal_still_gets_failure_receipt(
        monkeypatch, tmp_path):
    original_commit = live.DurableJournal._commit
    original_kill = os.kill

    def blocked_commit(self, state):
        time.sleep(20)
        return original_commit(self, state)

    def ignore_signal(pid, signum):
        if signum in (signal.SIGTERM, signal.SIGKILL):
            return None
        return original_kill(pid, signum)

    monkeypatch.setattr(live.DurableJournal, "_commit", blocked_commit)
    monkeypatch.setattr(live.os, "kill", ignore_signal)
    run_dir = tmp_path / "split-blocked-d-failure-receipt"
    result = live._supervise_fake_split_op1_once(
        run_dir=run_dir, grant_without_worker=_op1_without_worker(),
        work_seconds=0.12)
    receipt = run_dir / "receipt.json"
    disk = json.loads(receipt.read_bytes())
    assert result["receipt_preflight_accepted"] is True
    assert result["d_stop"] == "unproven"
    assert result["receipt_durable_proven"] is True
    assert disk["status"] == "fake_partial_split_unproven"
    assert disk["failure_code"] == "grant_proof_unavailable"
    assert disk["physical_stop_unproven"] is True
    assert disk["full_gate_pass"] is False


class _V3FakeResponse:
    """A deliberately short-reading fake response; never a network object."""

    def __init__(self, body, url, *, status=200, chunk_size=17,
                 first_chunk_size=None):
        self.body = body
        self.url = url
        self.status = status
        self.chunk_size = chunk_size
        self.first_chunk_size = first_chunk_size
        self.offset = 0

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def geturl(self):
        return self.url

    def getcode(self):
        return self.status

    def read(self, count=-1):
        assert count > 0 and count <= live.RESPONSE_LIMIT + 1
        size = min(count, self.first_chunk_size if self.offset == 0
                   and self.first_chunk_size is not None else self.chunk_size)
        result = self.body[self.offset:self.offset + size]
        self.offset += len(result)
        return result


def _v3_socket_sentinels(monkeypatch):
    """Any accidental real transport/openers fail before a connection."""

    def forbidden(*_args, **_kwargs):
        raise AssertionError("v3 fake test attempted a real socket/opener")

    monkeypatch.setattr(socket.socket, "__init__", forbidden)
    monkeypatch.setattr(socket.socket, "connect", forbidden)
    monkeypatch.setattr(socket.socket, "connect_ex", forbidden)
    monkeypatch.setattr(socket, "create_connection", forbidden)
    monkeypatch.setattr(urllib.request, "build_opener", forbidden)
    monkeypatch.setattr(urllib.request, "urlopen", forbidden)
    monkeypatch.setattr(urllib.request.OpenerDirector, "open", forbidden)


def _v3_port_observer(phase, daemon_port, runner_port):
    return _fake_seven_port_snapshot(
        phase=phase, daemon_port=daemon_port, runner_port=runner_port)


def _v5_fake_inputs(monkeypatch, tmp_path, *, port=None):
    """A v4-compatible binding whose private daemon port belongs only to H."""
    binding, base_observer, fake_http = _seven_fake_inputs(
        monkeypatch, tmp_path)
    if port is None:
        port = 30000 + (int.from_bytes(hashlib.sha256(
            str(tmp_path).encode()).digest()[:2], "big") % 20000)
    binding["daemon"]["port"] = port

    def observer(stage):
        row = base_observer(stage)
        row["daemon"]["port"] = port
        return row

    def port_observe(phase, daemon_port, runner_port):
        return _fake_seven_port_snapshot(
            phase=phase, daemon_port=daemon_port, runner_port=runner_port,
            expected_daemon_port=port)

    return binding, observer, fake_http, port_observe, port


def _v3_fake_factory(fake_http, marker_dir, *, variant=None,
                     daemon_port=11455):
    """Only the injected opener can answer; records the actual W Request."""
    counter = {"value": 0}

    def factory(proxy_handler, no_redirect_handler):
        assert isinstance(proxy_handler, urllib.request.ProxyHandler)
        assert proxy_handler.proxies == {}
        assert isinstance(no_redirect_handler,
                          urllib.request.HTTPRedirectHandler)
        assert type(no_redirect_handler) is not urllib.request.HTTPRedirectHandler

        class CompetingRedirect:
            def http_error_302(self, *_args):
                return object()

        class FakeOpener:
            def __init__(self):
                self.handlers = [no_redirect_handler]
                if variant == "proxy_before":
                    self.handlers.append(urllib.request.ProxyHandler(
                        {"http": "http://proxy.invalid:8080"}))
                if variant == "redirect_before":
                    self.handlers.append(urllib.request.HTTPRedirectHandler())
                if variant == "redirect_error_before":
                    self.handlers.append(CompetingRedirect())
                if variant == "redirect_policy_before":
                    no_redirect_handler.redirect_request = (
                        lambda *_args: object())

            def open(self, request, timeout=None):
                counter["value"] += 1
                ordinal = counter["value"]
                method, path = OPERATIONS[ordinal - 1]
                role_port = 55132 if ordinal in (5, 6) else daemon_port
                expected_url = f"http://127.0.0.1:{role_port}{path}"
                assert isinstance(request, urllib.request.Request)
                assert request.full_url == expected_url
                assert request.get_method() == method
                assert type(timeout) in (int, float) and 0 < timeout <= 2.0
                payload = request.data
                assert payload is None or type(payload) is bytes
                if method == "POST":
                    assert payload == _canonical(json.loads(payload))
                else:
                    assert payload is None
                (marker_dir / f"call-{ordinal}.json").write_bytes(_canonical({
                    "ordinal": ordinal, "method": method, "url": expected_url,
                    "payload_sha256": None if payload is None else
                    hashlib.sha256(payload).hexdigest(),
                    "timeout": timeout,
                }))
                if variant == "raise":
                    raise RuntimeError(CANARY)
                if variant == "block" or variant == f"block_at_{ordinal}":
                    time.sleep(10)
                if variant == "print_canary":
                    print(CANARY, flush=True)
                    print(CANARY, file=sys.stderr, flush=True)
                answer = fake_http(method, expected_url, payload, timeout,
                                   {"ordinal": ordinal})
                if variant == "proxy_after":
                    self.handlers.append(urllib.request.ProxyHandler(
                        {"http": "http://proxy.invalid:8080"}))
                if variant == "redirect_after":
                    self.handlers.append(urllib.request.HTTPRedirectHandler())
                if variant == "redirect_error_after":
                    self.handlers.append(CompetingRedirect())
                if variant == "redirect_policy_after":
                    no_redirect_handler.redirect_request = (
                        lambda *_args: object())
                body = answer["body"]
                if variant in ("oversize", "oversize_short_chunks"):
                    body = b"x" * (live.RESPONSE_LIMIT + 1)
                return _V3FakeResponse(
                    body,
                    (expected_url + "/changed" if variant == "effective_url"
                     else expected_url),
                    status=302 if variant == "redirect" else
                    503 if variant == "non200" else 200,
                    chunk_size=65536 if variant in (
                        "oversize", "oversize_short_chunks") else 17,
                    first_chunk_size=7 if variant ==
                    "oversize_short_chunks" else None,
                )

        return FakeOpener()

    return factory


@_DARWIN_FORK
def test_fake_seven_transport_v3_strict_opener_positive_zero_sockets(
        monkeypatch, tmp_path):
    """W-owned Request/opener, seven ordered proofs and separate R receipt."""
    binding, observer, fake_http = _seven_fake_inputs(monkeypatch, tmp_path)
    marker_dir = tmp_path / "v3-request-markers"
    marker_dir.mkdir()
    _v3_socket_sentinels(monkeypatch)
    run_dir = tmp_path / "seven-transport-v3"
    result = live._supervise_fake_seven_once(
        run_dir=run_dir, binding_template=binding,
        observe_identity=observer, fake_http=None,
        fake_opener_factory=_v3_fake_factory(fake_http, marker_dir),
        port_observe=_v3_port_observer, work_seconds=2.0)
    assert result["schema"] == "fake_seven_process_result_v3", result
    assert result["status"] == "fake_seven_process_pass", result
    assert result["transport_gate_proven"] is True
    assert result["transport_policy_calls"] == 7
    assert len(result["transport_proof_sha256"]) == 64
    assert result["port_gate_proven"] is True
    assert result["http_calls"] == 7
    assert result["fd_endpoints_reserved"] == 246
    assert result["receipt_durable_proven"] is True
    assert result["physical_stop_unproven"] is True
    assert result["full_gate_pass"] is False
    assert result["b_send_authorized"] is False
    assert [json.loads((marker_dir / f"call-{n}.json").read_bytes())["ordinal"]
            for n in range(1, 8)] == list(range(1, 8))
    journal_path, disk = _read_only_journal(run_dir)
    assert stat.S_IMODE(run_dir.stat().st_mode) == 0o700
    assert stat.S_IMODE(journal_path.stat().st_mode) == 0o600
    assert [op["ordinal"] for op in disk["operations"]] == list(range(1, 8))
    assert disk["reserved"] == disk["granted"] == disk["worker_issued"] == 7
    assert disk["completion_attempt_spent"] == 1
    assert all(op["on_wire"] == "yes" for op in disk["operations"])
    assert CANARY.encode() not in journal_path.read_bytes()
    receipt_path = run_dir / "receipt.json"
    receipt = json.loads(receipt_path.read_bytes())
    assert stat.S_IMODE(receipt_path.stat().st_mode) == 0o600
    assert receipt["schema"] == "fake_seven_process_receipt_v3"
    assert receipt["transport_gate_proven"] is True
    assert receipt["transport_policy_calls"] == 7
    assert receipt["transport_proof_sha256"] == result["transport_proof_sha256"]
    assert CANARY.encode() not in receipt_path.read_bytes()
    assert "prehash_gate_proven" not in result
    assert "prehash_gate_proven" not in receipt
    control = {**receipt, "status": "fake_seven_process_unproven",
               "failure_code": "initial_unavailable"}
    assert live._seven_receipt_valid(control, binding["run_id"])
    for code in ("pre_stage_unavailable", "pre_stage_mismatch",
                 "cleanup_review_required"):
        assert not live._seven_receipt_valid(
            {**control, "failure_code": code}, binding["run_id"])


@_DARWIN_FORK
def test_fake_seven_prehash_v4_precedes_port_and_seven_fake_opens(
        monkeypatch, tmp_path):
    """O hashes its fixed tiny fixture before W can receive its first GO."""
    binding, observer, fake_http = _seven_fake_inputs(monkeypatch, tmp_path)
    marker_dir = tmp_path / "v4-request-markers"
    marker_dir.mkdir()
    _v3_socket_sentinels(monkeypatch)
    base_factory = _v3_fake_factory(fake_http, marker_dir)
    literal = b"URUHA_P4B_FAKE_HASH_V4\n"
    pinned_sha = "2d2078a1d31c931402d626a1321b74731099a9144b32d6aa37e6718c968e95a7"
    assert len(literal) == 23
    assert hashlib.sha256(literal).hexdigest() == pinned_sha

    # Anonymous shared memory is test-only: O and W are separate forked
    # children, so an ordinary closure flag would not witness their order.
    original_send = live._seven_send
    original_receive = live._seven_receive
    with mmap.mmap(-1, 5) as stages:
        def witnessed_receive(fd, deadline, **validation):
            value = original_receive(fd, deadline, **validation)
            if (validation.get("phase") == "o_pre_hash_port_proof"
                    and value is not None):
                stages[2] = 1
            return value

        def witnessed_send(fd, value, deadline, **validation):
            if validation.get("phase") == "w_go":
                assert stages[0] == stages[1] == stages[2] == 1
            return original_send(fd, value, deadline, **validation)

        monkeypatch.setattr(live, "_seven_receive", witnessed_receive)
        monkeypatch.setattr(live, "_seven_send", witnessed_send)

        def hash_hook(phase, fixture_path):
            assert phase in ("before_open", "before_first_read")
            fixture = Path(fixture_path)
            assert fixture.is_absolute()
            assert fixture.name == "synthetic-prehash-v4.bin"
            assert fixture.stat().st_size == 23
            assert stat.S_IMODE(fixture.stat().st_mode) == 0o600
            assert stat.S_IMODE(fixture.parent.stat().st_mode) == 0o700
            if phase == "before_open":
                stages[3] = len(os.listdir("/dev/fd"))
            if phase == "before_first_read":
                stages[0] += 1
                stages[4] = len(os.listdir("/dev/fd"))

        def port_observe(phase, daemon_port, runner_port):
            if phase == "pre":
                assert stages[0] == 1
                assert not list(marker_dir.iterdir())
                stages[1] += 1
            return _v3_port_observer(phase, daemon_port, runner_port)

        def checked_factory(proxy_handler, no_redirect_handler):
            assert stages[0] == stages[1] == stages[2] == 1
            return base_factory(proxy_handler, no_redirect_handler)

        run_dir = tmp_path / "seven-prehash-v4"
        result = live._supervise_fake_seven_once(
            run_dir=run_dir, binding_template=binding,
            observe_identity=observer, fake_http=None,
            fake_opener_factory=checked_factory,
            port_observe=port_observe, fake_prehash=True,
            fake_hash_hook=hash_hook, work_seconds=2.0)
        assert stages[0] == stages[1] == stages[2] == 1
        assert stages[4] - stages[3] == 2

    assert result["schema"] == "fake_seven_process_result_v4", result
    assert result["status"] == "fake_seven_process_pass", result
    assert result["prehash_gate_proven"] is True
    assert result["prehash_sha256"] == pinned_sha
    assert result["prehash_logical_bytes"] == 23
    assert result["pre_stage_failure_code"] == "none"
    assert result["port_gate_proven"] is True
    assert result["transport_gate_proven"] is True
    assert result["transport_policy_calls"] == 7
    assert result["http_calls"] == 7
    assert result["identity_checks"] == 6
    assert result["fd_endpoints_reserved"] == 246
    assert all(result[f"{role}_reaped"] for role in (
        "d", "w", "r", "o", "s_d", "s_w", "s_r", "s_o"))
    assert result["receipt_durable_proven"] is True
    assert result["physical_stop_unproven"] is True
    assert result["full_gate_pass"] is False
    assert result["b_send_authorized"] is False
    assert [json.loads((marker_dir / f"call-{n}.json").read_bytes())["ordinal"]
            for n in range(1, 8)] == list(range(1, 8))
    journal_path, disk = _read_only_journal(run_dir)
    assert stat.S_IMODE(run_dir.stat().st_mode) == 0o700
    assert stat.S_IMODE(journal_path.stat().st_mode) == 0o600
    assert [op["ordinal"] for op in disk["operations"]] == list(range(1, 8))
    assert disk["reserved"] == disk["granted"] == disk["worker_issued"] == 7
    assert disk["completion_attempt_spent"] == 1
    receipt_path = run_dir / "receipt.json"
    receipt = json.loads(receipt_path.read_bytes())
    assert stat.S_IMODE(receipt_path.stat().st_mode) == 0o600
    assert receipt["schema"] == "fake_seven_process_receipt_v4"
    for key in ("prehash_gate_proven", "prehash_sha256",
                "prehash_logical_bytes", "pre_stage_failure_code"):
        assert receipt[key] == result[key]
    assert CANARY.encode() not in receipt_path.read_bytes()


@_DARWIN_FORK
def test_fake_seven_prehash_v4_blocked_first_read_has_no_port_or_opener(
        monkeypatch, tmp_path):
    binding, observer, fake_http = _seven_fake_inputs(monkeypatch, tmp_path)
    marker_dir = tmp_path / "v4-blocked-request-markers"
    marker_dir.mkdir()
    _v3_socket_sentinels(monkeypatch)
    base_factory = _v3_fake_factory(fake_http, marker_dir)

    original_send = live._seven_send
    with mmap.mmap(-1, 4) as stages:
        def record_w_go(fd, value, deadline, **validation):
            if validation.get("phase") == "w_go":
                stages[3] = 1
            return original_send(fd, value, deadline, **validation)

        monkeypatch.setattr(live, "_seven_send", record_w_go)

        def hash_hook(phase, fixture_path):
            if phase == "before_first_read":
                assert Path(fixture_path).name == "synthetic-prehash-v4.bin"
                stages[0] = 1
                time.sleep(10)

        def port_observe(phase, daemon_port, runner_port):
            stages[1] = 1
            return _v3_port_observer(phase, daemon_port, runner_port)

        def counted_factory(proxy_handler, no_redirect_handler):
            stages[2] = 1
            return base_factory(proxy_handler, no_redirect_handler)

        run_dir = tmp_path / "seven-prehash-v4-blocked"
        started = time.monotonic()
        result = live._supervise_fake_seven_once(
            run_dir=run_dir, binding_template=binding,
            observe_identity=observer, fake_http=None,
            fake_opener_factory=counted_factory,
            port_observe=port_observe, fake_prehash=True,
            fake_hash_hook=hash_hook, work_seconds=0.5,
            preparation_seconds=0.5, cleanup_seconds=0.5)
        assert time.monotonic() - started < 4.0
        assert tuple(stages[:]) == (1, 0, 0, 0)

    assert result["schema"] == "fake_seven_process_result_v4"
    assert result["status"] == "fake_seven_process_unproven"
    assert result["failure_code"] != "none"
    assert result["pre_stage_failure_code"] == "pre_stage_unavailable"
    assert result["prehash_gate_proven"] is False
    assert result["prehash_sha256"] is None
    assert result["prehash_logical_bytes"] is None
    assert result["granted"] == 0
    assert result["transport_policy_calls"] == 0
    assert result["receipt_durable_proven"] is True
    assert result["full_gate_pass"] is False
    assert result["b_send_authorized"] is False
    assert not list(marker_dir.iterdir())
    _, disk = _read_only_journal(run_dir)
    assert disk["reserved"] == disk["granted"] == disk["worker_issued"] == 0
    assert disk["operations"] == []
    receipt_path = run_dir / "receipt.json"
    receipt = json.loads(receipt_path.read_bytes())
    assert stat.S_IMODE(receipt_path.stat().st_mode) == 0o600
    assert receipt["schema"] == "fake_seven_process_receipt_v4"
    assert receipt["status"] == "fake_seven_process_unproven"
    assert receipt["pre_stage_failure_code"] == "pre_stage_unavailable"
    assert receipt["prehash_gate_proven"] is False
    assert receipt["prehash_sha256"] is None
    assert receipt["prehash_logical_bytes"] is None
    assert CANARY.encode() not in receipt_path.read_bytes()


@_DARWIN_FORK
def test_fake_seven_prehash_v4_same_length_file_drift_is_not_self_report(
        monkeypatch, tmp_path):
    """O's actual bytes, not the pinned expected digest, decide admission."""
    binding, observer, fake_http = _seven_fake_inputs(monkeypatch, tmp_path)
    marker_dir = tmp_path / "v4-drift-request-markers"
    marker_dir.mkdir()
    _v3_socket_sentinels(monkeypatch)

    def mutate_before_read(phase, fixture_path):
        if phase == "before_first_read":
            path = Path(fixture_path)
            path.write_bytes(b"ZRUHA_P4B_FAKE_HASH_V4\n")

    run_dir = tmp_path / "seven-prehash-v4-drift"
    result = live._supervise_fake_seven_once(
        run_dir=run_dir, binding_template=binding,
        observe_identity=observer, fake_http=None,
        fake_opener_factory=_v3_fake_factory(fake_http, marker_dir),
        port_observe=_v3_port_observer, fake_prehash=True,
        fake_hash_hook=mutate_before_read, work_seconds=2.0)
    assert result["schema"] == "fake_seven_process_result_v4"
    assert result["status"] == "fake_seven_process_unproven"
    assert result["pre_stage_failure_code"] == "pre_stage_mismatch"
    assert result["prehash_gate_proven"] is False
    assert result["prehash_sha256"] is None
    assert result["prehash_logical_bytes"] is None
    assert result["granted"] == 0
    assert not list(marker_dir.iterdir())
    _, disk = _read_only_journal(run_dir)
    assert disk["operations"] == []
    receipt_path = run_dir / "receipt.json"
    receipt = json.loads(receipt_path.read_bytes())
    assert stat.S_IMODE(receipt_path.stat().st_mode) == 0o600
    assert receipt["pre_stage_failure_code"] == "pre_stage_mismatch"
    assert receipt["prehash_gate_proven"] is False


@_DARWIN_FORK
@pytest.mark.parametrize("variant", ["bool_count", "extra_field", "wrong_phase"])
def test_fake_seven_prehash_v4_malformed_composite_proof_fails_closed(
        monkeypatch, tmp_path, variant):
    original_send = live._seven_child_send

    def damaged_preproof(pipes, name, run_id, phase, seq, own, deadline,
                         **extra):
        if name == "o_pre_proof" and phase == "o_pre_hash_port_proof":
            if variant == "bool_count":
                extra["prehash_logical_bytes"] = True
            elif variant == "extra_field":
                extra["unexpected_raw"] = CANARY
            else:
                phase = "o_pre_proof"
        return original_send(pipes, name, run_id, phase, seq, own, deadline,
                             **extra)

    monkeypatch.setattr(live, "_seven_child_send", damaged_preproof)
    binding, observer, fake_http = _seven_fake_inputs(monkeypatch, tmp_path)
    marker_dir = tmp_path / "v4-malformed-request-markers"
    marker_dir.mkdir()
    _v3_socket_sentinels(monkeypatch)
    run_dir = tmp_path / f"seven-prehash-v4-malformed-{variant}"
    result = live._supervise_fake_seven_once(
        run_dir=run_dir, binding_template=binding,
        observe_identity=observer, fake_http=None,
        fake_opener_factory=_v3_fake_factory(fake_http, marker_dir),
        port_observe=_v3_port_observer, fake_prehash=True,
        work_seconds=0.8)
    assert result["schema"] == "fake_seven_process_result_v4"
    assert result["status"] == "fake_seven_process_unproven"
    assert result["pre_stage_failure_code"] == "pre_stage_unavailable"
    assert result["prehash_gate_proven"] is False
    assert result["granted"] == 0
    assert not list(marker_dir.iterdir())
    receipt_path = run_dir / "receipt.json"
    assert receipt_path.exists()
    assert json.loads(receipt_path.read_bytes())[
        "pre_stage_failure_code"] == "pre_stage_unavailable"
    assert CANARY.encode() not in receipt_path.read_bytes()


@_DARWIN_FORK
@pytest.mark.parametrize("variant", ["wrong_sha", "wrong_count", "wrong_port",
                                     "port_occupied"])
def test_fake_seven_prehash_v4_wellformed_wrong_proof_stops_before_w_go(
        monkeypatch, tmp_path, variant):
    original_send = live._seven_child_send

    def wrong_preproof(pipes, name, run_id, phase, seq, own, deadline,
                       **extra):
        if name == "o_pre_proof" and phase == "o_pre_hash_port_proof":
            if variant == "wrong_sha":
                extra["prehash_sha256"] = "0" * 64
            elif variant == "wrong_count":
                extra["prehash_logical_bytes"] = 22
            elif variant == "wrong_port":
                extra["daemon_port"] += 1
            else:
                extra["daemon_vacant"] = False
        return original_send(pipes, name, run_id, phase, seq, own, deadline,
                             **extra)

    monkeypatch.setattr(live, "_seven_child_send", wrong_preproof)
    binding, observer, fake_http = _seven_fake_inputs(monkeypatch, tmp_path)
    marker_dir = tmp_path / "v4-wrong-proof-markers"
    marker_dir.mkdir()
    _v3_socket_sentinels(monkeypatch)
    run_dir = tmp_path / f"seven-prehash-v4-wrong-{variant}"
    result = live._supervise_fake_seven_once(
        run_dir=run_dir, binding_template=binding,
        observe_identity=observer, fake_http=None,
        fake_opener_factory=_v3_fake_factory(fake_http, marker_dir),
        port_observe=_v3_port_observer, fake_prehash=True,
        work_seconds=0.8)
    assert result["schema"] == "fake_seven_process_result_v4"
    assert result["status"] == "fake_seven_process_unproven"
    assert result["pre_stage_failure_code"] == (
        "port_pre_not_vacant" if variant == "port_occupied"
        else "pre_stage_mismatch")
    assert result["prehash_gate_proven"] is (variant in (
        "wrong_port", "port_occupied"))
    assert result["granted"] == 0
    assert result["transport_policy_calls"] == 0
    assert not list(marker_dir.iterdir())
    receipt_path = run_dir / "receipt.json"
    assert receipt_path.exists()
    receipt = json.loads(receipt_path.read_bytes())
    assert receipt["pre_stage_failure_code"] == result[
        "pre_stage_failure_code"]
    assert receipt["prehash_gate_proven"] == result[
        "prehash_gate_proven"]


@_DARWIN_FORK
@pytest.mark.parametrize("variant", ["duplicate", "trailing"])
def test_fake_seven_prehash_v4_rejects_extra_wire_after_proof(
        monkeypatch, tmp_path, variant):
    original_send = live._seven_child_send

    def extra_wire(pipes, name, run_id, phase, seq, own, deadline,
                   **extra):
        if name == "o_pre_proof" and phase == "o_pre_hash_port_proof":
            fd = pipes[name][1]
            try:
                frame = live.encode_frame(live._seven_frame(
                    run_id, phase, seq, own, **extra))
                suffix = frame if variant == "duplicate" else b"x"
                raw = frame + suffix
                assert os.write(fd, raw) == len(raw)
                return True
            finally:
                os.close(fd)
        return original_send(pipes, name, run_id, phase, seq, own, deadline,
                             **extra)

    monkeypatch.setattr(live, "_seven_child_send", extra_wire)
    binding, observer, fake_http = _seven_fake_inputs(monkeypatch, tmp_path)
    marker_dir = tmp_path / "v4-extra-wire-markers"
    marker_dir.mkdir()
    _v3_socket_sentinels(monkeypatch)
    run_dir = tmp_path / f"seven-prehash-v4-extra-{variant}"
    result = live._supervise_fake_seven_once(
        run_dir=run_dir, binding_template=binding,
        observe_identity=observer, fake_http=None,
        fake_opener_factory=_v3_fake_factory(fake_http, marker_dir),
        port_observe=_v3_port_observer, fake_prehash=True,
        work_seconds=0.8)
    assert result["schema"] == "fake_seven_process_result_v4"
    assert result["status"] == "fake_seven_process_unproven"
    assert result["pre_stage_failure_code"] == "pre_stage_unavailable"
    assert result["prehash_gate_proven"] is False
    assert result["granted"] == 0
    assert not list(marker_dir.iterdir())
    receipt_path = run_dir / "receipt.json"
    assert receipt_path.exists()
    assert json.loads(receipt_path.read_bytes())[
        "pre_stage_failure_code"] == "pre_stage_unavailable"


@_DARWIN_FORK
@pytest.mark.parametrize("variant", ["o_initial_missing", "s_o_initial_missing",
                                     "s_o_abnormal_exit"])
def test_fake_seven_prehash_v4_initial_and_signal_exit_precedence(
        monkeypatch, tmp_path, variant):
    binding, observer, fake_http = _seven_fake_inputs(monkeypatch, tmp_path)
    original_child_send = live._seven_child_send
    original_signal_child = live._split_signal_child
    marker_dir = tmp_path / "v4-initial-markers"
    marker_dir.mkdir()
    _v3_socket_sentinels(monkeypatch)
    with mmap.mmap(-1, 2) as callbacks:
        def hook(phase, _path):
            callbacks[0] = 1

        def port_observe(phase, daemon_port, runner_port):
            callbacks[1] = 1
            return _v3_port_observer(phase, daemon_port, runner_port)

        if variant == "o_initial_missing":
            def no_o_initial(*args, **kwargs):
                if args[1] == "o_initial":
                    return False
                return original_child_send(*args, **kwargs)
            monkeypatch.setattr(live, "_seven_child_send", no_o_initial)
        else:
            def altered_signal_child(*args, **kwargs):
                if kwargs.get("target_role") == "O":
                    if variant == "s_o_initial_missing":
                        return 125
                    code = original_signal_child(*args, **kwargs)
                    return 121 if code == 0 else code
                return original_signal_child(*args, **kwargs)
            monkeypatch.setattr(live, "_split_signal_child",
                                altered_signal_child)

        run_dir = tmp_path / f"seven-prehash-v4-{variant}"
        result = live._supervise_fake_seven_once(
            run_dir=run_dir, binding_template=binding,
            observe_identity=observer, fake_http=None,
            fake_opener_factory=_v3_fake_factory(fake_http, marker_dir),
            port_observe=port_observe, fake_prehash=True,
            fake_hash_hook=hook, work_seconds=1.0)
        if variant != "s_o_abnormal_exit":
            assert tuple(callbacks[:]) == (0, 0)
    assert result["schema"] == "fake_seven_process_result_v4"
    assert result["status"] == "fake_seven_process_unproven"
    if variant == "o_initial_missing":
        assert result["pre_stage_failure_code"] == \
               "port_helper_initial_unavailable"
        assert result["failure_code"] == "port_helper_initial_unavailable"
    elif variant == "s_o_initial_missing":
        assert result["pre_stage_failure_code"] == \
               "signal_helper_initial_unavailable"
        assert result["failure_code"] == "signal_helper_initial_unavailable"
    else:
        assert result["failure_code"] == "cleanup_review_required"
        assert result["s_o_normal_exit"] is False
    assert result["receipt_durable_proven"] is True
    receipt_path = run_dir / "receipt.json"
    assert receipt_path.exists()
    assert json.loads(receipt_path.read_bytes())[
        "pre_stage_failure_code"] == result["pre_stage_failure_code"]


@_DARWIN_FORK
@pytest.mark.parametrize("variant", [
    "same_bytes_new_inode", "symlink_leaf", "oversize", "hardlink",
])
def test_fake_seven_prehash_v4_fixture_identity_or_limit_refuses_read(
        monkeypatch, tmp_path, variant, request):
    binding, observer, fake_http = _seven_fake_inputs(monkeypatch, tmp_path)
    marker_dir = tmp_path / "v4-fixture-request-markers"
    marker_dir.mkdir()
    _v3_socket_sentinels(monkeypatch)
    fixture_marker = tmp_path / "v4-fixture-location.txt"

    def cleanup_test_created_entries():
        if not fixture_marker.exists():
            return
        leaf = Path(fixture_marker.read_text())
        directory = leaf.parent
        assert leaf.name == "synthetic-prehash-v4.bin"
        assert directory.name.startswith("uruha-p4b-v4-")
        assert directory.parent == Path(tempfile.gettempdir()).resolve()
        for name in ("replacement.bin", "extra-hardlink.bin"):
            extra = directory / name
            if extra.exists() or extra.is_symlink():
                extra.unlink()
        if leaf.exists() or leaf.is_symlink():
            leaf.unlink()
        if directory.exists():
            directory.rmdir()

    request.addfinalizer(cleanup_test_created_entries)
    with mmap.mmap(-1, 1) as port_called:
        def mutate_before_open(phase, fixture_path):
            if phase != "before_open":
                return
            path = Path(fixture_path)
            fixture_marker.write_text(str(path))
            if variant in ("same_bytes_new_inode", "symlink_leaf"):
                replacement = path.with_name("replacement.bin")
                replacement.write_bytes(b"URUHA_P4B_FAKE_HASH_V4\n")
                replacement.chmod(0o600)
                if variant == "same_bytes_new_inode":
                    os.replace(replacement, path)
                else:
                    path.unlink()
                    path.symlink_to(replacement)
            elif variant == "oversize":
                path.write_bytes(b"x" * (1024 * 1024 + 1))
            else:
                os.link(path, path.with_name("extra-hardlink.bin"))

        def port_observe(phase, daemon_port, runner_port):
            port_called[0] = 1
            return _v3_port_observer(phase, daemon_port, runner_port)

        run_dir = tmp_path / f"seven-prehash-v4-fixture-{variant}"
        result = live._supervise_fake_seven_once(
            run_dir=run_dir, binding_template=binding,
            observe_identity=observer, fake_http=None,
            fake_opener_factory=_v3_fake_factory(fake_http, marker_dir),
            port_observe=port_observe, fake_prehash=True,
            fake_hash_hook=mutate_before_open, work_seconds=0.8)
        assert port_called[0] == 0
    assert result["schema"] == "fake_seven_process_result_v4"
    assert result["status"] == "fake_seven_process_unproven"
    assert result["pre_stage_failure_code"] == "pre_stage_unavailable"
    assert result["prehash_gate_proven"] is False
    assert result["prehash_sha256"] is None
    assert result["prehash_logical_bytes"] is None
    assert result["granted"] == 0
    assert not list(marker_dir.iterdir())
    _, disk = _read_only_journal(run_dir)
    assert disk["operations"] == []
    receipt_path = run_dir / "receipt.json"
    assert receipt_path.exists()
    assert stat.S_IMODE(receipt_path.stat().st_mode) == 0o600
    assert json.loads(receipt_path.read_bytes())[
        "pre_stage_failure_code"] == "pre_stage_unavailable"


@_DARWIN_FORK
def test_fake_seven_prehash_v4_r_failure_keeps_hash_subverdict(
        monkeypatch, tmp_path):
    def unavailable_receipt(*_args, **_kwargs):
        raise RuntimeError(CANARY)

    monkeypatch.setattr(live, "_seven_write_receipt", unavailable_receipt)
    binding, observer, fake_http = _seven_fake_inputs(monkeypatch, tmp_path)
    marker_dir = tmp_path / "v4-r-fail-markers"
    marker_dir.mkdir()
    _v3_socket_sentinels(monkeypatch)
    run_dir = tmp_path / "seven-prehash-v4-r-fail"
    result = live._supervise_fake_seven_once(
        run_dir=run_dir, binding_template=binding,
        observe_identity=observer, fake_http=None,
        fake_opener_factory=_v3_fake_factory(fake_http, marker_dir),
        port_observe=_v3_port_observer, fake_prehash=True,
        work_seconds=2.0)
    assert len(list(marker_dir.glob("call-*.json"))) == 7
    assert result["schema"] == "fake_seven_process_result_v4"
    assert result["prehash_gate_proven"] is True
    assert result["pre_stage_failure_code"] == "none"
    assert result["transport_gate_proven"] is True
    assert result["status"] == "fake_seven_process_unproven"
    assert result["failure_code"] == "receipt_unavailable_review_required"
    assert result["receipt_durable_proven"] is False
    assert result["full_gate_pass"] is False
    assert result["b_send_authorized"] is False
    assert CANARY not in json.dumps(result)
    assert not (run_dir / "receipt.json").exists()


@_DARWIN_FORK
def test_fake_seven_prehash_v4_r_failure_after_hash_stall_keeps_first_error(
        monkeypatch, tmp_path):
    def unavailable_receipt(*_args, **_kwargs):
        raise RuntimeError(CANARY)

    monkeypatch.setattr(live, "_seven_write_receipt", unavailable_receipt)
    binding, observer, fake_http = _seven_fake_inputs(monkeypatch, tmp_path)
    marker_dir = tmp_path / "v4-r-after-stall-markers"
    marker_dir.mkdir()
    _v3_socket_sentinels(monkeypatch)

    def blocked_read(phase, _fixture_path):
        if phase == "before_first_read":
            time.sleep(10)

    run_dir = tmp_path / "seven-prehash-v4-r-after-stall"
    result = live._supervise_fake_seven_once(
        run_dir=run_dir, binding_template=binding,
        observe_identity=observer, fake_http=None,
        fake_opener_factory=_v3_fake_factory(fake_http, marker_dir),
        port_observe=_v3_port_observer, fake_prehash=True,
        fake_hash_hook=blocked_read, work_seconds=0.5)
    assert result["schema"] == "fake_seven_process_result_v4"
    assert result["status"] == "fake_seven_process_unproven"
    assert result["pre_stage_failure_code"] == "pre_stage_unavailable"
    assert result["failure_code"] == "receipt_unavailable_review_required"
    assert result["receipt_durable_proven"] is False
    assert result["prehash_gate_proven"] is False
    assert result["transport_policy_calls"] == 0
    assert not list(marker_dir.iterdir())
    assert not (run_dir / "receipt.json").exists()


@_DARWIN_FORK
@pytest.mark.parametrize("variant", ["print_canary", "raise_canary"])
def test_fake_seven_prehash_v4_hook_raw_output_is_contained(
        monkeypatch, tmp_path, capfd, variant):
    binding, observer, fake_http = _seven_fake_inputs(monkeypatch, tmp_path)
    marker_dir = tmp_path / "v4-hook-canary-markers"
    marker_dir.mkdir()
    _v3_socket_sentinels(monkeypatch)

    def noisy_hook(phase, _fixture_path):
        if phase == "before_first_read":
            print(CANARY, flush=True)
            print(CANARY, file=sys.stderr, flush=True)
            if variant == "raise_canary":
                raise RuntimeError(CANARY)

    run_dir = tmp_path / f"seven-prehash-v4-{variant}"
    result = live._supervise_fake_seven_once(
        run_dir=run_dir, binding_template=binding,
        observe_identity=observer, fake_http=None,
        fake_opener_factory=_v3_fake_factory(fake_http, marker_dir),
        port_observe=_v3_port_observer, fake_prehash=True,
        fake_hash_hook=noisy_hook, work_seconds=2.0)
    assert result["schema"] == "fake_seven_process_result_v4"
    assert result["status"] == (
        "fake_seven_process_pass" if variant == "print_canary"
        else "fake_seven_process_unproven")
    assert result["prehash_gate_proven"] is (variant == "print_canary")
    assert CANARY not in json.dumps(result)
    journal_path, _ = _read_only_journal(run_dir)
    assert CANARY.encode() not in journal_path.read_bytes()
    receipt_path = run_dir / "receipt.json"
    assert receipt_path.exists()
    assert CANARY.encode() not in receipt_path.read_bytes()
    captured = capfd.readouterr()
    assert CANARY not in captured.out + captured.err


@_DARWIN_FORK
def test_fake_seven_prehash_v4_blocked_cleanup_witness_keeps_first_error(
        monkeypatch, tmp_path):
    binding, observer, fake_http = _seven_fake_inputs(monkeypatch, tmp_path)
    marker_dir = tmp_path / "v4-cleanup-block-markers"
    marker_dir.mkdir()
    blocked_o_pid = tmp_path / "v4-blocked-o-pid"
    _v3_socket_sentinels(monkeypatch)

    def blocking_read_hook(phase, _fixture_path):
        if phase == "before_first_read":
            blocked_o_pid.write_text(str(os.getpid()))
            time.sleep(10)

    def blocked_cleanup_observer(pid):
        if blocked_o_pid.exists() and str(pid) == blocked_o_pid.read_text():
            time.sleep(10)
        return live._fake_os_witness(pid)

    run_dir = tmp_path / "seven-prehash-v4-cleanup-block"
    started = time.monotonic()
    result = live._supervise_fake_seven_once(
        run_dir=run_dir, binding_template=binding,
        observe_identity=observer, fake_http=None,
        fake_opener_factory=_v3_fake_factory(fake_http, marker_dir),
        port_observe=_v3_port_observer, fake_prehash=True,
        fake_hash_hook=blocking_read_hook,
        cleanup_observe=blocked_cleanup_observer,
        work_seconds=0.5, preparation_seconds=0.5,
        cleanup_seconds=0.5)
    assert time.monotonic() - started < 4.0
    assert result["schema"] == "fake_seven_process_result_v4"
    assert result["status"] == "fake_seven_process_unproven"
    assert result["pre_stage_failure_code"] == "pre_stage_unavailable"
    assert result["failure_code"] == "cleanup_review_required"
    assert result["prehash_gate_proven"] is False
    assert result["transport_policy_calls"] == 0
    assert result["o_stop"] == "unproven"
    assert result["receipt_durable_proven"] is True
    assert not list(marker_dir.iterdir())
    receipt_path = run_dir / "receipt.json"
    assert receipt_path.exists()
    receipt = json.loads(receipt_path.read_bytes())
    assert receipt["pre_stage_failure_code"] == "pre_stage_unavailable"
    assert receipt["failure_code"] == "cleanup_review_required"
    assert CANARY.encode() not in receipt_path.read_bytes()


@_DARWIN_FORK
def test_fake_seven_prehash_v4_fd_cap_fails_before_journal_or_work(
        monkeypatch, tmp_path):
    binding, observer, fake_http = _seven_fake_inputs(monkeypatch, tmp_path)
    marker_dir = tmp_path / "v4-fd-cap-markers"
    marker_dir.mkdir()
    _v3_socket_sentinels(monkeypatch)
    monkeypatch.setattr(live.resource, "getrlimit", lambda _kind: (245, 245))
    run_dir = tmp_path / "seven-prehash-v4-fd-cap"
    result = live._supervise_fake_seven_once(
        run_dir=run_dir, binding_template=binding,
        observe_identity=observer, fake_http=None,
        fake_opener_factory=_v3_fake_factory(fake_http, marker_dir),
        port_observe=_v3_port_observer, fake_prehash=True)
    assert result["schema"] == "fake_seven_process_result_v4"
    assert result["status"] == "fake_seven_process_unproven"
    assert result["failure_code"] == "fake_seven_fd_reservation_unavailable"
    assert result["fd_endpoints_reserved"] == 0
    assert result["prehash_gate_proven"] is False
    assert not run_dir.exists()
    assert not list(marker_dir.iterdir())


@pytest.mark.parametrize("variant", [
    "missing_factory", "missing_ports", "legacy_http", "hook_without_opt_in",
])
def test_fake_seven_prehash_v4_rejects_invalid_opt_in_before_work(
        monkeypatch, tmp_path, variant):
    binding, observer, fake_http = _seven_fake_inputs(monkeypatch, tmp_path)
    marker_dir = tmp_path / "v4-invalid-request-markers"
    marker_dir.mkdir()
    _v3_socket_sentinels(monkeypatch)
    run_dir = tmp_path / f"seven-prehash-v4-invalid-{variant}"
    kwargs = {
        "fake_prehash": variant != "hook_without_opt_in",
        "fake_hash_hook": (lambda _phase, _path: None),
        "fake_http": fake_http if variant in (
            "missing_factory", "legacy_http") else None,
        "fake_opener_factory": None if variant == "missing_factory" else
        _v3_fake_factory(fake_http, marker_dir),
        "port_observe": None if variant == "missing_ports" else
        _v3_port_observer,
    }
    with pytest.raises(live.LiveOperatorError,
                       match="^fake_seven_configuration_invalid$"):
        live._supervise_fake_seven_once(
            run_dir=run_dir, binding_template=binding,
            observe_identity=observer, **kwargs)
    assert not run_dir.exists()
    assert not list(marker_dir.iterdir())


@_DARWIN_FORK
def test_fake_seven_transport_v3_fd_cap_fails_before_journal_or_work(
        monkeypatch, tmp_path):
    binding, observer, fake_http = _seven_fake_inputs(monkeypatch, tmp_path)
    marker_dir = tmp_path / "v3-fd-markers"
    marker_dir.mkdir()
    monkeypatch.setattr(live.resource, "getrlimit", lambda _kind: (245, 245))
    run_dir = tmp_path / "seven-transport-v3-fd-cap"
    result = live._supervise_fake_seven_once(
        run_dir=run_dir, binding_template=binding,
        observe_identity=observer, fake_http=None,
        fake_opener_factory=_v3_fake_factory(fake_http, marker_dir),
        port_observe=_v3_port_observer)
    assert result["schema"] == "fake_seven_process_result_v3"
    assert result["status"] == "fake_seven_process_unproven"
    assert result["failure_code"] == "fake_seven_fd_reservation_unavailable"
    assert result["fd_endpoints_reserved"] == 0
    assert result["transport_gate_proven"] is False
    assert not run_dir.exists()
    assert not list(marker_dir.iterdir())


@_DARWIN_FORK
@pytest.mark.parametrize("variant", [
    "proxy_before", "proxy_after", "redirect_before", "redirect_after",
    "redirect_error_before", "redirect_error_after",
    "redirect_policy_before", "redirect_policy_after",
    "redirect", "effective_url", "non200", "oversize",
    "oversize_short_chunks", "raise", "block",
])
def test_fake_seven_transport_v3_faults_fail_closed_with_receipt(
        monkeypatch, tmp_path, variant):
    """Transport policy and bounded-read failures cannot become a pass."""
    binding, observer, fake_http = _seven_fake_inputs(monkeypatch, tmp_path)
    marker_dir = tmp_path / "v3-fault-markers"
    marker_dir.mkdir()
    _v3_socket_sentinels(monkeypatch)
    run_dir = tmp_path / f"seven-transport-v3-{variant}"
    started = time.monotonic()
    result = live._supervise_fake_seven_once(
        run_dir=run_dir, binding_template=binding,
        observe_identity=observer, fake_http=None,
        fake_opener_factory=_v3_fake_factory(
            fake_http, marker_dir, variant=variant),
        port_observe=_v3_port_observer, work_seconds=0.8)
    assert time.monotonic() - started < 3.0
    assert result["schema"] == "fake_seven_process_result_v3"
    assert result["status"] != "fake_seven_process_pass", result
    assert result["transport_gate_proven"] is False
    assert result["full_gate_pass"] is False
    assert result["b_send_authorized"] is False
    assert CANARY not in json.dumps(result)
    if variant in ("proxy_before", "redirect_before",
                   "redirect_error_before",
                   "redirect_policy_before"):
        assert not list(marker_dir.iterdir())
    else:
        assert (marker_dir / "call-1.json").is_file()
        assert not (marker_dir / "call-2.json").exists()
    receipt_path = run_dir / "receipt.json"
    assert receipt_path.exists()
    receipt = json.loads(receipt_path.read_bytes())
    assert stat.S_IMODE(receipt_path.stat().st_mode) == 0o600
    assert receipt["schema"] == "fake_seven_process_receipt_v3"
    assert receipt["transport_gate_proven"] is False
    assert CANARY.encode() not in receipt_path.read_bytes()


@_DARWIN_FORK
def test_fake_seven_transport_v3_printed_canary_is_contained(
        monkeypatch, tmp_path, capfd):
    binding, observer, fake_http = _seven_fake_inputs(monkeypatch, tmp_path)
    marker_dir = tmp_path / "v3-canary-markers"
    marker_dir.mkdir()
    _v3_socket_sentinels(monkeypatch)
    run_dir = tmp_path / "seven-transport-v3-print-canary"
    result = live._supervise_fake_seven_once(
        run_dir=run_dir, binding_template=binding,
        observe_identity=observer, fake_http=None,
        fake_opener_factory=_v3_fake_factory(
            fake_http, marker_dir, variant="print_canary"),
        port_observe=_v3_port_observer, work_seconds=2.0)
    assert result["status"] == "fake_seven_process_pass", result
    assert result["transport_gate_proven"] is True
    assert CANARY not in json.dumps(result)
    assert CANARY.encode() not in (run_dir / "receipt.json").read_bytes()
    assert CANARY.encode() not in (run_dir / live.JOURNAL_NAME).read_bytes()
    captured = capfd.readouterr()
    assert CANARY not in captured.out + captured.err


@_DARWIN_FORK
@pytest.mark.parametrize("variant,ordinal", [
    ("wrong_scheme", 1), ("wrong_host", 1), ("wrong_port", 1),
    ("wrong_path", 1), ("wrong_method", 1), ("wrong_payload", 3),
    ("wrong_nonce", 1),
])
def test_fake_seven_transport_v3_rejects_request_tamper_before_opener(
        monkeypatch, tmp_path, variant, ordinal):
    original_worker = live.worker_once
    marker_dir = tmp_path / "v3-tamper-markers"
    marker_dir.mkdir()

    def corrupted_worker(**kwargs):
        original_http = kwargs["http_call"]
        calls = {"count": 0}

        def corrupt(method, url, payload, remaining, grant):
            calls["count"] += 1
            if calls["count"] == ordinal:
                if variant == "wrong_scheme":
                    url = url.replace("http://", "https://", 1)
                elif variant == "wrong_host":
                    url = url.replace("127.0.0.1", "localhost", 1)
                elif variant == "wrong_port":
                    url = url.replace(":11455", ":11456", 1)
                elif variant == "wrong_path":
                    url += "/extra"
                elif variant == "wrong_method":
                    method = "POST"
                elif variant == "wrong_payload":
                    payload = {"model": "wrong"}
                elif variant == "wrong_nonce":
                    grant["nonce"] = "0" * 32
            return original_http(method, url, payload, remaining, grant)

        kwargs["http_call"] = corrupt
        return original_worker(**kwargs)

    monkeypatch.setattr(live, "worker_once", corrupted_worker)
    binding, observer, fake_http = _seven_fake_inputs(monkeypatch, tmp_path)
    _v3_socket_sentinels(monkeypatch)
    run_dir = tmp_path / f"seven-transport-v3-tamper-{variant}"
    result = live._supervise_fake_seven_once(
        run_dir=run_dir, binding_template=binding,
        observe_identity=observer, fake_http=None,
        fake_opener_factory=_v3_fake_factory(fake_http, marker_dir),
        port_observe=_v3_port_observer, work_seconds=0.8)
    assert result["schema"] == "fake_seven_process_result_v3"
    assert result["status"] != "fake_seven_process_pass"
    assert result["transport_gate_proven"] is False
    assert not (marker_dir / f"call-{ordinal}.json").exists()
    receipt_path = run_dir / "receipt.json"
    assert receipt_path.exists()
    assert json.loads(receipt_path.read_bytes())["transport_gate_proven"] is False
    assert CANARY.encode() not in receipt_path.read_bytes()


@_DARWIN_FORK
@pytest.mark.parametrize("variant", ["missing", "corrupt", "float_count"])
def test_fake_seven_transport_v3_missing_or_corrupt_w_summary_is_not_proof(
        monkeypatch, tmp_path, variant):
    original_send = live._seven_child_send

    def damaged_summary(pipes, name, run_id, phase, seq, own, deadline,
                        **extra):
        if name == "w_summary":
            if variant == "missing":
                return False
            extra["summary"] = dict(extra["summary"])
            if variant == "float_count":
                extra["summary"]["transport_policy_calls"] = 7.0
            else:
                extra["summary"]["transport_proof_sha256"] = "0" * 64
        return original_send(pipes, name, run_id, phase, seq, own, deadline,
                             **extra)

    monkeypatch.setattr(live, "_seven_child_send", damaged_summary)
    binding, observer, fake_http = _seven_fake_inputs(monkeypatch, tmp_path)
    marker_dir = tmp_path / "v3-summary-markers"
    marker_dir.mkdir()
    _v3_socket_sentinels(monkeypatch)
    run_dir = tmp_path / f"seven-transport-v3-summary-{variant}"
    result = live._supervise_fake_seven_once(
        run_dir=run_dir, binding_template=binding,
        observe_identity=observer, fake_http=None,
        fake_opener_factory=_v3_fake_factory(fake_http, marker_dir),
        port_observe=_v3_port_observer, work_seconds=2.0)
    assert len(list(marker_dir.glob("call-*.json"))) == 7
    assert result["schema"] == "fake_seven_process_result_v3"
    assert result["status"] != "fake_seven_process_pass"
    assert result["transport_gate_proven"] is False
    receipt_path = run_dir / "receipt.json"
    assert receipt_path.exists()
    receipt = json.loads(receipt_path.read_bytes())
    assert receipt["schema"] == "fake_seven_process_receipt_v3"
    assert receipt["transport_gate_proven"] is False
    assert CANARY.encode() not in receipt_path.read_bytes()


@_DARWIN_FORK
def test_fake_seven_transport_v3_parent_rehashes_received_result_frames(
        monkeypatch, tmp_path):
    """A W summary cannot certify a result frame P actually saw corrupted."""
    original_send = live._seven_child_send

    def damaged_result(pipes, name, run_id, phase, seq, own, deadline,
                       **extra):
        if name == "w_result_4":
            extra["response_sha256"] = "0" * 64
        return original_send(pipes, name, run_id, phase, seq, own, deadline,
                             **extra)

    monkeypatch.setattr(live, "_seven_child_send", damaged_result)
    binding, observer, fake_http = _seven_fake_inputs(monkeypatch, tmp_path)
    marker_dir = tmp_path / "v3-frame-markers"
    marker_dir.mkdir()
    _v3_socket_sentinels(monkeypatch)
    run_dir = tmp_path / "seven-transport-v3-frame-mismatch"
    result = live._supervise_fake_seven_once(
        run_dir=run_dir, binding_template=binding,
        observe_identity=observer, fake_http=None,
        fake_opener_factory=_v3_fake_factory(fake_http, marker_dir),
        port_observe=_v3_port_observer, work_seconds=2.0)
    assert len(list(marker_dir.glob("call-*.json"))) == 7
    assert result["schema"] == "fake_seven_process_result_v3"
    assert result["status"] != "fake_seven_process_pass"
    assert result["transport_gate_proven"] is False
    receipt_path = run_dir / "receipt.json"
    assert receipt_path.exists()
    assert json.loads(receipt_path.read_bytes())["transport_gate_proven"] is False


@_DARWIN_FORK
@pytest.mark.parametrize("ordinal", range(1, 8))
def test_fake_seven_transport_v3_blocked_read_at_each_ordinal_fail_closed(
        monkeypatch, tmp_path, ordinal):
    binding, observer, fake_http = _seven_fake_inputs(monkeypatch, tmp_path)
    marker_dir = tmp_path / f"v3-block-{ordinal}-markers"
    marker_dir.mkdir()
    _v3_socket_sentinels(monkeypatch)
    run_dir = tmp_path / f"seven-transport-v3-block-{ordinal}"
    result = live._supervise_fake_seven_once(
        run_dir=run_dir, binding_template=binding,
        observe_identity=observer, fake_http=None,
        fake_opener_factory=_v3_fake_factory(
            fake_http, marker_dir, variant=f"block_at_{ordinal}"),
        port_observe=_v3_port_observer, work_seconds=0.8)
    assert result["schema"] == "fake_seven_process_result_v3"
    assert result["status"] != "fake_seven_process_pass"
    assert result["transport_gate_proven"] is False
    assert sorted(int(path.stem.split("-")[1]) for path in
                  marker_dir.glob("call-*.json")) == list(range(1, ordinal + 1))
    receipt_path = run_dir / "receipt.json"
    assert receipt_path.exists()
    assert json.loads(receipt_path.read_bytes())["transport_gate_proven"] is False


@_DARWIN_FORK
def test_fake_seven_transport_v3_r_receipt_failure_does_not_erase_w_proof(
        monkeypatch, tmp_path):
    def no_receipt(*_args, **_kwargs):
        raise RuntimeError(CANARY)

    monkeypatch.setattr(live, "_seven_write_receipt", no_receipt)
    binding, observer, fake_http = _seven_fake_inputs(monkeypatch, tmp_path)
    marker_dir = tmp_path / "v3-r-fail-markers"
    marker_dir.mkdir()
    _v3_socket_sentinels(monkeypatch)
    run_dir = tmp_path / "seven-transport-v3-r-fail"
    result = live._supervise_fake_seven_once(
        run_dir=run_dir, binding_template=binding,
        observe_identity=observer, fake_http=None,
        fake_opener_factory=_v3_fake_factory(fake_http, marker_dir),
        port_observe=_v3_port_observer, work_seconds=2.0)
    assert len(list(marker_dir.glob("call-*.json"))) == 7
    assert result["schema"] == "fake_seven_process_result_v3"
    assert result["transport_gate_proven"] is True
    assert result["status"] != "fake_seven_process_pass"
    assert result["receipt_durable_proven"] is False
    assert result["full_gate_pass"] is False
    assert result["b_send_authorized"] is False
    assert CANARY not in json.dumps(result)
    assert not (run_dir / "receipt.json").exists()


@_DARWIN_FORK
@pytest.mark.parametrize("with_ports,schema", [
    (False, "fake_seven_process_result_v1"),
    (True, "fake_seven_process_result_v2"),
])
def test_fake_seven_transport_v3_opt_in_preserves_old_callback_paths(
        monkeypatch, tmp_path, with_ports, schema):
    binding, observer, fake_http = _seven_fake_inputs(monkeypatch, tmp_path)
    result = live._supervise_fake_seven_once(
        run_dir=tmp_path / "legacy-callback", binding_template=binding,
        observe_identity=observer, fake_http=fake_http,
        port_observe=_v3_port_observer if with_ports else None,
        work_seconds=2.0)
    assert result["schema"] == schema
    assert result["status"] == "fake_seven_process_pass"
    assert "transport_gate_proven" not in result
    assert "prehash_gate_proven" not in result
    receipt = json.loads((tmp_path / "legacy-callback" / "receipt.json")
                         .read_bytes())
    assert "prehash_gate_proven" not in receipt
    control = {**receipt, "status": "fake_seven_process_unproven",
               "failure_code": "initial_unavailable"}
    assert live._seven_receipt_valid(control, binding["run_id"])
    for code in ("pre_stage_unavailable", "pre_stage_mismatch",
                 "cleanup_review_required"):
        assert not live._seven_receipt_valid(
            {**control, "failure_code": code}, binding["run_id"])


@pytest.mark.parametrize("variant", ["missing_ports", "dual_transport"])
def test_fake_seven_transport_v3_rejects_invalid_opt_in_before_work(
        monkeypatch, tmp_path, variant):
    binding, observer, fake_http = _seven_fake_inputs(monkeypatch, tmp_path)
    marker_dir = tmp_path / "v3-config-markers"
    marker_dir.mkdir()
    _v3_socket_sentinels(monkeypatch)
    run_dir = tmp_path / f"seven-transport-v3-invalid-{variant}"
    with pytest.raises(live.LiveOperatorError,
                       match="^fake_seven_configuration_invalid$"):
        live._supervise_fake_seven_once(
            run_dir=run_dir, binding_template=binding,
            observe_identity=observer,
            fake_http=fake_http if variant == "dual_transport" else None,
            fake_opener_factory=_v3_fake_factory(fake_http, marker_dir),
            port_observe=_v3_port_observer if variant == "dual_transport"
            else None)
    assert not run_dir.exists()
    assert not list(marker_dir.iterdir())


def test_fake_seven_transport_v3_exact_response_and_request_size_bounds(
        monkeypatch):
    """W's fake seam includes the boundary and refuses oversize pre-open."""
    _v3_socket_sentinels(monkeypatch)
    calls = []

    def factory(proxy_handler, no_redirect_handler):
        assert proxy_handler.proxies == {}

        class FakeOpener:
            handlers = [no_redirect_handler]

            def open(self, request, timeout=None):
                calls.append((request.full_url, timeout))
                return _V3FakeResponse(
                    b"x" * live.RESPONSE_LIMIT, request.full_url,
                    chunk_size=65536, first_chunk_size=7)

        return FakeOpener()

    spec = _grant_fields(1)
    spec["expires_at"] = time.monotonic() + 3.0
    grant = {**spec, "nonce": "0" * 32}
    url = f"http://127.0.0.1:{spec['port']}{spec['path']}"
    answer = live._seven_v3_exchange(
        factory, method=spec["method"], url=url, payload_raw=None,
        remaining=2.0, grant=grant, spec=spec,
        work_deadline=time.monotonic() + 3.0)
    assert len(answer["body"]) == live.RESPONSE_LIMIT
    assert calls and calls[0][0] == url

    big = b"x" * (live.REQUEST_LIMIT + 1)
    spec = _grant_fields(3)
    spec["expires_at"] = time.monotonic() + 3.0
    spec["payload_sha256"] = hashlib.sha256(big).hexdigest()
    grant = {**spec, "nonce": "1" * 32}
    count_before = len(calls)
    with pytest.raises(live.LiveOperatorError,
                       match="^fake_seven_transport_gate_invalid$"):
        live._seven_v3_exchange(
            factory, method=spec["method"],
            url=f"http://127.0.0.1:{spec['port']}{spec['path']}",
            payload_raw=big, remaining=2.0, grant=grant, spec=spec,
            work_deadline=time.monotonic() + 3.0)
    assert len(calls) == count_before


@_DARWIN_FORK
def test_fake_seven_listener_v5_proves_owned_listen_before_w_go(
        monkeypatch, tmp_path):
    """V5 is process-backed admission, not another ready=True callback."""
    binding, observer, fake_http, port_observe, port = _v5_fake_inputs(
        monkeypatch, tmp_path)
    # A synthetic port is selected without opening a second socket. H is
    # the only process allowed to bind/listen in this fake-only contract.

    marker_dir = tmp_path / "v5-fake-opener-markers"
    marker_dir.mkdir()
    _v5_socket_sentinels(monkeypatch, port)
    # The result's 270 cumulative endpoints are not an open-FD peak.
    # Record the actual P/O/H measurements made by the frozen V5 barriers.
    fd_samples_path = tmp_path / "v5-fd-samples.jsonl"
    parent_pid = os.getpid()
    role_pids = {"P": parent_pid}
    original_fd_measure = live._seven_v5_fd_measure
    original_receive = live._seven_receive

    def measured_fd_barrier():
        count, maximum = original_fd_measure()
        row = _canonical({"pid": os.getpid(), "count": count,
                          "max_fd": maximum}) + b"\n"
        fd = os.open(fd_samples_path, os.O_WRONLY | os.O_APPEND | os.O_CREAT,
                     0o600)
        try:
            assert os.write(fd, row) == len(row)
        finally:
            os.close(fd)
        return count, maximum

    def record_child_witness(fd, deadline, **validation):
        value = original_receive(fd, deadline, **validation)
        expected = validation.get("expected")
        if (validation.get("phase") == "initial" and value is not None
                and expected in ({"role": "O"}, {"role": "H"})):
            role_pids[expected["role"]] = value["witness"]["pid"]
        return value

    monkeypatch.setattr(live, "_seven_v5_fd_measure", measured_fd_barrier)
    monkeypatch.setattr(live, "_seven_receive", record_child_witness)
    run_dir = tmp_path / "seven-synthetic-listener-v5"
    result = live._supervise_fake_seven_once(
        run_dir=run_dir, binding_template=binding,
        observe_identity=observer, fake_http=None,
        fake_opener_factory=_v3_fake_factory(
            fake_http, marker_dir, daemon_port=port),
        port_observe=port_observe, fake_prehash=True,
        fake_listener=True, work_seconds=2.0)

    assert result["schema"] == "fake_seven_process_result_v5", result
    assert result["status"] == "fake_seven_process_pass", result
    assert result["fd_endpoints_reserved"] == 270
    assert set(role_pids) == {"P", "O", "H"}
    samples = [json.loads(line) for line in fd_samples_path.read_bytes().splitlines()]
    assert stat.S_IMODE(fd_samples_path.stat().st_mode) == 0o600
    soft_limit, _ = live.resource.getrlimit(live.resource.RLIMIT_NOFILE)
    assert soft_limit == 256
    for role, pid in role_pids.items():
        rows = [row for row in samples if row["pid"] == pid]
        assert rows, (role, samples)
        assert max(row["count"] for row in rows) < soft_limit
        assert max(row["max_fd"] for row in rows) < soft_limit
    assert result["synthetic_listener_gate_proven"] is True
    assert result["continuous_listener_proven"] is False
    assert result["daemon_stage_failure_code"] == "none"
    assert result["listener_observation_sha256"] is not None
    assert result["h_reaped"] and result["h_stop"] == "normal_exit"
    assert result["s_h_reaped"] and result["s_h_normal_exit"]
    assert result["prehash_gate_proven"] and result["port_gate_proven"]
    assert result["transport_gate_proven"]
    assert result["http_calls"] == 7 and result["identity_checks"] == 6
    assert result["receipt_durable_proven"] is True
    assert result["physical_stop_unproven"] is True
    assert result["full_gate_pass"] is False
    assert result["b_send_authorized"] is False
    assert sorted(path.name for path in marker_dir.iterdir()) == [
        f"call-{n}.json" for n in range(1, 8)]
    receipt_path = run_dir / "receipt.json"
    receipt = json.loads(receipt_path.read_bytes())
    assert stat.S_IMODE(receipt_path.stat().st_mode) == 0o600
    assert receipt["schema"] == "fake_seven_process_receipt_v5"
    assert receipt["synthetic_listener_gate_proven"] is True
    assert receipt["listener_observation_sha256"] == result[
        "listener_observation_sha256"]


def _v5_negative_case(monkeypatch, tmp_path, *, port=None):
    binding, observer, fake_http, port_observe, port = _v5_fake_inputs(
        monkeypatch, tmp_path, port=port)
    marker_dir = tmp_path / "v5-request-markers"
    marker_dir.mkdir()
    run_dir = tmp_path / "v5-negative-run"
    w_go_sends = []
    original_send = live._seven_send

    def record_w_go(fd, value, deadline, **validation):
        if validation.get("phase") == "w_go":
            w_go_sends.append(value)
        return original_send(fd, value, deadline, **validation)

    monkeypatch.setattr(live, "_seven_send", record_w_go)
    kwargs = {
        "run_dir": run_dir, "binding_template": binding,
        "observe_identity": observer, "fake_http": None,
        "fake_opener_factory": _v3_fake_factory(
            fake_http, marker_dir, daemon_port=port),
        "port_observe": port_observe, "fake_prehash": True,
        "fake_listener": True, "work_seconds": 0.6,
        "preparation_seconds": 0.5, "cleanup_seconds": 0.5,
    }
    return kwargs, marker_dir, w_go_sends, port


def _v5_socket_sentinels(monkeypatch, port):
    """Permit H's one exact LISTEN, never an accept/connect or real opener."""
    original_bind = socket.socket.bind
    original_listen = socket.socket.listen
    original_setsockopt = socket.socket.setsockopt

    def checked_bind(sock, address):
        assert sock.family == socket.AF_INET
        assert sock.type == socket.SOCK_STREAM
        assert address == ("127.0.0.1", port)
        return original_bind(sock, address)

    def checked_listen(sock, backlog):
        assert sock.getsockname() == ("127.0.0.1", port)
        return original_listen(sock, backlog)

    def checked_setsockopt(sock, level, option, value):
        assert not (level == socket.SOL_SOCKET and option in (
            socket.SO_REUSEADDR, getattr(socket, "SO_REUSEPORT", -1)))
        return original_setsockopt(sock, level, option, value)

    def forbidden(*_args, **_kwargs):
        raise AssertionError("v5 fake listener attempted accept/connect/HTTP")

    monkeypatch.setattr(socket.socket, "bind", checked_bind)
    monkeypatch.setattr(socket.socket, "listen", checked_listen)
    monkeypatch.setattr(socket.socket, "setsockopt", checked_setsockopt)
    monkeypatch.setattr(socket.socket, "accept", forbidden)
    monkeypatch.setattr(socket.socket, "connect", forbidden)
    monkeypatch.setattr(socket.socket, "connect_ex", forbidden)
    monkeypatch.setattr(socket, "create_connection", forbidden)
    monkeypatch.setattr(urllib.request, "build_opener", forbidden)
    monkeypatch.setattr(urllib.request, "urlopen", forbidden)
    monkeypatch.setattr(urllib.request.OpenerDirector, "open", forbidden)


def _assert_v5_pre_w_failure(result, run_dir, marker_dir, w_go_sends,
                             stage_code):
    assert result["schema"] == "fake_seven_process_result_v5", result
    assert result["status"] == "fake_seven_process_unproven", result
    assert result["daemon_stage_failure_code"] == stage_code, result
    assert result["synthetic_listener_gate_proven"] is False
    assert result["listener_observation_sha256"] is None
    assert result["continuous_listener_proven"] is False
    assert result["zero_ack_received"] is True
    assert result["receipt_preflight_accepted"] is True
    assert result["granted"] == 0
    assert result["transport_policy_calls"] == 0
    assert result["port_gate_proven"] is False
    assert result["runner_port_vacant_after"] == "unknown"
    assert result["physical_stop_unproven"] is True
    assert result["full_gate_pass"] is False
    assert result["b_send_authorized"] is False
    assert not w_go_sends
    assert not list(marker_dir.iterdir())
    journal_path, disk = _read_only_journal(run_dir)
    assert disk["operations"] == []
    assert disk["reserved"] == disk["granted"] == 0
    assert CANARY.encode() not in journal_path.read_bytes()
    receipt_path = run_dir / "receipt.json"
    assert result["receipt_durable_proven"] is True, result
    assert stat.S_IMODE(receipt_path.stat().st_mode) == 0o600
    receipt = json.loads(receipt_path.read_bytes())
    assert receipt["schema"] == "fake_seven_process_receipt_v5"
    assert receipt["snapshot_phase"] == (
        "after_d_w_h_o_cleanup_attempt_before_r_final_reap")
    assert receipt["daemon_stage_failure_code"] == stage_code
    assert receipt["synthetic_listener_gate_proven"] is False
    assert receipt["listener_observation_sha256"] is None
    assert CANARY.encode() not in receipt_path.read_bytes()
    return receipt


@pytest.mark.parametrize("variant", [
    "wrong_type", "missing_prehash", "missing_factory", "missing_ports",
    "legacy_http", "hook_without_listener", "noncallable_hook",
])
def test_fake_seven_listener_v5_rejects_invalid_opt_in_before_journal_or_fork(
        monkeypatch, tmp_path, variant):
    binding, observer, fake_http = _seven_fake_inputs(monkeypatch, tmp_path)
    marker_dir = tmp_path / "v5-invalid-markers"
    marker_dir.mkdir()
    run_dir = tmp_path / f"v5-invalid-{variant}"
    kwargs = {
        "fake_listener": True, "fake_prehash": True, "fake_http": None,
        "fake_opener_factory": _v3_fake_factory(fake_http, marker_dir),
        "port_observe": _v3_port_observer,
    }
    if variant == "wrong_type":
        kwargs["fake_listener"] = 1
    elif variant == "missing_prehash":
        kwargs["fake_prehash"] = False
    elif variant == "missing_factory":
        kwargs["fake_opener_factory"] = None
    elif variant == "missing_ports":
        kwargs["port_observe"] = None
    elif variant == "legacy_http":
        kwargs["fake_http"] = fake_http
    elif variant == "hook_without_listener":
        kwargs["fake_listener"] = False
        kwargs["fake_listener_hook"] = lambda _phase: None
    else:
        kwargs["fake_listener_hook"] = object()
    with pytest.raises(live.LiveOperatorError,
                       match="^fake_seven_configuration_invalid$"):
        live._supervise_fake_seven_once(
            run_dir=run_dir, binding_template=binding,
            observe_identity=observer, **kwargs)
    assert not run_dir.exists()
    assert not list(marker_dir.iterdir())


@_DARWIN_FORK
@pytest.mark.parametrize("version", (1, 2, 3, 4))
def test_fake_seven_listener_v5_does_not_widen_v1_through_v4_receipts(
        monkeypatch, tmp_path, version):
    binding, observer, fake_http = _seven_fake_inputs(monkeypatch, tmp_path)
    marker_dir = tmp_path / "v5-legacy-markers"
    marker_dir.mkdir()
    run_dir = tmp_path / f"v{version}-unchanged"
    kwargs = {"fake_http": fake_http}
    if version >= 2:
        kwargs["port_observe"] = _v3_port_observer
    if version >= 3:
        kwargs["fake_http"] = None
        kwargs["fake_opener_factory"] = _v3_fake_factory(
            fake_http, marker_dir)
    if version >= 4:
        kwargs["fake_prehash"] = True
    result = live._supervise_fake_seven_once(
        run_dir=run_dir, binding_template=binding,
        observe_identity=observer, **kwargs)
    receipt = json.loads((run_dir / "receipt.json").read_bytes())
    assert result["schema"] == f"fake_seven_process_result_v{version}"
    assert receipt["schema"] == f"fake_seven_process_receipt_v{version}"
    for key in ("synthetic_listener_gate_proven",
                "listener_observation_sha256", "daemon_stage_failure_code",
                "h_reaped", "s_h_normal_exit"):
        assert key not in result and key not in receipt
    assert live._seven_receipt_valid(receipt, binding["run_id"])
    assert not live._seven_receipt_valid(
        {**receipt, "synthetic_listener_gate_proven": False},
        binding["run_id"])
    assert not live._seven_receipt_valid(
        {**receipt, "failure_code": "h_ready_unavailable"},
        binding["run_id"])


@_DARWIN_FORK
def test_fake_seven_listener_v5_phase2_fd_failure_keeps_zero_and_r_receipt(
        monkeypatch, tmp_path):
    kwargs, marker_dir, w_go_sends, port = _v5_negative_case(
        monkeypatch, tmp_path)
    _v5_socket_sentinels(monkeypatch, port)

    def no_phase2_fds(*_args, **_kwargs):
        _, disk = _read_only_journal(kwargs["run_dir"])
        assert disk["reserved"] == disk["granted"] == 0
        raise OSError(CANARY)

    monkeypatch.setattr(live, "_seven_v5_pipe_layout", no_phase2_fds)
    result = live._supervise_fake_seven_once(**kwargs)
    receipt = _assert_v5_pre_w_failure(
        result, kwargs["run_dir"], marker_dir, w_go_sends,
        "phase2_fd_unavailable")
    assert result["failure_code"] == "phase2_fd_unavailable"
    assert receipt["failure_code"] == "phase2_fd_unavailable"
    assert result["pre_stage_failure_code"] == "none"
    assert receipt["pre_stage_failure_code"] == "none"
    for role in ("d", "w"):
        assert result[f"{role}_stop"] in (
            "witnessed_term", "witnessed_kill"), result
        assert receipt[f"{role}_stop"] == result[f"{role}_stop"]
    assert result["fd_endpoints_reserved"] == 246


@_DARWIN_FORK
def test_fake_seven_listener_v5_bind_collision_is_not_readiness(
        monkeypatch, tmp_path):
    # A deliberately competing local LISTEN is the bind-collision negative
    # control; it is never accepted, connected to, or used as HTTP.
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as competitor:
        competitor.bind(("127.0.0.1", 0))
        port = competitor.getsockname()[1]
        competitor.listen(1)
        kwargs, marker_dir, w_go_sends, _ = _v5_negative_case(
            monkeypatch, tmp_path, port=port)
        _v5_socket_sentinels(monkeypatch, port)
        result = live._supervise_fake_seven_once(**kwargs)
    _assert_v5_pre_w_failure(
        result, kwargs["run_dir"], marker_dir, w_go_sends,
        "h_ready_unavailable")


@_DARWIN_FORK
@pytest.mark.parametrize("variant,stage", [
    ("h_initial_missing", "h_initial_unavailable"),
    ("s_h_initial_missing", "s_h_initial_unavailable"),
    ("h_ready_missing", "h_ready_unavailable"),
    ("h_ready_wrong_port", "h_ready_mismatch"),
    ("o_ready_wrong_sha", "o_ready_mismatch"),
])
def test_fake_seven_listener_v5_initial_and_proof_faults_never_release_w(
        monkeypatch, tmp_path, variant, stage):
    kwargs, marker_dir, w_go_sends, port = _v5_negative_case(
        monkeypatch, tmp_path)
    _v5_socket_sentinels(monkeypatch, port)
    original_child_send = live._seven_child_send
    original_signal_child = live._split_signal_child

    def damaged_send(pipes, name, run_id, phase, seq, own, deadline,
                     **extra):
        if variant == "h_initial_missing" and name == "h_initial":
            return False
        if variant == "h_ready_missing" and name == "h_ready":
            return False
        if variant == "h_ready_wrong_port" and name == "h_ready":
            extra["daemon_port"] = port + 1
        if variant == "o_ready_wrong_sha" and name == "o_ready_proof":
            extra["listener_observation_sha256"] = "0" * 64
        return original_child_send(pipes, name, run_id, phase, seq, own,
                                   deadline, **extra)

    def damaged_signal_child(*args, **signal_kwargs):
        if (variant == "s_h_initial_missing"
                and signal_kwargs.get("target_role") == "H"):
            return 125
        return original_signal_child(*args, **signal_kwargs)

    monkeypatch.setattr(live, "_seven_child_send", damaged_send)
    monkeypatch.setattr(live, "_split_signal_child", damaged_signal_child)
    result = live._supervise_fake_seven_once(**kwargs)
    _assert_v5_pre_w_failure(
        result, kwargs["run_dir"], marker_dir, w_go_sends, stage)
    if variant in ("h_initial_missing", "s_h_initial_missing"):
        assert result["h_reaped"] is True


@_DARWIN_FORK
@pytest.mark.parametrize("phase,action", [
    ("before_bind", "block"), ("before_bind", "crash"),
    ("after_listen", "block"), ("after_listen", "crash"),
])
def test_fake_seven_listener_v5_blocked_or_crashed_h_before_ready(
        monkeypatch, tmp_path, phase, action):
    kwargs, marker_dir, w_go_sends, port = _v5_negative_case(
        monkeypatch, tmp_path)
    _v5_socket_sentinels(monkeypatch, port)

    def stall_or_crash(current_phase):
        if current_phase == phase:
            if action == "crash":
                os._exit(77)
            time.sleep(2.0)

    started = time.monotonic()
    result = live._supervise_fake_seven_once(
        **kwargs, fake_listener_hook=stall_or_crash)
    assert time.monotonic() - started < 3.5
    _assert_v5_pre_w_failure(
        result, kwargs["run_dir"], marker_dir, w_go_sends,
        "h_ready_unavailable")


@_DARWIN_FORK
def test_fake_seven_listener_v5_h_ready_frame_without_eof_is_not_proof(
        monkeypatch, tmp_path):
    kwargs, marker_dir, w_go_sends, port = _v5_negative_case(
        monkeypatch, tmp_path)
    _v5_socket_sentinels(monkeypatch, port)
    original_child_send = live._seven_child_send

    def keep_h_ready_writer(pipes, name, run_id, phase, seq, own,
                            deadline, **extra):
        if name == "h_ready":
            fd = pipes[name][1]
            v5 = extra.pop("v5", False)
            frame = live._seven_frame(run_id, phase, seq, own, **extra)
            # A complete canonical frame is still not proof without EOF.
            return live._seven_send(fd, frame, deadline, run_id=run_id,
                                    phase=phase, seq=seq, witness=own,
                                    v5=v5)
        return original_child_send(pipes, name, run_id, phase, seq, own,
                                   deadline, **extra)

    monkeypatch.setattr(live, "_seven_child_send", keep_h_ready_writer)
    result = live._supervise_fake_seven_once(**kwargs)
    _assert_v5_pre_w_failure(
        result, kwargs["run_dir"], marker_dir, w_go_sends,
        "h_ready_unavailable")


@_DARWIN_FORK
@pytest.mark.parametrize("variant", [
    "wrong_owner", "wrong_address", "wrong_port", "wrong_state",
    "access_denied",
])
def test_fake_seven_listener_v5_o_requires_actual_h_owned_tcp4_listen(
        monkeypatch, tmp_path, variant):
    kwargs, marker_dir, w_go_sends, port = _v5_negative_case(
        monkeypatch, tmp_path)
    _v5_socket_sentinels(monkeypatch, port)
    actual_psutil = live._seven_v5_psutil()

    class ProcessProxy:
        def __init__(self, pid):
            self._real = actual_psutil.Process(pid)
            self.pid = pid + 1 if variant == "wrong_owner" else pid

        def net_connections(self, *, kind):
            assert kind == "tcp4"
            if variant == "access_denied":
                raise actual_psutil.AccessDenied(pid=self.pid)
            rows = self._real.net_connections(kind=kind)
            altered = []
            for row in rows:
                if row.status != "LISTEN":
                    altered.append(row)
                    continue
                if variant == "wrong_address":
                    address = type(row.laddr)("0.0.0.0", port)
                    altered.append(row._replace(laddr=address))
                elif variant == "wrong_port":
                    address = type(row.laddr)("127.0.0.1", port + 1)
                    altered.append(row._replace(laddr=address))
                elif variant == "wrong_state":
                    altered.append(row._replace(status="ESTABLISHED"))
                else:
                    altered.append(row)
            return altered

    class PsutilProxy:
        __version__ = actual_psutil.__version__
        AccessDenied = actual_psutil.AccessDenied

        @staticmethod
        def Process(pid):
            return ProcessProxy(pid)

    monkeypatch.setattr(live, "_seven_v5_psutil", lambda: PsutilProxy)
    result = live._supervise_fake_seven_once(**kwargs)
    _assert_v5_pre_w_failure(
        result, kwargs["run_dir"], marker_dir, w_go_sends,
        "o_ready_unavailable")


@_DARWIN_FORK
def test_fake_seven_listener_v5_r_death_at_admission_forbids_w_go(
        monkeypatch, tmp_path):
    kwargs, marker_dir, w_go_sends, port = _v5_negative_case(
        monkeypatch, tmp_path)
    _v5_socket_sentinels(monkeypatch, port)
    original_receive = live._seven_receive
    r_pid = None

    def kill_witnessed_r_at_o_proof(fd, deadline, **validation):
        nonlocal r_pid
        value = original_receive(fd, deadline, **validation)
        if (validation.get("phase") == "initial"
                and validation.get("expected") == {"role": "R"}
                and value is not None):
            r_pid = value["witness"]["pid"]
        if validation.get("phase") == "o_ready_proof" and value is not None:
            assert r_pid is not None
            os.kill(r_pid, signal.SIGKILL)
            # Yield to the already-spawned R, without consuming its waitpid.
            time.sleep(0.05)
        return value

    monkeypatch.setattr(live, "_seven_receive", kill_witnessed_r_at_o_proof)
    result = live._supervise_fake_seven_once(**kwargs)
    assert result["schema"] == "fake_seven_process_result_v5", result
    assert result["status"] == "fake_seven_process_unproven"
    assert result["receipt_durable_proven"] is False
    assert result["failure_code"] == "receipt_unavailable_review_required"
    assert not w_go_sends
    assert not list(marker_dir.iterdir())
    _, disk = _read_only_journal(kwargs["run_dir"])
    assert disk["reserved"] == disk["granted"] == 0
    assert not (kwargs["run_dir"] / "receipt.json").exists()
    assert result["full_gate_pass"] is False
    assert result["b_send_authorized"] is False


@_DARWIN_FORK
def test_fake_seven_listener_v5_midrun_h_loss_forbids_later_grants(
        monkeypatch, tmp_path):
    kwargs, marker_dir, w_go_sends, port = _v5_negative_case(
        monkeypatch, tmp_path)
    _v5_socket_sentinels(monkeypatch, port)
    kwargs["work_seconds"] = 2.0
    original_receive = live._seven_receive
    h_pid = None

    def kill_h_after_first_fake_result(fd, deadline, **validation):
        nonlocal h_pid
        value = original_receive(fd, deadline, **validation)
        if (validation.get("phase") == "initial"
                and validation.get("expected") == {"role": "H"}
                and value is not None):
            h_pid = value["witness"]["pid"]
        if (validation.get("phase") == "result_entry"
                and validation.get("seq") == 1 and value is not None):
            assert h_pid is not None
            os.kill(h_pid, signal.SIGKILL)
            time.sleep(0.05)
        return value

    monkeypatch.setattr(live, "_seven_receive", kill_h_after_first_fake_result)
    result = live._supervise_fake_seven_once(**kwargs)
    assert result["schema"] == "fake_seven_process_result_v5", result
    assert result["synthetic_listener_gate_proven"] is True, result
    assert result["listener_observation_sha256"] is not None
    assert result["daemon_stage_failure_code"] == "h_lost_after_ready"
    assert result["status"] == "fake_seven_process_unproven"
    assert len(w_go_sends) == 1
    assert (marker_dir / "call-1.json").exists()
    assert not (marker_dir / "call-2.json").exists()
    _, disk = _read_only_journal(kwargs["run_dir"])
    assert disk["reserved"] == disk["granted"] == 1
    assert disk["operations"][0]["on_wire"] == "yes"
    receipt_path = kwargs["run_dir"] / "receipt.json"
    assert stat.S_IMODE(receipt_path.stat().st_mode) == 0o600
    receipt = json.loads(receipt_path.read_bytes())
    assert receipt["daemon_stage_failure_code"] == "h_lost_after_ready"
    assert receipt["synthetic_listener_gate_proven"] is True
    assert receipt["listener_observation_sha256"] == result[
        "listener_observation_sha256"]
    assert result["full_gate_pass"] is False
    assert result["b_send_authorized"] is False


@_DARWIN_FORK
def test_fake_seven_listener_v5_h_cleanup_identity_stall_keeps_first_error(
        monkeypatch, tmp_path):
    kwargs, marker_dir, w_go_sends, port = _v5_negative_case(
        monkeypatch, tmp_path)
    _v5_socket_sentinels(monkeypatch, port)
    h_pid_file = tmp_path / "synthetic-h-pid"

    def blocked_h(phase):
        if phase == "before_bind":
            h_pid_file.write_text(str(os.getpid()))
            time.sleep(2.0)

    def blocked_fresh_witness(pid):
        if h_pid_file.exists() and str(pid) == h_pid_file.read_text():
            time.sleep(2.0)
        return live._fake_os_witness(pid)

    started = time.monotonic()
    result = live._supervise_fake_seven_once(
        **kwargs, fake_listener_hook=blocked_h,
        cleanup_observe=blocked_fresh_witness)
    assert time.monotonic() - started < 4.0
    receipt = _assert_v5_pre_w_failure(
        result, kwargs["run_dir"], marker_dir, w_go_sends,
        "h_ready_unavailable")
    assert result["failure_code"] == "cleanup_review_required"
    assert result["h_stop"] == "unproven"
    assert receipt["failure_code"] == "cleanup_review_required"
    assert receipt["h_stop"] == "unproven"


@_DARWIN_FORK
def test_fake_seven_listener_v5_r_failure_dominates_after_h_admission(
        monkeypatch, tmp_path):
    kwargs, marker_dir, _, port = _v5_negative_case(monkeypatch, tmp_path)
    _v5_socket_sentinels(monkeypatch, port)
    kwargs["work_seconds"] = 2.0

    def unavailable_receipt(*_args, **_kwargs):
        raise RuntimeError(CANARY)

    monkeypatch.setattr(live, "_seven_write_receipt", unavailable_receipt)
    result = live._supervise_fake_seven_once(**kwargs)
    assert result["schema"] == "fake_seven_process_result_v5", result
    assert result["synthetic_listener_gate_proven"] is True, result
    assert result["listener_observation_sha256"] is not None
    assert result["continuous_listener_proven"] is False
    assert result["daemon_stage_failure_code"] == "none"
    assert result["h_reaped"] and result["s_h_reaped"]
    assert result["status"] == "fake_seven_process_unproven"
    assert result["failure_code"] == "receipt_unavailable_review_required"
    assert result["receipt_durable_proven"] is False
    assert result["full_gate_pass"] is False
    assert result["b_send_authorized"] is False
    assert len(list(marker_dir.glob("call-*.json"))) == 7
    assert not (kwargs["run_dir"] / "receipt.json").exists()
    assert CANARY not in json.dumps(result)


@_DARWIN_FORK
@pytest.mark.parametrize("variant,pre_stage", [
    ("wrong_sha", "pre_stage_mismatch"),
    ("wrong_port", "pre_stage_mismatch"),
    ("port_occupied", "port_pre_not_vacant"),
])
def test_fake_seven_listener_v5_v4_prehash_or_port_failure_never_starts_h(
        monkeypatch, tmp_path, variant, pre_stage):
    kwargs, marker_dir, w_go_sends, port = _v5_negative_case(
        monkeypatch, tmp_path)
    _v5_socket_sentinels(monkeypatch, port)
    original_send = live._seven_child_send

    def wrong_v4_preproof(pipes, name, run_id, phase, seq, own, deadline,
                          **extra):
        if name == "o_pre_proof" and phase == "o_pre_hash_port_proof":
            if variant == "wrong_sha":
                extra["prehash_sha256"] = "0" * 64
            elif variant == "wrong_port":
                extra["daemon_port"] += 1
            else:
                extra["daemon_vacant"] = False
        return original_send(pipes, name, run_id, phase, seq, own, deadline,
                             **extra)

    monkeypatch.setattr(live, "_seven_child_send", wrong_v4_preproof)
    result = live._supervise_fake_seven_once(**kwargs)
    receipt = _assert_v5_pre_w_failure(
        result, kwargs["run_dir"], marker_dir, w_go_sends, "not_started")
    assert result["pre_stage_failure_code"] == pre_stage
    assert result["failure_code"] == pre_stage
    assert result["h_reaped"] is False and result["s_h_reaped"] is False
    assert result["h_term"] == result["h_kill"] == "not_attempted"
    assert receipt["pre_stage_failure_code"] == pre_stage
    assert receipt["failure_code"] == pre_stage


@_DARWIN_FORK
def test_fake_seven_listener_v5_partial_phase2_allocation_closes_its_fds(
        monkeypatch, tmp_path):
    kwargs, marker_dir, w_go_sends, port = _v5_negative_case(
        monkeypatch, tmp_path)
    _v5_socket_sentinels(monkeypatch, port)
    original_layout = live._seven_v5_pipe_layout
    original_pipe = os.pipe
    acquired = []
    closed_after_failure = []

    def fail_sixth_late_pipe():
        calls = 0

        def partial_pipe():
            nonlocal calls
            calls += 1
            if calls == 6:
                raise OSError(CANARY)
            pair = original_pipe()
            acquired.extend(pair)
            return pair

        live.os.pipe = partial_pipe
        try:
            return original_layout()
        except live.LiveOperatorError:
            closed_after_failure.extend(
                _fd_is_closed(fd) for fd in acquired)
            raise
        finally:
            live.os.pipe = original_pipe

    def _fd_is_closed(fd):
        try:
            os.fstat(fd)
        except OSError:
            return True
        return False

    monkeypatch.setattr(live, "_seven_v5_pipe_layout", fail_sixth_late_pipe)
    result = live._supervise_fake_seven_once(**kwargs)
    receipt = _assert_v5_pre_w_failure(
        result, kwargs["run_dir"], marker_dir, w_go_sends,
        "phase2_fd_unavailable")
    assert len(acquired) == 10
    assert closed_after_failure == [True] * 10
    assert result["fd_endpoints_reserved"] == 246
    assert result["pre_stage_failure_code"] == "none"
    assert result["failure_code"] == "phase2_fd_unavailable"
    assert receipt["pre_stage_failure_code"] == "none"
    assert receipt["failure_code"] == "phase2_fd_unavailable"
    for role in ("d", "w"):
        assert result[f"{role}_stop"] in (
            "witnessed_term", "witnessed_kill"), result


@_DARWIN_FORK
@pytest.mark.parametrize("edge,variant,stage", [
    ("o_ready_proof", "no_eof", "o_ready_unavailable"),
    ("o_ready_proof", "duplicate", "o_ready_unavailable"),
    ("o_ready_proof", "trailing", "o_ready_unavailable"),
    ("h_ready", "duplicate", "h_ready_unavailable"),
    ("h_ready", "trailing", "h_ready_unavailable"),
])
def test_fake_seven_listener_v5_rejects_extra_or_unterminated_ready_wire(
        monkeypatch, tmp_path, edge, variant, stage):
    kwargs, marker_dir, w_go_sends, port = _v5_negative_case(
        monkeypatch, tmp_path)
    _v5_socket_sentinels(monkeypatch, port)
    original_send = live._seven_child_send

    def damaged_ready_wire(pipes, name, run_id, phase, seq, own, deadline,
                           **extra):
        if name != edge:
            return original_send(pipes, name, run_id, phase, seq, own,
                                 deadline, **extra)
        fd = pipes[name][1]
        assert extra.pop("v5") is True
        frame_value = live._seven_frame(run_id, phase, seq, own, **extra)
        if variant == "no_eof":
            # A valid canonical frame with its writer still open is not a
            # completed proof, even though the child remains alive.
            return live._seven_send(
                fd, frame_value, deadline, run_id=run_id, phase=phase,
                seq=seq, witness=own, v5=True)
        frame = live.encode_frame(frame_value)
        raw = frame + (frame if variant == "duplicate" else b"x")
        try:
            assert os.write(fd, raw) == len(raw)
            return True
        finally:
            os.close(fd)

    monkeypatch.setattr(live, "_seven_child_send", damaged_ready_wire)
    result = live._supervise_fake_seven_once(**kwargs)
    _assert_v5_pre_w_failure(
        result, kwargs["run_dir"], marker_dir, w_go_sends, stage)


@_DARWIN_FORK
@pytest.mark.parametrize("field,bracket", [
    ("raw_generation", 1), ("raw_generation", 2),
    ("pgid", 1), ("pgid", 2),
])
def test_fake_seven_listener_v5_o_rejects_identity_drift_on_both_sides(
        monkeypatch, tmp_path, field, bracket):
    kwargs, marker_dir, w_go_sends, port = _v5_negative_case(
        monkeypatch, tmp_path)
    _v5_socket_sentinels(monkeypatch, port)
    original_observe = live._seven_v5_observe_listener
    original_witness = live._fake_os_witness

    def drift_during_o_bracket(h_witness, daemon_port):
        calls = 0

        def drifted_witness(pid):
            nonlocal calls
            calls += 1
            value = original_witness(pid)
            if calls == bracket:
                value = deepcopy(value)
                if field == "pgid":
                    value["pgid"] += 1
                else:
                    value["raw_generation"][-1] += 1
            return value

        live._fake_os_witness = drifted_witness
        try:
            return original_observe(h_witness, daemon_port)
        finally:
            live._fake_os_witness = original_witness

    monkeypatch.setattr(live, "_seven_v5_observe_listener",
                        drift_during_o_bracket)
    result = live._supervise_fake_seven_once(**kwargs)
    _assert_v5_pre_w_failure(
        result, kwargs["run_dir"], marker_dir, w_go_sends,
        "o_ready_unavailable")


@_DARWIN_FORK
def test_fake_seven_listener_v5_after_ready_crash_before_liveness_check(
        monkeypatch, tmp_path):
    kwargs, marker_dir, w_go_sends, port = _v5_negative_case(
        monkeypatch, tmp_path)
    _v5_socket_sentinels(monkeypatch, port)
    release = tmp_path / "release-after-o-proof"
    original_receive = live._seven_receive

    def crash_after_ready(phase):
        if phase == "after_ready":
            # Keep H's listener alive for O's independent OS proof, then
            # force a real exit before P's final nonblocking liveness check.
            while not release.exists():
                time.sleep(0.001)
            os._exit(77)

    def release_at_complete_o_proof(fd, deadline, **validation):
        value = original_receive(fd, deadline, **validation)
        if validation.get("phase") == "o_ready_proof" and value is not None:
            release.touch()
            time.sleep(0.05)
        return value

    monkeypatch.setattr(live, "_seven_receive", release_at_complete_o_proof)
    result = live._supervise_fake_seven_once(
        **kwargs, fake_listener_hook=crash_after_ready)
    _assert_v5_pre_w_failure(
        result, kwargs["run_dir"], marker_dir, w_go_sends,
        "h_ready_unavailable")
    assert release.exists()
    assert result["h_reaped"] is True


@_DARWIN_FORK
def test_fake_seven_listener_v5_after_ready_block_is_not_continuity(
        monkeypatch, tmp_path):
    kwargs, marker_dir, w_go_sends, port = _v5_negative_case(
        monkeypatch, tmp_path)
    _v5_socket_sentinels(monkeypatch, port)
    kwargs["work_seconds"] = 2.0

    def block_after_ready(phase):
        if phase == "after_ready":
            time.sleep(10.0)

    result = live._supervise_fake_seven_once(
        **kwargs, fake_listener_hook=block_after_ready)
    assert result["schema"] == "fake_seven_process_result_v5", result
    assert result["synthetic_listener_gate_proven"] is True, result
    assert result["listener_observation_sha256"] is not None
    assert result["continuous_listener_proven"] is False
    assert len(w_go_sends) == 1
    assert result["status"] == "fake_seven_process_unproven", result
    assert result["daemon_stage_failure_code"] == "h_stop_unavailable"
    assert result["h_stop"] in ("witnessed_term", "witnessed_kill")
    assert result["receipt_durable_proven"] is True
    assert len(list(marker_dir.glob("call-*.json"))) == 7
    receipt = json.loads((kwargs["run_dir"] / "receipt.json").read_bytes())
    assert receipt["daemon_stage_failure_code"] == "h_stop_unavailable"
    assert receipt["continuous_listener_proven"] is False
    assert result["full_gate_pass"] is False
    assert result["b_send_authorized"] is False


@_DARWIN_FORK
@pytest.mark.parametrize("role", ["H", "O", "S_H"])
def test_fake_seven_listener_v5_h_o_s_h_printed_canary_is_isolated(
        monkeypatch, tmp_path, capsys, role):
    kwargs, marker_dir, _, port = _v5_negative_case(monkeypatch, tmp_path)
    _v5_socket_sentinels(monkeypatch, port)
    kwargs["work_seconds"] = 2.0
    original_observe = live._seven_v5_observe_listener
    original_signal_child = live._split_signal_child

    def noisy_h(phase):
        if role == "H" and phase == "before_bind":
            print(CANARY, flush=True)
            print(CANARY, file=sys.stderr, flush=True)

    def noisy_o(h_witness, daemon_port):
        if role == "O":
            print(CANARY, flush=True)
            print(CANARY, file=sys.stderr, flush=True)
        return original_observe(h_witness, daemon_port)

    def noisy_s_h(*args, **signal_kwargs):
        if role == "S_H" and signal_kwargs.get("target_role") == "H":
            initial_reader = signal_kwargs["initial_reader"]

            def noisy_initial(pid):
                print(CANARY, flush=True)
                print(CANARY, file=sys.stderr, flush=True)
                return initial_reader(pid)

            signal_kwargs["initial_reader"] = noisy_initial
        return original_signal_child(*args, **signal_kwargs)

    monkeypatch.setattr(live, "_seven_v5_observe_listener", noisy_o)
    monkeypatch.setattr(live, "_split_signal_child", noisy_s_h)
    result = live._supervise_fake_seven_once(
        **kwargs, fake_listener_hook=noisy_h)
    assert result["status"] == "fake_seven_process_pass", {
        key: result[key] for key in (
            "failure_code", "pre_stage_failure_code",
            "daemon_stage_failure_code", "fd_endpoints_reserved",
            "zero_ack_received", "receipt_preflight_accepted",
            "receipt_durable_proven", "h_stop", "o_stop")}
    assert len(list(marker_dir.glob("call-*.json"))) == 7
    journal_path, _ = _read_only_journal(kwargs["run_dir"])
    receipt_path = kwargs["run_dir"] / "receipt.json"
    assert CANARY.encode() not in journal_path.read_bytes()
    assert CANARY.encode() not in receipt_path.read_bytes()
    assert CANARY not in json.dumps(result)
    # capfd's extra OS descriptors would itself exceed this V5 256-FD
    # stress path; these hooks intentionally use Python print streams.
    captured = capsys.readouterr()
    assert CANARY not in captured.out + captured.err


@_DARWIN_FORK
@pytest.mark.parametrize("failure_fork", [7, 8])
def test_fake_seven_listener_v5_post_phase2_observer_fork_failure_is_not_fd(
        monkeypatch, tmp_path, failure_fork):
    kwargs, marker_dir, w_go_sends, port = _v5_negative_case(
        monkeypatch, tmp_path)
    _v5_socket_sentinels(monkeypatch, port)
    original_fork = os.fork
    calls = 0

    def fail_o_or_s_o_fork():
        nonlocal calls
        calls += 1
        if calls == failure_fork:
            raise OSError(CANARY)
        return original_fork()

    monkeypatch.setattr(live.os, "fork", fail_o_or_s_o_fork)
    result = live._supervise_fake_seven_once(**kwargs)
    receipt = _assert_v5_pre_w_failure(
        result, kwargs["run_dir"], marker_dir, w_go_sends,
        "not_started")
    assert calls == failure_fork
    assert result["fd_endpoints_reserved"] == 270
    assert result["pre_stage_failure_code"] == "pre_stage_unavailable"
    assert result["daemon_stage_failure_code"] == "not_started"
    assert result["failure_code"] != "phase2_fd_unavailable"
    assert receipt["daemon_stage_failure_code"] == "not_started"
    assert receipt["failure_code"] != "phase2_fd_unavailable"


@_DARWIN_FORK
def test_fake_seven_listener_v5_missing_waitable_h_at_admission_forbids_w_go(
        monkeypatch, tmp_path):
    kwargs, marker_dir, w_go_sends, port = _v5_negative_case(
        monkeypatch, tmp_path)
    _v5_socket_sentinels(monkeypatch, port)
    original_receive = live._seven_receive
    original_waitpid = os.waitpid
    h_pid = None
    injected = False

    def no_waitable_once(pid, options):
        nonlocal injected
        if pid == h_pid and options == os.WNOHANG and not injected:
            injected = True
            raise ChildProcessError(CANARY)
        return original_waitpid(pid, options)

    def lose_waitability_at_o_proof(fd, deadline, **validation):
        nonlocal h_pid
        value = original_receive(fd, deadline, **validation)
        if (validation.get("phase") == "initial"
                and validation.get("expected") == {"role": "H"}
                and value is not None):
            h_pid = value["witness"]["pid"]
        if validation.get("phase") == "o_ready_proof" and value is not None:
            assert h_pid is not None
            live.os.waitpid = no_waitable_once
        return value

    monkeypatch.setattr(live, "_seven_receive", lose_waitability_at_o_proof)
    try:
        result = live._supervise_fake_seven_once(**kwargs)
    finally:
        live.os.waitpid = original_waitpid
    assert injected is True
    _assert_v5_pre_w_failure(
        result, kwargs["run_dir"], marker_dir, w_go_sends,
        "h_ready_unavailable")
    assert result["failure_code"] in (
        "h_ready_unavailable", "cleanup_review_required")


@_DARWIN_FORK
def test_fake_seven_listener_v5_late_normal_s_h_exit_is_not_timely_cleanup(
        monkeypatch, tmp_path):
    kwargs, marker_dir, _, port = _v5_negative_case(monkeypatch, tmp_path)
    _v5_socket_sentinels(monkeypatch, port)
    kwargs["work_seconds"] = 2.0
    original_signal_child = live._split_signal_child
    original_split_receive = live._split_receive
    original_waitpid = os.waitpid
    s_h_pid = None
    s_h_wait_statuses = []

    def record_s_h_reap(pid, options):
        waited_pid, wait_status = original_waitpid(pid, options)
        if pid == s_h_pid and waited_pid == pid:
            s_h_wait_statuses.append(wait_status)
        return waited_pid, wait_status

    def late_normal_s_h(*args, **signal_kwargs):
        code = original_signal_child(*args, **signal_kwargs)
        if signal_kwargs.get("target_role") == "H" and code == 0:
            # This fake child really exits zero, but only *after* its
            # frozen cleanup deadline. Its self-alarm is canceled solely
            # to make the late-normal counterexample observable.
            signal.setitimer(signal.ITIMER_REAL, 0)
            target = signal_kwargs["cleanup_deadline"] + 0.06
            time.sleep(max(0, target - time.monotonic()))
        return code

    def record_s_h_initial(fd, deadline, *, phase, **validation):
        nonlocal s_h_pid
        value = original_split_receive(fd, deadline, phase=phase,
                                       **validation)
        if phase == "initial" and validation.get("role") == "S_H":
            assert value is not None
            s_h_pid = value["witness"]["pid"]
        return value

    monkeypatch.setattr(live, "_split_signal_child", late_normal_s_h)
    monkeypatch.setattr(live, "_split_receive", record_s_h_initial)
    monkeypatch.setattr(live.os, "waitpid", record_s_h_reap)
    result = live._supervise_fake_seven_once(**kwargs)
    assert s_h_pid is not None
    # Whether P reaped during the bounded wait or the test reaps just after
    # it, the late child must really exit zero and leave no synthetic zombie.
    if not s_h_wait_statuses:
        waited_pid, wait_status = os.waitpid(s_h_pid, 0)
        assert waited_pid == s_h_pid
        s_h_wait_statuses.append(wait_status)
    assert any(os.WIFEXITED(status) and os.WEXITSTATUS(status) == 0
               for status in s_h_wait_statuses)
    assert result["schema"] == "fake_seven_process_result_v5", result
    assert result["synthetic_listener_gate_proven"] is True
    assert result["continuous_listener_proven"] is False
    assert result["h_reaped"] and result["h_stop"] == "normal_exit"
    assert result["s_h_normal_exit"] is False
    assert result["status"] == "fake_seven_process_unproven", result
    assert result["failure_code"] == "cleanup_review_required"
    assert result["receipt_durable_proven"] is True
    assert len(list(marker_dir.glob("call-*.json"))) == 7
    receipt = json.loads((kwargs["run_dir"] / "receipt.json").read_bytes())
    assert receipt["s_h_normal_exit"] is False
    assert receipt["failure_code"] == "cleanup_review_required"


@_DARWIN_FORK
@pytest.mark.parametrize("lose_kill_proof", [False, True])
def test_fake_seven_listener_v5_h_ignored_term_requires_witnessed_kill(
        monkeypatch, tmp_path, lose_kill_proof):
    kwargs, marker_dir, w_go_sends, port = _v5_negative_case(
        monkeypatch, tmp_path)
    _v5_socket_sentinels(monkeypatch, port)
    original_split_send = live._split_send

    def h_ignores_term_before_stalling(phase):
        if phase == "before_bind":
            signal.signal(signal.SIGTERM, signal.SIG_IGN)
            time.sleep(10.0)

    def lose_only_h_kill_reply(fd, value, deadline, **validation):
        if (lose_kill_proof
                and validation.get("phase") == "signal_result"
                and validation.get("target_role") == "H"
                and validation.get("signal_name") == "kill"):
            # S_H really sent KILL, but without its canonical response P
            # cannot promote waitpid's signaled status to witnessed stop.
            return True
        return original_split_send(fd, value, deadline, **validation)

    monkeypatch.setattr(live, "_split_send", lose_only_h_kill_reply)
    result = live._supervise_fake_seven_once(
        **kwargs, fake_listener_hook=h_ignores_term_before_stalling)
    receipt = _assert_v5_pre_w_failure(
        result, kwargs["run_dir"], marker_dir, w_go_sends,
        "h_ready_unavailable")
    assert result["h_term"] == "signal_sent", result
    assert result["h_reaped"] is True
    if lose_kill_proof:
        assert result["h_kill"] == "cleanup_response_unavailable"
        assert result["h_stop"] == "unproven"
        assert result["failure_code"] == "cleanup_review_required"
    else:
        assert result["h_kill"] == "signal_sent"
        assert result["h_stop"] == "witnessed_kill"
        cleanup_unproven = (
            any(not result[f"{role}_reaped"]
                or result[f"{role}_stop"] == "unproven"
                for role in ("d", "w", "h", "o"))
            or any(not result[f"s_{role}_reaped"]
                   or not result[f"s_{role}_normal_exit"]
                   for role in ("d", "w", "h", "o")))
        assert result["failure_code"] == (
            "cleanup_review_required" if cleanup_unproven
            else "h_ready_unavailable")
    assert receipt["h_term"] == result["h_term"]
    assert receipt["h_kill"] == result["h_kill"]
    assert receipt["h_stop"] == result["h_stop"]
    assert receipt["failure_code"] == result["failure_code"]


@_DARWIN_FORK
def test_fake_seven_listener_v5_r_death_at_h_initial_forbids_w_go(
        monkeypatch, tmp_path):
    kwargs, marker_dir, w_go_sends, port = _v5_negative_case(
        monkeypatch, tmp_path)
    _v5_socket_sentinels(monkeypatch, port)
    kwargs["work_seconds"] = 2.0
    original_receive = live._seven_receive
    r_pid = None
    killed_before_h_go = False

    def kill_r_when_h_initial_arrives(fd, deadline, **validation):
        nonlocal r_pid, killed_before_h_go
        value = original_receive(fd, deadline, **validation)
        if (validation.get("phase") == "initial"
                and validation.get("expected") == {"role": "R"}
                and value is not None):
            r_pid = value["witness"]["pid"]
        if (validation.get("phase") == "initial"
                and validation.get("expected") == {"role": "H"}
                and value is not None):
            assert r_pid is not None
            # This receive finishes before P can fork S_H or send H_GO.
            os.kill(r_pid, signal.SIGKILL)
            killed_before_h_go = True
            time.sleep(0.05)
        return value

    monkeypatch.setattr(live, "_seven_receive", kill_r_when_h_initial_arrives)
    result = live._supervise_fake_seven_once(**kwargs)
    assert killed_before_h_go is True
    assert result["schema"] == "fake_seven_process_result_v5", result
    assert result["status"] == "fake_seven_process_unproven"
    assert result["failure_code"] == "receipt_unavailable_review_required"
    assert result["receipt_durable_proven"] is False
    assert result["r_reaped"] is True
    assert result["h_reaped"] is True and result["s_h_reaped"] is True
    assert result["synthetic_listener_gate_proven"] is False
    assert result["continuous_listener_proven"] is False
    assert result["granted"] == 0
    assert result["transport_policy_calls"] == 0
    assert not w_go_sends
    assert not list(marker_dir.iterdir())
    _, disk = _read_only_journal(kwargs["run_dir"])
    assert disk["reserved"] == disk["granted"] == 0
    assert disk["operations"] == []
    assert not (kwargs["run_dir"] / "receipt.json").exists()
    assert result["full_gate_pass"] is False
    assert result["b_send_authorized"] is False


@_DARWIN_FORK
@pytest.mark.parametrize("drift_field", ["raw_generation", "pgid"])
def test_fake_seven_listener_v5_h_cleanup_structural_identity_drift_no_signal(
        monkeypatch, tmp_path, drift_field):
    kwargs, marker_dir, w_go_sends, port = _v5_negative_case(
        monkeypatch, tmp_path)
    _v5_socket_sentinels(monkeypatch, port)
    original_receive = live._seven_receive
    h_pid = None

    def record_h_initial(fd, deadline, **validation):
        nonlocal h_pid
        value = original_receive(fd, deadline, **validation)
        if (validation.get("phase") == "initial"
                and validation.get("expected") == {"role": "H"}
                and value is not None):
            h_pid = value["witness"]["pid"]
        return value

    def block_before_bind(phase):
        if phase == "before_bind":
            time.sleep(10.0)

    def drifted_cleanup_witness(pid):
        value = live._fake_os_witness(pid)
        if pid == h_pid:
            assert live._fake_witness_valid(value, pid)
            print(CANARY, flush=True)
            value = deepcopy(value)
            if drift_field == "raw_generation":
                value["raw_generation"][2] += 1
            else:
                value["pgid"] += 1
            assert live._fake_witness_valid(value, pid)
        return value

    monkeypatch.setattr(live, "_seven_receive", record_h_initial)
    result = live._supervise_fake_seven_once(
        **kwargs, fake_listener_hook=block_before_bind,
        cleanup_observe=drifted_cleanup_witness)
    assert h_pid is not None
    receipt = _assert_v5_pre_w_failure(
        result, kwargs["run_dir"], marker_dir, w_go_sends,
        "h_ready_unavailable")
    assert result["h_term"] == "identity_changed_no_signal", result
    assert result["h_kill"] == "identity_changed_no_signal", result
    assert result["h_stop"] == "unproven"
    assert result["failure_code"] == "cleanup_review_required"
    assert result["receipt_durable_proven"] is True
    assert receipt["h_term"] == result["h_term"]
    assert receipt["h_kill"] == result["h_kill"]
    assert receipt["h_stop"] == "unproven"
    assert receipt["failure_code"] == "cleanup_review_required"
    assert CANARY not in json.dumps(result)
    # No signal was allowed. The synthetic child either was already reaped
    # by P or must now exit under its independent hard-lifetime backstop.
    if not result["h_reaped"]:
        waited_pid, wait_status = os.waitpid(h_pid, 0)
        assert waited_pid == h_pid
        assert os.WIFEXITED(wait_status) and os.WEXITSTATUS(wait_status) == 124
