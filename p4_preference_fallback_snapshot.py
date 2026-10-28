#!/usr/bin/env python3
"""Read a launcher-owned P4 product DB for per-turn row-ID evidence.

This is *logically* read-only: it calls Chroma list/get APIs, never a write API.
Chroma PersistentClient itself has no filesystem read-only mode and may touch
its SQLite/telemetry files on open. Run only against a preserved isolated
runtime root, not the formal DB, and capture independent file hashes if byte-
for-byte DB immutability matters. The optional evidence file is an intentional
write, confined to that same validated root.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import stat
import tempfile


MANIFEST_NAME = "uruha_product_launcher_manifest.json"
SNAPSHOT_SCHEMA = "uruha_p4_preference_fallback_row_snapshot_v1"
LABEL_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,79}\Z")


class SnapshotError(ValueError):
    """The requested source is not a verified isolated product runtime."""


def _inside(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
        return path != parent
    except ValueError:
        return False


def _require_owned_mode(path: Path, *, mode: int, kind: str) -> None:
    info = path.lstat()
    if stat.S_ISLNK(info.st_mode):
        raise SnapshotError(f"{kind}_symlink:{path}")
    if info.st_uid != os.getuid():
        raise SnapshotError(f"{kind}_wrong_owner:{path}")
    expected_type = stat.S_ISDIR if kind in {"runtime_root", "memory_db", "evidence_dir"} else stat.S_ISREG
    if not expected_type(info.st_mode):
        raise SnapshotError(f"{kind}_wrong_type:{path}")
    if stat.S_IMODE(info.st_mode) != mode:
        raise SnapshotError(f"{kind}_wrong_mode:{path}")


def validate_runtime_root(requested: str | Path) -> Path:
    raw = Path(requested)
    if not raw.is_absolute():
        raise SnapshotError("runtime_root_must_be_absolute")
    if raw.is_symlink():
        raise SnapshotError("runtime_root_symlink")
    try:
        root = raw.resolve(strict=True)
    except OSError as exc:
        raise SnapshotError("runtime_root_missing") from exc
    temporary_parent = Path(tempfile.gettempdir()).resolve(strict=True)
    if not _inside(root, temporary_parent) or not root.name.startswith("uruha-product-"):
        raise SnapshotError(f"runtime_root_not_launcher_temp:{root}")
    _require_owned_mode(root, mode=0o700, kind="runtime_root")

    manifest = root / MANIFEST_NAME
    try:
        _require_owned_mode(manifest, mode=0o600, kind="manifest")
        marker = json.loads(manifest.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SnapshotError("invalid_launcher_manifest") from exc
    if not isinstance(marker, dict) or marker.get("schema") != "uruha_p4_b_runtime_root_v1" or marker.get("created_by_launcher") is not True:
        raise SnapshotError("invalid_launcher_manifest")

    memory_db = root / "memory_db"
    try:
        _require_owned_mode(memory_db, mode=0o700, kind="memory_db")
    except OSError as exc:
        raise SnapshotError("memory_db_missing") from exc
    sqlite_file = memory_db / "chroma.sqlite3"
    if sqlite_file.exists() or sqlite_file.is_symlink():
        info = sqlite_file.lstat()
        if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid():
            raise SnapshotError("invalid_chroma_sqlite_file")
    return root


def _collection_ids_and_metadata(collection, *, where: dict) -> list[dict]:
    rows = collection.get(where=where, include=["metadatas"])
    ids = rows.get("ids") or []
    metadatas = rows.get("metadatas") or []
    if len(ids) != len(metadatas):
        raise SnapshotError("chroma_ids_metadata_length_mismatch")
    return sorted(
        ({"id": str(row_id), "metadata": metadata} for row_id, metadata in zip(ids, metadatas)),
        key=lambda row: row["id"],
    )


def snapshot_runtime_root(requested: str | Path) -> dict:
    root = validate_runtime_root(requested)
    db_path = root / "memory_db"
    if not (db_path / "chroma.sqlite3").is_file():
        return {
            "schema": SNAPSHOT_SCHEMA,
            "runtime_root": str(root),
            "db_status": "absent",
            "user_profile_rows": [],
            "turn_episode_ids": [],
        }

    # Import only after validation; no PersistentClient is constructed for an
    # untrusted path, and no get_or_create_collection call is made.
    import chromadb

    client = chromadb.PersistentClient(path=str(db_path))
    names = {item.name if hasattr(item, "name") else str(item) for item in client.list_collections()}
    profiles = (
        _collection_ids_and_metadata(client.get_collection("user_profile"), where={"subject": "user"})
        if "user_profile" in names
        else []
    )
    episodes = (
        _collection_ids_and_metadata(client.get_collection("episodic_memory"), where={"source": "turn_episode"})
        if "episodic_memory" in names
        else []
    )
    if any(row["metadata"] is None or row["metadata"].get("subject") != "user" for row in profiles):
        raise SnapshotError("profile_source_filter_mismatch")
    if any(row["metadata"] is None or row["metadata"].get("source") != "turn_episode" for row in episodes):
        raise SnapshotError("episode_source_filter_mismatch")
    return {
        "schema": SNAPSHOT_SCHEMA,
        "runtime_root": str(root),
        "db_status": "present",
        "user_profile_rows": profiles,
        "turn_episode_ids": [row["id"] for row in episodes],
    }


def save_snapshot(root: str | Path, label: str, snapshot: dict) -> Path:
    root = validate_runtime_root(root)
    if snapshot.get("runtime_root") != str(root):
        raise SnapshotError("snapshot_runtime_root_mismatch")
    if not LABEL_RE.fullmatch(label) or label in {".", ".."}:
        raise SnapshotError("invalid_snapshot_label")
    evidence_dir = root / "evidence"
    try:
        evidence_dir.mkdir(mode=0o700, exist_ok=True)
    except OSError as exc:
        raise SnapshotError("cannot_create_evidence_dir") from exc
    _require_owned_mode(evidence_dir, mode=0o700, kind="evidence_dir")
    target = evidence_dir / f"snapshot-{label}.json"
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    fd = os.open(target, flags, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        handle.write(json.dumps(snapshot, ensure_ascii=False, sort_keys=True, indent=2) + "\n")
    return target


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime-root", required=True, help="Explicit launcher-owned 0700 isolated root")
    parser.add_argument("--save", metavar="LABEL", help="Create evidence/snapshot-LABEL.json, never overwrite")
    args = parser.parse_args(argv)
    snapshot = snapshot_runtime_root(args.runtime_root)
    if args.save is not None:
        target = save_snapshot(args.runtime_root, args.save, snapshot)
        print(f"saved: {target}", file=__import__("sys").stderr)
    print(json.dumps(snapshot, ensure_ascii=False, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
