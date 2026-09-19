"""Capability-limited reader for the B66 projected post-cutoff outcome."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import stat
from typing import Any


PUBLIC_ROOT_ENV = "URUHA_P3_B66_PUBLIC_ROOT"
ARTIFACT_ID = re.compile(r"^p3-b66-[0-9a-f]{16}$")
FORBIDDEN_NAMES = {"url", "track_url", "raw_metadata", "raw_caption", "context", "prediction"}


class B66ReaderError(ValueError):
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
        raise B66ReaderError("artifact path must be a regular non-symlink file")
    info = path.stat()
    if info.st_nlink != 1:
        raise B66ReaderError("artifact hardlink count must be one")
    if stat.S_IMODE(info.st_mode) != 0o400:
        raise B66ReaderError("artifact mode must be 0400")


def _public_root() -> Path:
    raw = os.environ.get(PUBLIC_ROOT_ENV)
    if not raw:
        raise B66ReaderError("public root environment is required")
    root = Path(raw).resolve()
    if not root.is_dir() or root.is_symlink():
        raise B66ReaderError("public root must be a directory")
    if stat.S_IMODE(root.stat().st_mode) != 0o500:
        raise B66ReaderError("public root mode must be 0500")
    return root


def read_artifact(artifact_id: str) -> dict[str, Any]:
    if not ARTIFACT_ID.fullmatch(artifact_id):
        raise B66ReaderError("invalid artifact id")
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
        raise B66ReaderError("invalid public JSON") from exc
    if manifest.get("schema") != "uruha_p3_b66_public_future_outcome_manifest_v1":
        raise B66ReaderError("manifest schema")
    if artifact.get("schema") != "uruha_p3_b66_public_future_outcome_v1":
        raise B66ReaderError("artifact schema")
    if manifest.get("artifact_id") != artifact_id:
        raise B66ReaderError("artifact id mismatch")
    if manifest.get("artifact_sha256") != sha256_bytes(artifact_bytes):
        raise B66ReaderError("artifact hash mismatch")
    if artifact.get("source_id") != "youtube_4y5GiQpgJgo":
        raise B66ReaderError("source id")
    if artifact.get("future_seconds") != [3181.0, 3241.0]:
        raise B66ReaderError("future boundary")
    if artifact.get("language_code") != "ja" or artifact.get("track_type") != "automatic":
        raise B66ReaderError("track identity")
    if _forbidden_field_paths({"manifest": manifest, "artifact": artifact}):
        raise B66ReaderError("forbidden public fields")
    cues = artifact.get("cues")
    if not isinstance(cues, list) or not cues:
        raise B66ReaderError("cues required")
    previous = None
    for cue in cues:
        if not isinstance(cue, dict) or set(cue) != {"start_seconds", "end_seconds", "text"}:
            raise B66ReaderError("cue shape")
        start = cue["start_seconds"]
        end = cue["end_seconds"]
        text = cue["text"]
        if not isinstance(start, (int, float)) or not isinstance(end, (int, float)):
            raise B66ReaderError("cue time type")
        if start < 3181.0 or end > 3241.0 or end < start:
            raise B66ReaderError("cue future boundary")
        if not isinstance(text, str) or not text.strip():
            raise B66ReaderError("cue text")
        order = (start, end)
        if previous is not None and order < previous:
            raise B66ReaderError("cue ordering")
        previous = order
    if manifest.get("cue_count") != len(cues):
        raise B66ReaderError("cue count mismatch")
    return {"manifest": manifest, "artifact": artifact}


def main() -> None:
    parser = argparse.ArgumentParser(description="Read the B66 projected future outcome")
    parser.add_argument("--read", required=True)
    arguments = parser.parse_args()
    print(json.dumps(read_artifact(arguments.read), ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
