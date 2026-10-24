#!/usr/bin/env python3
"""Hash every isolated P4 user_profile record, without exporting its contents.

This is a logical read of a launcher-owned test database. Chroma's
PersistentClient is not filesystem read-only and may touch SQLite/telemetry
files when opened. Never point this tool at the formal or private database.
The optional receipt is created exclusively inside the validated test root.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import stat

from p4_preference_fallback_snapshot import SnapshotError, validate_runtime_root


SNAPSHOT_SCHEMA = "uruha_p4_profile_full_content_snapshot_v1"
LABEL_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,79}\Z")
_DIGEST_RE = re.compile(r"[0-9a-f]{64}\Z")
_RECEIPT_KEYS = frozenset({
    "schema", "runtime_root", "db_status", "profile_collection_status",
    "profile_row_count", "profile_content_sha256",
})


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def _receipt(root: Path, *, db_status: str, collection_status: str,
             rows: list[dict] | None = None) -> dict:
    return {
        "schema": SNAPSHOT_SCHEMA,
        "runtime_root": str(root),
        "db_status": db_status,
        "profile_collection_status": collection_status,
        "profile_row_count": len(rows) if rows is not None else 0,
        # A missing DB/collection is not evidence that an empty collection was
        # queried. Only a present collection has a content digest.
        "profile_content_sha256": (
            hashlib.sha256(_canonical_bytes(rows)).hexdigest()
            if rows is not None else None
        ),
    }


def _rows_from_collection(collection) -> list[dict]:
    count_before = collection.count()
    payload = collection.get(include=["metadatas", "documents", "embeddings"])
    count_after = collection.count()
    ids = payload.get("ids")
    metadatas = payload.get("metadatas")
    documents = payload.get("documents")
    embeddings = payload.get("embeddings")
    if not isinstance(count_before, int) or count_before < 0 or count_before != count_after:
        raise SnapshotError("profile_collection_changed_during_snapshot")
    if any(value is None for value in (ids, metadatas, documents, embeddings)):
        raise SnapshotError("profile_full_content_missing")
    if not (len(ids) == len(metadatas) == len(documents) == len(embeddings) == count_before):
        raise SnapshotError("profile_full_content_length_mismatch")
    if len(set(ids)) != len(ids) or any(not isinstance(row_id, str) for row_id in ids):
        raise SnapshotError("profile_invalid_ids")

    rows = []
    for row_id, metadata, document, embedding in zip(ids, metadatas, documents, embeddings):
        vector = embedding.tolist() if hasattr(embedding, "tolist") else embedding
        if not isinstance(vector, list) or not vector:
            raise SnapshotError("profile_embedding_missing")
        rows.append({
            "id": row_id,
            "metadata": metadata,
            "document": document,
            "embedding": vector,
        })
    rows.sort(key=lambda row: row["id"])
    return rows


def _validate_memory_db_tree(root: Path) -> None:
    """Reject links and special nodes before Chroma can open a reused DB.

    The launcher owns this private tree, but Chroma has no read-only mode and
    follows filesystem paths internally. Inspect every existing descendant
    without following symlinks, including the SQLite file and index files.
    """
    db_path = root / "memory_db"
    stack = [db_path]
    while stack:
        directory = stack.pop()
        info = directory.lstat()
        if (not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid()
                or stat.S_IMODE(info.st_mode) != 0o700):
            raise SnapshotError(f"unsafe_memory_db_directory:{directory}")
        with os.scandir(directory) as entries:
            for entry in entries:
                child = Path(entry.path)
                child_info = entry.stat(follow_symlinks=False)
                if child_info.st_uid != os.getuid():
                    raise SnapshotError(f"memory_db_foreign_owner:{child}")
                if stat.S_ISLNK(child_info.st_mode):
                    raise SnapshotError(f"memory_db_symlink:{child}")
                if stat.S_ISDIR(child_info.st_mode):
                    stack.append(child)
                elif stat.S_ISREG(child_info.st_mode):
                    if child_info.st_nlink != 1:
                        raise SnapshotError(f"memory_db_hardlink:{child}")
                    if stat.S_IMODE(child_info.st_mode) & 0o077:
                        raise SnapshotError(f"memory_db_nonprivate_file:{child}")
                else:
                    raise SnapshotError(f"memory_db_special_file:{child}")


def snapshot_runtime_root(requested: str | Path) -> dict:
    root = validate_runtime_root(requested)
    _validate_memory_db_tree(root)
    db_path = root / "memory_db"
    if not (db_path / "chroma.sqlite3").is_file():
        return _receipt(root, db_status="absent", collection_status="unavailable")

    # Import and open only after the launcher's isolation proof is checked.
    import chromadb

    client = chromadb.PersistentClient(path=str(db_path))
    names = {item.name if hasattr(item, "name") else str(item)
             for item in client.list_collections()}
    if "user_profile" not in names:
        return _receipt(root, db_status="present", collection_status="absent")
    rows = _rows_from_collection(client.get_collection("user_profile"))
    return _receipt(root, db_status="present", collection_status="present", rows=rows)


def save_snapshot(requested: str | Path, label: str, snapshot: dict) -> Path:
    root = validate_runtime_root(requested)
    _validate_memory_db_tree(root)
    if set(snapshot) != _RECEIPT_KEYS or snapshot.get("schema") != SNAPSHOT_SCHEMA:
        raise SnapshotError("invalid_profile_full_content_receipt")
    if snapshot.get("runtime_root") != str(root):
        raise SnapshotError("snapshot_runtime_root_mismatch")
    if snapshot.get("db_status") not in {"absent", "present"} or snapshot.get(
        "profile_collection_status"
    ) not in {"unavailable", "absent", "present"}:
        raise SnapshotError("invalid_profile_full_content_status")
    if (snapshot["db_status"], snapshot["profile_collection_status"]) not in {
        ("absent", "unavailable"), ("present", "absent"), ("present", "present"),
    }:
        raise SnapshotError("invalid_profile_full_content_status_pair")
    if not isinstance(snapshot.get("profile_row_count"), int) or snapshot["profile_row_count"] < 0:
        raise SnapshotError("invalid_profile_row_count")
    digest = snapshot.get("profile_content_sha256")
    if (snapshot["profile_collection_status"] == "present") != (
        isinstance(digest, str) and _DIGEST_RE.fullmatch(digest) is not None
    ):
        raise SnapshotError("invalid_profile_content_digest")
    if not LABEL_RE.fullmatch(label) or label in {".", ".."}:
        raise SnapshotError("invalid_snapshot_label")

    evidence_dir = root / "evidence"
    evidence_dir.mkdir(mode=0o700, exist_ok=True)
    info = evidence_dir.lstat()
    if (stat.S_ISLNK(info.st_mode) or not stat.S_ISDIR(info.st_mode)
            or info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) != 0o700):
        raise SnapshotError("invalid_evidence_dir")
    target = evidence_dir / f"profile-full-{label}.json"
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    fd = os.open(target, flags, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        handle.write(json.dumps(snapshot, ensure_ascii=False, sort_keys=True, indent=2) + "\n")
    return target


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime-root", required=True,
                        help="Explicit launcher-owned 0700 isolated root")
    parser.add_argument("--save", metavar="LABEL", help="Create exclusive 0600 receipt")
    args = parser.parse_args(argv)
    snapshot = snapshot_runtime_root(args.runtime_root)
    if args.save is not None:
        target = save_snapshot(args.runtime_root, args.save, snapshot)
        print(f"saved: {target}", file=__import__("sys").stderr)
    print(json.dumps(snapshot, ensure_ascii=False, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
