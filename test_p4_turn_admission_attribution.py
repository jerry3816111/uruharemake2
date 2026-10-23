"""Prospective, zero-provider contracts for opt-in Web turn admission.

These tests locate background work relative to *server registration*, not a
physical Safari click. They do not authorize a tick-1 product gate or prove
durable Chroma writes, fresh generation, or visual delivery.
"""

import json
import os
import stat
import statistics
import threading
from types import SimpleNamespace

import pytest

import uruha_web_ui as web
from uruha_compute_ledger import ComputeLedger, InstrumentedChromaCollection


RAW_INPUT = "private-admission-user-7f90"
RAW_REPLY = "private-admission-reply-3d61"


class _Client:
    def __init__(self, directory):
        self.directory = directory

    def get_settings(self):
        return SimpleNamespace(persist_directory=self.directory)


class _Brain:
    def __init__(self, directory):
        self.memory = SimpleNamespace(
            client=_Client(directory), get_runtime_snapshot=lambda: {},
            session_profile={}, session_turns=[], short_term_buffer=[],
            _consolidated_turn_index=0, _last_decay_at=None,
        )
        self.psyche = SimpleNamespace(get_state=lambda: {})
        self.runtime = SimpleNamespace(autonomous_tick_index=0)
        self.runtime_marker = "before"
        self.generation_calls = 0
        self.background_calls = 0
        self.background_entered = None
        self.background_release = None
        self.background_error = None
        self.ledger = None
        self.vector_error = None
        self.reset_called = threading.Event()

    def run_background_cycle(self, allow_model_maintenance=False):
        assert allow_model_maintenance is False
        self.background_calls += 1
        if self.background_entered is not None:
            self.background_entered.set()
            assert self.background_release.wait(3), "test barrier timed out"
        if self.background_error is not None:
            raise self.background_error
        if self.ledger is not None:
            self.ledger.record_vector_store_operation(
                collection_name="episodic_memory",
                embedding_function="fake-local",
                operation="update",
                arguments={"ids": ["opaque-id"], "metadatas": [{"state": "changed"}]},
                result=None,
                latency_seconds=0.001,
                error=self.vector_error,
            )
        self.runtime.autonomous_tick_index += 1
        # No reported writes is deliberately not an assertion of no state change.
        return {"goal": {"kind": "test"}, "memory_writes": []}

    def run_turn_debug(self, user_text, input_context=None):
        self.generation_calls += 1
        assert user_text == RAW_INPUT
        return {
            "reply": RAW_REPLY,
            "logic": {"intent": "chat", "routing_path": "high_road"},
            "memory_data": {"episodes": []},
            "runtime_trace": {"blackboard": [
                {"stage": "observe", "label": "perception", "payload": {"source": "current_turn"}},
                {"stage": "surface", "label": "utterance", "payload": {"text": RAW_REPLY}},
            ]},
            "runtime_state": {},
            "episode_doc": f"User: {user_text} | Uruha: {RAW_REPLY}",
        }

    def reset_session(self, path):
        self.reset_called.set()
        self.memory.client.directory = path
        self.runtime.autonomous_tick_index = 0

    def get_runtime_snapshot(self):
        return {"autonomous_tick_index": self.runtime.autonomous_tick_index}

    def _runtime_public_state(self):
        return {**self.get_runtime_snapshot(), "marker": self.runtime_marker}


@pytest.fixture
def private_admission(tmp_path, monkeypatch):
    root = tmp_path / "isolated"
    root.mkdir(mode=0o700)
    root.chmod(0o700)
    memory_db = root / "memory_db"
    session_db = root / "session_db"
    memory_db.mkdir(mode=0o700)
    session_db.mkdir(mode=0o700)
    journal = root / "turn_admission_journal.jsonl"
    monkeypatch.setenv("URUHA_MEMORY_DB_PATH", str(memory_db))
    monkeypatch.setenv("URUHA_WEB_SESSION_DB_PATH", str(session_db))
    monkeypatch.setattr(web, "WEB_TURN_ADMISSION_JOURNAL_PATH", str(journal), raising=False)
    monkeypatch.setattr(web, "WEB_ACTIVE_DB_RECEIPT_PATH", "")
    monkeypatch.setattr(web.RuntimeManager, "_idle_consolidation_loop", lambda self: None)
    manager = web.RuntimeManager()
    brain = _Brain(str(memory_db))
    manager._brain = brain
    manager._active_db_phase = "ready"
    monkeypatch.setattr(web, "RUNTIME", manager)
    return manager, brain, root, memory_db, session_db, journal


def _events(journal):
    return [json.loads(line) for line in journal.read_text(encoding="utf-8").splitlines()]


def _run_admitted(manager, token):
    result = web._run_turn(RAW_INPUT, auto_tts=False, admission_token=token)
    assert result["reply"] == RAW_REPLY
    return result


def _private_web_logs(monkeypatch, root):
    logs = root / "web_logs"
    logs.mkdir(mode=0o700)
    logs.chmod(0o700)
    monkeypatch.setattr(web, "WEB_LOG_JSONL", str(logs / "conversation.jsonl"))
    monkeypatch.setattr(web, "WEB_LOG_TXT", str(logs / "conversation.txt"))


def _attach_complete_ledger(manager, brain):
    ledger = ComputeLedger()
    manager._compute_ledger = ledger
    brain.compute_ledger = ledger
    brain.memory.compute_ledger = ledger
    brain.ledger = ledger
    for name in ("kb_col", "episode_col", "wisdom_col", "procedural_col", "profile_col"):
        setattr(brain.memory, name, InstrumentedChromaCollection(
            SimpleNamespace(name=name), ledger, collection_name=name,
        ))
    return ledger


