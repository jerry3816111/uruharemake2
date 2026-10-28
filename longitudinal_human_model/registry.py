"""Immutable experiment bindings and atomic result artifacts."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import tempfile
from typing import Any


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path: str | Path) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"{path}: JSON root must be an object")
    return data


def git_snapshot(repo_root: str | Path) -> dict[str, Any]:
    root = Path(repo_root)
    def run(*args: str) -> str:
        completed = subprocess.run(
            ["git", *args], cwd=root, text=True, capture_output=True, check=True
        )
        return completed.stdout.strip()
    status = run("status", "--porcelain")
    return {
        "commit": run("rev-parse", "HEAD"),
        "branch": run("branch", "--show-current"),
        "worktree_dirty": bool(status),
        "dirty_path_count": len(status.splitlines()) if status else 0,
    }


def runtime_snapshot() -> dict[str, Any]:
    return {
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "python": platform.python_version(),
        "platform": platform.platform(),
        "pid": os.getpid(),
    }


def verify_lock(lock: dict[str, Any], *, repo_root: str | Path) -> list[str]:
    errors: list[str] = []
    root = Path(repo_root)
    bindings = lock.get("file_bindings")
    if not isinstance(bindings, list) or not bindings:
        return ["lock.file_bindings must be a non-empty array"]
    for index, binding in enumerate(bindings):
        if not isinstance(binding, dict):
            errors.append(f"file_bindings[{index}] must be an object")
            continue
        relative = binding.get("path")
        expected = binding.get("sha256")
        if not isinstance(relative, str) or not isinstance(expected, str):
            errors.append(f"file_bindings[{index}] requires path and sha256")
            continue
        path = root / relative
        if not path.is_file():
            errors.append(f"missing bound file: {relative}")
            continue
        actual = sha256_file(path)
        if actual != expected:
            errors.append(f"hash mismatch: {relative}: expected {expected}, got {actual}")
    return errors


def write_json_atomic(path: str | Path, data: dict[str, Any]) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    serialized = json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=target.parent, delete=False) as handle:
        temporary = Path(handle.name)
        handle.write(serialized)
        handle.flush()
        os.fsync(handle.fileno())
    temporary.replace(target)
