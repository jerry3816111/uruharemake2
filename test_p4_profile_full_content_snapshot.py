"""Isolated full-profile content receipts; no model, Web, or formal DB."""

from __future__ import annotations

import json
import os
import stat

import chromadb
import pytest

import p4_b_safe_isolated_product_launcher as launcher
from p4_preference_fallback_snapshot import SnapshotError
from p4_profile_full_content_snapshot import save_snapshot, snapshot_runtime_root


def _runtime(tmp_path):
    root, created = launcher.prepare_runtime_root(None, reuse=False, temporary_parent=tmp_path)
    assert created
    launcher.build_runtime_layout(root)
    return root


def _profiles(root):
    client = chromadb.PersistentClient(path=str(root / "memory_db"))
    return client.get_or_create_collection("user_profile")


def test_status_distinguishes_missing_db_collection_and_present_empty(tmp_path):
    root = _runtime(tmp_path)
    before = snapshot_runtime_root(root)
    assert before["db_status"] == "absent"
    assert before["profile_collection_status"] == "unavailable"
    assert before["profile_content_sha256"] is None
    assert not (root / "memory_db" / "chroma.sqlite3").exists()

    chromadb.PersistentClient(path=str(root / "memory_db"))
    no_collection = snapshot_runtime_root(root)
    assert no_collection["db_status"] == "present"
    assert no_collection["profile_collection_status"] == "absent"
    assert no_collection["profile_content_sha256"] is None

    _profiles(root)
    empty = snapshot_runtime_root(root)
    assert empty["profile_collection_status"] == "present"
    assert empty["profile_row_count"] == 0
    assert len(empty["profile_content_sha256"]) == 64


def test_all_subject_document_metadata_embedding_and_membership_affect_digest(tmp_path):
    root = _runtime(tmp_path)
    profiles = _profiles(root)
    profiles.add(
        ids=["user-b", "friend-a"],
        embeddings=[[0.2, 0.8], [1.0, 0.0]],
        metadatas=[{"subject": "user", "value": "柚子茶"},
                   {"subject": "friend", "value": "珈琲"}],
        documents=["private user preference", "private friend preference"],
    )
    base = snapshot_runtime_root(root)
    assert base["profile_row_count"] == 2
    assert base["profile_collection_status"] == "present"

    # The prior ID/metadata-only, subject=user snapshot misses this change.
    profiles.update(ids=["friend-a"], documents=["changed friend document"],
                    embeddings=[[1.0, 0.0]])
    changed_document = snapshot_runtime_root(root)
    assert changed_document["profile_content_sha256"] != base["profile_content_sha256"]
    profiles.update(ids=["friend-a"], documents=["private friend preference"],
                    embeddings=[[1.0, 0.0]])
    assert snapshot_runtime_root(root)["profile_content_sha256"] == base["profile_content_sha256"]

    profiles.update(ids=["friend-a"], metadatas=[{"subject": "friend", "value": "紅茶"}])
    assert snapshot_runtime_root(root)["profile_content_sha256"] != base["profile_content_sha256"]
    profiles.update(ids=["friend-a"], metadatas=[{"subject": "friend", "value": "珈琲"}])
    assert snapshot_runtime_root(root)["profile_content_sha256"] == base["profile_content_sha256"]

    profiles.update(ids=["friend-a"], embeddings=[[0.9, 0.1]])
    assert snapshot_runtime_root(root)["profile_content_sha256"] != base["profile_content_sha256"]
    profiles.update(ids=["friend-a"], embeddings=[[1.0, 0.0]])
    assert snapshot_runtime_root(root)["profile_content_sha256"] == base["profile_content_sha256"]

    profiles.add(ids=["third-c"], embeddings=[[0.0, 1.0]],
                 metadatas=[{"subject": "other"}], documents=["other fact"])
    assert snapshot_runtime_root(root)["profile_row_count"] == 3
    assert snapshot_runtime_root(root)["profile_content_sha256"] != base["profile_content_sha256"]
    profiles.delete(ids=["third-c"])
    assert snapshot_runtime_root(root)["profile_content_sha256"] == base["profile_content_sha256"]

    profiles.delete(ids=["friend-a"])
    profiles.add(ids=["friend-new"], embeddings=[[1.0, 0.0]],
                 metadatas=[{"subject": "friend", "value": "珈琲"}],
                 documents=["private friend preference"])
    assert snapshot_runtime_root(root)["profile_row_count"] == 2
    assert snapshot_runtime_root(root)["profile_content_sha256"] != base["profile_content_sha256"]


