#!/usr/bin/env python3
"""Private, fail-closed ONNX preparation and durable DB snapshots for P4 probes.

This never writes to the repository, host ONNX source, or a formal memory DB.
Only a controller-created immediate child of the system temporary directory is
accepted.  Snapshot files are exclusive 0600 evidence, not mutable receipts.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import stat
import tarfile
import tempfile
import time


ARCHIVE_SHA = "913d7300ceae3b2dbc2c50d1de4baacab4be7b9380491c27fab7418616a16ec3"
ARCHIVE_SIZE = 83_178_821
MODEL_FILES = frozenset({
    "config.json", "model.onnx", "special_tokens_map.json",
    "tokenizer_config.json", "tokenizer.json", "vocab.txt",
})


def _sha(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def _root(raw: str) -> Path:
    given = Path(raw)
    if given.is_symlink():
        raise ValueError("root_symlink")
    root = given.resolve(strict=True)
    if root.parent != Path(tempfile.gettempdir()).resolve() or not root.name.startswith("uruha-product-"):
        raise ValueError("not_immediate_product_temp_root")
    info = os.lstat(root)
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) != 0o700:
        raise ValueError("root_not_private")
    manifest = root / "uruha_product_launcher_manifest.json"
    if manifest.is_symlink() or not manifest.is_file():
        raise ValueError("missing_launcher_manifest")
    if json.loads(manifest.read_text()).get("created_by_launcher") is not True:
        raise ValueError("root_not_launcher_owned")
    return root


def _private_dir(path: Path) -> None:
    if path.exists() or path.is_symlink():
        info = os.lstat(path)
        if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) != 0o700:
            raise ValueError(f"unsafe_directory:{path}")
    else:
        path.mkdir(mode=0o700)


def _private_bytes(path: Path, data: bytes) -> None:
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "wb") as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())


def prepare_cache(root: Path, source: Path) -> dict:
    if source.is_symlink() or not source.is_file() or source.stat().st_size != ARCHIVE_SIZE or _sha(source) != ARCHIVE_SHA:
        raise ValueError("host_onnx_archive_unverified")
    model = root / ".cache/chroma/onnx_models/all-MiniLM-L6-v2"
    for directory in (root / ".cache", root / ".cache/chroma", root / ".cache/chroma/onnx_models", model, model / "onnx"):
        _private_dir(directory)
    archive = model / "onnx.tar.gz"
    with source.open("rb") as incoming:
        fd = os.open(archive, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, "wb") as outgoing:
            for chunk in iter(lambda: incoming.read(1024 * 1024), b""):
                outgoing.write(chunk)
            outgoing.flush()
            os.fsync(outgoing.fileno())
    if ((archive.stat().st_dev, archive.stat().st_ino) ==
            (source.stat().st_dev, source.stat().st_ino) or _sha(archive) != ARCHIVE_SHA):
        raise ValueError("private_archive_not_independent_or_changed")
    with tarfile.open(archive, "r:gz") as bundle:
        members = bundle.getmembers()
        if {m.name for m in members if m.isfile()} != {f"onnx/{n}" for n in MODEL_FILES}:
            raise ValueError("onnx_member_set_mismatch")
        if any(not (m.isfile() or m.name == "onnx" and m.isdir()) for m in members):
            raise ValueError("onnx_unsafe_member")
        for name in sorted(MODEL_FILES):
            content = bundle.extractfile(f"onnx/{name}")
            if content is None:
                raise ValueError("onnx_member_unreadable")
            _private_bytes(model / "onnx" / name, content.read())
    return {"archive": str(archive), "size": archive.stat().st_size, "sha256": _sha(archive),
            "private_inode": archive.stat().st_ino, "host_inode": source.stat().st_ino}


def warm_cache(root: Path) -> dict:
    os.environ["HOME"] = str(root)
    os.environ["TMPDIR"] = str(root)
    import httpx
    import numpy as np
    from chromadb.utils.embedding_functions.onnx_mini_lm_l6_v2 import ONNXMiniLM_L6_V2

    attempted = 0

    def reject_download(*args, **kwargs):
        nonlocal attempted
        attempted += 1
        raise RuntimeError("onnx_download_forbidden")

    original = httpx.stream
    httpx.stream = reject_download
    try:
        embedder = ONNXMiniLM_L6_V2()
        model_path = Path(embedder.DOWNLOAD_PATH).resolve()
        if not model_path.is_relative_to(root / ".cache"):
            raise ValueError("onnx_model_path_outside_private_root")
        values = embedder(["offline ready"])
    finally:
        httpx.stream = original
    if attempted or len(values) != 1 or len(values[0]) != 384 or not np.isfinite(values[0]).all():
        raise ValueError("offline_embedding_not_ready")
    return {"offline_embedding_ready": True, "vectors": 1, "dimensions": 384,
            "httpx_stream_download_attempts": attempted, "model_path": str(model_path)}


def _tree(root: Path) -> dict:
    found: dict[str, dict] = {}
    for dirname in ("memory_db", "session_db"):
        top = root / dirname
        top_info = os.lstat(top)
        if not stat.S_ISDIR(top_info.st_mode) or top_info.st_uid != os.getuid() or stat.S_IMODE(top_info.st_mode) != 0o700:
            raise ValueError(f"unsafe_db_root:{top}")
        for parent, dirs, files in os.walk(top, followlinks=False):
            parent_path = Path(parent)
            parent_info = os.lstat(parent_path)
            if not stat.S_ISDIR(parent_info.st_mode) or parent_info.st_uid != os.getuid():
                raise ValueError("unsafe_db_directory")
            for name in dirs:
                child = parent_path / name
                info = os.lstat(child)
                if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid():
                    raise ValueError(f"unsafe_db_subdirectory:{child}")
            for name in files:
                child = parent_path / name
                info = os.lstat(child)
                if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_nlink != 1:
                    raise ValueError(f"unsafe_db_file:{child}")
                found[str(child.relative_to(root))] = {
                    "size": info.st_size, "sha256": _sha(child), "mode": oct(stat.S_IMODE(info.st_mode)),
                    "device": info.st_dev, "inode": info.st_ino,
                }
    return found


def _journal_state(root: Path) -> dict:
    journal = root / "turn_admission_journal.jsonl"
    if not journal.exists():
        return {"exists": False, "events": 0, "last_sequence": None}
    if journal.is_symlink() or not journal.is_file():
        raise ValueError("unsafe_journal")
    data = journal.read_bytes()
    lines = data.splitlines()
    last = json.loads(lines[-1]) if lines else {}
    return {"exists": True, "events": len(lines), "last_sequence": last.get("sequence"),
            "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def snapshot(root: Path, label: str) -> dict:
    if label not in {"t0", "tpre", "tpost"}:
        raise ValueError("invalid_snapshot_label")
    evidence = root / "evidence"
    _private_dir(evidence)
    dest = evidence / f"db-{label}.json"
    if dest.exists() or dest.is_symlink():
        raise ValueError("snapshot_already_exists")
    receipt_path = root / "active_db_receipt.json"
    if receipt_path.is_symlink() or not receipt_path.is_file():
        raise ValueError("missing_active_db_receipt")
    start = time.monotonic_ns()
    receipt_bytes = receipt_path.read_bytes()
    before_journal = _journal_state(root)
    before = _tree(root)
    after = _tree(root)
    after_journal = _journal_state(root)
    receipt_again = receipt_path.read_bytes()
    end = time.monotonic_ns()
    if before != after or before_journal != after_journal or receipt_bytes != receipt_again:
        raise ValueError("snapshot_source_drift")
    receipt = json.loads(receipt_bytes)
    payload = {"schema": "uruha_p4_private_db_snapshot_v1", "label": label,
               "runtime_root": str(root), "monotonic_start_ns": start,
               "monotonic_end_ns": end, "db_regular_files": before,
               "journal": before_journal, "active_receipt_sha256": hashlib.sha256(receipt_bytes).hexdigest(),
               "active_receipt": receipt}
    _private_bytes(dest, (json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode())
    dirfd = os.open(evidence, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(dirfd)
    finally:
        os.close(dirfd)
    return {"path": str(dest), "sha256": _sha(dest), "db_regular_files": len(before),
            "journal_events": before_journal["events"], "monotonic_end_ns": end}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("cache", "warm", "snapshot"))
    parser.add_argument("--runtime-root", required=True)
    parser.add_argument("--source-archive")
    parser.add_argument("--label", choices=("t0", "tpre", "tpost"))
    args = parser.parse_args()
    root = _root(args.runtime_root)
    if args.action == "cache":
        if not args.source_archive or args.label:
            parser.error("cache requires --source-archive only")
        result = prepare_cache(root, Path(args.source_archive))
    elif args.action == "warm":
        if args.source_archive or args.label:
            parser.error("warm accepts no source or label")
        result = warm_cache(root)
    else:
        if not args.label or args.source_archive:
            parser.error("snapshot requires --label only")
        result = snapshot(root, args.label)
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
