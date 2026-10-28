"""Zero-model contracts for browser-bound page-load graph hydration.

Synthetic private rows prove the display guard, not fresh model output or
Safari reload behavior.  The older observatory's backward-scanning helper is
deliberately not used for page-load authorization.
"""

from copy import deepcopy
import json

import pytest

import uruha_web_ui as web
from test_p4_web_final_graph_evidence_delivery import _finalize, _web_result


@pytest.fixture
def private_positive(monkeypatch, tmp_path):
    result = _web_result(monkeypatch)
    assert "BOUNDED SLOT LEDGER" in _finalize(result)
    log_dir = tmp_path / "private-web-logs"
    log_dir.mkdir(mode=0o700)
    log_dir.chmod(0o700)
    log_path = log_dir / "conversation.jsonl"
    monkeypatch.setattr(web, "WEB_LOG_JSONL", str(log_path))
    monkeypatch.setattr(web, "WEB_LOG_TXT", str(log_dir / "conversation.txt"))
    monkeypatch.setattr(web.RUNTIME, "_session_id", "browser-h-session")
    monkeypatch.setattr(web.RUNTIME, "_turn_index", 1)
    monkeypatch.setattr(web.RUNTIME, "next_turn_meta", lambda: ("browser-h-session", 1))
    record = web._append_conversation_log("text", result)
    assert record["episode_doc"] == result["episode_doc"]
    assert log_path.stat().st_mode & 0o777 == 0o600
    client = web._client_turn_record_m24(
        record,
        web._client_cognition_payload_m24(result["cognition_trace"]),
        web._client_memory_payload_m24(result["memory_snapshot"]),
    )
    receipt = web._mint_browser_graph_receipt(client, "browser-h-session")
    assert set(receipt) == {"schema", "session_id", "turn_index", "mac"}
    return {
        "result": result,
        "record": record,
        "client": client,
        "receipt": receipt,
        "log_dir": log_dir,
        "log_path": log_path,
    }


def _assert_blank(html, private_positive):
    assert private_positive["record"]["user_text"] not in html
    assert "BOUNDED SLOT LEDGER" not in html
    assert '<path class="brain-edge is-atomic-delivery"' not in html


def test_latest_private_row_and_same_browser_receipt_restore_only_genuine_graph(private_positive):
    record, raw_row = web._latest_private_log_row()
    assert record == private_positive["record"]
    assert isinstance(raw_row, bytes)
    assert raw_row == private_positive["log_path"].read_bytes().rstrip(b"\n")
    html = web._load_browser_graph(private_positive["receipt"])
    assert "BOUNDED SLOT LEDGER" in html
    assert html.count('<path class="brain-edge is-atomic-delivery"') == 6
    assert private_positive["record"]["user_text"] in html
    assert private_positive["result"]["episode_doc"] not in html


@pytest.mark.parametrize("input_mode,authorized", [
    ("audio", True),
    ("autonomous_proactive", False),
])
def test_only_delivered_human_text_or_audio_row_can_mint_receipt(
    private_positive, input_mode, authorized,
):
    record = deepcopy(private_positive["record"])
    record["input_mode"] = input_mode
    private_positive["log_path"].write_text(
        json.dumps(record, ensure_ascii=False) + "\n", encoding="utf-8",
    )
    receipt = web._mint_browser_graph_receipt(
        private_positive["client"], "browser-h-session",
    )
    if authorized:
        assert set(receipt) == {"schema", "session_id", "turn_index", "mac"}
        assert "BOUNDED SLOT LEDGER" in web._load_browser_graph(receipt)
    else:
        assert receipt == web._browser_graph_tombstone()
        _assert_blank(web._load_browser_graph(receipt), private_positive)


def test_browser_state_receipt_is_compact_and_contains_no_raw_episode(private_positive):
    payload = json.dumps(private_positive["receipt"], ensure_ascii=False)
    assert len(payload.encode("utf-8")) < 512
    for secret_text in (
        private_positive["result"]["episode_doc"],
        private_positive["record"]["user_text"],
        private_positive["record"]["assistant_reply"],
        "episode_doc",
        "memory_snapshot",
        "cognition_trace",
    ):
        assert secret_text not in payload
    client_payload = json.dumps(private_positive["client"], ensure_ascii=False)
    assert private_positive["result"]["episode_doc"] not in client_payload
    assert "episode_doc" not in private_positive["client"]


