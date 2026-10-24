#!/usr/bin/env python3
"""One-shot, disclosed empty-profile setup for a stopped isolated P4 run.

This intentionally writes a *new* Chroma DB. It is not a product turn, a
read-only snapshot, or a repair for any earlier T0 receipt. The caller must
name the exact first-run controller identity observed at 0-turn readiness.
"""

from __future__ import annotations

import argparse
import json
import math
import os
from pathlib import Path
import re
import stat
import subprocess
import time

import p4_b_safe_isolated_product_launcher_v2 as sandbox
import p4_preference_fallback_detached_control as control
import p4_preference_fallback_launchd_control as launchd
from p4_preference_fallback_snapshot import SnapshotError, validate_runtime_root
from p4_profile_full_content_snapshot import snapshot_runtime_root


ROOT = Path(__file__).resolve().parent
SCHEMA = "uruha_p4_isolated_profile_preinitialize_v1"
INTENT_NAME = "profile-preinitialize-intent.json"
RECEIPT_NAME = "profile-preinitialize-receipt.json"
_RUN_METADATA_RE = re.compile(r"p4_preference_fallback_detached\.[0-9a-f]{16}\.json\Z")
_CHILD_CODE = """
import json
import os
from pathlib import Path
import chromadb

db = Path(os.environ["URUHA_MEMORY_DB_PATH"])
if not db.is_dir() or any(db.iterdir()):
    raise RuntimeError("profile_setup_db_not_empty_at_child_start")
client = chromadb.PersistentClient(path=str(db))
if client.list_collections():
    raise RuntimeError("profile_setup_existing_collection")
profile = client.create_collection("user_profile")
names = sorted(item.name if hasattr(item, "name") else str(item)
               for item in client.list_collections())
count = profile.count()
if names != ["user_profile"] or count != 0:
    raise RuntimeError("profile_setup_not_exclusively_empty")
print("PROFILE_PREINIT_RESULT=" + json.dumps({"collections": names, "profile_rows": count}))
"""


class PreinitializeError(RuntimeError):
    """The setup is not provably confined to a fresh stopped test runtime."""


def _timestamp(value: object) -> bool:
    return type(value) in (int, float) and math.isfinite(value) and value > 0


def _require_private_tree(root: Path) -> None:
    """Do not let Chroma follow links, hardlinks or special nodes in HOME."""
    stack = [root]
    while stack:
        directory = stack.pop()
        info = directory.lstat()
        if (not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid()
                or stat.S_IMODE(info.st_mode) != 0o700):
            raise PreinitializeError(f"unsafe_runtime_directory:{directory}")
        with os.scandir(directory) as entries:
            for entry in entries:
                child = Path(entry.path)
                item = entry.stat(follow_symlinks=False)
                if item.st_uid != os.getuid() or stat.S_ISLNK(item.st_mode):
                    raise PreinitializeError(f"unsafe_runtime_owner_or_link:{child}")
                if stat.S_ISDIR(item.st_mode):
                    stack.append(child)
                elif stat.S_ISREG(item.st_mode):
                    if item.st_nlink != 1 or stat.S_IMODE(item.st_mode) & 0o077:
                        raise PreinitializeError(f"unsafe_runtime_file:{child}")
                else:
                    raise PreinitializeError(f"unsafe_runtime_special_node:{child}")


def _private_json(path: Path, value: dict) -> None:
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    fd = os.open(path, flags, 0o600)
    os.fchmod(fd, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=False, sort_keys=True, indent=2)
        stream.write("\n")


def _empty_layout(root: Path) -> dict[str, Path]:
    layout = {
        "runtime_root": root,
        "memory_db": root / "memory_db",
        "session_db": root / "session_db",
        "web_logs": root / "web_logs",
        "jsonl_log": root / "web_logs" / "conversation.jsonl",
        "text_log": root / "web_logs" / "conversation.txt",
    }
    for key in ("memory_db", "session_db", "web_logs"):
        directory = layout[key]
        if not directory.is_dir() or any(directory.iterdir()):
            raise PreinitializeError(f"zero_turn_tree_not_empty:{key}")
    return layout


def _database_bytes(db: Path) -> int:
    return sum(path.stat().st_size for path in db.rglob("*") if path.is_file())


