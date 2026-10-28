from __future__ import annotations

from contextlib import ExitStack
import inspect
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import threading
import unittest
from unittest import mock

import m56_4_separate_formal_scorer as scorer
import m56_7_mac_full_sync_generation as durable
import m56_9_single_writer_formal_scoring as single_writer
import m56_10_crash_safe_outcome_join as crash_safe
from test_m56_9_single_writer_formal_scoring import (
    materialize_scoring_run,
    m569_private_roots,
)


ROOT = Path(__file__).resolve().parent


class m5610_private_roots:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.stack = ExitStack()

    def __enter__(self):
        self.stack.enter_context(m569_private_roots(self.root))
        return self

    def __exit__(self, exc_type, exc, traceback):
        return self.stack.__exit__(exc_type, exc, traceback)


def run_with_counted_outcome_load(root: Path, run_id: str):
    original_load = scorer.load_outcome_inputs
    count = {"value": 0}

    def counted_load(value: str):
        count["value"] += 1
        return original_load(value)

    patcher = mock.patch.object(scorer, "load_outcome_inputs", side_effect=counted_load)
    return count, patcher


class M5610CrashSafeOutcomeJoinTests(unittest.TestCase):
    def test_contract_and_frozen_dependencies_validate(self):
        report = crash_safe.validate_contract()
        self.assertTrue(report["valid"], report["errors"])
        self.assertEqual(report["binding_count"], 3)

    def test_public_execution_accepts_only_run_id(self):
        signature = inspect.signature(crash_safe.execute_crash_safe_outcome_join_formal_scoring)
        self.assertEqual(list(signature.parameters), ["run_id"])

    def test_current_live_state_is_denied_and_zero(self):
        audit = crash_safe.build_live_audit()
        self.assertEqual(audit["counts"]["v7_slots_by_ledger"], [0, 0])
        self.assertEqual(audit["counts"]["real_temporal_rows"], 0)
        self.assertFalse(audit["formal_scoring_authorized"])
        self.assertEqual(audit["formal_model_calls"], 0)
        self.assertEqual(audit["target_outcome_access_count"], 0)
        self.assertFalse(audit["formal_result_created"])

    def test_missing_run_fails_before_run_or_m5610_artifact_creation(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            run_id = "missing-human-authorized-m5610"
            with m5610_private_roots(root):
                with self.assertRaises(PermissionError):
                    crash_safe.execute_crash_safe_outcome_join_formal_scoring(run_id)
            self.assertFalse((root / run_id).exists())

    def test_uninterrupted_full_path_loads_outcome_once_and_preserves_m564_result(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            run_id = "m5610-uninterrupted-full-path"
            with m5610_private_roots(root):
                run_root = materialize_scoring_run(root, run_id)
                count, patcher = run_with_counted_outcome_load(root, run_id)
                with patcher:
                    result = crash_safe.execute_crash_safe_outcome_join_formal_scoring(run_id)
            self.assertEqual(count["value"], 1)
            self.assertEqual(result["status"], "formal_scoring_complete_result_committed")
            self.assertEqual(result["m56_10_private_outcome_load_this_invocation"], 1)
            self.assertTrue(result["m56_10_at_most_once_sanctioned_path"])
            report = scorer.load_json(run_root / "scoring" / scorer.SCORE_REPORT_FILENAME)
            commitment = scorer.load_json(
                run_root / "commitments" / scorer.RESULT_COMMITMENT_FILENAME
            )
            self.assertTrue(scorer.validate_score_report(report)["valid"])
            self.assertTrue(scorer.validate_result_commitment(commitment, report)["valid"])
            self.assertEqual(len(report["condition_metrics"]), 7)

    def test_completed_sequential_replay_reuses_checkpoint_without_reload(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            run_id = "m5610-completed-sequential-replay"
            with m5610_private_roots(root):
                materialize_scoring_run(root, run_id)
                count, patcher = run_with_counted_outcome_load(root, run_id)
                with patcher:
                    first = crash_safe.execute_crash_safe_outcome_join_formal_scoring(run_id)
                    second = crash_safe.execute_crash_safe_outcome_join_formal_scoring(run_id)
            self.assertEqual(count["value"], 1)
            self.assertEqual(first["result_commitment_hash"], second["result_commitment_hash"])
            self.assertEqual(second["m56_10_private_outcome_load_this_invocation"], 0)
            self.assertEqual(
                second["m56_10_checkpoint_write"],
                "validated_existing_restart_checkpoint",
            )

    def test_checkpointed_crash_restarts_without_reloading_outcome(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            run_id = "m5610-checkpointed-crash-restart"
            with m5610_private_roots(root):
                run_root = materialize_scoring_run(root, run_id)
                count, patcher = run_with_counted_outcome_load(root, run_id)
                original_finalize = crash_safe._finalize_from_checkpoint
                with patcher, mock.patch.object(
                    crash_safe,
                    "_finalize_from_checkpoint",
                    side_effect=RuntimeError("injected stop after durable checkpoint"),
                ):
                    with self.assertRaisesRegex(RuntimeError, "after durable checkpoint"):
                        crash_safe.execute_crash_safe_outcome_join_formal_scoring(run_id)
                self.assertEqual(count["value"], 1)
                self.assertTrue((run_root / "scoring" / crash_safe.CHECKPOINT_FILENAME).exists())
                self.assertFalse((run_root / "scoring" / scorer.SCORE_REPORT_FILENAME).exists())
                with mock.patch.object(crash_safe, "_finalize_from_checkpoint", original_finalize), patcher:
                    result = crash_safe.execute_crash_safe_outcome_join_formal_scoring(run_id)
            self.assertEqual(count["value"], 1)
            self.assertEqual(result["m56_10_private_outcome_load_this_invocation"], 0)
            self.assertTrue(result["formal_result_created"])

    def test_intent_only_failure_is_terminal_and_never_reloads_outcome(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            run_id = "m5610-intent-only-terminal"
            with m5610_private_roots(root):
                run_root = materialize_scoring_run(root, run_id)
                count, patcher = run_with_counted_outcome_load(root, run_id)
                with patcher, mock.patch.object(
                    scorer,
                    "build_score_report",
                    side_effect=RuntimeError("injected failure after outcome load"),
                ):
                    with self.assertRaisesRegex(RuntimeError, "after outcome load"):
                        crash_safe.execute_crash_safe_outcome_join_formal_scoring(run_id)
                self.assertEqual(count["value"], 1)
                self.assertTrue((run_root / "telemetry" / crash_safe.INTENT_FILENAME).exists())
                self.assertFalse((run_root / "scoring" / crash_safe.CHECKPOINT_FILENAME).exists())
                self.assertTrue((run_root / "telemetry" / crash_safe.FAILURE_FILENAME).exists())
                with patcher:
                    with self.assertRaisesRegex(PermissionError, "terminal"):
                        crash_safe.execute_crash_safe_outcome_join_formal_scoring(run_id)
            self.assertEqual(count["value"], 1)

    def test_existing_m569_result_cannot_be_retroactively_certified(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            run_id = "m5610-no-retroactive-certification"
            with m5610_private_roots(root):
                materialize_scoring_run(root, run_id)
                single_writer.execute_single_writer_durable_release_gated_formal_scoring(run_id)
                original_load = scorer.load_outcome_inputs
                with mock.patch.object(scorer, "load_outcome_inputs", wraps=original_load) as load:
                    with self.assertRaisesRegex(PermissionError, "retroactively"):
                        crash_safe.execute_crash_safe_outcome_join_formal_scoring(run_id)
                    self.assertEqual(load.call_count, 0)

    def test_checkpoint_without_intent_fails_closed_without_reload(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            run_id = "m5610-checkpoint-without-intent"
            with m5610_private_roots(root):
                run_root = materialize_scoring_run(root, run_id)
                crash_safe.execute_crash_safe_outcome_join_formal_scoring(run_id)
                (run_root / "telemetry" / crash_safe.INTENT_FILENAME).unlink()
                original_load = scorer.load_outcome_inputs
                with mock.patch.object(scorer, "load_outcome_inputs", wraps=original_load) as load:
                    with self.assertRaisesRegex(PermissionError, "without its immutable join intent"):
                        crash_safe.execute_crash_safe_outcome_join_formal_scoring(run_id)
                    self.assertEqual(load.call_count, 0)

    def test_canonical_result_without_checkpoint_fails_closed_without_reload(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            run_id = "m5610-canonical-without-checkpoint"
            with m5610_private_roots(root):
                run_root = materialize_scoring_run(root, run_id)
                crash_safe.execute_crash_safe_outcome_join_formal_scoring(run_id)
                (run_root / "scoring" / crash_safe.CHECKPOINT_FILENAME).unlink()
                original_load = scorer.load_outcome_inputs
                with mock.patch.object(scorer, "load_outcome_inputs", wraps=original_load) as load:
                    with self.assertRaisesRegex(PermissionError, "without M56.10 checkpoint"):
                        crash_safe.execute_crash_safe_outcome_join_formal_scoring(run_id)
                    self.assertEqual(load.call_count, 0)

    def test_mutated_checkpoint_fails_closed_without_reload(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            run_id = "m5610-mutated-checkpoint"
            with m5610_private_roots(root):
                run_root = materialize_scoring_run(root, run_id)
                crash_safe.execute_crash_safe_outcome_join_formal_scoring(run_id)
                path = run_root / "scoring" / crash_safe.CHECKPOINT_FILENAME
                checkpoint = json.loads(path.read_text(encoding="utf-8"))
                checkpoint["score_report_hash"] = "0" * 64
                path.write_text(json.dumps(checkpoint), encoding="utf-8")
                original_load = scorer.load_outcome_inputs
                with mock.patch.object(scorer, "load_outcome_inputs", wraps=original_load) as load:
                    with self.assertRaisesRegex(ValueError, "checkpoint invalid"):
                        crash_safe.execute_crash_safe_outcome_join_formal_scoring(run_id)
                    self.assertEqual(load.call_count, 0)

    def test_full_sync_artifact_order_places_intent_before_outcome_and_checkpoint_before_result(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            run_id = "m5610-durable-order"
            with m5610_private_roots(root):
                materialize_scoring_run(root, run_id)
                original_write = durable._durable_atomic_write_json
                original_load = scorer.load_outcome_inputs
                events: list[str] = []

                def recorded_write(path, value, *, exclusive=False):
                    events.append(f"write:{Path(path).name}")
                    return original_write(path, value, exclusive=exclusive)

                def recorded_load(value):
                    events.append("load:private_outcome")
                    return original_load(value)

                with mock.patch.object(
                    durable, "_durable_atomic_write_json", side_effect=recorded_write
                ), mock.patch.object(scorer, "load_outcome_inputs", side_effect=recorded_load):
                    crash_safe.execute_crash_safe_outcome_join_formal_scoring(run_id)
            self.assertLess(events.index(f"write:{crash_safe.MODE_FILENAME}"), events.index(f"write:{gated_filename()}"))
            self.assertLess(events.index(f"write:{crash_safe.INTENT_FILENAME}"), events.index("load:private_outcome"))
            self.assertLess(events.index("load:private_outcome"), events.index(f"write:{crash_safe.CHECKPOINT_FILENAME}"))
            self.assertLess(events.index(f"write:{crash_safe.CHECKPOINT_FILENAME}"), events.index(f"write:{scorer.SCORE_REPORT_FILENAME}"))
            self.assertLess(events.index(f"write:{scorer.SCORE_REPORT_FILENAME}"), events.index(f"write:{scorer.RESULT_COMMITMENT_FILENAME}"))

    def test_same_run_concurrent_contender_is_rejected_before_second_outcome_load(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            run_id = "m5610-concurrent-owner"
            with m5610_private_roots(root):
                materialize_scoring_run(root, run_id)
                original_load = scorer.load_outcome_inputs
                entered = threading.Event()
                release = threading.Event()
                load_count = 0
                owner_result: list[dict] = []

                def held_load(value: str):
                    nonlocal load_count
                    load_count += 1
                    entered.set()
                    if not release.wait(timeout=10):
                        raise TimeoutError("test did not release outcome loader")
                    return original_load(value)

                def owner():
                    owner_result.append(
                        crash_safe.execute_crash_safe_outcome_join_formal_scoring(run_id)
                    )

                with mock.patch.object(scorer, "load_outcome_inputs", side_effect=held_load):
                    thread = threading.Thread(target=owner)
                    thread.start()
                    self.assertTrue(entered.wait(timeout=10))
                    with self.assertRaisesRegex(PermissionError, "active local owner"):
                        crash_safe.execute_crash_safe_outcome_join_formal_scoring(run_id)
                    self.assertEqual(load_count, 1)
                    release.set()
                    thread.join(timeout=15)
                    self.assertFalse(thread.is_alive())
            self.assertEqual(load_count, 1)
            self.assertEqual(len(owner_result), 1)
            self.assertTrue(owner_result[0]["formal_result_created"])

    def test_rehearsal_and_dashboard_are_graphical_read_only_and_honest(self):
        rehearsal = crash_safe.build_synthetic_rehearsal()
        self.assertEqual(rehearsal["pre_change"]["private_outcome_loader_calls"], 2)
        self.assertEqual(rehearsal["post_change"]["uninterrupted_completed_run_total_outcome_loads"], 1)
        self.assertEqual(rehearsal["post_change"]["checkpointed_restart_additional_outcome_loads"], 0)
        self.assertFalse(rehearsal["unconditional_exactly_once_completion"])
        page = crash_safe.render_dashboard()
        self.assertIn("M56.10", page)
        self.assertIn("三種重啟狀態", page)
        self.assertIn("只有 intent", page)
        self.assertIn("at-most-once", page)
        self.assertIn("0 REAL OUTCOME READS", page)
        self.assertIn("0/18", page)
        self.assertNotIn("<form", page)
        self.assertNotIn("overflow-x", page)

    def test_implementation_freeze_matches_frozen_files(self):
        freeze_path = (
            ROOT
            / "research/m56_10_crash_safe_outcome_join_implementation_freeze_2026-09-03.json"
        )
        if not freeze_path.exists():
            self.skipTest("implementation freeze is created after pre-freeze verification")
        freeze = crash_safe.load_json(freeze_path)
        self.assertEqual(
            freeze["schema"],
            "uruha_m56_crash_safe_outcome_join_implementation_freeze_v1",
        )
        self.assertEqual(freeze["status"], "frozen_before_any_real_m56_target_outcome_access")
        for row in freeze["files"]:
            self.assertEqual(crash_safe.sha256_file(ROOT / row["path"]), row["sha256"], row["path"])


def gated_filename() -> str:
    import m56_8_durable_release_gated_scoring as gated

    return gated.GATE_FILENAME


if __name__ == "__main__":
    unittest.main()
