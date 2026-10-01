from __future__ import annotations

from contextlib import ExitStack
import inspect
import json
import os
from pathlib import Path
import platform
import stat
from tempfile import TemporaryDirectory
import unittest
from unittest import mock

import m56_3_lease_gated_generation_runner as runner
import m56_5_crash_safe_no_retry_continuation as continuation
import m56_6_single_writer_formal_generation as single_writer
import m56_7_mac_full_sync_generation as durable
from test_m56_5_crash_safe_no_retry_continuation import (
    DeterministicProvider,
    materialize_run,
    private_roots,
)


ROOT = Path(__file__).resolve().parent


class SimulatedPowerLoss(BaseException):
    pass


class m567_private_roots:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.stack = ExitStack()

    def __enter__(self):
        self.stack.enter_context(private_roots(self.root))
        self.stack.enter_context(mock.patch.object(single_writer, "PRIVATE_ROOT", self.root))
        self.stack.enter_context(mock.patch.object(durable, "PRIVATE_ROOT", self.root))
        return self

    def __exit__(self, exc_type, exc, traceback):
        return self.stack.__exit__(exc_type, exc, traceback)


class M567MacFullSyncGenerationTests(unittest.TestCase):
    def test_contract_and_frozen_dependencies_validate(self):
        report = durable.validate_contract()
        self.assertTrue(report["valid"], report["errors"])
        self.assertEqual(report["binding_count"], 6)

    def test_public_execution_accepts_only_run_id(self):
        self.assertEqual(list(inspect.signature(durable.execute_full_sync_formal_generation).parameters), ["run_id"])

    def test_current_live_state_is_denied_and_zero(self):
        audit = durable.build_live_audit()
        self.assertEqual(audit["platform_observed"], "Darwin")
        self.assertEqual(audit["counts"]["v7_slots_by_ledger"], [0, 0])
        self.assertEqual(audit["counts"]["real_temporal_rows"], 0)
        self.assertFalse(audit["formal_generation_authorized"])
        self.assertEqual(audit["formal_model_calls"], 0)
        self.assertEqual(audit["generation_target_outcome_access_count"], 0)
        self.assertFalse(audit["m56_7_durable_release_created"])
        self.assertFalse(audit["formal_result_created"])

    def test_missing_run_fails_without_creating_run_or_mode(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            run_id = "missing-human-authorized-m567"
            with m567_private_roots(root):
                with self.assertRaises(FileNotFoundError):
                    durable.execute_full_sync_formal_generation(run_id)
            self.assertFalse((root / run_id).exists())

    def test_real_mac_file_and_directory_fullsync_writer(self):
        self.assertEqual(platform.system(), "Darwin")
        with TemporaryDirectory() as temp:
            path = Path(temp) / "nested" / "artifact.json"
            events: list[dict] = []
            event_token = durable._DURABILITY_EVENTS.set(events)
            cache_token = durable._DURABLE_DIRECTORY_CACHE.set(set())
            try:
                durable._durable_atomic_write_json(path, {"value": "full-sync"}, exclusive=True)
            finally:
                durable._DURABLE_DIRECTORY_CACHE.reset(cache_token)
                durable._DURABILITY_EVENTS.reset(event_token)
            self.assertEqual(json.loads(path.read_text(encoding="utf-8")), {"value": "full-sync"})
            self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)
            kinds = [row["kind"] for row in events if row["path"] in {str(path), str(path.parent)}]
            payload = kinds.index("file_payload_complete")
            file_fsync = kinds.index("file_fsync")
            file_fullsync = kinds.index("file_f_fullfsync")
            directory_fsync = max(index for index, kind in enumerate(kinds) if kind == "directory_fsync")
            directory_fullsync = max(index for index, kind in enumerate(kinds) if kind == "directory_f_fullfsync")
            committed = kinds.index("artifact_commit_complete")
            self.assertLess(payload, file_fsync)
            self.assertLess(file_fsync, file_fullsync)
            self.assertLess(file_fullsync, directory_fsync)
            self.assertLess(directory_fsync, directory_fullsync)
            self.assertLess(directory_fullsync, committed)

    def test_dispatch_is_context_local_and_legacy_context_keeps_frozen_writer(self):
        durable._install_context_dispatcher()
        with mock.patch.object(durable, "_ORIGINAL_ATOMIC_WRITE_JSON") as original, mock.patch.object(
            durable, "_durable_atomic_write_json"
        ) as full_sync:
            durable._atomic_write_dispatch(Path("legacy.json"), {"a": 1}, exclusive=True)
            original.assert_called_once()
            full_sync.assert_not_called()
            token = durable._DURABLE_WRITER_ACTIVE.set(True)
            try:
                durable._atomic_write_dispatch(Path("durable.json"), {"a": 2}, exclusive=True)
            finally:
                durable._DURABLE_WRITER_ACTIVE.reset(token)
            full_sync.assert_called_once()

    def test_unsupported_fullsync_fails_before_m565_delegate_or_transport(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            run_id = "unsupported-fullsync-no-human"
            materialize_run(root, run_id)
            with m567_private_roots(root), mock.patch.object(
                durable, "_require_bound_platform", side_effect=OSError(
                    "M56.7 requires the frozen Darwin F_FULLFSYNC boundary"
                )
            ), mock.patch.object(
                continuation, "execute_resumable_formal_generation"
            ) as delegate, mock.patch.object(runner, "_ollama_generate") as provider:
                with self.assertRaisesRegex(OSError, "requires the frozen Darwin"):
                    durable.execute_full_sync_formal_generation(run_id)
            delegate.assert_not_called()
            provider.assert_not_called()
            self.assertFalse((root / run_id / "telemetry" / durable.MODE_FILENAME).exists())
            self.assertFalse((root / run_id / "telemetry" / runner.FAILURE_FILENAME).exists())

    def test_preexisting_m565_state_without_m567_mode_is_rejected_before_call(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            run_id = "legacy-state-no-m567-mode"
            rows = materialize_run(root, run_id)
            with m567_private_roots(root), mock.patch.object(runner, "_ollama_generate") as provider:
                paths = continuation._paths(run_id)
                legacy_mode = continuation.build_mode_commitment(run_id, rows["lease"]["lease_hash"])
                runner._atomic_write_json(paths["mode"], legacy_mode, exclusive=True)
                with self.assertRaisesRegex(PermissionError, "preexisting M56.5 generation state"):
                    durable.execute_full_sync_formal_generation(run_id)
            provider.assert_not_called()
            self.assertFalse((root / run_id / "telemetry" / durable.MODE_FILENAME).exists())

    def test_exclusive_collision_preserves_existing_artifact(self):
        with TemporaryDirectory() as temp:
            path = Path(temp) / "artifact.json"
            path.write_text('{"old": true}\n', encoding="utf-8")
            with self.assertRaises(FileExistsError):
                durable._durable_atomic_write_json(path, {"new": True}, exclusive=True)
            self.assertEqual(path.read_text(encoding="utf-8"), '{"old": true}\n')

    def test_fullsync_failure_cleans_partial_before_delegate_use(self):
        with TemporaryDirectory() as temp:
            path = Path(temp) / "artifact.json"
            with mock.patch.object(durable.fcntl, "fcntl", side_effect=OSError("fullsync unavailable")):
                with self.assertRaisesRegex(OSError, "fullsync unavailable"):
                    durable._durable_atomic_write_json(path, {"new": True}, exclusive=True)
            self.assertFalse(path.exists())

    def test_checkpoint_is_fullsynced_before_intent_clear_and_resume_never_recalls_it(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            run_id = "checkpoint-barrier-before-intent-clear-no-human"
            materialize_run(root, run_id)
            provider = DeterministicProvider()

            def lose_power(step_index: int) -> None:
                self.assertEqual(step_index, 1)
                events = durable._DURABILITY_EVENTS.get() or []
                checkpoint_commits = [
                    row for row in events
                    if row["kind"] == "artifact_commit_complete" and row["path"].endswith("0001.json")
                ]
                self.assertEqual(len(checkpoint_commits), 1)
                raise SimulatedPowerLoss()

            with m567_private_roots(root), mock.patch.object(
                runner, "_ollama_generate", side_effect=provider
            ), mock.patch.object(
                continuation, "_after_checkpoint_write_before_intent_clear_hook", side_effect=lose_power
            ):
                with self.assertRaises(SimulatedPowerLoss):
                    durable.execute_full_sync_formal_generation(run_id)
            checkpoint_dir = root / run_id / "telemetry" / continuation.CHECKPOINT_DIRECTORY
            self.assertTrue((checkpoint_dir / "0001.json").exists())
            self.assertTrue((checkpoint_dir / "0001.intent.json").exists())
            self.assertEqual(provider.call_count, 1)
            with m567_private_roots(root), mock.patch.object(runner, "_ollama_generate", side_effect=provider):
                result = durable.execute_full_sync_formal_generation(run_id)
            self.assertEqual(result["status"], "formal_generation_complete_scoring_released")
            self.assertEqual(provider.call_count, 180)
            self.assertFalse((checkpoint_dir / "0001.intent.json").exists())
            self.assertGreaterEqual(result["reused_completed_step_count"], 1)

    def test_full_forged_path_has_unchanged_calls_and_durable_release(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            run_id = "forged-m567-full-path-no-human"
            materialize_run(root, run_id)
            provider = DeterministicProvider()
            with m567_private_roots(root), mock.patch.object(runner, "_ollama_generate", side_effect=provider):
                result = durable.execute_full_sync_formal_generation(run_id)
            self.assertEqual(result["status"], "formal_generation_complete_scoring_released")
            self.assertEqual(provider.call_count, 180)
            self.assertEqual(result["model_call_count"], 180)
            self.assertEqual(result["generation_target_outcome_access_count"], 0)
            self.assertEqual(result["m56_7_durable_artifact_commits_this_process"], 400)
            self.assertEqual(result["m56_7_file_fullsyncs_this_process"], 400)
            self.assertGreaterEqual(result["m56_7_directory_fullsyncs_this_process"], 400)
            checkpoint_dir = root / run_id / "telemetry" / continuation.CHECKPOINT_DIRECTORY
            self.assertEqual(len(list(checkpoint_dir.glob("[0-9][0-9][0-9][0-9].json"))), 211)
            self.assertEqual(len(list(checkpoint_dir.glob("*.intent.json"))), 0)
            release = durable.load_json(root / run_id / "commitments" / durable.RELEASE_FILENAME)
            self.assertEqual(release["submission_hash"], result["submission_hash"])
            self.assertEqual(release["prediction_commitment_hash"], result["commitment_hash"])
            self.assertEqual(release["scoring_release_hash"], result["scoring_release_hash"])
            self.assertFalse((root / run_id / "telemetry" / runner.FAILURE_FILENAME).exists())

    def test_second_completed_invocation_is_validation_only_and_reuses_release(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            run_id = "forged-m567-complete-no-human"
            materialize_run(root, run_id)
            provider = DeterministicProvider()
            with m567_private_roots(root), mock.patch.object(runner, "_ollama_generate", side_effect=provider):
                first = durable.execute_full_sync_formal_generation(run_id)
                second = durable.execute_full_sync_formal_generation(run_id)
            self.assertEqual(provider.call_count, 180)
            self.assertEqual(first["m56_7_durable_release_hash"], second["m56_7_durable_release_hash"])
            self.assertEqual(second["status"], "formal_generation_already_complete_scoring_released")
            self.assertEqual(second["m56_7_durable_artifact_commits_this_process"], 0)

    def test_implementation_freeze_matches_frozen_files(self):
        freeze = durable.load_json(
            ROOT / "research/m56_7_mac_full_sync_generation_implementation_freeze_2026-09-03.json"
        )
        self.assertEqual(freeze["schema"], "uruha_m56_mac_full_sync_generation_implementation_freeze_v1")
        self.assertEqual(freeze["status"], "frozen_before_any_real_m56_generation_call")
        self.assertEqual(len(freeze["files"]), 4)
        for row in freeze["files"]:
            self.assertEqual(durable.sha256_file(ROOT / row["path"]), row["sha256"], row["path"])
        evidence = freeze["pre_freeze_evidence"]
        self.assertEqual(evidence["formal_model_calls"], 0)
        self.assertEqual(evidence["target_outcome_access"], 0)
        self.assertFalse(evidence["actual_power_cut_performed"])
        self.assertFalse(evidence["formal_result_created"])

    def test_rehearsal_and_dashboard_are_read_only_graphical_and_honest(self):
        rehearsal = durable.build_synthetic_rehearsal()
        self.assertFalse(rehearsal["actual_power_cut_performed"])
        self.assertEqual(rehearsal["formal_model_call_count"], 0)
        self.assertEqual(rehearsal["target_outcome_access_count"], 0)
        page = durable.render_dashboard()
        self.assertIn("M56.7", page)
        self.assertIn("先真的落盤再往下走", page)
        self.assertIn("fsync + F_FULLFSYNC", page)
        self.assertIn("checkpoint + intent", page)
        self.assertIn("0 FORMAL CALLS", page)
        self.assertIn("0/18", page)
        self.assertNotIn("<form", page)
        self.assertNotIn("overflow-x", page)


if __name__ == "__main__":
    unittest.main()