@pytest.mark.parametrize("fault", [
    "absent", "empty", "nonsense", "wrong_mac", "wrong_session",
    "wrong_turn", "extra_field", "tombstone",
])
def test_missing_or_forged_browser_proof_never_displays_private_graph(private_positive, fault):
    receipt = deepcopy(private_positive["receipt"])
    if fault == "absent":
        receipt = None
    elif fault == "empty":
        receipt = {}
    elif fault == "nonsense":
        receipt = "not-a-receipt"
    elif fault == "wrong_mac":
        receipt["mac"] = "0" * 64 if receipt["mac"] != "0" * 64 else "1" * 64
    elif fault == "wrong_session":
        receipt["session_id"] = "another-browser-session"
    elif fault == "wrong_turn":
        receipt["turn_index"] += 1
    elif fault == "extra_field":
        receipt["user_text"] = private_positive["record"]["user_text"]
    else:
        receipt = web._browser_graph_tombstone()
        assert isinstance(receipt, dict) and receipt
    _assert_blank(web._load_browser_graph(receipt), private_positive)


def test_runtime_session_change_invalidates_old_receipt_and_late_mint(monkeypatch, private_positive):
    old_receipt = private_positive["receipt"]
    monkeypatch.setattr(web.RUNTIME, "_session_id", "reset-session")
    _assert_blank(web._load_browser_graph(old_receipt), private_positive)
    late = web._mint_browser_graph_receipt(
        private_positive["client"], expected_session_id="browser-h-session",
    )
    assert late == web._browser_graph_tombstone()
    _assert_blank(web._load_browser_graph(late), private_positive)


@pytest.mark.parametrize("change", ["session", "turn_index"])
def test_reset_or_new_turn_during_graph_render_discards_stale_html(
    monkeypatch, private_positive, change,
):
    def render_then_change(_result):
        if change == "session":
            monkeypatch.setattr(web.RUNTIME, "_session_id", "reset-during-render")
        else:
            monkeypatch.setattr(web.RUNTIME, "_turn_index", 2)
        return "PRIVATE_GRAPH_RENDERED_BEFORE_RESET"

    monkeypatch.setattr(web, "_render_flow_html", render_then_change)
    html = web._load_browser_graph(private_positive["receipt"])
    assert "PRIVATE_GRAPH_RENDERED_BEFORE_RESET" not in html
    _assert_blank(html, private_positive)


@pytest.mark.parametrize("fault", ["changed_value", "same_json_different_bytes", "no_final_newline"])
def test_changed_or_incomplete_latest_row_invalidates_mac(private_positive, fault):
    path = private_positive["log_path"]
    original = path.read_bytes()
    if fault == "changed_value":
        changed = deepcopy(private_positive["record"])
        changed["assistant_reply"] += " altered"
        path.write_text(json.dumps(changed, ensure_ascii=False) + "\n", encoding="utf-8")
    elif fault == "same_json_different_bytes":
        path.write_text(
            json.dumps(private_positive["record"], ensure_ascii=False, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        assert json.loads(path.read_text(encoding="utf-8")) == private_positive["record"]
        assert path.read_bytes() != original
    else:
        path.write_bytes(original[:-1])
        assert web._latest_private_log_row() is None
    _assert_blank(web._load_browser_graph(private_positive["receipt"]), private_positive)


def test_truncated_latest_line_never_revives_previous_positive(private_positive):
    path = private_positive["log_path"]
    with path.open("ab") as handle:
        handle.write(b'{"session_id":"browser-h-session","turn_index":2')
    assert web._latest_private_log_row() is None
    _assert_blank(web._load_browser_graph(private_positive["receipt"]), private_positive)


def test_corrupt_encoded_latest_row_never_revives_private_graph(private_positive):
    path = private_positive["log_path"]
    disk = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(disk["cognition_trace"], str)
    disk["turn_index"] = 2
    disk["cognition_trace_codec"]["sha256"] = "0" * 64
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(disk, ensure_ascii=False) + "\n")
    assert web._latest_private_log_row() is None
    _assert_blank(web._load_browser_graph(private_positive["receipt"]), private_positive)


def test_valid_latest_negative_does_not_revive_prior_ledger(monkeypatch, private_positive):
    latest = {
        "timestamp": "2026-10-21T12:00:00",
        "session_id": "browser-h-session",
        "turn_index": 2,
        "input_mode": "text",
        "user_text": "LATEST_NEGATIVE_USER_SIGNAL",
        "assistant_reply": "LATEST_NEGATIVE_REPLY",
        "planner_debug": {},
        "logic": {},
        "cognition_trace": {},
        "memory_snapshot": {},
    }
    with private_positive["log_path"].open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(latest, ensure_ascii=False) + "\n")
    monkeypatch.setattr(web.RUNTIME, "_turn_index", 2)
    _assert_blank(web._load_browser_graph(private_positive["receipt"]), private_positive)
    latest_receipt = web._mint_browser_graph_receipt(latest, "browser-h-session")
    assert set(latest_receipt) == {"schema", "session_id", "turn_index", "mac"}
    html = web._load_browser_graph(latest_receipt)
    assert latest["user_text"] in html
    assert private_positive["record"]["user_text"] not in html
    assert "BOUNDED SLOT LEDGER" not in html
    assert '<path class="brain-edge is-atomic-delivery"' not in html


