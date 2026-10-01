"""Capability-limited reader for B68 four-row future-only artifacts."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import stat
from typing import Any


PUBLIC_ROOT_ENV = "URUHA_P3_B68_PUBLIC_ROOT"
ARTIFACT_ID = re.compile(r"^p3-b68-(r0600|r1200|r1800|r2400)-[0-9a-f]{16}$")
ROW_BOUNDARIES = {
    "r0600": [781.0, 841.0],
    "r1200": [1381.0, 1441.0],
    "r1800": [1981.0, 2041.0],
    "r2400": [2581.0, 2641.0],
}


class B68ReaderError(ValueError):
    pass


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _secure(path: Path) -> None:
    if path.is_symlink() or not path.is_file() or path.stat().st_nlink != 1 or stat.S_IMODE(path.stat().st_mode) != 0o400:
        raise B68ReaderError("insecure public artifact")


def _root() -> Path:
    raw = os.environ.get(PUBLIC_ROOT_ENV)
    if not raw:
        raise B68ReaderError("public root required")
    root = Path(raw).resolve()
    if not root.is_dir() or root.is_symlink() or stat.S_IMODE(root.stat().st_mode) != 0o500:
        raise B68ReaderError("invalid public root")
    return root


def read_artifact(artifact_id: str) -> dict[str, Any]:
    match = ARTIFACT_ID.fullmatch(artifact_id)
    if not match:
        raise B68ReaderError("artifact id")
    row_id = match.group(1)
    root = _root()
    artifact_path = root / f"{artifact_id}.json"
    manifest_path = root / f"{artifact_id}.manifest.json"
    _secure(artifact_path)
    _secure(manifest_path)
    artifact_bytes = artifact_path.read_bytes()
    try:
        artifact = json.loads(artifact_bytes)
        manifest = json.loads(manifest_path.read_bytes())
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise B68ReaderError("JSON") from exc
    if artifact.get("schema") != "uruha_p3_b68_public_future_row_v1" or manifest.get("schema") != "uruha_p3_b68_public_future_row_manifest_v1":
        raise B68ReaderError("schema")
    if artifact.get("row_id") != row_id or manifest.get("row_id") != row_id or manifest.get("artifact_id") != artifact_id:
        raise B68ReaderError("identity")
    if manifest.get("artifact_sha256") != sha256_bytes(artifact_bytes):
        raise B68ReaderError("hash")
    boundary = ROW_BOUNDARIES[row_id]
    if artifact.get("future_seconds") != boundary or artifact.get("source_id") != "youtube_4y5GiQpgJgo":
        raise B68ReaderError("boundary")
    cues = artifact.get("cues")
    if not isinstance(cues, list) or not cues or manifest.get("cue_count") != len(cues):
        raise B68ReaderError("cues")
    previous = None
    for cue in cues:
        if not isinstance(cue, dict) or set(cue) != {"start_seconds", "end_seconds", "text"}:
            raise B68ReaderError("cue shape")
        start, end, text = cue["start_seconds"], cue["end_seconds"], cue["text"]
        if not isinstance(start, (int, float)) or not isinstance(end, (int, float)) or start < boundary[0] or end > boundary[1] or end < start:
            raise B68ReaderError("cue boundary")
        if not isinstance(text, str) or not text.strip():
            raise B68ReaderError("cue text")
        if previous is not None and (start, end) < previous:
            raise B68ReaderError("cue order")
        previous = (start, end)
    return {"manifest": manifest, "artifact": artifact}


def read_batch(artifact_ids: list[str]) -> dict[str, Any]:
    rows = [read_artifact(artifact_id) for artifact_id in artifact_ids]
    if [row["artifact"]["row_id"] for row in rows] != ["r0600", "r1200", "r1800", "r2400"]:
        raise B68ReaderError("row order")
    return {"rows": rows, "context_content_returned": False}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--read-batch", nargs=4, required=True)
    args = parser.parse_args()
    print(json.dumps(read_batch(args.read_batch), ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
