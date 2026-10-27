"""Lossless codec for new owner-only Web conversation JSONL rows.

This module has no Web/runtime imports so offline readers can decode the same
logical record. The caller, not this codec, must enforce private file modes.
"""

from __future__ import annotations

import base64
import binascii
import hashlib
import json
import re
import zlib
from pathlib import Path


CODEC_VERSION = "zlib-json-base64-v1"
MAX_TRACE_BYTES = 16 * 1024 * 1024
MAX_ROW_BYTES = 16 * 1024 * 1024
_DESCRIPTOR_KEYS = frozenset({"version", "uncompressed_bytes", "sha256"})
_SHA256 = re.compile(r"[0-9a-f]{64}\Z")


class LogCodecError(ValueError):
    """An encoded row is unsupported or cannot be verified losslessly."""


def encode_private_log_record(record: dict) -> dict:
    """Return a new disk object; leave the full logical input untouched."""
    if not isinstance(record, dict) or "cognition_trace_codec" in record:
        raise LogCodecError("invalid_private_log_record")
    trace = record.get("cognition_trace")
    if not isinstance(trace, dict):
        raise LogCodecError("trace_not_object")
    try:
        raw_trace = json.dumps(trace, ensure_ascii=False).encode("utf-8")
    except (TypeError, ValueError, UnicodeError) as exc:
        raise LogCodecError("trace_not_json") from exc
    if len(raw_trace) > MAX_TRACE_BYTES:
        raise LogCodecError("trace_over_decode_limit")
    encoded = dict(record)
    encoded["cognition_trace"] = base64.b64encode(zlib.compress(raw_trace, 6)).decode("ascii")
    encoded["cognition_trace_codec"] = {
        "version": CODEC_VERSION,
        "uncompressed_bytes": len(raw_trace),
        "sha256": hashlib.sha256(raw_trace).hexdigest(),
    }
    try:
        disk_bytes = json.dumps(encoded, ensure_ascii=False).encode("utf-8")
    except (TypeError, ValueError, UnicodeError) as exc:
        raise LogCodecError("row_not_json") from exc
    if len(disk_bytes) > MAX_ROW_BYTES:
        raise LogCodecError("encoded_row_over_browser_limit")
    return encoded


def decode_conversation_log_record(record: dict) -> dict:
    """Decode an encoded row, or return a legacy logical row unchanged."""
    if not isinstance(record, dict):
        raise LogCodecError("row_not_object")
    if "cognition_trace_codec" not in record:
        if "cognition_trace" in record and not isinstance(record["cognition_trace"], dict):
            raise LogCodecError("legacy_trace_not_object")
        return record
    descriptor = record["cognition_trace_codec"]
    if not isinstance(descriptor, dict) or set(descriptor) != _DESCRIPTOR_KEYS:
        raise LogCodecError("invalid_codec_descriptor")
    if descriptor["version"] != CODEC_VERSION:
        raise LogCodecError("unknown_codec_version")
    length = descriptor["uncompressed_bytes"]
    if type(length) is not int or length < 0 or length > MAX_TRACE_BYTES:
        raise LogCodecError("invalid_uncompressed_length")
    digest = descriptor["sha256"]
    if not isinstance(digest, str) or not _SHA256.fullmatch(digest):
        raise LogCodecError("invalid_trace_sha256")
    trace = record.get("cognition_trace")
    if not isinstance(trace, str) or not trace or len(trace) > MAX_ROW_BYTES:
        raise LogCodecError("invalid_encoded_trace")
    try:
        compressed = base64.b64decode(trace, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise LogCodecError("invalid_trace_base64") from exc
    if base64.b64encode(compressed).decode("ascii") != trace:
        raise LogCodecError("noncanonical_trace_base64")
    try:
        inflater = zlib.decompressobj()
        raw_trace = inflater.decompress(compressed, length + 1)
    except zlib.error as exc:
        raise LogCodecError("invalid_trace_zlib") from exc
    if (
        not inflater.eof or inflater.unused_data or inflater.unconsumed_tail
        or len(raw_trace) != length
    ):
        raise LogCodecError("trace_stream_or_length_mismatch")
    if hashlib.sha256(raw_trace).hexdigest() != digest:
        raise LogCodecError("trace_sha256_mismatch")
    try:
        logical_trace = json.loads(raw_trace)
    except (UnicodeDecodeError, ValueError, TypeError) as exc:
        raise LogCodecError("trace_not_json") from exc
    if not isinstance(logical_trace, dict):
        raise LogCodecError("trace_not_object")
    decoded = dict(record)
    del decoded["cognition_trace_codec"]
    decoded["cognition_trace"] = logical_trace
    return decoded


def _unique_json_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise LogCodecError("duplicate_json_key")
        result[key] = value
    return result


def decode_conversation_log_line(line: bytes | str) -> dict:
    """Parse one complete JSON object with duplicate-key and codec checks."""
    try:
        record = json.loads(line, object_pairs_hook=_unique_json_object)
    except LogCodecError:
        raise
    except (UnicodeDecodeError, ValueError, TypeError) as exc:
        raise LogCodecError("invalid_log_json") from exc
    return decode_conversation_log_record(record)


def load_decoded_conversation_jsonl(path) -> list[dict]:
    """Explicit offline bridge for immutable historical readers (not Web auth)."""
    source = Path(path)
    if not source.exists():
        return []
    with source.open("rb") as handle:
        return [decode_conversation_log_line(line) for line in handle if line.strip()]
