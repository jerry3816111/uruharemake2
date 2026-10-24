"""Zero-model contracts for the opt-in product Web compute receipt.

These synthetic turns prove attribution/privacy wiring, not fresh generation,
Safari presentation, provider-wide coverage, or a formal comparison result.
"""

import json
import threading
from types import SimpleNamespace

import pytest

import uruha_web_ui as web
from uruha_compute_ledger import ComputeLedger


RAW_PROMPT = "private-turn-prompt-7c14"
RAW_REPLY = "private-turn-reply-8e25"


def _record_generation(ledger, *, error=None):
    ledger.record_native_ollama_chat(
        {"model": "fake-local", "messages": [{"role": "user", "content": RAW_PROMPT}]},
        None if error else {
            "message": {"content": RAW_REPLY},
            "prompt_eval_count": 11,
            "eval_count": 5,
        },
        0.25,
        error=error,
    )


def _record_vector(ledger):
    ledger.record_vector_store_operation(
        collection_name="episodic_memory",
        embedding_function="fake-local-embedding",
        operation="query",
        arguments={"query_texts": [RAW_PROMPT], "n_results": 2},
        result={"ids": [[]]},
        latency_seconds=0.125,
    )


def _assert_raw_free(receipt):
    encoded = json.dumps(receipt, ensure_ascii=False)
    assert RAW_PROMPT not in encoded
    assert RAW_REPLY not in encoded
    assert receipt["contains_raw_prompt_or_reply"] is False


def test_item_checkpoint_copies_only_this_turn_and_keeps_zero_distinct():
    ledger = ComputeLedger()
    _record_generation(ledger)  # prewarm is outside either turn
    first_checkpoint = ledger.checkpoint()
    with ledger.item_scope("turn-one", "product_web"):
        with ledger.stage("reply_planner"):
            _record_generation(ledger)
            _record_vector(ledger)
    first = ledger.snapshot_item("turn-one", since_call_index=first_checkpoint)
    assert first["call_count"] == 2
    assert first["attribution_complete"] is True
    assert first["summary"]["generative_call_count"] == 1
    assert first["summary"]["vector_store_operation_count"] == 1
    assert first["summary"]["embedding_expected_operation_count"] == 1
    assert first["summary"]["total_tokens"] == 16
    assert first["summary"]["by_stage"] == {"reply_planner": 2}
    assert all(call["item_id"] == "turn-one" for call in first["calls"])
    _assert_raw_free(first)

    second_checkpoint = ledger.checkpoint()
    with ledger.item_scope("turn-two", "product_web"):
        pass
    second = ledger.snapshot_item("turn-two", since_call_index=second_checkpoint)
    assert second["call_count"] == 0
    assert second["summary"]["generative_call_count"] == 0
    assert second["attribution_complete"] is True
    assert first["calls"] == ledger.snapshot_item(
        "turn-one", since_call_index=first_checkpoint
    )["calls"]
    with pytest.raises(ValueError):
        ledger.snapshot_item("unscoped")
    with pytest.raises(ValueError):
        ledger.snapshot_item("turn-two", since_call_index=ledger.checkpoint() + 1)


def test_unscoped_or_other_item_work_in_window_blocks_complete_attribution():
    ledger = ComputeLedger()
    checkpoint = ledger.checkpoint()
    with ledger.item_scope("target", "product_web"):
        _record_generation(ledger)
    _record_generation(ledger)  # lost contextvars / background work
    with ledger.item_scope("another", "product_web"):
        _record_generation(ledger)
    target = ledger.snapshot_item("target", since_call_index=checkpoint)
    assert target["call_count"] == 1
    assert target["unscoped_call_count_during_window"] == 1
    assert target["other_item_call_count_during_window"] == 1
    assert target["attribution_complete"] is False
    receipt = web._product_compute_receipt(ledger, "target", checkpoint, "text")
    assert receipt["status"] == "attribution_ambiguous"
    _assert_raw_free(receipt)