def test_browser_arrival_is_opaque_ordered_and_journal_is_private_raw_free(private_admission):
    manager, brain, root, memory_db, _session_db, journal = private_admission
    first_time, first_token = manager.begin_human_turn_with_token(source="browser")
    second_time, second_token = manager.begin_human_turn_with_token(source="browser")
    assert isinstance(first_time, float) and first_time > 0
    assert second_time >= first_time
    assert first_token and second_token and first_token != second_token
    assert RAW_INPUT not in first_token and RAW_REPLY not in first_token
    rows = _events(journal)
    assert [row["event"] for row in rows] == [
        "arrival", "admission_snapshot", "arrival", "admission_snapshot",
    ]
    assert [row["sequence"] for row in rows] == sorted(row["sequence"] for row in rows)
    assert [row["submission_id"] for row in rows] == [first_token] * 2 + [second_token] * 2
    assert all(row["session_id"] == manager._session_id for row in rows)
    assert all(row["reset_generation"] == 0 for row in rows)
    # Queue-free arrival is a server-side ordering point; it cannot promise
    # an atomic Brain snapshot while a background cycle may hold Brain lock.
    assert rows[0]["active_db_path"] is None and rows[2]["active_db_path"] is None
    assert rows[0]["autonomous_tick_index"] is None and rows[2]["autonomous_tick_index"] is None
    assert rows[1]["active_db_path"] == str(memory_db.resolve())
    assert rows[3]["active_db_path"] == str(memory_db.resolve())
    assert rows[1]["autonomous_tick_index"] == rows[3]["autonomous_tick_index"] == 0
    assert stat.S_IMODE(root.stat().st_mode) == 0o700
    assert stat.S_IMODE(journal.stat().st_mode) == 0o600
    assert journal.stat().st_uid == os.getuid()
    assert RAW_INPUT not in journal.read_text(encoding="utf-8")
    assert RAW_REPLY not in journal.read_text(encoding="utf-8")
    assert brain.generation_calls == 0
    manager.finish_human_turn(admission_token=first_token, terminal_status="empty_input")
    manager.finish_human_turn(admission_token=second_token, terminal_status="empty_input")
    final_rows = _events(journal)
    assert len(manager._admission_journal_write_latencies_seconds) == len(final_rows) == 6
    assert all(value >= 0 for value in manager._admission_journal_write_latencies_seconds)
    assert journal.stat().st_size > 0
    assert [row["event"] for row in final_rows] == [
        "arrival", "admission_snapshot", "arrival", "admission_snapshot", "terminal", "terminal",
    ]
    assert all(row["status"] == "empty_input" for row in final_rows[-2:])


def test_waiting_human_prevents_new_background_and_records_generation_bounds(private_admission):
    manager, brain, _root, _memory_db, _session_db, journal = private_admission
    _, token = manager.begin_human_turn_with_token(source="browser")
    assert manager.run_background_once() is None
    assert brain.background_calls == 0
    _run_admitted(manager, token)
    manager.finish_human_turn(admission_token=token, terminal_status="delivered")
    rows = _events(journal)
    assert [row["event"] for row in rows] == [
        "arrival", "admission_snapshot", "cognition_start", "cognition_end", "terminal",
    ]
    assert [row["sequence"] for row in rows] == sorted(row["sequence"] for row in rows)
    assert all(row["submission_id"] == token for row in rows)
    assert rows[2]["autonomous_tick_index"] == 0
    assert rows[3]["autonomous_tick_index"] == 0
    assert rows[-1]["status"] == "delivered"
    assert brain.generation_calls == 1
    assert RAW_INPUT not in journal.read_text(encoding="utf-8")
    assert RAW_REPLY not in journal.read_text(encoding="utf-8")
    if os.getenv("URUHA_REPORT_ADMISSION_COST") == "1":
        durations = manager._admission_journal_write_latencies_seconds
        print(json.dumps({
            "scope": "fake_brain_journal_only_not_safari_or_model",
            "event_count": len(rows),
            "journal_bytes": journal.stat().st_size,
            "append_fsync_readback_median_ms": round(statistics.median(durations) * 1000, 3),
            "append_fsync_readback_max_ms": round(max(durations) * 1000, 3),
        }, sort_keys=True))


def test_completed_background_before_arrival_still_fails_without_write_attribution(private_admission):
    manager, brain, _root, _memory_db, _session_db, journal = private_admission
    manager.run_background_once()
    _, token = manager.begin_human_turn_with_token(source="browser")
    with pytest.raises(RuntimeError, match="background_write_attribution_unavailable"):
        web._run_turn(RAW_INPUT, auto_tts=False, admission_token=token)
    manager.finish_human_turn(admission_token=token, terminal_status="invalid")
    rows = _events(journal)
    assert [row["event"] for row in rows] == [
        "background_start", "background_end", "arrival",
        "admission_snapshot", "invalid", "terminal",
    ]
    assert rows[0]["autonomous_tick_index"] == 0
    assert rows[1]["autonomous_tick_index"] == 1
    assert rows[2]["autonomous_tick_index"] is None
    assert rows[3]["autonomous_tick_index"] == 1
    assert rows[4]["autonomous_tick_index"] == 1
    assert rows[0]["runtime_sha256"] != rows[1]["runtime_sha256"]
    assert brain.background_calls == 1 and brain.generation_calls == 0


def test_inflight_background_crossing_arrival_is_recorded_and_invalid(private_admission, monkeypatch):
    manager, brain, _root, _memory_db, _session_db, journal = private_admission
    brain.background_entered = threading.Event()
    brain.background_release = threading.Event()
    failure = []
    arrival_seen = threading.Event()
    admission = []
    original_append = web._append_private_turn_admission_event

    def observed_append(path, payload):
        saved = original_append(path, payload)
        if payload.get("event") == "arrival" and saved:
            arrival_seen.set()
        return saved

    monkeypatch.setattr(web, "_append_private_turn_admission_event", observed_append)

    def background():
        try:
            manager.run_background_once()
        except Exception as exc:
            failure.append(exc)

    worker = threading.Thread(target=background)
    worker.start()
    assert brain.background_entered.wait(3)

    def human():
        try:
            admission.append(manager.begin_human_turn_with_token(source="browser"))
        except Exception as exc:
            failure.append(exc)

    human_worker = threading.Thread(target=human)
    human_worker.start()
    try:
        assert arrival_seen.wait(3)
    finally:
        brain.background_release.set()
    worker.join(timeout=3)
    human_worker.join(timeout=3)
    assert not worker.is_alive() and not human_worker.is_alive() and not failure
    _, token = admission[0]
    with pytest.raises(RuntimeError):
        web._run_turn(RAW_INPUT, auto_tts=False, admission_token=token)
    assert brain.generation_calls == 0
    manager.finish_human_turn(admission_token=token, terminal_status="invalid")
    rows = _events(journal)
    assert [row["event"] for row in rows] == [
        "background_start", "arrival", "background_end",
        "admission_snapshot", "invalid", "terminal",
    ]
    assert rows[1]["autonomous_tick_index"] is None
    assert rows[2]["autonomous_tick_index"] == 1
    assert rows[3]["autonomous_tick_index"] == 1