def _verified_stopped_first_run(root: Path, *, run_id: str, pid: int,
                                entrypoint: Path) -> tuple[dict, Path]:
    if not re.fullmatch(r"[0-9a-f]{16}", run_id) or pid <= 0:
        raise PreinitializeError("invalid_explicit_run_identity")
    if (not entrypoint.is_absolute() or entrypoint.parent != ROOT
            or not entrypoint.name.startswith("uruha_web_ui_product_p4_")
            or entrypoint.suffix != ".py" or entrypoint.is_symlink()
            or not entrypoint.is_file()):
        raise PreinitializeError("invalid_expected_product_entrypoint")
    metadata_files = [path for path in root.iterdir()
                      if _RUN_METADATA_RE.fullmatch(path.name)]
    if len(metadata_files) != 1 or metadata_files[0].name != control._name(run_id, "json"):
        raise PreinitializeError("not_a_single_first_run")
    current = control._read_private_json(root / control.CURRENT)
    if current != {"schema": control.SCHEMA, "run_id": run_id, "uid": os.getuid()}:
        raise PreinitializeError("current_run_identity_mismatch")
    metadata = control._read_private_json(root / control._name(run_id, "json"))
    python_path = metadata.get("python_path")
    calibration = metadata.get("calibration")
    profile = root / control._name(run_id, "sandbox.sb")
    if (metadata.get("schema") != control.SCHEMA
            or metadata.get("runtime_root") != str(root)
            or metadata.get("run_id") != run_id
            or metadata.get("previous_run_id") is not None
            or metadata.get("mode") != "product"
            or metadata.get("uid") != os.getuid()
            or metadata.get("pid") != pid
            or metadata.get("port") != control.PORT
            or metadata.get("auto_restart") is not False
            or not isinstance(python_path, str)
            or not Path(python_path).is_absolute()
            or not Path(python_path).is_file()
            or not os.access(python_path, os.X_OK)
            or not isinstance(calibration, dict)
            or not isinstance(calibration.get("python_ps_executable"), str)
            or not Path(calibration["python_ps_executable"]).is_absolute()
            or not Path(calibration["python_ps_executable"]).is_file()
            or not os.access(calibration["python_ps_executable"], os.X_OK)
            or not isinstance(metadata.get("start_identity"), dict)
            or metadata["start_identity"].get("pid") != pid
            or metadata["start_identity"].get("uid") != os.getuid()
            or metadata["start_identity"].get("pgid") != pid
            or metadata.get("isolation") != control._expected_isolation(root)
            or metadata.get("expected_argv") != sandbox.sandbox_command(
                profile, [python_path, str(entrypoint)])
            or metadata.get("wrapper_expected_command") != " ".join(metadata["expected_argv"])
            or metadata.get("pre_main_command") != f"{python_path} {entrypoint}"
            or metadata.get("final_command") != (
                f"{calibration['python_ps_executable']} {entrypoint}")
            or metadata["start_identity"].get("command") not in {
                metadata.get("wrapper_expected_command"),
                metadata.get("pre_main_command"), metadata.get("final_command")
            }
            or not _timestamp(metadata.get("started_at_unix"))):
        raise PreinitializeError("product_run_metadata_mismatch")
    if not profile.is_file() or profile.read_text(encoding="utf-8") != sandbox.sandbox_profile_text(
        [ROOT, sandbox.ORIGINAL_CHECKOUT]
    ):
        raise PreinitializeError("sandbox_profile_mismatch")
    ready = control._read_private_json(root / control._name(run_id, "ready.json"))
    final_identity = ready.get("final_identity")
    if (ready.get("schema") != control.SCHEMA or ready.get("runtime_root") != str(root)
            or ready.get("run_id") != run_id or ready.get("pid") != pid
            or ready.get("start_identity") != metadata["start_identity"]
            or ready.get("http_status") != 200
            or ready.get("listener_same_pid_before_after") is not True
            or not _timestamp(ready.get("verified_at_unix"))
            or ready["verified_at_unix"] < metadata["started_at_unix"]
            or not isinstance(final_identity, dict)
            or not control._same_origin(final_identity, metadata)
            or final_identity.get("command") != metadata["final_command"]):
        raise PreinitializeError("zero_turn_ready_record_mismatch")
    stopped = control._read_private_json(root / control._name(run_id, "stop.json"))
    if (stopped.get("schema") != control.SCHEMA
            or stopped.get("runtime_root") != str(root)
            or stopped.get("run_id") != run_id or stopped.get("pid") != pid
            or stopped.get("before_identity") != final_identity
            or stopped.get("before_stage") != "final_python"
            or stopped.get("ready_identity") != final_identity
            or stopped.get("signalled") is not True
            or stopped.get("planned_stop") is not True
            or stopped.get("original_pid_exited") is not True
            or stopped.get("port_vacant") is not True
            or stopped.get("port_vacancy_basis") != "no_tcp_listener_all_owners_lsof"
            or not _timestamp(stopped.get("observed_at_unix"))
            or stopped["observed_at_unix"] < ready["verified_at_unix"]):
        raise PreinitializeError("zero_turn_planned_stop_record_mismatch")
    if control._identity(pid) is not None or control._group_members(pid) != []:
        raise PreinitializeError("old_product_process_still_active")
    if control._port_listeners() != set():
        raise PreinitializeError("product_port_not_vacant")
    if not sandbox.SANDBOX_EXEC.is_file() or not os.access(sandbox.SANDBOX_EXEC, os.X_OK):
        raise PreinitializeError("sandbox_executor_unavailable")
    return metadata, profile


