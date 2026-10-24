"""Capability-limited fresh reader for B60 pre-cutoff caption artifacts."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import stat
from typing import Any


PUBLIC_ROOT_ENV = "URUHA_P3_B60_PUBLIC_ROOT"
ARTIFACT_ID = re.compile(r"^p3-b60-[0-9a-f]{16}$")
FORBIDDEN_NAMES = {"url", "track_url", "raw_metadata", "raw_caption", "future", "outcome"}


class B60ReaderError(ValueError):
    pass


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


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
        raise B60ReaderError("artifact path must be a regular non-symlink file")
    info = path.stat()
    if info.st_nlink != 1:
        raise B60ReaderError("artifact hardlink count must be one")
    if stat.S_IMODE(info.st_mode) != 0o400:
        raise B60ReaderError("artifact mode must be 0400")


def _public_root() -> Path:
    raw = os.environ.get(PUBLIC_ROOT_ENV)
    if not raw:
        raise B60ReaderError("public root environment is required")
    root = Path(raw).resolve()
    if not root.is_dir() or root.is_symlink():
        raise B60ReaderError("public root must be a directory")
    if stat.S_IMODE(root.stat().st_mode) != 0o500:
        raise B60ReaderError("public root mode must be 0500")
    return root


def inspect_artifact(artifact_id: str) -> dict[str, Any]:
    if not ARTIFACT_ID.fullmatch(artifact_id):
        raise B60ReaderError("invalid artifact id")
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
        raise B60ReaderError("invalid public JSON") from exc
    if manifest.get("schema") != "uruha_p3_b60_caption_context_manifest_v1":
        raise B60ReaderError("manifest schema")
    if artifact.get("schema") != "uruha_p3_b60_caption_context_v1":
        raise B60ReaderError("artifact schema")
    if manifest.get("artifact_id") != artifact_id:
        raise B60ReaderError("artifact id mismatch")
    if manifest.get("artifact_sha256") != sha256_bytes(artifact_bytes):
        raise B60ReaderError("artifact hash mismatch")
    if artifact.get("source_id") != "youtube_4y5GiQpgJgo":
        raise B60ReaderError("source id")
    if artifact.get("context_seconds") != [3000.0, 3180.0]:
        raise B60ReaderError("context boundary")
    if artifact.get("language_code") != "ja" or artifact.get("track_type") != "automatic":
        raise B60ReaderError("track identity")
    forbidden = _forbidden_field_paths({"manifest": manifest, "artifact": artifact})
    if forbidden:
        raise B60ReaderError("forbidden public fields")
    cues = artifact.get("cues")
    if not isinstance(cues, list) or not cues:
        raise B60ReaderError("cues required")
    previous = None
    for cue in cues:
        if not isinstance(cue, dict) or set(cue) != {"start_seconds", "end_seconds", "text"}:
            raise B60ReaderError("cue shape")
        start = cue["start_seconds"]
        end = cue["end_seconds"]
        text = cue["text"]
        if not isinstance(start, (int, float)) or not isinstance(end, (int, float)):
            raise B60ReaderError("cue time type")
        if start < 3000.0 or end > 3180.0 or end < start:
            raise B60ReaderError("cue cutoff boundary")
        if not isinstance(text, str) or not text.strip():
            raise B60ReaderError("cue text")
        order = (start, end)
        if previous is not None and order < previous:
            raise B60ReaderError("cue ordering")
        previous = order
    if manifest.get("cue_count") != len(cues):
        raise B60ReaderError("cue count mismatch")
    return {
        "manifest": manifest,
        "artifact_summary": {
            "artifact_sha256": manifest["artifact_sha256"],
            "cue_count": len(cues),
            "first_cue_start_seconds": cues[0]["start_seconds"],
            "last_cue_end_seconds": max(cue["end_seconds"] for cue in cues),
            "caption_text_returned": False,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Inspect B60 caption context without returning text")
    parser.add_argument("--inspect", required=True)
    arguments = parser.parse_args()
    print(json.dumps(inspect_artifact(arguments.inspect), ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
