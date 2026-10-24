"""Isolated row-ID snapshot evidence contract; no formal DB or Web traffic."""

from __future__ import annotations

import json
import os
import stat

import chromadb
import pytest

import p4_b_safe_isolated_product_launcher as launcher
from p4_preference_fallback_snapshot import (
    SnapshotError,
    save_snapshot,
    snapshot_runtime_root,
    validate_runtime_root,
)


def _runtime(tmp_path):
    root, created = launcher.prepare_runtime_root(None, reuse=False, temporary_parent=tmp_path)
    assert created
    launcher.build_runtime_layout(root)
    return root


def test_snapshot_exact_user_profile_metadata_and_only_turn_episode_ids(tmp_path):
    root = _runtime(tmp_path)
    before = snapshot_runtime_root(root)
    assert before["db_status"] == "absent"
    assert before["user_profile_rows"] == []
    assert before["turn_episode_ids"] == []
    assert not (root / "memory_db" / "chroma.sqlite3").exists()

    client = chromadb.PersistentClient(path=str(root / "memory_db"))
    profiles = client.get_or_create_collection("user_profile")
    profiles.add(
        ids=["user-z", "other-a", "user-b"],
        embeddings=[[1.0, 0.0], [0.0, 1.0], [0.2, 0.8]],
        metadatas=[
            {"subject": "user", "fact_type": "like", "value": "柚子茶", "memory_state": "active", "decay_multiplier": 1.0},
            {"subject": "friend", "fact_type": "like", "value": "珈琲"},
            {"subject": "user", "fact_type": "dislike", "value": "辛味", "memory_state": "historical", "decay_multiplier": 0.4},
        ],
    )
    episodes = client.get_or_create_collection("episodic_memory")
    episodes.add(
        ids=["turn-z", "summary-a", "turn-b"],
        embeddings=[[1.0, 0.0], [0.0, 1.0], [0.2, 0.8]],
        metadatas=[{"source": "turn_episode"}, {"source": "consolidation"}, {"source": "turn_episode"}],
    )
    snapshot = snapshot_runtime_root(root)
    assert snapshot["db_status"] == "present"
    assert [row["id"] for row in snapshot["user_profile_rows"]] == ["user-b", "user-z"]
    assert snapshot["user_profile_rows"][0]["metadata"] == {
        "subject": "user", "fact_type": "dislike", "value": "辛味",
        "memory_state": "historical", "decay_multiplier": 0.4,
    }
    assert snapshot["turn_episode_ids"] == ["turn-b", "turn-z"]
    assert profiles.count() == 3
    assert episodes.count() == 3

    target = save_snapshot(root, "before-t1", snapshot)
    assert target.parent == root / "evidence"
    assert stat.S_IMODE(target.stat().st_mode) == 0o600
    assert stat.S_IMODE(target.parent.stat().st_mode) == 0o700
    assert json.loads(target.read_text(encoding="utf-8")) == snapshot
    with pytest.raises(FileExistsError):
        save_snapshot(root, "before-t1", snapshot)


def test_snapshot_rejects_unverified_root_and_unsafe_evidence_labels(tmp_path):
    root = _runtime(tmp_path)
    assert validate_runtime_root(root) == root.resolve()
    with pytest.raises(SnapshotError, match="runtime_root_must_be_absolute"):
        snapshot_runtime_root("relative/path")
    with pytest.raises(SnapshotError, match="invalid_snapshot_label"):
        save_snapshot(root, "../outside", snapshot_runtime_root(root))

    os.chmod(root, 0o755)
    with pytest.raises(SnapshotError, match="runtime_root_wrong_mode"):
        snapshot_runtime_root(root)
    os.chmod(root, 0o700)
    (root / launcher.MANIFEST_NAME).write_text('{"created_by_launcher":false}', encoding="utf-8")
    with pytest.raises(SnapshotError, match="invalid_launcher_manifest"):
        snapshot_runtime_root(root)


def test_snapshot_rejects_memory_db_symlink(tmp_path):
    root = _runtime(tmp_path)
    db_dir = root / "memory_db"
    db_dir.rmdir()
    db_dir.symlink_to(tmp_path, target_is_directory=True)
    with pytest.raises(SnapshotError, match="memory_db_symlink"):
        snapshot_runtime_root(root)