@pytest.mark.parametrize("fault", [
    "missing_token", "duplicate_token", "path_drift", "reset_drift",
    "tick_drift", "state_drift",
])
def test_invalid_admission_fails_before_generation(private_admission, fault):
    manager, brain, _root, _memory_db, session_db, journal = private_admission
    _, token = manager.begin_human_turn_with_token(source="browser")
    if fault == "missing_token":
        token = ""
    elif fault == "duplicate_token":
        _run_admitted(manager, token)
    elif fault == "path_drift":
        brain.memory.client.directory = str(session_db)
    elif fault == "reset_drift":
        manager.reset_brain_session()
    elif fault == "tick_drift":
        brain.runtime.autonomous_tick_index += 1
    else:
        brain.runtime_marker = "after"
    calls_before = brain.generation_calls
    with pytest.raises(RuntimeError):
        web._run_turn(RAW_INPUT, auto_tts=False, admission_token=token)
    assert brain.generation_calls == calls_before
    rows = _events(journal)
    assert any(row["event"] == "invalid" for row in rows)
    assert RAW_INPUT not in journal.read_text(encoding="utf-8")
    assert RAW_REPLY not in journal.read_text(encoding="utf-8")


def test_background_exception_has_terminal_end_event_not_false_zero(private_admission):
    manager, brain, _root, _memory_db, _session_db, journal = private_admission
    brain.background_error = RuntimeError("fake-background-error")
    with pytest.raises(RuntimeError, match="fake-background-error"):
        manager.run_background_once()
    rows = _events(journal)
    assert [row["event"] for row in rows] == ["background_start", "background_end"]
    assert rows[1]["status"] not in {"completed", "no_change", "zero_writes"}
    assert brain.generation_calls == 0


def test_lost_background_journal_event_poison_future_admission(private_admission, monkeypatch):
    manager, brain, _root, _memory_db, _session_db, journal = private_admission
    original_append = web._append_private_turn_admission_event

    def drop_one_start(path, payload):
        if payload.get("event") == "background_start":
            return False
        return original_append(path, payload)

    monkeypatch.setattr(web, "_append_private_turn_admission_event", drop_one_start)
    manager.run_background_once()
    _, token = manager.begin_human_turn_with_token(source="browser")
    with pytest.raises(RuntimeError):
        web._run_turn(RAW_INPUT, auto_tts=False, admission_token=token)
    assert brain.generation_calls == 0
    assert any(row["event"] == "background_end" for row in _events(journal))


@pytest.mark.parametrize("operation_error", [False, True])
def test_background_vector_mutation_method_return_or_error_is_not_zero(
    private_admission, operation_error,
):
    manager, brain, _root, _memory_db, _session_db, journal = private_admission
    ledger = _attach_complete_ledger(manager, brain)
    brain.vector_error = RuntimeError("synthetic-update-failure") if operation_error else None
    manager.run_background_once()
    end = next(row for row in _events(journal) if row["event"] == "background_end")
    assert end["reported_memory_write_count"] == 0
    assert end["ledger_status"] == "attributed"
    assert end["vector_mutation_returned_count"] == (0 if operation_error else 1)
    assert end["vector_mutation_error_count"] == (1 if operation_error else 0)
    assert end["compute_summary"]["call_count"] == 1
    assert end["compute_summary"]["by_operation"] == {"update": 1}
    assert end["compute_summary"]["total_tokens"] == 0
    assert len(ledger._calls) == (1 if operation_error else 0)
    assert brain.generation_calls == 0


def test_reset_uses_same_brain_lock_as_cognition(private_admission):
    manager, brain, _root, _memory_db, _session_db, _journal = private_admission
    launched = threading.Event()
    failures = []

    def reset():
        launched.set()
        try:
            manager.reset_brain_session()
        except Exception as exc:
            failures.append(exc)

    with manager._lock:
        worker = threading.Thread(target=reset)
        worker.start()
        assert launched.wait(3)
        assert not brain.reset_called.wait(0.05), "reset raced with a held cognition lock"
    worker.join(timeout=3)
    assert not worker.is_alive() and not failures
    assert brain.reset_called.is_set()


def test_journal_loss_after_arrival_stops_before_model(private_admission):
    manager, brain, root, _memory_db, _session_db, journal = private_admission
    _, token = manager.begin_human_turn_with_token(source="browser")
    root.chmod(0o755)
    try:
        with pytest.raises(RuntimeError):
            web._run_turn(RAW_INPUT, auto_tts=False, admission_token=token)
    finally:
        root.chmod(0o700)
    assert brain.generation_calls == 0
    assert [row["event"] for row in _events(journal)] == ["arrival", "admission_snapshot"]


def test_active_independent_brain_worker_is_not_claimed_atomic(private_admission):
    manager, brain, _root, _memory_db, _session_db, journal = private_admission
    stop_worker = threading.Event()
    worker = threading.Thread(target=stop_worker.wait)
    brain._event_worker_thread = worker
    worker.start()
    try:
        _, token = manager.begin_human_turn_with_token(source="browser")
        with pytest.raises(RuntimeError, match="independent_worker_active"):
            web._run_turn(RAW_INPUT, auto_tts=False, admission_token=token)
    finally:
        stop_worker.set()
        worker.join(timeout=3)
    assert not worker.is_alive()
    assert brain.generation_calls == 0
    assert any(row["event"] == "invalid" for row in _events(journal))