def preinitialize_isolated_profile(requested: str | Path, *, run_id: str, pid: int,
                                   entrypoint: str | Path) -> dict:
    """Create one empty collection; return a receipt also saved under evidence/."""
    try:
        root = validate_runtime_root(requested)
    except SnapshotError as exc:
        raise PreinitializeError(str(exc)) from exc
    _require_private_tree(root)
    layout = _empty_layout(root)
    entrypoint = Path(entrypoint)
    metadata, profile = _verified_stopped_first_run(
        root, run_id=run_id, pid=pid, entrypoint=entrypoint,
    )
    evidence = root / "evidence"
    if evidence.exists() or evidence.is_symlink():
        if not evidence.is_dir() or stat.S_IMODE(evidence.lstat().st_mode) != 0o700:
            raise PreinitializeError("unsafe_evidence_directory")
    else:
        evidence.mkdir(mode=0o700)
    if (evidence / INTENT_NAME).exists() or (evidence / RECEIPT_NAME).exists():
        raise PreinitializeError("profile_preinitialization_already_attempted")
    before = snapshot_runtime_root(root)
    if (before["db_status"], before["profile_collection_status"],
            before["profile_row_count"], before["profile_content_sha256"]) != (
            "absent", "unavailable", 0, None):
        raise PreinitializeError("profile_db_not_absent_before_setup")
    started_at = time.time()
    started_clock = time.perf_counter()
    intent = {
        "schema": SCHEMA, "runtime_root": str(root), "run_id": run_id,
        "pid": pid, "started_at_unix": started_at,
        "before": before, "db_bytes_before": _database_bytes(layout["memory_db"]),
    }
    _private_json(evidence / INTENT_NAME, intent)
    env = launchd._isolated_env(layout, port=control.PORT)
    env["ANONYMIZED_TELEMETRY"] = "False"
    command = sandbox.sandbox_command(
        profile, [metadata["python_path"], "-c", _CHILD_CODE],
    )
    try:
        completed = subprocess.run(
            command, cwd=ROOT, env=env, stdin=subprocess.DEVNULL,
            capture_output=True, text=True, check=False, timeout=90, umask=0o077,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise PreinitializeError(f"sandboxed_profile_setup_failed:{type(exc).__name__}") from exc
    if completed.returncode != 0:
        raise PreinitializeError(f"sandboxed_profile_setup_failed:rc={completed.returncode}")
    marker = "PROFILE_PREINIT_RESULT="
    results = [line[len(marker):] for line in completed.stdout.splitlines()
               if line.startswith(marker)]
    try:
        child = json.loads(results[0]) if len(results) == 1 else None
    except json.JSONDecodeError as exc:
        raise PreinitializeError("sandboxed_profile_setup_output_invalid") from exc
    if child != {"collections": ["user_profile"], "profile_rows": 0}:
        raise PreinitializeError("sandboxed_profile_setup_output_invalid")
    _require_private_tree(root)
    bytes_after_creation = _database_bytes(layout["memory_db"])
    after = snapshot_runtime_root(root)
    if (after["db_status"], after["profile_collection_status"],
            after["profile_row_count"]) != ("present", "present", 0):
        raise PreinitializeError("profile_setup_after_status_invalid")
    if not isinstance(after["profile_content_sha256"], str):
        raise PreinitializeError("profile_setup_digest_missing")
    # The content snapshot deliberately reports only user_profile. Recheck
    # collection membership independently so an episode collection cannot be
    # hidden by an otherwise valid empty-profile digest.
    import chromadb

    client = chromadb.PersistentClient(path=str(layout["memory_db"]))
    names = sorted(item.name if hasattr(item, "name") else str(item)
                   for item in client.list_collections())
    if names != ["user_profile"] or client.get_collection("user_profile").count() != 0:
        raise PreinitializeError("profile_setup_unexpected_collection_or_rows")
    _require_private_tree(root)
    if control._identity(pid) is not None or control._group_members(pid) != []:
        raise PreinitializeError("old_product_process_active_after_setup")
    if control._port_listeners() != set():
        raise PreinitializeError("product_port_occupied_after_setup")
    receipt = {
        **intent, "entrypoint": str(entrypoint), "python_path": metadata["python_path"],
        "sandbox_profile": str(profile),
        "zero_turn_ready_and_planned_stop_verified": True,
        "old_pid_and_group_absent": True, "port_vacant_rechecked": True,
        "collections_after_verification": names,
        "episodic_memory_collection_status": "absent",
        "after": after, "db_bytes_after_creation": bytes_after_creation,
        "db_bytes_after_verification": _database_bytes(layout["memory_db"]),
        "finished_at_unix": time.time(),
        "setup_wall_seconds": time.perf_counter() - started_clock,
    }
    _private_json(evidence / RECEIPT_NAME, receipt)
    return receipt


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime-root", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--pid", required=True, type=int)
    parser.add_argument("--entrypoint", required=True,
                        help="Exact product entrypoint used for the stopped 0-turn run")
    args = parser.parse_args(argv)
    receipt = preinitialize_isolated_profile(
        args.runtime_root, run_id=args.run_id, pid=args.pid,
        entrypoint=args.entrypoint,
    )
    print(json.dumps(receipt, ensure_ascii=False, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