def test_item_receipt_scrubs_free_form_model_options_without_losing_usage():
    ledger = ComputeLedger()
    checkpoint = ledger.checkpoint()
    with ledger.item_scope("private-options", "product_web"):
        ledger.record_native_ollama_chat(
            {
                "model": "fake-local",
                "messages": [{"role": "user", "content": RAW_PROMPT}],
                "options": {"temperature": 0, "stop": [RAW_PROMPT]},
            },
            {
                "message": {"content": RAW_REPLY},
                "prompt_eval_count": 11,
                "eval_count": 5,
            },
            0.25,
        )
    receipt = web._product_compute_receipt(ledger, "private-options", checkpoint, "text")
    assert receipt["status"] == "captured"
    assert receipt["snapshot"]["summary"]["total_tokens"] == 16
    _assert_raw_free(receipt)
    assert receipt["snapshot"]["calls"][0]["request"]["options_key_count"] == 2
    assert "options" not in receipt["snapshot"]["calls"][0]["request"]
    # The additive item projection must not mutate the frozen legacy schema.
    assert ledger.snapshot()["calls"][0]["request"]["options"]["stop"] == [RAW_PROMPT]


def test_local_generation_option_names_and_values_are_not_in_item_receipt():
    ledger = ComputeLedger()
    checkpoint = ledger.checkpoint()
    with ledger.item_scope("local-options", "product_web"):
        ledger.record_local_generation(
            model="fake-local",
            prompt_text=RAW_PROMPT,
            prompt_tokens=7,
            completion_text=RAW_REPLY,
            completion_tokens=3,
            generation_options={RAW_PROMPT: RAW_REPLY, "stop": [RAW_PROMPT]},
            latency_seconds=0.4,
        )
    item = ledger.snapshot_item("local-options", since_call_index=checkpoint)
    assert item["summary"]["total_tokens"] == 10
    assert item["calls"][0]["request"]["options_key_count"] == 2
    assert "options" not in item["calls"][0]["request"]
    _assert_raw_free(item)
    assert ledger.snapshot()["calls"][0]["request"]["options"][RAW_PROMPT] == RAW_REPLY


class _FakeBrain:
    def __init__(self, ledger, actions):
        self.compute_ledger = ledger
        self.actions = iter(actions)

    def run_turn_debug(self, user_text, input_context=None):
        action = next(self.actions)
        if action in {"generation", "heavy_generation"}:
            with self.compute_ledger.stage("reply_planner"):
                _record_generation(self.compute_ledger)
                for _ in range(11 if action == "heavy_generation" else 1):
                    _record_vector(self.compute_ledger)
        elif action == "openai_missing_total":
            self.compute_ledger.record_chat_completion(
                {"model": "fake-local", "messages": [{"role": "user", "content": RAW_PROMPT}]},
                SimpleNamespace(
                    choices=[SimpleNamespace(message=SimpleNamespace(content=RAW_REPLY))],
                    usage=SimpleNamespace(prompt_tokens=11, completion_tokens=5, total_tokens=None),
                ),
                0.25,
            )
        elif action == "provider_failure":
            error = RuntimeError("private-provider-error-49a0")
            _record_generation(self.compute_ledger, error=error)
            raise error
        elif action == "generation_with_unscoped":
            _record_generation(self.compute_ledger)
            worker = threading.Thread(target=_record_generation, args=(self.compute_ledger,))
            worker.start()
            worker.join()
        return {
            "reply": "そうなんだ。ちゃんと聞いてるよ。",
            "logic": {"intent": "chat", "routing_path": "high_road"},
            "memory_data": {"episodes": []},
            "runtime_trace": {"blackboard": [
                {"stage": "observe", "label": "perception", "payload": {"source": "current_turn"}},
                {"stage": "surface", "label": "utterance", "payload": {"text": "そうなんだ。ちゃんと聞いてるよ。"}},
            ]},
            "runtime_state": {},
            "episode_doc": f"User: {user_text} | Uruha: そうなんだ。ちゃんと聞いてるよ。",
        }


