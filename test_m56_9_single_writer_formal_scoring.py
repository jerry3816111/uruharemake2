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

import m56_4_separate_formal_scorer as scorer
import m56_8_durable_release_gated_scoring as gated
import m56_9_single_writer_formal_scoring as single_writer
from test_m56_4_separate_formal_scorer import complete_rows, write_private_run
from test_m56_8_durable_release_gated_scoring import (
    attach_exact_m567_artifacts,
    m568_private_roots,
)


ROOT = Path(__file__).resolve().parent


class m569_private_roots:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.stack = ExitStack()

    def __enter__(self):
        self.stack.enter_context(m568_private_roots(self.root))
        self.stack.enter_context(mock.patch.object(single_writer, "PRIVATE_ROOT", self.root))
        return self

    def __exit__(self, exc_type, exc, traceback):
        return self.stack.__exit__(exc_type, exc, traceback)


def materialize_scoring_run(root: Path, run_id: str) -> Path:
    rows, outcome_key, split_report = complete_rows(run_id)
    run_root = write_private_run(root, run_id, rows, outcome_key, split_report)
    attach_exact_m567_artifacts(root, run_id, rows)
    return run_root


class M569SingleWriterFormalScoringTests(unittest.TestCase):
    def test_contract_and_frozen_dependencies_validate(self):
        report = single_writer.validate_contract()
        self.assertTrue(report["valid"], report["errors"])
        self.assertEqual(report["binding_count"], 3)

    def test_public_execution_accepts_only_run_id(self):
        signature = inspect.signature(
            single_writer.execute_single_writer_durable_release_gated_formal_scoring
        )
        self.assertEqual(list(signature.parameters), ["run_id"])

    def test_current_live_state_is_denied_and_zero(self):
        audit = single_writer.build_live_audit()
        self.assertEqual(audit["counts"]["v7_slots_by_ledger"], [0, 0])
        self.assertEqual(audit["counts"]["real_temporal_rows"], 0)
        self.assertEqual(audit["active_formal_scoring_lock_holders"], 0)
        self.assertFalse(audit["formal_scoring_authorized"])
        self.assertEqual(audit["formal_model_calls"], 0)
        self.assertEqual(audit["target_outcome_access_count"], 0)
        self.assertFalse(audit["formal_result_created"])

    def test_missing_run_fails_before_lock_file_or_run_directory_is_created(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            run_id = "missing-human-authorized-m569"
            with m569_private_roots(root):
                with self.assertRaises(PermissionError):
                    single_writer.execute_single_writer_durable_release_gated_formal_scoring(run_id)
            self.assertFalse((root / run_id).exists())

    def test_lock_is_held_across_exactly_one_unchanged_m568_delegate(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            run_id = "single-scoring-delegate-fixture"
            lock_path = root / run_id / "telemetry" / single_writer.LOCK_FILENAME
            calls: list[str] = []

            def delegate(value: str) -> dict:
                calls.append(value)
                with self.assertRaisesRegex(PermissionError, "active local owner"):
                    with single_writer._exclusive_scoring_lock(lock_path):
                        self.fail("a second scorer acquired the held lock")
                return {"status": "delegate-return", "run_id": value}

            with m569_private_roots(root), mock.patch.object(
                single_writer, "_validate_permitted_run"
            ), mock.patch.object(
                gated, "execute_durable_release_gated_formal_scoring", side_effect=delegate
            ):
                result = single_writer.execute_single_writer_durable_release_gated_formal_scoring(run_id)
            self.assertEqual(calls, [run_id])
            self.assertEqual(result, {"status": "delegate-return", "run_id": run_id})

    def test_overlapping_full_m568_callers_produce_one_outcome_load_and_one_rejection(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            run_id = "overlapping-full-m568-fixture"
            with m569_private_roots(root):
                run_root = materialize_scoring_run(root, run_id)
                original_load = scorer.load_outcome_inputs
                entered_loader = threading.Event()
                release_loader = threading.Event()
                load_count = 0
                load_count_lock = threading.Lock()
                owner_result: list[dict] = []
                owner_errors: list[BaseException] = []

                def held_load(value: str):
                    nonlocal load_count
                    with load_count_lock:
                        load_count += 1
                    entered_loader.set()
                    if not release_loader.wait(timeout=10):
                        raise TimeoutError("test did not release the private outcome loader")
                    return original_load(value)

                def owner() -> None:
                    try:
                        owner_result.append(
                            single_writer.execute_single_writer_durable_release_gated_formal_scoring(run_id)
                        )
                    except BaseException as exc:  # pragma: no cover - asserted below
                        owner_errors.append(exc)

                with mock.patch.object(scorer, "load_outcome_inputs", side_effect=held_load):
                    thread = threading.Thread(target=owner)
                    thread.start()
                    self.assertTrue(entered_loader.wait(timeout=10))
                    with self.assertRaisesRegex(PermissionError, "active local owner"):
                        single_writer.execute_single_writer_durable_release_gated_formal_scoring(run_id)
                    self.assertEqual(load_count, 1)
                    self.assertFalse(
                        (run_root / "scoring" / scorer.SCORE_REPORT_FILENAME).exists()
                    )
                    self.assertFalse(
                        (run_root / "commitments" / scorer.RESULT_COMMITMENT_FILENAME).exists()
                    )
                    release_loader.set()
                    thread.join(timeout=15)
                    self.assertFalse(thread.is_alive())
                self.assertEqual(owner_errors, [])
                self.assertEqual(len(owner_result), 1)
                self.assertEqual(
                    owner_result[0]["status"], "formal_scoring_complete_result_committed"
                )
                self.assertEqual(load_count, 1)
                self.assertTrue(
                    (run_root / "telemetry" / single_writer.LOCK_FILENAME).exists()
                )

    def test_delegate_exception_releases_lock_without_rewriting_semantics(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            run_id = "scoring-delegate-exception-fixture"
            with m569_private_roots(root), mock.patch.object(
                single_writer, "_validate_permitted_run"
            ), mock.patch.object(
                gated,
                "execute_durable_release_gated_formal_scoring",
                side_effect=RuntimeError("upstream scoring failure"),
            ):
                with self.assertRaisesRegex(RuntimeError, "upstream scoring failure"):
                    single_writer.execute_single_writer_durable_release_gated_formal_scoring(run_id)
            with single_writer._exclusive_scoring_lock(
                root / run_id / "telemetry" / single_writer.LOCK_FILENAME
            ):
                pass

    def test_abrupt_process_exit_releases_os_lock_and_stale_file_is_reusable(self):
        with TemporaryDirectory() as temp:
            lock_path = Path(temp) / "run" / "telemetry" / single_writer.LOCK_FILENAME
            code = (
                "import os,sys\n"
                "from pathlib import Path\n"
                "import m56_9_single_writer_formal_scoring as m\n"
                "with m._exclusive_scoring_lock(Path(sys.argv[1])):\n"
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
            with single_writer._exclusive_scoring_lock(lock_path):
                pass

    def test_different_run_ids_do_not_block_each_other(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            path_a = root / "run-a" / "telemetry" / single_writer.LOCK_FILENAME
            path_b = root / "run-b" / "telemetry" / single_writer.LOCK_FILENAME
            with single_writer._exclusive_scoring_lock(path_a):
                with single_writer._exclusive_scoring_lock(path_b):
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
                with single_writer._exclusive_scoring_lock(symlink):
                    pass
            hardlink = root / "hardlink.lock"
            os.link(target, hardlink)
            with self.assertRaisesRegex(PermissionError, "exactly one hard link"):
                with single_writer._exclusive_scoring_lock(target):
                    pass
            hardlink.unlink()
            target.chmod(0o640)
            with self.assertRaisesRegex(PermissionError, "group or world"):
                with single_writer._exclusive_scoring_lock(target):
                    pass
            target.chmod(0o600)
            with mock.patch.object(single_writer.os, "getuid", return_value=os.getuid() + 1):
                with self.assertRaisesRegex(PermissionError, "current user"):
                    with single_writer._exclusive_scoring_lock(target):
                        pass

    def test_stale_lock_file_content_is_not_authority(self):
        with TemporaryDirectory() as temp:
            path = Path(temp) / "run" / "telemetry" / single_writer.LOCK_FILENAME
            path.parent.mkdir(parents=True)
            path.write_text("stale pid metadata must not become authority\n", encoding="utf-8")
            path.chmod(0o600)
            with single_writer._exclusive_scoring_lock(path) as identity:
                self.assertGreaterEqual(identity["inode"], 1)
            self.assertIn("stale pid metadata", path.read_text(encoding="utf-8"))

    def test_full_forged_m568_path_remains_compatible_and_one_writer(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            run_id = "forged-m569-full-path-no-human"
            with m569_private_roots(root):
                run_root = materialize_scoring_run(root, run_id)
                result = single_writer.execute_single_writer_durable_release_gated_formal_scoring(
                    run_id
                )
            self.assertEqual(result["status"], "formal_scoring_complete_result_committed")
            self.assertTrue(result["m56_8_scoring_authorized"])
            self.assertEqual(result["scorer_model_call_count"], 0)
            report = scorer.load_json(run_root / "scoring" / scorer.SCORE_REPORT_FILENAME)
            self.assertTrue(scorer.validate_score_report(report)["valid"])
            self.assertEqual(len(report["condition_metrics"]), 7)

    def test_sequential_replay_limitation_is_explicit_and_not_misclaimed(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            run_id = "sequential-replay-remains-fixture"
            with m569_private_roots(root):
                materialize_scoring_run(root, run_id)
                original_load = scorer.load_outcome_inputs
                load_count = 0

                def counted_load(value: str):
                    nonlocal load_count
                    load_count += 1
                    return original_load(value)

                with mock.patch.object(scorer, "load_outcome_inputs", side_effect=counted_load):
                    first = single_writer.execute_single_writer_durable_release_gated_formal_scoring(
                        run_id
                    )
                    second = single_writer.execute_single_writer_durable_release_gated_formal_scoring(
                        run_id
                    )
            self.assertTrue(first["formal_result_created"])
            self.assertTrue(second["formal_result_created"])
            self.assertEqual(load_count, 2)
            boundary = single_writer.load_contract()["sequential_replay_boundary"]
            self.assertTrue(boundary["sequential_invocation_after_lock_release_may_reopen_outcome"])
            self.assertFalse(boundary["exactly_once_outcome_access_across_process_lifetimes"])

    def test_rehearsal_and_dashboard_are_graphical_read_only_and_honest(self):
        rehearsal = single_writer.build_synthetic_rehearsal()
        self.assertEqual(rehearsal["pre_change"]["private_outcome_loader_calls"], 2)
        self.assertEqual(rehearsal["post_change"]["private_outcome_loader_calls"], 1)
        self.assertEqual(rehearsal["post_change"]["rejected_before_m56_8"], 1)
        self.assertTrue(rehearsal["sequential_replay_can_reopen_outcome"])
        page = single_writer.render_dashboard()
        self.assertIn("M56.9", page)
        self.assertIn("2 次", page)
        self.assertIn("1 次", page)
        self.assertIn("同一時間只准一個評分者", page)
        self.assertIn("還不是「永遠只開一次」", page)
        self.assertIn("0 REAL OUTCOME READS", page)
        self.assertIn("0/18", page)
        self.assertNotIn("<form", page)
        self.assertNotIn("overflow-x", page)

    def test_implementation_freeze_matches_frozen_files(self):
        freeze_path = (
            ROOT
            / "research/m56_9_single_writer_formal_scoring_implementation_freeze_2026-09-03.json"
        )
        if not freeze_path.exists():
            self.skipTest("implementation freeze is created after pre-freeze verification")
        freeze = single_writer.load_json(freeze_path)
        self.assertEqual(
            freeze["schema"], "uruha_m56_single_writer_formal_scoring_implementation_freeze_v1"
        )
        self.assertEqual(freeze["status"], "frozen_before_any_real_m56_target_outcome_access")
        for row in freeze["files"]:
            self.assertEqual(
                single_writer.sha256_file(ROOT / row["path"]), row["sha256"], row["path"]
            )


if __name__ == "__main__":
    unittest.main()
