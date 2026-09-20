"""Capability-limited reader for B71C future-only artifacts."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import stat
from typing import Any


PUBLIC_ROOT_ENV = "URUHA_P3_B71C_PUBLIC_ROOT"
ARTIFACT_ID = re.compile(r"^p3-b71c-(s3r0600|s3r1200|s3r1800|s3r2400)-[0-9a-f]{16}$")
ROW_BOUNDARIES = {
    "s3r0600": [781.0, 841.0],
    "s3r1200": [1381.0, 1441.0],
    "s3r1800": [1981.0, 2041.0],
    "s3r2400": [2581.0, 2641.0],
}


class B71CReaderError(ValueError):
    pass


def _secure(path: Path) -> None:
    if path.is_symlink() or not path.is_file() or path.stat().st_nlink != 1 or stat.S_IMODE(path.stat().st_mode) != 0o400:
        raise B71CReaderError("insecure artifact")


def read_artifact(artifact_id: str) -> dict[str, Any]:
    match = ARTIFACT_ID.fullmatch(artifact_id)
    if not match:
        raise B71CReaderError("artifact id")
    row_id = match.group(1)
    raw_root = os.environ.get(PUBLIC_ROOT_ENV)
    if not raw_root:
        raise B71CReaderError("root")
    root = Path(raw_root).resolve()
    if not root.is_dir() or root.is_symlink() or stat.S_IMODE(root.stat().st_mode) != 0o500:
        raise B71CReaderError("root security")
    artifact_path, manifest_path = root / f"{artifact_id}.json", root / f"{artifact_id}.manifest.json"
    _secure(artifact_path); _secure(manifest_path)
    artifact_bytes = artifact_path.read_bytes()
    try:
        artifact = json.loads(artifact_bytes); manifest = json.loads(manifest_path.read_bytes())
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise B71CReaderError("JSON") from exc
    if artifact.get("schema") != "uruha_p3_b71c_public_future_row_v1" or manifest.get("schema") != "uruha_p3_b71c_public_future_row_manifest_v1":
        raise B71CReaderError("schema")
    if artifact.get("row_id") != row_id or manifest.get("row_id") != row_id or manifest.get("artifact_id") != artifact_id:
        raise B71CReaderError("identity")
    if manifest.get("artifact_sha256") != hashlib.sha256(artifact_bytes).hexdigest():
        raise B71CReaderError("hash")
    boundary = ROW_BOUNDARIES[row_id]
    if artifact.get("future_seconds") != boundary or artifact.get("source_id") != "youtube_j6Hlk9cY9LQ":
        raise B71CReaderError("boundary")
    cues = artifact.get("cues")
    if not isinstance(cues, list) or not cues or manifest.get("cue_count") != len(cues):
        raise B71CReaderError("cues")
    previous = None
    for cue in cues:
        if not isinstance(cue, dict) or set(cue) != {"start_seconds", "end_seconds", "text"}:
            raise B71CReaderError("cue shape")
        start, end, text = cue["start_seconds"], cue["end_seconds"], cue["text"]
        if not isinstance(start, (int, float)) or not isinstance(end, (int, float)) or start < boundary[0] or end > boundary[1] or end < start or not isinstance(text, str) or not text.strip():
            raise B71CReaderError("cue")
        if previous is not None and (start, end) < previous:
            raise B71CReaderError("order")
        previous = (start, end)
    return {"manifest": manifest, "artifact": artifact}


def read_batch(artifact_ids: list[str]) -> dict[str, Any]:
    if len(artifact_ids) != 4 or len(set(artifact_ids)) != 4:
        raise B71CReaderError("four unique artifacts")
    rows = [read_artifact(artifact_id) for artifact_id in artifact_ids]
    if [row["artifact"]["row_id"] for row in rows] != list(ROW_BOUNDARIES):
        raise B71CReaderError("row order")
    return {"rows": rows, "context_content_returned": False}


def main() -> None:
    parser = argparse.ArgumentParser(); parser.add_argument("--read-batch", nargs=4, required=True)
    print(json.dumps(read_batch(parser.parse_args().read_batch), ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