def test_opt_out_browser_admission_keeps_original_callback_shape(private_admission, monkeypatch):
    _manager, brain, _root, _memory_db, _session_db, journal = private_admission
    monkeypatch.setattr(web, "WEB_TURN_ADMISSION_JOURNAL_PATH", "")
    manager = web.RuntimeManager()
    manager._brain = brain
    manager._active_db_phase = "ready"
    monkeypatch.setattr(web, "RUNTIME", manager)
    started, session = web.begin_human_submission_with_session(RAW_INPUT)
    assert isinstance(started, float) and started > 0
    assert session == manager._session_id
    assert not journal.exists()
    assert brain.generation_calls == 0
    manager.finish_human_turn()


@pytest.mark.parametrize("mode", ["text", "audio"])
def test_browser_callback_carries_server_token_through_delivery(private_admission, monkeypatch, mode):
    manager, brain, root, _memory_db, _session_db, journal = private_admission
    _private_web_logs(monkeypatch, root)
    if mode == "audio":
        audio = root / "input.wav"
        audio.write_bytes(b"synthetic-audio-file-no-provider")
        monkeypatch.setattr(
            manager, "get_ears",
            lambda: SimpleNamespace(transcribe_audio_file=lambda _path: RAW_INPUT),
        )
        submitted = str(audio)
    else:
        submitted = RAW_INPUT
    started, session_state = web.begin_human_submission_with_session(submitted)
    assert isinstance(session_state, dict)
    assert session_state["session_id"] == manager._session_id
    token = session_state["admission_token"]
    assert token
    if mode == "audio":
        updates = list(web.submit_audio_browser_bound(submitted, [], False, started, session_state))
    else:
        updates = list(web.submit_text_browser_bound(submitted, [], False, started, session_state))
    assert updates and updates[-1][0][-1] == {"role": "assistant", "content": RAW_REPLY}
    rows = _events(journal)
    assert [row["event"] for row in rows] == [
        "arrival", "admission_snapshot", "cognition_start", "cognition_end", "terminal",
    ]
    assert all(row["submission_id"] == token for row in rows)
    assert rows[-1]["status"] == "delivered"
    assert brain.generation_calls == 1
    assert RAW_INPUT not in journal.read_text(encoding="utf-8")
    assert RAW_REPLY not in journal.read_text(encoding="utf-8")


def test_direct_function_call_is_not_mislabelled_as_browser_admission(private_admission, monkeypatch):
    manager, brain, root, _memory_db, _session_db, journal = private_admission
    _private_web_logs(monkeypatch, root)
    updates = list(web.submit_text(RAW_INPUT, [], False))
    assert updates[-1][0][-1] == {"role": "assistant", "content": RAW_REPLY}
    rows = _events(journal)
    arrival = [row for row in rows if row["event"] == "arrival"]
    assert len(arrival) == 1
    assert arrival[0]["source"] == "direct_no_browser_admission"
    assert brain.generation_calls == 1


def test_empty_text_has_own_terminal_without_cognition_or_model(private_admission):
    _manager, brain, _root, _memory_db, _session_db, journal = private_admission
    updates = list(web.submit_text("", [], False))
    assert updates
    rows = _events(journal)
    assert [row["event"] for row in rows] == [
        "arrival", "admission_snapshot", "terminal",
    ]
    assert rows[0]["source"] == "direct_no_browser_admission"
    assert rows[-1]["status"] == "empty_input"
    assert brain.generation_calls == 0


def test_audio_transcription_only_has_terminal_but_no_cognition(private_admission, monkeypatch):
    manager, brain, root, _memory_db, _session_db, journal = private_admission
    audio = root / "transcription_only.wav"
    audio.write_bytes(b"synthetic-audio-file-no-provider")
    monkeypatch.setattr(
        manager, "get_ears", lambda: SimpleNamespace(transcribe_audio_file=lambda _path: RAW_INPUT),
    )
    started, session_state = web.begin_human_submission_with_session(str(audio))
    updates = list(web.handle_audio_stop_browser_bound(
        str(audio), [], False, False, started, session_state,
    ))
    assert updates
    rows = _events(journal)
    assert [row["event"] for row in rows] == [
        "arrival", "admission_snapshot", "terminal",
    ]
    assert rows[-1]["status"] == "transcription_only"
    assert brain.generation_calls == 0


def test_generator_close_is_aborted_not_successful_delivery(private_admission):
    _manager, brain, _root, _memory_db, _session_db, journal = private_admission
    started, session_state = web.begin_human_submission_with_session(RAW_INPUT)
    stream = web.submit_text_browser_bound(RAW_INPUT, [], False, started, session_state)
    first = next(stream)
    assert first
    stream.close()
    rows = _events(journal)
    assert [row["event"] for row in rows] == [
        "arrival", "admission_snapshot", "terminal",
    ]
    assert rows[-1]["status"] == "aborted"
    assert brain.generation_calls == 0


def test_terminal_is_written_before_waiter_release_and_next_background(private_admission, monkeypatch):
    manager, brain, _root, _memory_db, _session_db, journal = private_admission
    _, token = manager.begin_human_turn_with_token(source="browser")
    _run_admitted(manager, token)
    original_append = web._append_private_turn_admission_event
    waiter_counts_at_terminal = []

    def observe_terminal(path, payload):
        if payload.get("event") == "terminal":
            waiter_counts_at_terminal.append(manager._human_waiters)
        return original_append(path, payload)

    monkeypatch.setattr(web, "_append_private_turn_admission_event", observe_terminal)
    manager.finish_human_turn(admission_token=token, terminal_status="delivered")
    assert waiter_counts_at_terminal == [1]
    assert manager._human_waiters == 0
    manager.run_background_once()
    rows = _events(journal)
    assert rows[-3]["event"] == "terminal"
    assert rows[-2]["event"] == "background_start"
    assert rows[-1]["event"] == "background_end"
    assert rows[-3]["sequence"] < rows[-2]["sequence"]
    assert brain.generation_calls == 1 and brain.background_calls == 1