class _FakeRuntime:
    def __init__(self, ledger, actions):
        self._compute_ledger = ledger
        self._brain = _FakeBrain(ledger, actions)
        self._lock = threading.Lock()
        self._brain_load_trace = {"status": "ready", "elapsed_seconds": 0.0}
        self._turn_index = 0

    def mark_activity(self):
        pass

    def get_brain(self):
        return self._brain

    def next_turn_meta(self):
        self._turn_index += 1
        return "isolated-test", self._turn_index

    def scheduler_trace(self):
        return {"schema": "test_scheduler", "human_waiters": 1}


def _private_web_log(monkeypatch, tmp_path):
    log_dir = tmp_path / "web_logs"
    log_dir.mkdir(mode=0o700)
    log_dir.chmod(0o700)
    monkeypatch.setattr(web, "WEB_LOG_JSONL", str(log_dir / "conversation.jsonl"))
    monkeypatch.setattr(web, "WEB_LOG_TXT", str(log_dir / "conversation.txt"))
    return log_dir


def _graph_cost_payload(result):
    rows = result["cognition_trace"]["runtime_trace"]["blackboard"]
    matching = [row for row in rows if row.get("label") == "product_turn_compute_receipt_p4"]
    assert len(matching) == 1
    assert rows.index(matching[0]) > next(
        index for index, row in enumerate(rows) if row.get("label") == "utterance"
    )
    return matching[0]["payload"]


def test_web_two_turns_keep_reply_and_join_private_log_graph_and_receipt(monkeypatch, tmp_path):
    log_dir = _private_web_log(monkeypatch, tmp_path)
    monkeypatch.setattr(web, "RUNTIME", _FakeRuntime(ComputeLedger(), ["generation", "zero"]))
    results = []
    for user_text in ("第一個測試", "第二個測試"):
        result = web._run_turn(user_text, auto_tts=False)
        assert result["reply"] == "そうなんだ。ちゃんと聞いてるよ。"
        assert result["logic"]["intent"] == "chat"
        assert result["logic"]["routing_path"] == "high_road"
        assert result["memory_snapshot"]["episodes"] == []
        _assert_raw_free(result["compute_receipt"])
        card = _graph_cost_payload(result)
        assert card["item_id"] == result["compute_receipt"]["item_id"]
        assert card["contains_raw_prompt_or_reply"] is False
        assert RAW_PROMPT not in json.dumps(card, ensure_ascii=False)
        assert RAW_REPLY not in json.dumps(card, ensure_ascii=False)
        assert "product_turn_compute_receipt_p4" in result["flow_html"]
        record = web._append_conversation_log("text", result)
        assert record["compute_receipt_item_id"] == card["item_id"]
        assert record["compute_receipt"]["item_id"] == card["item_id"]
        assert record["compute_receipt_private_persisted"] is True
        assert result["compute_receipt_durable_status"] == "private_jsonl"
        results.append(result)

    first, second = results
    assert first["compute_receipt"]["item_id"] != second["compute_receipt"]["item_id"]
    assert first["compute_receipt"]["status"] == "captured"
    assert first["compute_receipt"]["snapshot"]["summary"]["total_tokens"] == 16
    assert second["compute_receipt"]["status"] == "scoped_zero_generation"
    assert second["compute_receipt"]["snapshot"]["summary"]["generative_call_count"] == 0
    lines = [json.loads(line) for line in (log_dir / "conversation.jsonl").read_text(encoding="utf-8").splitlines()]
    assert len(lines) == 2
    assert [row["turn_index"] for row in lines] == [1, 2]
    assert [row["compute_receipt_item_id"] for row in lines] == [
        result["compute_receipt"]["item_id"] for result in results
    ]
    assert (log_dir / "conversation.jsonl").stat().st_mode & 0o777 == 0o600


