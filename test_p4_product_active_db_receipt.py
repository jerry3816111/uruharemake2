"""Zero-model contracts for the opt-in, same-PID active Chroma DB receipt.

These tests do not establish a fresh model, Safari, or DB writeback result.
"""

import json
import os
import stat
from types import SimpleNamespace

import pytest

import uruha_web_ui as web


PRIVATE_DIALOGUE = "raw-user-dialogue-must-not-appear-42"


class FakeClient:
    def __init__(self, directory):
        self.directory = directory
        self.settings_calls = 0
        self.fail_settings = False

    def get_settings(self):
        self.settings_calls += 1
        if self.fail_settings:
            raise RuntimeError("settings unavailable")
        return SimpleNamespace(persist_directory=self.directory)


class FakeBrain:
    def __init__(self, directory):
        self.memory = SimpleNamespace(client=FakeClient(directory))
        self.runtime = SimpleNamespace(autonomous_tick_index=0)
        self.reset_calls = []
        self.generation_calls = 0
        self.fail_reset = False

    def reset_session(self, path):
        self.reset_calls.append(path)
        self.memory.client.directory = path
        if self.fail_reset:
            raise RuntimeError("reset failed")
        self.runtime.autonomous_tick_index = 0

    def run_background_cycle(self, allow_model_maintenance=False):
        assert allow_model_maintenance is False
        self.runtime.autonomous_tick_index += 1
        return {"goal": {"kind": "test"}}


@pytest.fixture
def isolated_root(tmp_path, monkeypatch):
    root = tmp_path / "isolated"
    root.mkdir(mode=0o700)
    os.chmod(root, 0o700)
    memory_db = root / "memory_db"
    session_db = root / "session_db"
    memory_db.mkdir(mode=0o700)
    session_db.mkdir(mode=0o700)
    receipt = root / "active_db_receipt.json"
    monkeypatch.setenv("URUHA_MEMORY_DB_PATH", str(memory_db))
    monkeypatch.setenv("URUHA_WEB_SESSION_DB_PATH", str(session_db))
    monkeypatch.setattr(web, "WEB_ACTIVE_DB_RECEIPT_PATH", str(receipt))
    monkeypatch.setattr(web.RuntimeManager, "_idle_consolidation_loop", lambda self: None)
    return root, memory_db, session_db, receipt


def _read(receipt):
    return json.loads(receipt.read_text(encoding="utf-8"))


def test_receipt_tracks_live_client_before_and_after_reset_without_generation(
    isolated_root, monkeypatch
):
    root, memory_db, session_db, receipt = isolated_root
    brain = FakeBrain(str(memory_db))
    monkeypatch.setattr(web, "UruhaBrainV4_Mac", lambda **_kwargs: brain)
    manager = web.RuntimeManager()
    before = _read(receipt)
    assert before["brain_status"] == "not_started"
    assert before["active_db_path"] is None
    assert before["reset_generation"] == 0
    assert manager.get_brain() is brain
    ready = _read(receipt)
    assert ready == {
        "schema": "uruha_web_active_db_receipt_p4_v1",
        "pid": os.getpid(),
        "session_id": manager._session_id,
        "reset_generation": 0,
        "human_submission_finish_count": 0,
        "brain_status": "ready",
        "active_db_status": "available",
        "active_db_path": str(memory_db.resolve()),
        "autonomous_tick_index": 0,
        "contains_raw_dialogue": False,
    }
    assert stat.S_IMODE(receipt.stat().st_mode) == 0o600
    assert receipt.stat().st_uid == os.getuid()
    assert PRIVATE_DIALOGUE not in receipt.read_text(encoding="utf-8")
    assert brain.generation_calls == 0
    assert brain.memory.client.settings_calls >= 1

    # The completion hook re-reads the live client.  A silent path change
    # after startup must not leave the startup receipt looking current.
    brain.memory.client.directory = str(session_db)
    manager.finish_human_turn()
    after_turn = _read(receipt)
    assert after_turn["human_submission_finish_count"] == 1
    assert after_turn["active_db_path"] == str(session_db.resolve())
    brain.memory.client.directory = str(memory_db)

    prior_session = manager._session_id
    assert manager.reset_brain_session() is brain
    after = _read(receipt)
    assert after["pid"] == ready["pid"]
    assert after["session_id"] != prior_session
    assert after["session_id"] == manager._session_id
    assert after["reset_generation"] == 1
    assert after["human_submission_finish_count"] == 1
    assert after["active_db_path"] == str(session_db.resolve())
    assert after["autonomous_tick_index"] == 0
    assert brain.reset_calls == [str(session_db)]
    assert brain.generation_calls == 0

    manager.run_background_once()
    background = _read(receipt)
    assert background["autonomous_tick_index"] == 1
    assert background["active_db_path"] == str(session_db.resolve())
    assert brain.generation_calls == 0