def test_untrusted_journal_destination_fails_closed_before_generation(private_admission):
    manager, brain, root, _memory_db, _session_db, journal = private_admission
    root.chmod(0o755)
    try:
        try:
            _started, token = manager.begin_human_turn_with_token(source="browser")
        except RuntimeError:
            token = None
        if token is not None:
            with pytest.raises(RuntimeError):
                web._run_turn(RAW_INPUT, auto_tts=False, admission_token=token)
    finally:
        root.chmod(0o700)
    assert not journal.exists()
    assert brain.generation_calls == 0


def test_live_chroma_outside_controller_root_fails_before_generation(private_admission, tmp_path):
    manager, brain, _root, _memory_db, _session_db, journal = private_admission
    outside = tmp_path / "other_memory_db"
    outside.mkdir(mode=0o700)
    brain.memory.client.directory = str(outside)
    _, token = manager.begin_human_turn_with_token(source="browser")
    with pytest.raises(RuntimeError, match="live_db_not_isolated"):
        _run_admitted(manager, token)
    assert brain.generation_calls == 0
    assert any(row["status"] == "live_db_not_isolated" for row in _events(journal))


def test_symlinked_controller_db_fails_closed(private_admission):
    manager, brain, root, _memory_db, session_db, journal = private_admission
    session_db.rename(root / "session_db_real")
    session_db.symlink_to(root / "session_db_real", target_is_directory=True)
    _, token = manager.begin_human_turn_with_token(source="browser")
    with pytest.raises(RuntimeError, match="arrival_not_durable"):
        _run_admitted(manager, token)
    assert brain.generation_calls == 0 and not journal.exists()


def test_uncreated_session_db_is_allowed_only_while_memory_db_is_live(private_admission):
    manager, brain, _root, _memory_db, session_db, journal = private_admission
    session_db.rmdir()
    _, token = manager.begin_human_turn_with_token(source="browser")
    _run_admitted(manager, token)
    manager.finish_human_turn(admission_token=token, terminal_status="delivered")
    assert [row["event"] for row in _events(journal)][-1] == "terminal"
    assert brain.generation_calls == 1


def test_unknown_or_duplicate_terminal_cannot_release_another_waiter(private_admission):
    manager, brain, _root, _memory_db, _session_db, journal = private_admission
    _, first = manager.begin_human_turn_with_token(source="browser")
    _, second = manager.begin_human_turn_with_token(source="browser")
    manager.finish_human_turn(admission_token="unknown", terminal_status="delivered")
    assert manager._human_waiters == 2
    assert manager._human_submission_finish_count == 0
    manager.finish_human_turn(admission_token=first, terminal_status="empty_input")
    manager.finish_human_turn(admission_token=first, terminal_status="delivered")
    assert manager._human_waiters == 1
    assert manager.run_background_once() is None and brain.background_calls == 0
    manager.finish_human_turn(admission_token=second, terminal_status="empty_input")
    assert manager._human_waiters == 0
    assert manager._human_submission_finish_count == 2
    assert [row["status"] for row in _events(journal) if row["event"] == "terminal"] == [
        "missing_or_unknown_token", "empty_input", "missing_or_unknown_token", "empty_input",
    ]


def test_unknown_background_attribution_stays_invalid_after_64_more_cycles(private_admission):
    manager, brain, _root, _memory_db, _session_db, _journal = private_admission
    manager.run_background_once()  # no ledger; permanently unknown for this trial
    _attach_complete_ledger(manager, brain)
    for _ in range(65):
        manager.run_background_once()
    assert len(manager._background_admission_events) == 64
    assert all(row["ledger_status"] == "attributed" for row in manager._background_admission_events)
    _, token = manager.begin_human_turn_with_token(source="browser")
    with pytest.raises(RuntimeError, match="background_audit_unavailable"):
        _run_admitted(manager, token)
    assert brain.generation_calls == 0


def test_background_error_stays_invalid_even_if_ledger_attributed(private_admission):
    manager, brain, _root, _memory_db, _session_db, journal = private_admission
    _attach_complete_ledger(manager, brain)
    brain.background_error = RuntimeError("synthetic-background-failure")
    with pytest.raises(RuntimeError, match="synthetic-background-failure"):
        manager.run_background_once()
    end = next(row for row in _events(journal) if row["event"] == "background_end")
    assert end["status"] == "error" and end["ledger_status"] == "attributed"
    _, token = manager.begin_human_turn_with_token(source="browser")
    with pytest.raises(RuntimeError, match="background_audit_unavailable"):
        _run_admitted(manager, token)
    assert brain.generation_calls == 0


def test_journal_pair_readback_failure_keeps_compute_evidence(private_admission, monkeypatch):
    manager, brain, _root, _memory_db, _session_db, journal = private_admission
    ledger = _attach_complete_ledger(manager, brain)
    retired = []
    monkeypatch.setattr(web, "_verified_background_admission_pair", lambda *_args: False)
    monkeypatch.setattr(ledger, "retire_item_snapshot", lambda snapshot: retired.append(snapshot))
    manager.run_background_once()
    end = next(row for row in _events(journal) if row["event"] == "background_end")
    assert end["ledger_status"] == "attributed" and end["vector_mutation_returned_count"] == 1
    assert retired == [] and manager._admission_audit_invalid is True


def test_terminal_reset_during_delivery_is_not_recorded_as_delivered(private_admission):
    manager, brain, _root, _memory_db, _session_db, journal = private_admission
    _, token = manager.begin_human_turn_with_token(source="browser")
    _run_admitted(manager, token)
    manager.reset_brain_session()
    manager.finish_human_turn(admission_token=token, terminal_status="delivered")
    terminal = [row for row in _events(journal) if row["event"] == "terminal"][-1]
    assert terminal["status"] == "terminal_state_drift"
    assert terminal["delivery_observation"] == "server_generator_only"
    assert manager._admission_audit_invalid is True
    assert brain.generation_calls == 1