def test_private_web_fifty_turns_retire_scoped_calls_without_changing_receipts(monkeypatch, tmp_path):
    log_dir = _private_web_log(monkeypatch, tmp_path)
    ledger = ComputeLedger()
    monkeypatch.setattr(web, "RUNTIME", _FakeRuntime(ledger, ["heavy_generation"] * 50))
    first_receipt = None
    first_call_indices = None
    for index in range(50):
        result = web._run_turn(f"isolated test {index}", auto_tts=False)
        receipt = result["compute_receipt"]
        assert receipt["status"] == "captured"
        assert receipt["snapshot"]["call_count"] == 12
        assert receipt["snapshot"]["summary"]["total_tokens"] == 16
        assert _graph_cost_payload(result)["item_id"] == receipt["item_id"]
        record = web._append_conversation_log("text", result)
        assert record["compute_receipt"]["item_id"] == receipt["item_id"]
        assert result["compute_ledger_retention_status"] == "retired"
        assert len(ledger._calls) == 0
        if index == 0:
            first_receipt = json.loads(json.dumps(receipt))
            first_call_indices = [call["call_index"] for call in receipt["snapshot"]["calls"]]
    assert ledger.checkpoint() == 600
    assert first_call_indices == list(range(1, 13))
    saved_first = json.loads((log_dir / "conversation.jsonl").read_text(encoding="utf-8").splitlines()[0])
    assert first_receipt["snapshot"]["calls"] == saved_first["compute_receipt"]["snapshot"]["calls"]
    assert (log_dir / "conversation.jsonl").stat().st_size > 0
    _assert_raw_free(first_receipt)
    with pytest.raises(RuntimeError, match="full_snapshot_unavailable"):
        ledger.snapshot()
    with pytest.raises(RuntimeError, match="reset_requires_new_ledger"):
        ledger.reset()


def test_retirement_keeps_late_work_and_stale_checkpoint_fails_closed():
    ledger = ComputeLedger()
    checkpoint = ledger.checkpoint()
    with ledger.item_scope("first", "product_web"):
        _record_generation(ledger)
    first = ledger.snapshot_item("first", since_call_index=checkpoint)
    _record_generation(ledger)  # late unscoped work: not part of the frozen window
    assert ledger.retire_item_snapshot(first) == 1
    assert ledger.checkpoint() == 2
    assert [call["call_index"] for call in ledger._calls] == [2]
    with pytest.raises(ValueError, match="checkpoint_contains_retired_calls"):
        ledger.snapshot_item("first", since_call_index=checkpoint)
    later_checkpoint = ledger.checkpoint()
    with ledger.item_scope("second", "product_web"):
        _record_generation(ledger)
    second = ledger.snapshot_item("second", since_call_index=later_checkpoint)
    assert second["attribution_complete"] is True
    assert [call["call_index"] for call in second["calls"]] == [3]
    assert ledger.retire_item_snapshot(second) == 1
    assert [call["call_index"] for call in ledger._calls] == [2]


def test_out_of_order_private_web_logging_retires_exact_items(monkeypatch, tmp_path):
    _private_web_log(monkeypatch, tmp_path)
    ledger = ComputeLedger()
    monkeypatch.setattr(web, "RUNTIME", _FakeRuntime(ledger, ["generation", "generation"]))
    first = web._run_turn("first", auto_tts=False)
    second = web._run_turn("second", auto_tts=False)
    assert len(ledger._calls) == 4
    web._append_conversation_log("text", second)
    assert [call["item_id"] for call in ledger._calls] == [first["compute_receipt"]["item_id"]] * 2
    web._append_conversation_log("text", first)
    assert len(ledger._calls) == 0
    assert first["compute_ledger_retention_status"] == "retired"
    assert second["compute_ledger_retention_status"] == "retired"
    assert ledger.checkpoint() == 4


def test_ambiguous_snapshot_is_not_retired_even_if_privately_written(monkeypatch, tmp_path):
    _private_web_log(monkeypatch, tmp_path)
    ledger = ComputeLedger()
    monkeypatch.setattr(web, "RUNTIME", _FakeRuntime(ledger, ["generation_with_unscoped"]))
    result = web._run_turn("ambiguous", auto_tts=False)
    receipt = result["compute_receipt"]
    assert receipt["status"] == "attribution_ambiguous"
    assert receipt["snapshot"]["unscoped_call_count_during_window"] == 1
    web._append_conversation_log("text", result)
    assert result["compute_ledger_retention_status"] == "held_ambiguous"
    assert len(ledger._calls) == 2


