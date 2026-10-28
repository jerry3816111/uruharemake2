"""Zero-model Web contracts for genuine final/reload graph evidence.

These synthetic turns do not establish fresh generation or Safari delivery.
"""

from copy import deepcopy
import json
from types import SimpleNamespace

import pytest

import uruha_web_ui as web
from uruha_web_log_codec import decode_conversation_log_line
from test_p4_typed_act_semantic_ledger import _delivered_graph_result


def _web_result(monkeypatch, case_id="T0"):
    turn = _delivered_graph_result(monkeypatch, case_id)
    # The underlying transaction harness fakes a shortened episode document.
    # Web evidence delivery must instead receive the real save_episode shape.
    logic = turn["logic"]
    turn["psyche_after"] = "calm"
    turn["episode_doc"] = (
        f"Time: 2026-10-20 14:00:00 | Intent: {logic.get('intent', 'chat')} | "
        f"Scene: {logic.get('scene', 'casual')} | "
        f"CognitiveMode: {logic.get('cognitive_mode', 'direct')} | "
        f"PremiseCheck: {logic.get('premise_check', 'accept')} | "
        f"Routing: {logic.get('routing_path', 'high_road')} | "
        f"User: {turn['user_text']} | Summary: {logic.get('jp_summary', '')} | "
        f"Uruha: {turn['reply']} | Mood: calm"
    )
    monkeypatch.setattr(web.RUNTIME, "mark_activity", lambda: None)
    monkeypatch.setattr(
        web.RUNTIME, "get_brain",
        lambda: SimpleNamespace(run_turn_debug=lambda _text: deepcopy(turn)),
    )
    result = web._run_turn(turn["user_text"], False)
    assert result["episode_doc"] == turn["episode_doc"]
    return result


def _finalize(result):
    web._finalize_surface_delivery(result, 1.0, 1.0, 1.0)
    return result["flow_html"]


@pytest.mark.parametrize("case_id", ["T0", "T2"])
def test_final_web_render_preserves_actual_episode_witness_for_ledger(monkeypatch, case_id):
    result = _web_result(monkeypatch, case_id)
    assert "BOUNDED SLOT LEDGER" in result["flow_html"]
    html = _finalize(result)
    assert "BOUNDED SLOT LEDGER" in html
    assert html.count('<path class="brain-edge is-atomic-delivery"') == 6
    assert html.count('marker-end="url(#brain-atomic-arrow)"') == 6
    assert result["episode_doc"] not in html


@pytest.mark.parametrize("bad_doc", ["", "Time: t | User: x | Uruha: 別の答え。 | Mood: calm", "append"])
def test_final_web_render_still_fails_closed_without_matching_episode(monkeypatch, bad_doc):
    result = _web_result(monkeypatch)
    result["episode_doc"] = result["episode_doc"] + " ADDED" if bad_doc == "append" else bad_doc
    html = _finalize(result)
    assert "BOUNDED SLOT LEDGER" not in html
    assert '<path class="brain-edge is-atomic-delivery"' not in html
    assert "M32 · verified" in html


def test_private_log_reload_keeps_witness_but_client_payload_does_not(monkeypatch, tmp_path):
    result = _web_result(monkeypatch)
    assert "BOUNDED SLOT LEDGER" in _finalize(result)
    tmp_path.chmod(0o700)
    monkeypatch.setattr(web, "WEB_LOG_JSONL", str(tmp_path / "conversation.jsonl"))
    monkeypatch.setattr(web, "WEB_LOG_TXT", str(tmp_path / "conversation.txt"))
    monkeypatch.setattr(web.RUNTIME, "next_turn_meta", lambda: ("isolated-test", 1))
    record = web._append_conversation_log("text", result)
    assert record["episode_doc"] == result["episode_doc"]
    raw_saved = (tmp_path / "conversation.jsonl").read_text(encoding="utf-8")
    assert isinstance(json.loads(raw_saved)["cognition_trace"], str)
    saved = decode_conversation_log_line(raw_saved)
    assert saved["episode_doc"] == result["episode_doc"]
    reloaded = web._observatory_result_from_log_record(saved)
    assert reloaded["logic"] == result["logic"]
    assert "BOUNDED SLOT LEDGER" in web._render_flow_html(reloaded)
    assert "BOUNDED SLOT LEDGER" in web._render_flow_html(web._latest_observatory_result())
    client = web._client_turn_record_m24(
        saved,
        web._client_cognition_payload_m24(result["cognition_trace"]),
        web._client_memory_payload_m24(result["memory_snapshot"]),
    )
    assert "episode_doc" not in client
    assert result["episode_doc"] not in json.dumps(client, ensure_ascii=False)
    assert result["episode_doc"] not in result["flow_html"]
    assert (tmp_path / "conversation.jsonl").stat().st_mode & 0o777 == 0o600