@pytest.mark.parametrize("changed", ["memory", "psyche"])
def test_terminal_fingerprint_change_without_tick_is_not_delivered(private_admission, changed):
    manager, brain, _root, _memory_db, _session_db, journal = private_admission
    live_state = {"marker": "before"}
    if changed == "memory":
        brain.memory.session_profile = live_state
    else:
        brain.psyche.get_state = lambda: dict(live_state)
    _, token = manager.begin_human_turn_with_token(source="browser")
    _run_admitted(manager, token)
    live_state["marker"] = "changed_after_cognition"
    manager.finish_human_turn(admission_token=token, terminal_status="delivered")
    terminal = [row for row in _events(journal) if row["event"] == "terminal"][-1]
    assert terminal["autonomous_tick_index"] == 0
    assert terminal["status"] == "terminal_state_drift"
    assert manager._admission_audit_invalid is True


def test_cognition_end_unavailable_fingerprint_invalidates_turn(private_admission):
    manager, brain, _root, _memory_db, _session_db, journal = private_admission
    original = brain.run_turn_debug

    def run_and_lose_snapshot(*args, **kwargs):
        result = original(*args, **kwargs)

        del brain.memory.session_profile
        return result

    brain.run_turn_debug = run_and_lose_snapshot
    _, token = manager.begin_human_turn_with_token(source="browser")
    with pytest.raises(RuntimeError, match="cognition_state_drift"):
        web._run_turn(RAW_INPUT, auto_tts=False, admission_token=token)
    assert brain.generation_calls == 1
    assert [row for row in _events(journal) if row["event"] == "cognition_end"][-1]["status"] == "state_drift"


def test_admission_memory_fingerprint_never_queries_chroma(private_admission):
    manager, brain, _root, _memory_db, _session_db, journal = private_admission
    _attach_complete_ledger(manager, brain)
    called = []

    def query_bearing_snapshot():
        called.append("chroma_query")
        raise RuntimeError("must-not-be-called")

    brain.memory.get_runtime_snapshot = query_bearing_snapshot
    _, token = manager.begin_human_turn_with_token(source="browser")
    result = _run_admitted(manager, token)
    manager.finish_human_turn(admission_token=token, terminal_status="delivered")
    assert called == []
    assert all(row.get("memory_fingerprint_scope") in (None, "in_memory_only") for row in _events(journal))
    assert result["compute_receipt"]["snapshot"]["attribution_complete"] is True
    assert result["compute_receipt"]["snapshot"]["unscoped_call_count_during_window"] == 0
    assert brain.generation_calls == 1


def test_background_live_db_path_switch_keeps_ledger_evidence(private_admission, tmp_path, monkeypatch):
    manager, brain, _root, _memory_db, _session_db, journal = private_admission
    ledger = _attach_complete_ledger(manager, brain)
    outside = tmp_path / "external_db"
    outside.mkdir(mode=0o700)
    original_cycle = brain.run_background_cycle

    def switch_path(*args, **kwargs):
        result = original_cycle(*args, **kwargs)
        brain.memory.client.directory = str(outside)
        return result

    brain.run_background_cycle = switch_path
    retired = []
    monkeypatch.setattr(ledger, "retire_item_snapshot", lambda snapshot: retired.append(snapshot))
    manager.run_background_once()
    end = next(row for row in _events(journal) if row["event"] == "background_end")
    assert end["active_db_path"] == str(outside)
    assert end["ledger_status"] == "attributed"
    assert retired == [] and manager._admission_audit_invalid is True


def test_background_missing_before_fingerprint_keeps_compute_evidence(private_admission, monkeypatch):
    manager, brain, _root, _memory_db, _session_db, journal = private_admission
    ledger = _attach_complete_ledger(manager, brain)
    del brain.memory.session_profile
    original_cycle = brain.run_background_cycle

    def restore_after_cycle(*args, **kwargs):
        result = original_cycle(*args, **kwargs)
        brain.memory.session_profile = {}
        return result

    brain.run_background_cycle = restore_after_cycle
    retired = []
    monkeypatch.setattr(ledger, "retire_item_snapshot", lambda snapshot: retired.append(snapshot))
    manager.run_background_once()
    rows = _events(journal)
    assert rows[0]["memory_sha256"] is None
    assert rows[1]["memory_sha256"] is not None
    assert rows[1]["ledger_status"] == "attributed"
    assert retired == [] and manager._admission_audit_invalid is True


def test_terminal_status_and_unknown_token_cannot_write_raw_dialogue(private_admission):
    manager, _brain, _root, _memory_db, _session_db, journal = private_admission
    _, token = manager.begin_human_turn_with_token(source="browser")
    manager.finish_human_turn(admission_token=token, terminal_status=RAW_INPUT)
    manager.finish_human_turn(admission_token=RAW_REPLY, terminal_status="delivered")
    contents = journal.read_text(encoding="utf-8")
    assert RAW_INPUT not in contents and RAW_REPLY not in contents
    assert [row["status"] for row in _events(journal) if row["event"] == "terminal"] == [
        "unknown_status", "missing_or_unknown_token",
    ]


def test_unstarted_queued_callback_timeout_is_unknown_and_cannot_fake_clean_gate(private_admission):
    manager, brain, _root, _memory_db, _session_db, journal = private_admission
    _, token = manager.begin_human_turn_with_token(source="browser")
    manager._admission_records[token]["last_progress_at"] -= web._UNSTARTED_ADMISSION_LEASE_SECONDS + 1
    manager.run_background_once()
    assert manager._human_waiters == 0
    assert token not in manager._admission_records
    assert manager._admission_audit_invalid is True
    assert any(row["event"] == "terminal" and row["status"] == "admission_timeout_unknown" for row in _events(journal))
    with pytest.raises(RuntimeError, match="missing_or_unknown_token"):
        _run_admitted(manager, token)
    assert brain.generation_calls == 0