def test_zero_call_snapshot_retirement_does_not_invalidate_next_checkpoint():
    ledger = ComputeLedger()
    checkpoint = ledger.checkpoint()
    with ledger.item_scope("empty", "product_web"):
        pass
    empty = ledger.snapshot_item("empty", since_call_index=checkpoint)
    assert ledger.retire_item_snapshot(empty) == 0
    assert ledger.snapshot()["call_count"] == 0
    with ledger.item_scope("later", "product_web"):
        _record_generation(ledger)
    later = ledger.snapshot_item("later", since_call_index=checkpoint)
    assert later["attribution_complete"] is True
    assert later["calls"][0]["call_index"] == 1


def test_jsonl_failure_does_not_retire_but_txt_failure_after_jsonl_does(monkeypatch, tmp_path):
    log_dir = _private_web_log(monkeypatch, tmp_path)
    ledger = ComputeLedger()
    monkeypatch.setattr(web, "RUNTIME", _FakeRuntime(ledger, ["generation", "generation"]))
    first = web._run_turn("jsonl fails", auto_tts=False)
    original_dumps = web.json.dumps

    def fail_log_row(value, *args, **kwargs):
        if isinstance(value, dict) and "cognition_trace" in value and "timestamp" in value:
            raise TypeError("injected-jsonl-serialization-error")
        return original_dumps(value, *args, **kwargs)

    with monkeypatch.context() as patch:
        patch.setattr(web.json, "dumps", fail_log_row)
        with pytest.raises(TypeError, match="injected-jsonl"):
            web._append_conversation_log("text", first)
    assert len(ledger._calls) == 2
    assert (log_dir / "conversation.jsonl").stat().st_size == 0

    second = web._run_turn("txt fails", auto_tts=False)
    monkeypatch.setattr(web, "WEB_LOG_TXT", str(tmp_path / "missing" / "conversation.txt"))
    with pytest.raises(FileNotFoundError):
        web._append_conversation_log("text", second)
    assert second["compute_ledger_retention_status"] == "retired"
    assert [call["item_id"] for call in ledger._calls] == [first["compute_receipt"]["item_id"]] * 2
    saved = json.loads((log_dir / "conversation.jsonl").read_text(encoding="utf-8"))
    assert saved["compute_receipt_item_id"] == second["compute_receipt"]["item_id"]


def test_truncated_private_log_tail_cannot_authorize_retirement(monkeypatch, tmp_path):
    log_dir = _private_web_log(monkeypatch, tmp_path)
    path = log_dir / "conversation.jsonl"
    path.write_bytes(b'{"partial":')
    ledger = ComputeLedger()
    monkeypatch.setattr(web, "RUNTIME", _FakeRuntime(ledger, ["generation"]))
    result = web._run_turn("truncated-tail case", auto_tts=False)
    web._append_conversation_log("text", result)
    assert web._latest_private_log_row() is None
    assert result["compute_receipt_durable_status"] == "unavailable_private_log_row_unverified"
    assert result["compute_ledger_retention_status"] == "held_unverified_private_log"
    assert len(ledger._calls) == 2


def test_retirement_rechecks_ambiguous_window_even_if_snapshot_flag_changes():
    ledger = ComputeLedger()
    checkpoint = ledger.checkpoint()
    with ledger.item_scope("target", "product_web"):
        _record_generation(ledger)
    _record_generation(ledger)
    snapshot = ledger.snapshot_item("target", since_call_index=checkpoint)
    assert snapshot["attribution_complete"] is False
    snapshot["attribution_complete"] = True
    with pytest.raises(ValueError, match="snapshot_window_changed_or_ambiguous"):
        ledger.retire_item_snapshot(snapshot)
    assert ledger.snapshot()["call_count"] == 2