@pytest.mark.parametrize("fault", ["public_dir", "public_file", "symlink", "hardlink"])
def test_nonprivate_or_linked_log_never_hydrates(monkeypatch, private_positive, fault):
    path = private_positive["log_path"]
    if fault == "public_dir":
        private_positive["log_dir"].chmod(0o755)
    elif fault == "public_file":
        path.chmod(0o644)
    elif fault == "symlink":
        target = private_positive["log_dir"] / "moved-private.jsonl"
        path.rename(target)
        path.symlink_to(target)
    else:
        twin = private_positive["log_dir"] / "linked-private.jsonl"
        twin.hardlink_to(path)
    assert web._latest_private_log_row() is None
    _assert_blank(web._load_browser_graph(private_positive["receipt"]), private_positive)
    assert web._mint_browser_graph_receipt(
        private_positive["client"], "browser-h-session",
    ) == web._browser_graph_tombstone()


def _surface_update(size, client_record):
    update = [f"surface-{index}" for index in range(size)]
    update[10] = client_record
    return tuple(update)


@pytest.mark.parametrize("wrapper_name,underlying_name,args,size", [
    (
        "submit_text_browser_bound", "submit_text",
        ("message", [], False, 7.0, "enqueue-session"), 13,
    ),
    (
        "submit_audio_browser_bound", "submit_audio",
        ("recording.wav", [], False, 7.0, "enqueue-session"), 14,
    ),
    (
        "handle_audio_stop_browser_bound", "handle_audio_stop",
        ("recording.wav", [], False, True, 7.0, "enqueue-session"), 14,
    ),
])
def test_text_and_audio_wrappers_mint_only_on_final_client_turn(
    monkeypatch, wrapper_name, underlying_name, args, size,
):
    client = {"session_id": "enqueue-session", "turn_index": 1}
    partials = [
        _surface_update(size, web.gr.skip()),
        _surface_update(size, {}),
        _surface_update(size, web.gr.skip()),
    ]
    final = _surface_update(size, client)

    def stream(*_args):
        yield from (*partials, final)

    monkeypatch.setattr(web, underlying_name, stream)
    calls = []

    def mint(row, expected_session_id):
        calls.append((row, expected_session_id))
        return {"authorized": True}

    monkeypatch.setattr(web, "_mint_browser_graph_receipt", mint)
    updates = list(getattr(web, wrapper_name)(*args))
    assert len(updates) == 4
    assert all(update[:-1] == old for update, old in zip(updates, (*partials, final)))
    assert all(update[-1] == web.gr.skip() for update in updates[:-1])
    assert updates[-1][-1] == {"authorized": True}
    assert calls == [(client, "enqueue-session")]


@pytest.mark.parametrize("wrapper_name,underlying_name,args,size", [
    (
        "submit_text_browser_bound", "submit_text",
        ("", [], False, 0.0, "enqueue-session"), 13,
    ),
    (
        "submit_audio_browser_bound", "submit_audio",
        (None, [], False, 0.0, "enqueue-session"), 14,
    ),
    (
        "handle_audio_stop_browser_bound", "handle_audio_stop",
        ("recording.wav", [], False, False, 7.0, "enqueue-session"), 14,
    ),
])
def test_empty_failed_or_transcript_only_path_skips_browser_state(
    monkeypatch, wrapper_name, underlying_name, args, size,
):
    monkeypatch.setattr(
        web, underlying_name,
        lambda *_args: iter([_surface_update(size, web.gr.skip())]),
    )

    def forbidden_mint(*_args):
        pytest.fail("non-final delivery minted a browser receipt")

    monkeypatch.setattr(web, "_mint_browser_graph_receipt", forbidden_mint)
    updates = list(getattr(web, wrapper_name)(*args))
    assert len(updates) == 1
    assert updates[0][-1] == web.gr.skip()


