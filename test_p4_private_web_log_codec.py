"""Zero-model lossless private-row contract; no real conversation data is read."""

from copy import deepcopy
import base64
import importlib
import json
import zlib

import pytest

from uruha_web_log_codec import (
    CODEC_VERSION,
    LogCodecError,
    decode_conversation_log_record,
    decode_conversation_log_line,
    encode_private_log_record,
    load_decoded_conversation_jsonl,
)


def _logical_row():
    return {
        "session_id": "isolated-session",
        "turn_index": 3,
        "user_text": "今はちょっと待って。🍓",
        "assistant_reply": "うん、待つよ。",
        "cognition_trace": {
            "runtime_state": {"recent_turn_traces": [{"note": "いったん違う"}] * 20},
            "runtime_trace": {"blackboard": [{"stage": "memory", "payload": {"known": True}}]},
            "psyche_before": {"trust": 0.4},
        },
        "memory_snapshot": {"source": "isolated-test"},
        "compute_receipt": {"item_id": "isolated-item"},
    }


def test_private_codec_preserves_full_logical_row_and_legacy():
    logical = _logical_row()
    before = deepcopy(logical)
    encoded = encode_private_log_record(logical)
    assert logical == before
    assert encoded["cognition_trace_codec"]["version"] == CODEC_VERSION
    assert isinstance(encoded["cognition_trace"], str)
    assert encoded["memory_snapshot"] == logical["memory_snapshot"]
    assert decode_conversation_log_record(encoded) == logical
    assert decode_conversation_log_record(logical) == logical
    assert len(json.dumps(encoded, ensure_ascii=False).encode()) < len(
        json.dumps(logical, ensure_ascii=False).encode()
    )


@pytest.mark.parametrize("fault", [
    "unknown_version", "missing_version", "extra_descriptor", "wrong_length",
    "short_length", "wrong_sha", "bad_base64", "noncanonical_base64", "bad_zlib",
    "truncated_stream", "trailing_stream", "oversize_claim",
    "trace_string_without_descriptor",
])
def test_encoded_trace_corruption_fails_closed(fault, monkeypatch):
    from uruha_web_log_codec import MAX_TRACE_BYTES

    row = encode_private_log_record(_logical_row())
    row = deepcopy(row)
    descriptor = row["cognition_trace_codec"]
    if fault == "unknown_version":
        descriptor["version"] = "future-unknown"
    elif fault == "missing_version":
        del descriptor["version"]
    elif fault == "extra_descriptor":
        descriptor["unexpected"] = True
    elif fault == "wrong_length":
        descriptor["uncompressed_bytes"] += 1
    elif fault == "short_length":
        descriptor["uncompressed_bytes"] -= 1
    elif fault == "wrong_sha":
        descriptor["sha256"] = "0" * 64
    elif fault == "bad_base64":
        row["cognition_trace"] = "invalid!"
    elif fault == "noncanonical_base64":
        row["cognition_trace"] += "="
    elif fault == "bad_zlib":
        row["cognition_trace"] = base64.b64encode(b"not-zlib").decode("ascii")
    elif fault == "truncated_stream":
        blob = base64.b64decode(row["cognition_trace"])
        row["cognition_trace"] = base64.b64encode(blob[:-2]).decode("ascii")
    elif fault == "trailing_stream":
        blob = base64.b64decode(row["cognition_trace"])
        row["cognition_trace"] = base64.b64encode(blob + zlib.compress(b"{}")).decode("ascii")
    elif fault == "oversize_claim":
        descriptor["uncompressed_bytes"] = MAX_TRACE_BYTES + 1
    else:
        del row["cognition_trace_codec"]
    with pytest.raises(LogCodecError):
        decode_conversation_log_record(row)


def test_encode_rejects_non_object_or_oversize_trace(monkeypatch):
    import uruha_web_log_codec as codec

    row = _logical_row()
    row["cognition_trace"] = "not-an-object"
    with pytest.raises(LogCodecError):
        encode_private_log_record(row)
    monkeypatch.setattr(codec, "MAX_TRACE_BYTES", 16 * 1024 * 1024)
    monkeypatch.setattr(codec, "MAX_ROW_BYTES", 30)
    with pytest.raises(LogCodecError, match="encoded_row_over_browser_limit"):
        encode_private_log_record(_logical_row())
    row["cognition_trace"] = {"text": "too-long"}
    monkeypatch.setattr(codec, "MAX_TRACE_BYTES", 5)
    with pytest.raises(LogCodecError):
        encode_private_log_record(row)