@pytest.mark.parametrize("directory_mode,file_mode", [(0o755, 0o600), (0o700, 0o644)])
def test_unsafe_log_never_persists_full_receipt(monkeypatch, tmp_path, directory_mode, file_mode):
    log_dir = tmp_path / "web_logs"
    log_dir.mkdir(mode=directory_mode)
    log_dir.chmod(directory_mode)
    log_path = log_dir / "conversation.jsonl"
    log_path.touch(mode=file_mode)
    log_path.chmod(file_mode)
    monkeypatch.setattr(web, "WEB_LOG_JSONL", str(log_path))
    monkeypatch.setattr(web, "WEB_LOG_TXT", str(tmp_path / "conversation.txt"))
    ledger = ComputeLedger()
    monkeypatch.setattr(web, "RUNTIME", _FakeRuntime(ledger, ["generation"]))
    result = web._run_turn("test", auto_tts=False)
    record = web._append_conversation_log("text", result)
    assert "compute_receipt" not in record
    assert record["compute_receipt_private_persisted"] is False
    assert result["compute_receipt_durable_status"] == "unavailable_nonprivate_log"
    assert result["compute_ledger_retention_status"] == "held_nonprivate_log"
    assert len(ledger._calls) == 2
    saved = json.loads(log_path.read_text(encoding="utf-8"))
    assert "compute_receipt" not in saved
    assert saved["compute_receipt_item_id"] == _graph_cost_payload(result)["item_id"]


def test_missing_provider_total_is_partial_and_graph_shows_prompt_plus_completion(monkeypatch):
    monkeypatch.setattr(web, "RUNTIME", _FakeRuntime(ComputeLedger(), ["openai_missing_total"]))
    result = web._run_turn("sum token case", auto_tts=False)
    receipt = result["compute_receipt"]
    summary = receipt["snapshot"]["summary"]
    assert receipt["status"] == "partial_provider_total"
    assert summary["generative_token_accounting_complete"] is True
    assert summary["provider_total_token_accounting_complete"] is False
    assert summary["total_tokens"] == 0  # Native provider total was absent; do not display this as zero cost.
    assert summary["summed_prompt_plus_completion_tokens"] == 16
    card = _graph_cost_payload(result)
    assert card["status"] == "partial_provider_total"
    assert "P+C 16（總量未回報）" in card["summary"]
    assert "token 0" not in card["summary"]
    assert "P+C 16" in result["flow_html"]
    _assert_raw_free(receipt)


def test_provider_terminal_failure_is_raw_free_private_and_reraised(monkeypatch, tmp_path):
    log_dir = _private_web_log(monkeypatch, tmp_path)
    ledger = ComputeLedger()
    monkeypatch.setattr(web, "RUNTIME", _FakeRuntime(ledger, ["provider_failure"]))
    with pytest.raises(RuntimeError, match="private-provider-error-49a0"):
        web._run_turn("failure case", auto_tts=False)
    failure_path = log_dir / "compute_failures.jsonl"
    rows = [json.loads(line) for line in failure_path.read_text(encoding="utf-8").splitlines()]
    assert len(rows) == 1
    receipt = rows[0]
    assert len(receipt["item_id"]) == 32
    assert receipt["terminal_error_type"] == "RuntimeError"
    assert receipt["snapshot"]["summary"]["failed_call_count"] == 1
    assert receipt["status"] == "terminal_error"
    assert receipt["accounting_status"] == "partial_token_usage"
    assert "private-provider-error-49a0" not in json.dumps(receipt, ensure_ascii=False)
    _assert_raw_free(receipt)
    assert failure_path.stat().st_mode & 0o777 == 0o600
    assert not (log_dir / "conversation.jsonl").exists()
    assert ledger.checkpoint() == 1
    assert len(ledger._calls) == 0


def test_provider_failure_without_private_evidence_keeps_call(monkeypatch, tmp_path):
    log_dir = tmp_path / "unsafe_web_logs"
    log_dir.mkdir(mode=0o755)
    log_dir.chmod(0o755)
    monkeypatch.setattr(web, "WEB_LOG_JSONL", str(log_dir / "conversation.jsonl"))
    ledger = ComputeLedger()
    monkeypatch.setattr(web, "RUNTIME", _FakeRuntime(ledger, ["provider_failure"]))
    with pytest.raises(RuntimeError, match="private-provider-error-49a0"):
        web._run_turn("unsafe failure", auto_tts=False)
    assert not (log_dir / "compute_failures.jsonl").exists()
    assert len(ledger._calls) == 1
    assert ledger.snapshot()["calls"][0]["error_type"] == "RuntimeError"


