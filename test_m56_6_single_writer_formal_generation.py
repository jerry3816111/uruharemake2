from __future__ import annotations

from contextlib import ExitStack
import inspect
import os
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import threading
import unittest
from unittest import mock

import m56_3_lease_gated_generation_runner as runner
import m56_5_crash_safe_no_retry_continuation as continuation
import m56_6_single_writer_formal_generation as single_writer
from test_m56_5_crash_safe_no_retry_continuation import (
    DeterministicProvider,
    materialize_run,
    private_roots,
)


ROOT = Path(__file__).resolve().parent


class m566_private_roots:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.stack = ExitStack()

    def __enter__(self):
        self.stack.enter_context(private_roots(self.root))
        self.stack.enter_context(mock.patch.object(single_writer, "PRIVATE_ROOT", self.root))
        return self

    def __exit__(self, exc_type, exc, traceback):
        return self.stack.__exit__(exc_type, exc, traceback)


class M566SingleWriterFormalGenerationTests(unittest.TestCase):
    def test_contract_and_frozen_dependencies_validate(self):
        report = single_writer.validate_contract()
        self.assertTrue(report["valid"], report["errors"])
        self.assertEqual(report["binding_count"], 3)

    def test_public_execution_accepts_only_run_id(self):
        signature = inspect.signature(single_writer.execute_single_writer_formal_generation)
        self.assertEqual(list(signature.parameters), ["run_id"])

    def test_current_live_state_is_denied_and_zero(self):
        audit = single_writer.build_live_audit()
        self.assertEqual(audit["counts"]["v7_slots_by_ledger"], [0, 0])
        self.assertEqual(audit["counts"]["real_temporal_rows"], 0)
        self.assertFalse(audit["formal_generation_authorized"])
        self.assertEqual(audit["active_formal_lock_holders"], 0)
        self.assertEqual(audit["formal_model_calls"], 0)
        self.assertEqual(audit["generation_target_outcome_access_count"], 0)
        self.assertFalse(audit["formal_result_created"])

    def test_missing_run_fails_before_lock_file_or_run_directory_is_created(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            run_id = "missing-human-authorized-m566"
            with m566_private_roots(root):
                with self.assertRaises(FileNotFoundError):
                    single_writer.execute_single_writer_formal_generation(run_id)
            self.assertFalse((root / run_id).exists())

    def test_lock_is_held_across_exactly_one_unchanged_m565_delegate(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            run_id = "single-delegate-fixture"
            lock_path = root / run_id / "telemetry" / single_writer.LOCK_FILENAME
            delegate_calls: list[str] = []

            def delegate(value: str) -> dict:
                delegate_calls.append(value)
                with self.assertRaisesRegex(PermissionError, "active local writer"):
                    with single_writer._exclusive_run_lock(lock_path):
                        self.fail("a second writer acquired the held lock")
                return {"status": "delegate-return", "run_id": value}

            with m566_private_roots(root), mock.patch.object(
                single_writer, "_validate_permitted_run"
            ), mock.patch.object(
                continuation, "execute_resumable_formal_generation", side_effect=delegate
            ):
                result = single_writer.execute_single_writer_formal_generation(run_id)
            self.assertEqual(delegate_calls, [run_id])
            self.assertEqual(result, {"status": "delegate-return", "run_id": run_id})

    def test_simultaneous_contender_is_rejected_before_delegate_and_terminal_failure(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            run_id = "contended-run-fixture"
            lock_path = root / run_id / "telemetry" / single_writer.LOCK_FILENAME
            failure_path = root / run_id / "telemetry" / runner.FAILURE_FILENAME
            delegate = mock.Mock(return_value={"status": "must-not-run"})
            with m566_private_roots(root), single_writer._exclusive_run_lock(lock_path), mock.patch.object(
                single_writer, "_validate_permitted_run"
            ), mock.patch.object(
                continuation, "execute_resumable_formal_generation", delegate
            ):
                with self.assertRaisesRegex(PermissionError, "active local writer"):
                    single_writer.execute_single_writer_formal_generation(run_id)
            delegate.assert_not_called()
            self.assertFalse(failure_path.exists())

    def test_two_threads_racing_same_run_produce_one_delegate_and_one_rejection(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            run_id = "thread-race-fixture"
            barrier = threading.Barrier(2)
            delegate_entered = threading.Event()
            contender_done = threading.Event()
            release_delegate = threading.Event()
            outcomes: list[str] = []
            outcome_lock = threading.Lock()

            def validate(value: str) -> None:
                self.assertEqual(value, run_id)
                barrier.wait(timeout=5)

            def delegate(value: str) -> dict:
                self.assertEqual(value, run_id)
                delegate_entered.set()
                self.assertTrue(release_delegate.wait(timeout=5))
                return {"status": "one-owner"}

            def worker() -> None:
                try:
                    result = single_writer.execute_single_writer_formal_generation(run_id)
                    outcome = result["status"]
                except PermissionError as exc:
                    outcome = str(exc)
                    contender_done.set()
                with outcome_lock:
                    outcomes.append(outcome)

            with m566_private_roots(root), mock.patch.object(
                single_writer, "_validate_permitted_run", side_effect=validate
            ), mock.patch.object(
                continuation, "execute_resumable_formal_generation", side_effect=delegate
            ) as delegate_mock:
                threads = [threading.Thread(target=worker) for _ in range(2)]
                for thread in threads:
                    thread.start()
                self.assertTrue(delegate_entered.wait(timeout=5))
                self.assertTrue(contender_done.wait(timeout=5))
                release_delegate.set()
                for thread in threads:
                    thread.join(timeout=5)
                    self.assertFalse(thread.is_alive())
            self.assertEqual(delegate_mock.call_count, 1)
            self.assertEqual(len(outcomes), 2)
            self.assertIn("one-owner", outcomes)
            self.assertEqual(sum("active local writer" in value for value in outcomes), 1)
            self.assertFalse((root / run_id / "telemetry" / runner.FAILURE_FILENAME).exists())

    def test_delegate_exception_releases_lock_without_rewriting_semantics(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            run_id = "delegate-exception-fixture"
            with m566_private_roots(root), mock.patch.object(
                single_writer, "_validate_permitted_run"
            ), mock.patch.object(
                continuation, "execute_resumable_formal_generation", side_effect=RuntimeError("upstream failure")
            ):
                with self.assertRaisesRegex(RuntimeError, "upstream failure"):
                    single_writer.execute_single_writer_formal_generation(run_id)
            lock_path = root / run_id / "telemetry" / single_writer.LOCK_FILENAME
            with single_writer._exclusive_run_lock(lock_path):
                pass

    def test_abrupt_process_exit_releases_os_lock_and_stale_file_is_reusable(self):
        with TemporaryDirectory() as temp:
            lock_path = Path(temp) / "run" / "telemetry" / single_writer.LOCK_FILENAME
            code = (
                "import os,sys\n"
                "from pathlib import Path\n"
                "import m56_6_single_writer_formal_generation as m\n"
                "with m._exclusive_run_lock(Path(sys.argv[1])):\n"
                " print('LOCKED', flush=True)\n"
                " os._exit(19)\n"
            )
            process = subprocess.Popen(
                [sys.executable, "-c", code, str(lock_path)],
                cwd=ROOT,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            self.assertEqual(process.stdout.readline().strip(), "LOCKED")
            self.assertEqual(process.wait(timeout=10), 19)
            self.assertTrue(lock_path.exists())
            with single_writer._exclusive_run_lock(lock_path):
                pass

    def test_different_run_ids_do_not_block_each_other(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            path_a = root / "run-a" / "telemetry" / single_writer.LOCK_FILENAME
            path_b = root / "run-b" / "telemetry" / single_writer.LOCK_FILENAME
            with single_writer._exclusive_run_lock(path_a):
                with single_writer._exclusive_run_lock(path_b):
                    self.assertNotEqual(path_a, path_b)

    def test_symlink_hardlink_owner_and_permission_attacks_fail_closed(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            target = root / "target.lock"
            target.write_text("stale\n", encoding="utf-8")
            target.chmod(0o600)
            symlink = root / "symlink.lock"
            symlink.symlink_to(target)
            with self.assertRaises((OSError, PermissionError)):
                with single_writer._exclusive_run_lock(symlink):
                    pass
            hardlink = root / "hardlink.lock"
            os.link(target, hardlink)
            with self.assertRaisesRegex(PermissionError, "exactly one hard link"):
                with single_writer._exclusive_run_lock(target):
                    pass
            hardlink.unlink()
            target.chmod(0o640)
            with self.assertRaisesRegex(PermissionError, "group or world"):
                with single_writer._exclusive_run_lock(target):
                    pass
            target.chmod(0o600)
            with mock.patch.object(single_writer.os, "getuid", return_value=os.getuid() + 1):
                with self.assertRaisesRegex(PermissionError, "current user"):
                    with single_writer._exclusive_run_lock(target):
                        pass

    def test_stale_lock_file_content_is_not_authority(self):
        with TemporaryDirectory() as temp:
            path = Path(temp) / "run" / "telemetry" / single_writer.LOCK_FILENAME
            path.parent.mkdir(parents=True)
            path.write_text("stale pid metadata must not become authority\n", encoding="utf-8")
            path.chmod(0o600)
            with single_writer._exclusive_run_lock(path) as identity:
                self.assertGreaterEqual(identity["inode"], 1)
            self.assertIn("stale pid metadata", path.read_text(encoding="utf-8"))

    def test_full_forged_m565_path_remains_compatible_and_one_writer(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            run_id = "forged-m566-full-path-no-human"
            materialize_run(root, run_id)
            provider = DeterministicProvider()
            with m566_private_roots(root), mock.patch.object(
                runner, "_ollama_generate", side_effect=provider
            ):
                result = single_writer.execute_single_writer_formal_generation(run_id)
            self.assertEqual(result["status"], "formal_generation_complete_scoring_released")
            self.assertEqual(provider.call_count, 180)
            self.assertEqual(result["model_call_count"], 180)
            self.assertEqual(result["generation_target_outcome_access_count"], 0)
            self.assertTrue((root / run_id / "telemetry" / single_writer.LOCK_FILENAME).exists())
            self.assertFalse((root / run_id / "telemetry" / runner.FAILURE_FILENAME).exists())

    def test_implementation_freeze_matches_frozen_files(self):
        freeze = single_writer.load_json(
            ROOT / "research/m56_6_single_writer_formal_generation_implementation_freeze_2026-09-03.json"
        )
        self.assertEqual(freeze["schema"], "uruha_m56_single_writer_formal_generation_implementation_freeze_v1")
        self.assertEqual(freeze["status"], "frozen_before_any_real_m56_generation_call")
        self.assertEqual(len(freeze["files"]), 4)
        for row in freeze["files"]:
            self.assertEqual(single_writer.sha256_file(ROOT / row["path"]), row["sha256"], row["path"])
        evidence = freeze["pre_freeze_evidence"]
        self.assertEqual(evidence["formal_model_calls"], 0)
        self.assertEqual(evidence["target_outcome_access"], 0)
        self.assertFalse(evidence["formal_commitment_created"])
        self.assertFalse(evidence["formal_scoring_release_created"])
        self.assertFalse(evidence["formal_result_created"])

    def test_rehearsal_and_dashboard_are_graphical_read_only_and_honest(self):
        rehearsal = single_writer.build_synthetic_rehearsal()
        self.assertEqual(rehearsal["contenders"], 2)
        self.assertEqual(rehearsal["lock_holders"], 1)
        self.assertEqual(rehearsal["model_call_count"], 0)
        self.assertEqual(rehearsal["target_outcome_access_count"], 0)
        page = single_writer.render_dashboard()
        self.assertIn("M56.6", page)
        self.assertIn("同一場正式實驗只能有一個執行者", page)
        self.assertIn("run-id 單寫入者鎖", page)
        self.assertIn("0 terminal failure", page)
        self.assertIn("0 FORMAL CALLS", page)
        self.assertIn("0/18", page)
        self.assertNotIn("<form", page)
        self.assertNotIn("overflow-x", page)


if __name__ == "__main__":
    unittest.main()