def test_receipt_excludes_plaintext_is_exclusive_and_rejects_unsafe_input(tmp_path):
    root = _runtime(tmp_path)
    profiles = _profiles(root)
    profiles.add(ids=["secret-id"], embeddings=[[1.0, 0.0]],
                 metadatas=[{"subject": "friend", "value": "SECRET_VALUE"}],
                 documents=["SECRET_DOCUMENT"])
    snapshot = snapshot_runtime_root(root)
    target = save_snapshot(root, "before-t1", snapshot)
    saved = target.read_text(encoding="utf-8")
    assert json.loads(saved) == snapshot
    assert "SECRET_DOCUMENT" not in saved
    assert "SECRET_VALUE" not in saved
    assert "secret-id" not in saved
    assert stat.S_IMODE(target.stat().st_mode) == 0o600
    assert stat.S_IMODE(target.parent.stat().st_mode) == 0o700
    with pytest.raises(FileExistsError):
        save_snapshot(root, "before-t1", snapshot)
    with pytest.raises(SnapshotError, match="invalid_snapshot_label"):
        save_snapshot(root, "../escape", snapshot)
    with pytest.raises(SnapshotError, match="invalid_profile_full_content_receipt"):
        save_snapshot(root, "injected", {**snapshot, "document": "SECRET_DOCUMENT"})

    os.chmod(root, 0o755)
    with pytest.raises(SnapshotError, match="runtime_root_wrong_mode"):
        snapshot_runtime_root(root)
    os.chmod(root, 0o700)
    with pytest.raises(SnapshotError, match="runtime_root_must_be_absolute"):
        snapshot_runtime_root("relative/path")


def test_count_change_during_read_fails_closed(tmp_path, monkeypatch):
    root = _runtime(tmp_path)
    _profiles(root)

    class ChangingCollection:
        def __init__(self):
            self.calls = 0

        def count(self):
            self.calls += 1
            return self.calls

        def get(self, *, include):
            assert include == ["metadatas", "documents", "embeddings"]
            return {"ids": ["one"], "metadatas": [None],
                    "documents": ["text"], "embeddings": [[1.0, 0.0]]}

    class ChangingClient:
        def list_collections(self):
            return ["user_profile"]

        def get_collection(self, name):
            assert name == "user_profile"
            return ChangingCollection()

    monkeypatch.setattr(chromadb, "PersistentClient", lambda **_: ChangingClient())
    with pytest.raises(SnapshotError, match="profile_collection_changed_during_snapshot"):
        snapshot_runtime_root(root)


@pytest.mark.parametrize("link_kind", ["sqlite_hardlink", "nested_symlink", "nested_hardlink"])
def test_memory_db_link_is_rejected_before_chroma_or_receipt(tmp_path, monkeypatch, link_kind):
    root = _runtime(tmp_path)
    clean = snapshot_runtime_root(root)
    db_path = root / "memory_db"
    external = tmp_path / "external-data"
    external.write_text("outside isolated root", encoding="utf-8")
    if link_kind == "sqlite_hardlink":
        os.link(external, db_path / "chroma.sqlite3")
    else:
        nested = db_path / "index-dir"
        nested.mkdir(mode=0o700)
        if link_kind == "nested_symlink":
            (nested / "external-link").symlink_to(external)
        else:
            os.link(external, nested / "external-hardlink")

    # This must fail before PersistentClient can follow or mutate a link.
    monkeypatch.setattr(chromadb, "PersistentClient", lambda **_: pytest.fail("Chroma opened unsafe DB"))
    with pytest.raises(SnapshotError, match="memory_db_(hardlink|symlink)"):
        snapshot_runtime_root(root)
    with pytest.raises(SnapshotError, match="memory_db_(hardlink|symlink)"):
        save_snapshot(root, "unsafe", clean)
    assert not (root / "evidence" / "profile-full-unsafe.json").exists()


def test_memory_db_special_file_is_rejected(tmp_path):
    root = _runtime(tmp_path)
    os.mkfifo(root / "memory_db" / "unexpected-pipe")
    with pytest.raises(SnapshotError, match="memory_db_special_file"):
        snapshot_runtime_root(root)