def test_brain_initialization_failure_is_terminal_unavailable_not_zero(monkeypatch, tmp_path):
    log_dir = _private_web_log(monkeypatch, tmp_path)
    runtime = _FakeRuntime(ComputeLedger(), [])

    def fail_load():
        raise RuntimeError("private-initialization-detail")

    runtime._brain = None
    runtime.get_brain = fail_load
    monkeypatch.setattr(web, "RUNTIME", runtime)
    with pytest.raises(RuntimeError, match="private-initialization-detail"):
        web._run_turn("initialization failure", auto_tts=False)
    row = json.loads((log_dir / "compute_failures.jsonl").read_text(encoding="utf-8"))
    assert row["status"] == "terminal_error"
    assert row["accounting_status"] == "unavailable_brain_not_instrumented"
    assert row["failure_phase"] == "brain_initialization"
    assert row["coverage"]["instrumented_generation_and_vector_operations"] is False
    assert "private-initialization-detail" not in json.dumps(row, ensure_ascii=False)
    assert not (log_dir / "conversation.jsonl").exists()


def test_late_or_missing_brain_instrumentation_is_unavailable_not_zero(monkeypatch):
    ledger = ComputeLedger()
    runtime = _FakeRuntime(ledger, ["zero"])
    runtime._brain.compute_ledger = None
    monkeypatch.setattr(web, "RUNTIME", runtime)
    result = web._run_turn("late attachment", auto_tts=False)
    assert result["compute_receipt"]["status"] == "unavailable_brain_not_instrumented"
    assert result["compute_receipt"]["snapshot"] is None
    assert result["compute_receipt"]["coverage"]["instrumented_generation_and_vector_operations"] is False
    assert _graph_cost_payload(result)["status"] == "unavailable_brain_not_instrumented"


def test_optin_does_not_change_same_fake_turn_visible_reply_or_memory_fields(monkeypatch):
    plain = _FakeRuntime(None, ["zero"])
    monkeypatch.setattr(web, "RUNTIME", plain)
    before = web._run_turn("same input", auto_tts=False)
    instrumented = _FakeRuntime(ComputeLedger(), ["zero"])
    monkeypatch.setattr(web, "RUNTIME", instrumented)
    after = web._run_turn("same input", auto_tts=False)
    for field in ("user_text", "reply", "audio_path", "episode_doc", "memory_snapshot"):
        assert after[field] == before[field]
    for field in ("intent", "routing_path"):
        assert after["logic"][field] == before["logic"][field]
    assert "compute_receipt" not in before
    assert not any(
        row.get("label") == "product_turn_compute_receipt_p4"
        for row in before["cognition_trace"]["runtime_trace"]["blackboard"]
    )
    assert after["compute_receipt"]["status"] == "scoped_zero_generation"


@pytest.mark.parametrize("enabled", [False, True])
def test_runtime_optin_is_constructed_before_brain_and_default_stays_plain(monkeypatch, enabled):
    created = []

    def fake_brain(**kwargs):
        created.append(kwargs)
        return SimpleNamespace(compute_ledger=kwargs.get("compute_ledger"))

    monkeypatch.setattr(web, "WEB_COMPUTE_LEDGER_ENABLED", enabled)
    monkeypatch.setattr(web.RuntimeManager, "_idle_consolidation_loop", lambda self: None)
    monkeypatch.setattr(web, "UruhaBrainV4_Mac", fake_brain)
    manager = web.RuntimeManager()
    brain = manager.get_brain()
    assert len(created) == 1
    if enabled:
        assert isinstance(manager._compute_ledger, ComputeLedger)
        assert created[0]["compute_ledger"] is manager._compute_ledger
        assert brain.compute_ledger is manager._compute_ledger
    else:
        assert manager._compute_ledger is None
        assert created[0] == {}