def test_mismatched_brain_ledger_is_not_attributed(private_admission):
    manager, brain, _root, _memory_db, _session_db, journal = private_admission
    manager._compute_ledger = ComputeLedger()
    manager.run_background_once()
    end = next(row for row in _events(journal) if row["event"] == "background_end")
    assert end["ledger_status"] == "unavailable"
    assert end["ledger_coverage_complete"] is False
    assert manager._admission_audit_invalid is True


def test_background_checkpoint_error_still_has_end_and_poisoned_audit(private_admission, monkeypatch):
    manager, brain, _root, _memory_db, _session_db, journal = private_admission
    ledger = _attach_complete_ledger(manager, brain)

    def checkpoint_error():
        raise RuntimeError("synthetic-checkpoint-error")

    monkeypatch.setattr(ledger, "checkpoint", checkpoint_error)
    with pytest.raises(RuntimeError, match="synthetic-checkpoint-error"):
        manager.run_background_once()
    rows = _events(journal)
    assert [row["event"] for row in rows] == ["background_start", "background_end"]
    assert rows[-1]["status"] == "error"
    assert manager._admission_audit_invalid is True
    assert brain.background_calls == 0 and brain.generation_calls == 0


def test_nonempty_journal_from_prior_process_cannot_be_reused(private_admission, monkeypatch):
    manager, brain, _root, memory_db, _session_db, journal = private_admission
    _, old_token = manager.begin_human_turn_with_token(source="browser")
    manager.finish_human_turn(admission_token=old_token, terminal_status="empty_input")
    assert journal.stat().st_size > 0
    second = web.RuntimeManager()
    second._brain = _Brain(str(memory_db))
    second._active_db_phase = "ready"
    monkeypatch.setattr(web, "RUNTIME", second)
    assert second._admission_audit_invalid is True
    _, new_token = second.begin_human_turn_with_token(source="browser")
    with pytest.raises(RuntimeError):
        web._run_turn(RAW_INPUT, auto_tts=False, admission_token=new_token)
    assert second._brain.generation_calls == 0
    assert brain.generation_calls == 0


@pytest.mark.parametrize("tamper", ["delete_arrival", "rewrite_snapshot"])
def test_tampered_arrival_chain_cannot_reach_generation(private_admission, tamper):
    manager, brain, _root, _memory_db, _session_db, journal = private_admission
    _, token = manager.begin_human_turn_with_token(source="browser")
    rows = _events(journal)
    if tamper == "delete_arrival":
        rows.pop(0)
    else:
        rows[1]["status"] = "tampered_but_valid_json"
    journal.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows), encoding="utf-8")
    with pytest.raises(RuntimeError):
        web._run_turn(RAW_INPUT, auto_tts=False, admission_token=token)
    assert brain.generation_calls == 0
    assert manager._admission_audit_invalid is True


def test_tampered_cognition_chain_cannot_be_terminal_delivered(private_admission):
    manager, brain, _root, _memory_db, _session_db, journal = private_admission
    _, token = manager.begin_human_turn_with_token(source="browser")
    _run_admitted(manager, token)
    rows = _events(journal)
    rows[2]["status"] = "tampered_but_valid_json"
    journal.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows), encoding="utf-8")
    manager.finish_human_turn(admission_token=token, terminal_status="delivered")
    assert manager._admission_audit_invalid is True
    assert [row for row in _events(journal) if row["event"] == "terminal"][-1]["status"] == "terminal_state_drift"
    assert brain.generation_calls == 1


def test_malformed_background_result_has_end_and_cannot_admit_generation(private_admission):
    manager, brain, _root, _memory_db, _session_db, journal = private_admission
    _attach_complete_ledger(manager, brain)
    brain.run_background_cycle = lambda allow_model_maintenance=False: ["malformed"]
    with pytest.raises(TypeError, match="malformed_background_result"):
        manager.run_background_once()
    rows = _events(journal)
    assert [row["event"] for row in rows] == ["background_start", "background_end"]
    assert rows[-1]["status"] == "error"
    assert rows[-1]["reported_memory_write_count"] is None
    assert manager._admission_audit_invalid is True
    _, token = manager.begin_human_turn_with_token(source="browser")
    with pytest.raises(RuntimeError):
        _run_admitted(manager, token)
    assert brain.generation_calls == 0


def test_unpaired_background_start_is_rejected_before_generation(private_admission, monkeypatch):
    manager, brain, _root, _memory_db, _session_db, journal = private_admission
    _attach_complete_ledger(manager, brain)
    original_event = manager._admission_event_under_gate

    def lose_end(event, **fields):
        if event == "background_end":
            raise RuntimeError("synthetic_end_journal_failure")
        return original_event(event, **fields)

    monkeypatch.setattr(manager, "_admission_event_under_gate", lose_end)
    with pytest.raises(RuntimeError, match="synthetic_end_journal_failure"):
        manager.run_background_once()
    monkeypatch.setattr(manager, "_admission_event_under_gate", original_event)
    assert [row["event"] for row in _events(journal)] == ["background_start"]
    _, token = manager.begin_human_turn_with_token(source="browser")
    with pytest.raises(RuntimeError, match="background_journal_pair_unavailable"):
        _run_admitted(manager, token)
    assert brain.generation_calls == 0


def test_orphan_background_end_without_start_sequence_is_not_a_pair(private_admission):
    manager, brain, _root, _memory_db, _session_db, journal = private_admission
    with manager._human_gate_lock:
        _, saved = manager._admission_event_under_gate(
            "background_end", submission_id="orphan", status="completed",
        )
    assert saved and _events(journal)[0]["event"] == "background_end"
    _, token = manager.begin_human_turn_with_token(source="browser")
    with pytest.raises(RuntimeError, match="background_journal_pair_unavailable"):
        _run_admitted(manager, token)
    assert brain.generation_calls == 0


