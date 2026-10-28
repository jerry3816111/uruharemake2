"""Capability-limited fresh reader for B67 context-only row artifacts."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import stat
from typing import Any


PUBLIC_ROOT_ENV = "URUHA_P3_B67_PUBLIC_ROOT"
ARTIFACT_ID = re.compile(r"^p3-b67-(r0600|r1200|r1800|r2400)-[0-9a-f]{16}$")
ROW_BOUNDARIES = {
    "r0600": [600.0, 780.0],
    "r1200": [1200.0, 1380.0],
    "r1800": [1800.0, 1980.0],
    "r2400": [2400.0, 2580.0],
}
FORBIDDEN_NAMES = {"url", "track_url", "raw_metadata", "raw_caption", "future", "outcome", "prediction"}


class B67ReaderError(ValueError):
    pass


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _forbidden_field_paths(value: Any, prefix: str = "") -> list[str]:
    found: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            path = f"{prefix}.{key}" if prefix else str(key)
            if str(key).casefold() in FORBIDDEN_NAMES:
                found.append(path)
            found.extend(_forbidden_field_paths(child, path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            found.extend(_forbidden_field_paths(child, f"{prefix}[{index}]"))
    return found


def _secure_file(path: Path) -> None:
    if path.is_symlink() or not path.is_file():
        raise B67ReaderError("artifact path must be a regular non-symlink file")
    info = path.stat()
    if info.st_nlink != 1:
        raise B67ReaderError("artifact hardlink count must be one")
    if stat.S_IMODE(info.st_mode) != 0o400:
        raise B67ReaderError("artifact mode must be 0400")


def _public_root() -> Path:
    raw = os.environ.get(PUBLIC_ROOT_ENV)
    if not raw:
        raise B67ReaderError("public root environment is required")
    root = Path(raw).resolve()
    if not root.is_dir() or root.is_symlink():
        raise B67ReaderError("public root must be a directory")
    if stat.S_IMODE(root.stat().st_mode) != 0o500:
        raise B67ReaderError("public root mode must be 0500")
    return root


def read_artifact(artifact_id: str) -> dict[str, Any]:
    match = ARTIFACT_ID.fullmatch(artifact_id)
    if not match:
        raise B67ReaderError("invalid artifact id")
    row_id = match.group(1)
    root = _public_root()
    manifest_path = root / f"{artifact_id}.manifest.json"
    artifact_path = root / f"{artifact_id}.json"
    _secure_file(manifest_path)
    _secure_file(artifact_path)
    manifest_bytes = manifest_path.read_bytes()
    artifact_bytes = artifact_path.read_bytes()
    try:
        manifest = json.loads(manifest_bytes)
        artifact = json.loads(artifact_bytes)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise B67ReaderError("invalid public JSON") from exc
    if manifest.get("schema") != "uruha_p3_b67_public_context_row_manifest_v1":
        raise B67ReaderError("manifest schema")
    if artifact.get("schema") != "uruha_p3_b67_public_context_row_v1":
        raise B67ReaderError("artifact schema")
    if manifest.get("artifact_id") != artifact_id or manifest.get("row_id") != row_id:
        raise B67ReaderError("artifact identity")
    if manifest.get("artifact_sha256") != sha256_bytes(artifact_bytes):
        raise B67ReaderError("artifact hash mismatch")
    if artifact.get("source_id") != "youtube_4y5GiQpgJgo" or artifact.get("row_id") != row_id:
        raise B67ReaderError("source or row")
    boundary = ROW_BOUNDARIES[row_id]
    if artifact.get("context_seconds") != boundary:
        raise B67ReaderError("context boundary")
    if artifact.get("language_code") != "ja" or artifact.get("track_type") != "automatic":
        raise B67ReaderError("track identity")
    if _forbidden_field_paths({"manifest": manifest, "artifact": artifact}):
        raise B67ReaderError("forbidden public fields")
    cues = artifact.get("cues")
    if not isinstance(cues, list) or not cues:
        raise B67ReaderError("cues required")
    previous = None
    for cue in cues:
        if not isinstance(cue, dict) or set(cue) != {"start_seconds", "end_seconds", "text"}:
            raise B67ReaderError("cue shape")
        start = cue["start_seconds"]
        end = cue["end_seconds"]
        text = cue["text"]
        if not isinstance(start, (int, float)) or not isinstance(end, (int, float)):
            raise B67ReaderError("cue time type")
        if start < boundary[0] or end > boundary[1] or end < start:
            raise B67ReaderError("cue context boundary")
        if not isinstance(text, str) or not text.strip():
            raise B67ReaderError("cue text")
        order = (start, end)
        if previous is not None and order < previous:
            raise B67ReaderError("cue ordering")
        previous = order
    if manifest.get("cue_count") != len(cues):
        raise B67ReaderError("cue count mismatch")
    return {"manifest": manifest, "artifact": artifact}


def read_batch(artifact_ids: list[str]) -> dict[str, Any]:
    if len(artifact_ids) != 4 or len(set(artifact_ids)) != 4:
        raise B67ReaderError("exactly four unique artifacts required")
    rows = [read_artifact(artifact_id) for artifact_id in artifact_ids]
    if [row["artifact"]["row_id"] for row in rows] != ["r0600", "r1200", "r1800", "r2400"]:
        raise B67ReaderError("row order")
    return {"rows": rows, "future_content_returned": False}


def main() -> None:
    parser = argparse.ArgumentParser(description="Read the B67 context-only batch")
    parser.add_argument("--read-batch", nargs=4, required=True)
    arguments = parser.parse_args()
    print(json.dumps(read_batch(arguments.read_batch), ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
