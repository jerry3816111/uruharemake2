"""Capability-limited fresh reader for B71B source3 context artifacts."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import stat
from typing import Any


PUBLIC_ROOT_ENV = "URUHA_P3_B71B_PUBLIC_ROOT"
ARTIFACT_ID = re.compile(r"^p3-b71b-(s3r0600|s3r1200|s3r1800|s3r2400)-[0-9a-f]{16}$")
ROW_BOUNDARIES = {
    "s3r0600": [600.0, 780.0],
    "s3r1200": [1200.0, 1380.0],
    "s3r1800": [1800.0, 1980.0],
    "s3r2400": [2400.0, 2580.0],
}
FORBIDDEN_NAMES = {"url", "track_url", "raw_metadata", "raw_caption", "future", "outcome", "prediction"}


class B71BReaderError(ValueError):
    pass


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _forbidden_field_paths(value: Any, prefix: str = "") -> list[str]:
    found = []
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
        raise B71BReaderError("artifact path")
    info = path.stat()
    if info.st_nlink != 1 or stat.S_IMODE(info.st_mode) != 0o400:
        raise B71BReaderError("artifact security")


def _public_root() -> Path:
    raw = os.environ.get(PUBLIC_ROOT_ENV)
    if not raw:
        raise B71BReaderError("public root environment")
    root = Path(raw).resolve()
    if not root.is_dir() or root.is_symlink() or stat.S_IMODE(root.stat().st_mode) != 0o500:
        raise B71BReaderError("public root security")
    return root


def read_artifact(artifact_id: str) -> dict[str, Any]:
    match = ARTIFACT_ID.fullmatch(artifact_id)
    if not match:
        raise B71BReaderError("artifact id")
    row_id = match.group(1)
    root = _public_root()
    manifest_path = root / f"{artifact_id}.manifest.json"
    artifact_path = root / f"{artifact_id}.json"
    _secure_file(manifest_path)
    _secure_file(artifact_path)
    manifest_bytes, artifact_bytes = manifest_path.read_bytes(), artifact_path.read_bytes()
    try:
        manifest, artifact = json.loads(manifest_bytes), json.loads(artifact_bytes)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise B71BReaderError("public JSON") from exc
    if manifest.get("schema") != "uruha_p3_b71b_public_context_row_manifest_v1" or artifact.get("schema") != "uruha_p3_b71b_public_context_row_v1":
        raise B71BReaderError("schema")
    if manifest.get("artifact_id") != artifact_id or manifest.get("row_id") != row_id or manifest.get("artifact_sha256") != sha256_bytes(artifact_bytes):
        raise B71BReaderError("identity or hash")
    if artifact.get("source_id") != "youtube_j6Hlk9cY9LQ" or artifact.get("row_id") != row_id or artifact.get("context_seconds") != ROW_BOUNDARIES[row_id]:
        raise B71BReaderError("source row boundary")
    if artifact.get("language_code") != "ja" or artifact.get("track_type") != "automatic" or _forbidden_field_paths({"manifest": manifest, "artifact": artifact}):
        raise B71BReaderError("track or forbidden")
    cues = artifact.get("cues")
    if not isinstance(cues, list) or not cues:
        raise B71BReaderError("cues")
    previous = None
    for cue in cues:
        if not isinstance(cue, dict) or set(cue) != {"start_seconds", "end_seconds", "text"}:
            raise B71BReaderError("cue shape")
        start, end, text = cue["start_seconds"], cue["end_seconds"], cue["text"]
        boundary = ROW_BOUNDARIES[row_id]
        if not isinstance(start, (int, float)) or not isinstance(end, (int, float)) or start < boundary[0] or end > boundary[1] or end < start:
            raise B71BReaderError("cue boundary")
        if not isinstance(text, str) or not text.strip() or (previous is not None and (start, end) < previous):
            raise B71BReaderError("cue content or order")
        previous = (start, end)
    if manifest.get("cue_count") != len(cues):
        raise B71BReaderError("cue count")
    return {"manifest": manifest, "artifact": artifact}


def read_batch(artifact_ids: list[str]) -> dict[str, Any]:
    if len(artifact_ids) != 4 or len(set(artifact_ids)) != 4:
        raise B71BReaderError("four unique artifacts")
    rows = [read_artifact(artifact_id) for artifact_id in artifact_ids]
    if [row["artifact"]["row_id"] for row in rows] != list(ROW_BOUNDARIES):
        raise B71BReaderError("row order")
    return {"rows": rows, "future_content_returned": False}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--read-batch", nargs=4, required=True)
    arguments = parser.parse_args()
    print(json.dumps(read_batch(arguments.read_batch), ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