@pytest.mark.parametrize("fault", ["missing_doc", "wrong_doc", "extra_doc", "missing_logic", "missing_memory"])
def test_log_reload_does_not_project_unwitnessed_ledger(monkeypatch, fault):
    result = _web_result(monkeypatch)
    record = {
        "user_text": result["user_text"],
        "assistant_reply": result["reply"],
        "logic": deepcopy(result["logic"]),
        "episode_doc": result["episode_doc"],
        "memory_snapshot": deepcopy(result["memory_snapshot"]),
        "cognition_trace": deepcopy(result["cognition_trace"]),
    }
    if fault == "missing_doc":
        record.pop("episode_doc")
    elif fault == "wrong_doc":
        record["episode_doc"] = record["episode_doc"].replace(result["reply"], "別の答え。")
    elif fault == "extra_doc":
        record["episode_doc"] += " ADDED"
    elif fault == "missing_logic":
        record.pop("logic")
    else:
        record["memory_snapshot"] = {}
    html = web._render_flow_html(web._observatory_result_from_log_record(record))
    assert "BOUNDED SLOT LEDGER" not in html
    assert '<path class="brain-edge is-atomic-delivery"' not in html


@pytest.mark.parametrize("missing_snapshot", [None, {}])
def test_final_web_render_fails_closed_when_memory_snapshot_is_missing(monkeypatch, missing_snapshot):
    result = _web_result(monkeypatch)
    result["memory_snapshot"] = missing_snapshot
    html = _finalize(result)
    assert "BOUNDED SLOT LEDGER" not in html
    assert '<path class="brain-edge is-atomic-delivery"' not in html


@pytest.mark.parametrize("directory_mode,file_mode,expect_episode", [
    (0o700, 0o600, True),
    (0o755, 0o600, False),
    (0o700, 0o644, False),
])
def test_episode_log_requires_private_directory_and_file(
    monkeypatch, tmp_path, directory_mode, file_mode, expect_episode,
):
    result = _web_result(monkeypatch)
    log_dir = tmp_path / "web_logs"
    log_dir.mkdir(mode=directory_mode)
    log_dir.chmod(directory_mode)
    log_path = log_dir / "conversation.jsonl"
    log_path.touch(mode=file_mode)
    log_path.chmod(file_mode)
    monkeypatch.setattr(web, "WEB_LOG_JSONL", str(log_path))
    monkeypatch.setattr(web, "WEB_LOG_TXT", str(tmp_path / "conversation.txt"))
    monkeypatch.setattr(web.RUNTIME, "next_turn_meta", lambda: ("isolated-test", 1))
    record = web._append_conversation_log("text", result)
    saved = json.loads(log_path.read_text(encoding="utf-8"))
    assert ("episode_doc" in record) is expect_episode
    assert ("episode_doc" in saved) is expect_episode


def test_annotation_draft_browser_payload_never_contains_private_episode(monkeypatch, tmp_path):
    result = _web_result(monkeypatch)
    source_record = {
        "session_id": "isolated-test", "turn_index": 1,
        "user_text": result["user_text"], "assistant_reply": result["reply"],
        "episode_doc": result["episode_doc"],
    }
    queue_path = tmp_path / "drafts.json"
    queue_path.write_text(json.dumps({
        "drafts": [{"draft_id": "private-source", "source_record": source_record}],
        "summary": {"draft_count": 1},
    }, ensure_ascii=False), encoding="utf-8")
    monkeypatch.setattr(web, "ANNOTATION_DRAFT_QUEUE_JSON_PATH", str(queue_path))
    payload = web._annotation_draft_queue_payload()
    assert result["episode_doc"] not in json.dumps(payload, ensure_ascii=False)
    loaded = web.load_annotation_draft("private-source")
    assert result["episode_doc"] not in json.dumps(loaded, ensure_ascii=False, default=str)
    assert "episode_doc" not in loaded[0]


def test_private_episode_is_not_written_through_symlink_or_hardlink(monkeypatch, tmp_path):
    result = _web_result(monkeypatch)
    tmp_path.chmod(0o700)
    target = tmp_path / "other-private.jsonl"
    target.touch(mode=0o600)
    target.chmod(0o600)
    log_path = tmp_path / "conversation.jsonl"
    monkeypatch.setattr(web, "WEB_LOG_JSONL", str(log_path))
    monkeypatch.setattr(web, "WEB_LOG_TXT", str(tmp_path / "conversation.txt"))
    monkeypatch.setattr(web.RUNTIME, "next_turn_meta", lambda: ("isolated-test", 1))
    log_path.symlink_to(target)
    with pytest.raises(OSError):
        web._append_conversation_log("text", result)
    assert target.read_text(encoding="utf-8") == ""
    log_path.unlink()
    log_path.hardlink_to(target)
    record = web._append_conversation_log("text", result)
    assert "episode_doc" not in record
    assert "episode_doc" not in json.loads(target.read_text(encoding="utf-8"))


def test_ordinary_record_does_not_duplicate_episode_into_private_log(monkeypatch, tmp_path):
    result = _web_result(monkeypatch)
    result["logic"] = {}
    monkeypatch.setattr(web, "WEB_LOG_JSONL", str(tmp_path / "conversation.jsonl"))
    monkeypatch.setattr(web, "WEB_LOG_TXT", str(tmp_path / "conversation.txt"))
    monkeypatch.setattr(web.RUNTIME, "next_turn_meta", lambda: ("isolated-test", 1))
    record = web._append_conversation_log("text", result)
    assert "episode_doc" not in record
    saved = json.loads((tmp_path / "conversation.jsonl").read_text(encoding="utf-8"))
    assert "episode_doc" not in saved
