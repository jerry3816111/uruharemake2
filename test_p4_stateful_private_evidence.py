"""No-provider contracts for the private f3 measurement helper."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

import p4_stateful_private_evidence as evidence


@pytest.fixture
def private_root(tmp_path, monkeypatch):
    monkeypatch.setattr(evidence.tempfile, "gettempdir", lambda: str(tmp_path))
    root = tmp_path / "uruha-product-test"
    root.mkdir(mode=0o700)
    (root / "uruha_product_launcher_manifest.json").write_text(
        json.dumps({"schema": "uruha_p4_b_runtime_root_v1", "created_by_launcher": True})
    )
    for name in ("memory_db", "session_db"):
        (root / name).mkdir(mode=0o700)
    return root


def test_snapshot_is_durable_exclusive_and_bound_to_receipt(private_root):
    root = private_root
    (root / "memory_db" / "chroma.sqlite3").write_bytes(b"private fixture")
    receipt = {"pid": os.getpid(), "session_id": "isolated", "active_db_path": str(root / "memory_db")}
    (root / "active_db_receipt.json").write_text(json.dumps(receipt))
    assert evidence._root(str(root)) == root
    output = evidence.snapshot(root, "t0")
    saved = json.loads(Path(output["path"]).read_text())
    assert saved["active_receipt"] == receipt
    assert saved["db_regular_files"]["memory_db/chroma.sqlite3"]["size"] == 15
    assert Path(output["path"]).stat().st_mode & 0o777 == 0o600
    assert saved["monotonic_start_ns"] <= saved["monotonic_end_ns"]
    with pytest.raises(ValueError, match="snapshot_already_exists"):
        evidence.snapshot(root, "t0")


def test_snapshot_rejects_symlinked_db_file(private_root, tmp_path):
    root = private_root
    outside = tmp_path / "outside"
    outside.write_text("do not follow")
    (root / "memory_db" / "link").symlink_to(outside)
    (root / "active_db_receipt.json").write_text("{}")
    with pytest.raises(ValueError, match="unsafe_db_file"):
        evidence.snapshot(root, "tpre")
    assert not (root / "evidence" / "db-tpre.json").exists()


def test_root_must_be_launcher_owned(private_root, tmp_path):
    alien = tmp_path / "other"
    alien.mkdir(mode=0o700)
    with pytest.raises(ValueError, match="not_immediate_product_temp_root"):
        evidence._root(str(alien))
    alias = tmp_path / "uruha-product-alias"
    alias.symlink_to(private_root, target_is_directory=True)
    with pytest.raises(ValueError, match="root_symlink"):
        evidence._root(str(alias))