@pytest.mark.parametrize("wrapper_name,underlying_name,args,size", [
    (
        "submit_text_browser_bound", "submit_text",
        ("message", [], False, 7.0, "browser-h-session"), 13,
    ),
    (
        "submit_audio_browser_bound", "submit_audio",
        ("recording.wav", [], False, 7.0, "browser-h-session"), 14,
    ),
])
@pytest.mark.parametrize("reset_phase", ["queued", "in_flight"])
def test_reset_before_queued_or_inflight_final_cannot_reauthorize_old_browser(
    monkeypatch, private_positive, wrapper_name, underlying_name, args, size,
    reset_phase,
):
    partial = _surface_update(size, web.gr.skip())
    final = _surface_update(size, private_positive["client"])
    monkeypatch.setattr(web, underlying_name, lambda *_args: iter((partial, final)))
    if reset_phase == "queued":
        monkeypatch.setattr(web.RUNTIME, "_session_id", "new-session-after-reset")
        updates = list(getattr(web, wrapper_name)(*args))
    else:
        stream = getattr(web, wrapper_name)(*args)
        first = next(stream)
        monkeypatch.setattr(web.RUNTIME, "_session_id", "new-session-after-reset")
        updates = [first, *stream]
    assert updates[0][-1] == web.gr.skip()
    assert updates[-1][-1] == web._browser_graph_tombstone()
    _assert_blank(web._load_browser_graph(updates[-1][-1]), private_positive)


def test_reset_overwrites_receipt_with_truthy_denial(monkeypatch, private_positive):
    old = private_positive["receipt"]
    assert "BOUNDED SLOT LEDGER" in web._load_browser_graph(old)
    monkeypatch.setattr(web, "reset_session", lambda: tuple(range(13)))
    reset = web.reset_session_browser_bound(web._RESET_INSTANCE_MARKER)
    assert reset[:-1] == tuple(range(13))
    assert reset[-1] == web._browser_graph_tombstone()
    assert isinstance(reset[-1], dict) and reset[-1]
    _assert_blank(web._load_browser_graph(reset[-1]), private_positive)


def test_enqueue_marker_captures_session_at_admission(monkeypatch):
    monkeypatch.setattr(web.RUNTIME, "_session_id", "session-at-enqueue")
    monkeypatch.setattr(web, "begin_human_submission", lambda _value: 12.5)
    assert web.begin_human_submission_with_session("hello") == (
        12.5, "session-at-enqueue",
    )


def test_gradio_bindings_only_hydrate_graph_and_share_human_reset_lane(monkeypatch):
    # Build the real event graph, but never launch a server or execute a model.
    monkeypatch.setattr(
        web, "_latest_observatory_result",
        lambda: pytest.fail("page construction read server-global private graph"),
    )
    demo = web.build_demo()
    components = {component["id"]: component for component in demo.config["components"]}
    browser_ids = [key for key, component in components.items() if component["type"] == "browserstate"]
    assert len(browser_ids) == 1
    browser_id = browser_ids[0]
    assert components[browser_id]["props"]["default_value"] == web._browser_graph_tombstone()

    by_name = {}
    for function_id, dependency in demo.fns.items():
        by_name.setdefault(dependency.fn.__name__, []).append(
            (dependency, demo.config["dependencies"][function_id])
        )
    load_fn, load_event = by_name["_load_browser_graph"][0]
    # Gradio's component id is process-global across prior build_demo() calls;
    # this checks the load event without assuming the first Blocks id is zero.
    assert len(load_event["targets"]) == 1
    assert load_event["targets"][0][1] == "load"
    assert load_event["inputs"] == [browser_id]
    assert len(load_event["outputs"]) == 1
    flow_id = load_event["outputs"][0]
    assert components[flow_id]["type"] == "html"
    assert "BOUNDED SLOT LEDGER" not in components[flow_id]["props"]["value"]
    assert load_event["queue"] is True
    assert load_fn.concurrency_id == "human_turn_m19"
    assert load_fn.concurrency_limit == 1

    wrapper_counts = {
        "submit_text_browser_bound": 2,
        "submit_audio_browser_bound": 1,
        "handle_audio_stop_browser_bound": 1,
        "reset_session_browser_bound": 1,
    }
    for name, count in wrapper_counts.items():
        assert len(by_name[name]) == count
        for fn, event in by_name[name]:
            assert event["outputs"][-1] == browser_id
            assert event["queue"] is True
            assert fn.concurrency_id == "human_turn_m19"
            assert fn.concurrency_limit == 1
            if name != "reset_session_browser_bound":
                assert flow_id in event["outputs"]
    assert len(by_name["begin_exact_text_submission_with_session"]) == 2
    assert len(by_name["begin_exact_audio_submission_with_session"]) == 2
    assert all(
        len(event["outputs"]) == 2
        for name in ("begin_exact_text_submission_with_session", "begin_exact_audio_submission_with_session")
        for _, event in by_name[name]
    )
    for _, event in by_name["poll_proactive_turn"]:
        assert browser_id not in event["outputs"]