def test_delivered_without_cognition_pair_is_invalid(private_admission):
    manager, brain, _root, _memory_db, _session_db, journal = private_admission
    _, token = manager.begin_human_turn_with_token(source="browser")
    manager.finish_human_turn(admission_token=token, terminal_status="delivered")
    assert [row["event"] for row in _events(journal)] == [
        "arrival", "admission_snapshot", "terminal",
    ]
    assert _events(journal)[-1]["status"] == "terminal_state_drift"
    assert manager._admission_audit_invalid is True
    assert brain.generation_calls == 0


def test_cognition_error_cannot_be_marked_delivered(private_admission):
    manager, brain, _root, _memory_db, _session_db, journal = private_admission
    _, token = manager.begin_human_turn_with_token(source="browser")
    with manager._lock:
        manager.start_admitted_turn(token, brain)
        manager.end_admitted_cognition(token, brain, status="error_RuntimeError")
    manager.finish_human_turn(admission_token=token, terminal_status="delivered")
    assert _events(journal)[-1]["status"] == "terminal_state_drift"
    assert manager._admission_audit_invalid is True
    assert brain.generation_calls == 0


def test_sticky_audit_failure_after_cognition_is_not_delivered(private_admission):
    manager, brain, _root, _memory_db, _session_db, journal = private_admission
    _, token = manager.begin_human_turn_with_token(source="browser")
    _run_admitted(manager, token)
    manager._admission_audit_invalid = True
    manager.finish_human_turn(admission_token=token, terminal_status="delivered")
    assert _events(journal)[-1]["status"] == "terminal_state_drift"
    assert brain.generation_calls == 1


def test_empty_browser_send_keeps_browser_source_without_model(private_admission):
    manager, brain, _root, _memory_db, _session_db, journal = private_admission
    started, session_state = web.begin_human_submission_with_session("")
    assert started > 0 and session_state["admission_token"]
    assert list(web.submit_text_browser_bound("", [], False, started, session_state))
    rows = _events(journal)
    assert [row["event"] for row in rows] == ["arrival", "admission_snapshot", "terminal"]
    assert rows[0]["source"] == "browser"
    assert rows[-1]["status"] == "empty_input"
    assert manager._human_waiters == 0 and brain.generation_calls == 0


def test_opt_in_constructor_checks_imported_db_before_any_init(private_admission, tmp_path, monkeypatch):
    manager, _brain, _root, _memory_db, _session_db, _journal = private_admission
    outside = tmp_path / "wrong_db"
    outside.mkdir(mode=0o700)
    module = web.sys.modules["uruha_brain_mac"]
    monkeypatch.setattr(module, "DB_PATH", str(outside))
    constructed = []
    monkeypatch.setattr(web, "UruhaBrainV4_Mac", lambda **kwargs: constructed.append(kwargs))
    manager._brain = None
    with pytest.raises(RuntimeError, match="constructor_db_not_isolated"):
        manager.get_brain()
    assert constructed == []


def test_opt_in_reset_checks_db_before_any_reset(private_admission, tmp_path, monkeypatch):
    manager, brain, _root, _memory_db, _session_db, _journal = private_admission
    outside = tmp_path / "wrong_session_db"
    monkeypatch.setenv("URUHA_WEB_SESSION_DB_PATH", str(outside))
    with pytest.raises(RuntimeError, match="db_preflight_unavailable"):
        manager.reset_brain_session()
    assert brain.reset_called.is_set() is False
    assert manager._reset_generation == 0
    assert not outside.exists()


def test_opt_in_valid_constructor_and_reset_stay_in_private_root(private_admission, monkeypatch):
    manager, _brain, _root, memory_db, session_db, _journal = private_admission
    module = web.sys.modules["uruha_brain_mac"]
    monkeypatch.setattr(module, "DB_PATH", str(memory_db))
    built = []

    def build_fake(**_kwargs):
        brain = _Brain(str(memory_db))
        built.append(brain)
        return brain

    monkeypatch.setattr(web, "UruhaBrainV4_Mac", build_fake)
    manager._brain = None
    assert manager.get_brain() is built[0]
    assert manager.reset_brain_session() is built[0]
    assert built[0].reset_called.is_set()
    assert built[0].memory.client.directory == str(session_db)


def test_proactive_poll_cannot_mutate_during_queue_free_arrival(private_admission):
    manager, brain, _root, _memory_db, _session_db, journal = private_admission
    entered = threading.Event()
    release = threading.Event()
    arrived = threading.Event()
    admission = []

    def delayed_empty():
        entered.set()
        assert release.wait(3)
        return {}

    brain.consume_pending_proactive_turn = delayed_empty
    poll_worker = threading.Thread(target=lambda: web.poll_proactive_turn([], False))
    poll_worker.start()
    assert entered.wait(3)

    def arrive():
        admission.append(manager.begin_human_turn_with_token(source="browser"))
        arrived.set()

    arrival_worker = threading.Thread(target=arrive)
    arrival_worker.start()
    assert not arrived.wait(0.05)
    assert not journal.exists()
    release.set()
    poll_worker.join(timeout=3)
    arrival_worker.join(timeout=3)
    assert not poll_worker.is_alive() and not arrival_worker.is_alive()
    assert arrived.is_set()
    _run_admitted(manager, admission[0][1])
    manager.finish_human_turn(admission_token=admission[0][1], terminal_status="delivered")
    assert brain.generation_calls == 1
    assert _events(journal)[-1]["status"] == "delivered"


def test_proactive_delivery_invalidates_opt_in_trial_before_user_generation(private_admission):
    manager, brain, _root, _memory_db, _session_db, journal = private_admission
    brain.runtime.last_autonomous_result = {}
    brain.consume_pending_proactive_turn = lambda: {"line": ""}
    assert web.poll_proactive_turn([], False)
    assert _events(journal)[0]["status"] == "proactive_delivery_unattributed"
    _, token = manager.begin_human_turn_with_token(source="browser")
    with pytest.raises(RuntimeError, match="background_audit_unavailable"):
        _run_admitted(manager, token)
    assert brain.generation_calls == 0