def test_settings_error_is_unavailable_and_never_falls_back_to_env(isolated_root, monkeypatch):
    _root, memory_db, _session_db, receipt = isolated_root
    brain = FakeBrain(str(memory_db))
    brain.memory.client.fail_settings = True
    monkeypatch.setattr(web, "UruhaBrainV4_Mac", lambda **_kwargs: brain)
    manager = web.RuntimeManager()
    manager.get_brain()
    row = _read(receipt)
    assert row["brain_status"] == "ready"
    assert row["active_db_status"] == "unavailable"
    assert row["active_db_path"] is None
    assert row["autonomous_tick_index"] is None
    assert str(memory_db) not in receipt.read_text(encoding="utf-8")


def test_failed_reset_invalidates_prior_ready_receipt(isolated_root, monkeypatch):
    _root, memory_db, _session_db, receipt = isolated_root
    brain = FakeBrain(str(memory_db))
    monkeypatch.setattr(web, "UruhaBrainV4_Mac", lambda **_kwargs: brain)
    manager = web.RuntimeManager()
    manager.get_brain()
    original_session = manager._session_id
    brain.fail_reset = True
    with pytest.raises(RuntimeError, match="reset failed"):
        manager.reset_brain_session()
    row = _read(receipt)
    assert row["brain_status"] == "reset_error"
    assert row["active_db_path"] is None
    assert row["reset_generation"] == 0
    assert row["session_id"] == original_session


def test_receipt_replace_is_atomic_private_and_contains_no_raw_data(
    isolated_root, monkeypatch
):
    root, memory_db, _session_db, receipt = isolated_root
    brain = FakeBrain(str(memory_db))
    monkeypatch.setattr(web, "UruhaBrainV4_Mac", lambda **_kwargs: brain)
    original_replace = web.os.replace
    observations = []

    def inspect_then_replace(source, target):
        assert source.parent == root and target == receipt
        assert stat.S_IMODE(source.stat().st_mode) == 0o600
        if target.exists():
            assert isinstance(_read(target), dict)
        observations.append(source.name)
        original_replace(source, target)

    monkeypatch.setattr(web.os, "replace", inspect_then_replace)
    manager = web.RuntimeManager()
    manager.get_brain()
    assert len(observations) >= 3  # not_started, loading, ready
    assert not list(root.glob(".active_db_receipt.*.tmp"))
    assert stat.S_IMODE(receipt.stat().st_mode) == 0o600
    assert PRIVATE_DIALOGUE not in receipt.read_text(encoding="utf-8")


def test_untrusted_receipt_root_or_target_fails_closed_without_changing_brain(
    isolated_root, monkeypatch
):
    root, memory_db, _session_db, receipt = isolated_root
    brain = FakeBrain(str(memory_db))
    monkeypatch.setattr(web, "UruhaBrainV4_Mac", lambda **_kwargs: brain)
    os.chmod(root, 0o755)
    manager = web.RuntimeManager()
    assert manager.get_brain() is brain
    assert not receipt.exists()
    assert brain.generation_calls == 0
    os.chmod(root, 0o700)
    receipt.symlink_to(root / "memory_db")
    assert manager._publish_active_db_receipt() is False
    assert receipt.is_symlink()
    assert brain.generation_calls == 0


def test_optout_has_no_private_receipt_and_no_live_settings_read(isolated_root, monkeypatch):
    _root, memory_db, _session_db, receipt = isolated_root
    brain = FakeBrain(str(memory_db))
    monkeypatch.setattr(web, "WEB_ACTIVE_DB_RECEIPT_PATH", "")
    monkeypatch.setattr(web, "UruhaBrainV4_Mac", lambda **_kwargs: brain)
    manager = web.RuntimeManager()
    assert manager.get_brain() is brain
    assert not receipt.exists()
    assert brain.memory.client.settings_calls == 0