def test_line_parser_rejects_duplicate_keys_and_non_object():
    with pytest.raises(LogCodecError):
        decode_conversation_log_line('{"cognition_trace": {}, "cognition_trace": {}}')
    with pytest.raises(LogCodecError):
        decode_conversation_log_line('[]')


@pytest.mark.parametrize("module_name,function_name", [
    ("build_annotation_candidate_queue", "load_jsonl"),
    ("build_annotation_draft_queue", "_load_jsonl"),
    ("build_human_feedback_regression_dataset", "_load_jsonl"),
    ("audit_m49_web_evidence", "_load"),
    ("audit_m50_web_evidence", "_load"),
    ("audit_m51_web_evidence", "_load"),
    ("audit_m52_web_evidence", "_load"),
])
def test_offline_readers_keep_legacy_and_encoded_logical_rows(tmp_path, module_name, function_name):
    module = importlib.import_module(module_name)
    reader = getattr(module, function_name)
    logical = _logical_row()
    path = tmp_path / "isolated.jsonl"
    path.write_text(
        json.dumps(logical, ensure_ascii=False) + "\n"
        + json.dumps(encode_private_log_record(logical), ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    loaded = reader(path)
    rows = loaded[0] if isinstance(loaded, tuple) else loaded
    assert rows == [logical, logical]


def test_immutable_v76_can_receive_decoded_rows_via_explicit_bridge(tmp_path):
    import planner_supervision_v76 as v76

    logical = _logical_row()
    path = tmp_path / "isolated.jsonl"
    path.write_text(json.dumps(encode_private_log_record(logical), ensure_ascii=False) + "\n", encoding="utf-8")
    assert load_decoded_conversation_jsonl(path) == [logical]
    assert v76.input_context_from_log(load_decoded_conversation_jsonl(path)[0]) == (
        v76.input_context_from_log(logical)
    )


@pytest.mark.parametrize("module_name", [
    "audit_m45_web_evidence",
    "audit_m46_web_evidence",
    "audit_m47_web_evidence",
    "audit_m48_web_evidence",
    "audit_m49_web_evidence",
    "audit_m50_web_evidence",
    "audit_m51_web_evidence",
    "audit_m52_web_evidence",
])
def test_web_evidence_audit_has_legacy_encoded_parity(tmp_path, module_name):
    audit = importlib.import_module(module_name).audit
    logical = _logical_row()
    plain = tmp_path / "legacy.jsonl"
    compressed = tmp_path / "encoded.jsonl"
    plain.write_text(json.dumps(logical, ensure_ascii=False) + "\n", encoding="utf-8")
    compressed.write_text(
        json.dumps(encode_private_log_record(logical), ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    if module_name == "audit_m49_web_evidence":
        legacy_report = audit(plain, plain)
        encoded_report = audit(compressed, compressed)
    else:
        legacy_report = audit(plain)
        encoded_report = audit(compressed)
    for report in (legacy_report, encoded_report):
        report.pop("source_log", None)
        report.pop("source_logs", None)
    assert legacy_report == encoded_report


@pytest.mark.parametrize("module_name,function_name", [
    ("build_annotation_candidate_queue", "load_jsonl"),
    ("build_annotation_draft_queue", "_load_jsonl"),
    ("build_human_feedback_regression_dataset", "_load_jsonl"),
])
def test_annotation_readers_do_not_silently_skip_corrupt_encoded_trace(
    tmp_path, module_name, function_name,
):
    reader = getattr(importlib.import_module(module_name), function_name)
    encoded = encode_private_log_record(_logical_row())
    encoded["cognition_trace_codec"]["sha256"] = "0" * 64
    path = tmp_path / "corrupt.jsonl"
    path.write_text(json.dumps(encoded, ensure_ascii=False) + "\n", encoding="utf-8")
    with pytest.raises(LogCodecError, match="trace_sha256_mismatch"):
        reader(path)
