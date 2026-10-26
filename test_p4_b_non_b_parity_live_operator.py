"""Fake-only contract for the one-use non-B parity live operator.

No test starts Ollama, opens HTTP or uses a real model. The process-watchdog
slice signals only its own short-lived synthetic fork children.
"""

from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import select
import signal
import stat
import sys
import time

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
