"""Fresh-root, no-product-turn checks for explicit P4 profile setup."""

from __future__ import annotations

import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import time

import chromadb
import pytest

import p4_b_safe_isolated_product_launcher as launcher
import p4_b_safe_isolated_product_launcher_v2 as sandbox
import p4_preference_fallback_detached_control as control
from p4_profile_preinitialize_isolated import (
    INTENT_NAME, RECEIPT_NAME, PreinitializeError,
    preinitialize_isolated_profile,
)


RUN_ID = "0123456789abcdef"
PID = 424242
ROOT = Path(__file__).resolve().parent
ENTRYPOINT = ROOT / "uruha_web_ui_product_p4_hash_prefix_transport.py"


def _record(path: Path, payload: dict) -> None:
    control._private_json(path, payload)


def _first_stopped_run(tmp_path: Path, monkeypatch) -> Path:
    root, created = launcher.prepare_runtime_root(None, reuse=False, temporary_parent=tmp_path)
    assert created
    launcher.build_runtime_layout(root)
    frozen = root / control._name(RUN_ID, "sandbox.sb")
    control._private_bytes(frozen, sandbox.sandbox_profile_text(
        [ROOT, sandbox.ORIGINAL_CHECKOUT]
    ).encode("utf-8"))
    for suffix in ("stdout.log", "stderr.log"):
        control._private_bytes(root / control._name(RUN_ID, suffix), b"")
    python = str(Path(sys.executable).absolute())
    started = time.time() - 3
    expected = sandbox.sandbox_command(frozen, [python, str(ENTRYPOINT)])
    wrapper = {
        "pid": PID, "uid": os.getuid(), "pgid": PID,
        "lstart": "Sat Oct 17 01:02:03 2026", "command": " ".join(expected),
    }
    final = {**wrapper, "command": f"{python} {ENTRYPOINT}"}
    metadata = {
        "schema": control.SCHEMA, "runtime_root": str(root), "run_id": RUN_ID,
        "previous_run_id": None, "uid": os.getuid(), "mode": "product",
        "port": control.PORT, "pid": PID, "start_identity": wrapper,
        "expected_argv": expected, "wrapper_expected_command": " ".join(expected),
        "pre_main_command": f"{python} {ENTRYPOINT}",
        "final_command": final["command"], "python_path": python,
        "calibration": {"python_ps_executable": python},
        "isolation": control._expected_isolation(root), "auto_restart": False,
        "started_at_unix": started,
    }
    _record(root / control._name(RUN_ID, "json"), metadata)
    _record(root / control.CURRENT, {
        "schema": control.SCHEMA, "run_id": RUN_ID, "uid": os.getuid(),
    })
    _record(root / control._name(RUN_ID, "ready.json"), {
        "schema": control.SCHEMA, "runtime_root": str(root),
        "run_id": RUN_ID, "pid": PID, "start_identity": wrapper,
        "final_identity": final, "http_status": 200,
        "listener_same_pid_before_after": True,
        "verified_at_unix": started + 1,
    })
    _record(root / control._name(RUN_ID, "stop.json"), {
        "schema": control.SCHEMA, "runtime_root": str(root),
        "run_id": RUN_ID, "pid": PID, "before_identity": final,
        "before_stage": "final_python", "ready_identity": final,
        "signalled": True, "planned_stop": True,
        "original_pid_exited": True, "port_vacant": True,
        "port_vacancy_basis": "no_tcp_listener_all_owners_lsof",
        "observed_at_unix": started + 2,
    })
    monkeypatch.setattr(control, "_identity", lambda pid: None)
    monkeypatch.setattr(control, "_group_members", lambda pid: [])
    monkeypatch.setattr(control, "_port_listeners", lambda: set())
    return root


def _setup(root: Path) -> dict:
    return preinitialize_isolated_profile(
        root, run_id=RUN_ID, pid=PID, entrypoint=ENTRYPOINT,
    )


def test_one_shot_real_chroma_setup_has_private_before_after_receipt(tmp_path, monkeypatch):
    if not sandbox.SANDBOX_EXEC.is_file():
        pytest.skip("macOS sandbox-exec unavailable")
    root = _first_stopped_run(tmp_path, monkeypatch)
    receipt = _setup(root)
    assert receipt["before"]["db_status"] == "absent"
    assert receipt["before"]["profile_collection_status"] == "unavailable"
    assert receipt["before"]["profile_content_sha256"] is None
    assert receipt["db_bytes_before"] == 0
    assert receipt["after"]["db_status"] == "present"
    assert receipt["after"]["profile_collection_status"] == "present"
    assert receipt["after"]["profile_row_count"] == 0
    assert isinstance(receipt["after"]["profile_content_sha256"], str)
    assert len(receipt["after"]["profile_content_sha256"]) == 64
    assert receipt["db_bytes_after_creation"] > 0
    assert receipt["db_bytes_after_verification"] > 0
    assert receipt["collections_after_verification"] == ["user_profile"]
    assert receipt["episodic_memory_collection_status"] == "absent"
    assert receipt["setup_wall_seconds"] >= 0
    assert receipt["finished_at_unix"] >= receipt["started_at_unix"]
    client = chromadb.PersistentClient(path=str(root / "memory_db"))
    assert [item.name for item in client.list_collections()] == ["user_profile"]
    assert client.get_collection("user_profile").count() == 0
    intent_path = root / "evidence" / INTENT_NAME
    receipt_path = root / "evidence" / RECEIPT_NAME
    assert json.loads(receipt_path.read_text(encoding="utf-8")) == receipt
    assert json.loads(intent_path.read_text(encoding="utf-8"))["before"] == receipt["before"]
    assert stat.S_IMODE(intent_path.stat().st_mode) == 0o600
    assert stat.S_IMODE(receipt_path.stat().st_mode) == 0o600
    with pytest.raises(PreinitializeError, match="zero_turn_tree_not_empty|already_attempted"):
        _setup(root)


@pytest.mark.parametrize("defect", [
    "unplanned_stop", "missing_ready", "active_old_pid", "port_occupied",
    "conversation_log", "existing_db", "second_run", "symlink", "hardlink",
])
def test_unsafe_or_nonzero_turn_state_never_invokes_chroma(tmp_path, monkeypatch, defect):
    root = _first_stopped_run(tmp_path, monkeypatch)
    stop_path = root / control._name(RUN_ID, "stop.json")
    ready_path = root / control._name(RUN_ID, "ready.json")
    if defect == "unplanned_stop":
        payload = json.loads(stop_path.read_text(encoding="utf-8"))
        payload["planned_stop"] = False
        stop_path.write_text(json.dumps(payload), encoding="utf-8")
    elif defect == "missing_ready":
        ready_path.unlink()
    elif defect == "active_old_pid":
        monkeypatch.setattr(control, "_identity", lambda pid: {"pid": PID})
    elif defect == "port_occupied":
        monkeypatch.setattr(control, "_port_listeners", lambda: {(str(PID), "127.0.0.1:7894")})
    elif defect == "conversation_log":
        (root / "web_logs" / "conversation.jsonl").write_text("turn\n", encoding="utf-8")
    elif defect == "existing_db":
        (root / "memory_db" / "chroma.sqlite3").write_bytes(b"already present")
    elif defect == "second_run":
        _record(root / control._name("fedcba9876543210", "json"), {"unexpected": True})
    elif defect == "symlink":
        (root / "memory_db" / "outside").symlink_to(tmp_path)
    elif defect == "hardlink":
        outside = tmp_path / "outside"
        outside.write_text("outside", encoding="utf-8")
        os.link(outside, root / "memory_db" / "outside")
    monkeypatch.setattr(subprocess, "run", lambda *args, **kwargs: pytest.fail("setup subprocess invoked"))
    with pytest.raises((PreinitializeError, control.ControllerError, FileNotFoundError)):
        _setup(root)
    assert not (root / "evidence" / INTENT_NAME).exists()
    assert not (root / "evidence" / RECEIPT_NAME).exists()


def test_child_failure_leaves_one_shot_0600_intent_and_no_success_receipt(tmp_path, monkeypatch):
    root = _first_stopped_run(tmp_path, monkeypatch)

    class Failed:
        returncode = 17
        stdout = ""
        stderr = "failure"

    calls = []

    def fail_child(command, **kwargs):
        calls.append((command, kwargs))
        return Failed()

    monkeypatch.setattr(subprocess, "run", fail_child)
    with pytest.raises(PreinitializeError, match="sandboxed_profile_setup_failed:rc=17"):
        _setup(root)
    assert len(calls) == 1
    command, kwargs = calls[0]
    assert command[:3] == [str(sandbox.SANDBOX_EXEC), "-f",
                           str(root / control._name(RUN_ID, "sandbox.sb"))]
    assert command[3] == str(Path(sys.executable).absolute())
    assert kwargs["env"]["HOME"] == str(root)
    assert kwargs["env"]["TMPDIR"] == str(root)
    assert kwargs["env"]["URUHA_MEMORY_DB_PATH"] == str(root / "memory_db")
    intent = root / "evidence" / INTENT_NAME
    assert stat.S_IMODE(intent.stat().st_mode) == 0o600
    assert not (root / "evidence" / RECEIPT_NAME).exists()
    with pytest.raises(PreinitializeError, match="already_attempted"):
        _setup(root)
    assert len(calls) == 1
