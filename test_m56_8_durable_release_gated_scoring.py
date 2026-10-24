from __future__ import annotations

from contextlib import ExitStack
from copy import deepcopy
import inspect
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest import mock

import m56_2_real_data_activation_envelope as activation
import m56_3_lease_gated_generation_runner as runner
import m56_4_separate_formal_scorer as scorer
import m56_5_crash_safe_no_retry_continuation as continuation
import m56_6_single_writer_formal_generation as single_writer
import m56_7_mac_full_sync_generation as durable
import m56_8_durable_release_gated_scoring as gated
from test_m56_3_lease_gated_generation_runner import mechanics
from test_m56_4_separate_formal_scorer import (
    bind_private_hashes,
    complete_rows,
    outcome_artifacts,
    write_private_run,
)
from test_m56_5_crash_safe_no_retry_continuation import DeterministicProvider


ROOT = Path(__file__).resolve().parent


class m568_private_roots:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.stack = ExitStack()

    def __enter__(self):
        self.stack.enter_context(mock.patch.object(runner, "PRIVATE_ROOT", self.root))
        self.stack.enter_context(mock.patch.object(continuation, "PRIVATE_ROOT", self.root))
        self.stack.enter_context(mock.patch.object(single_writer, "PRIVATE_ROOT", self.root))
        self.stack.enter_context(mock.patch.object(durable, "PRIVATE_ROOT", self.root))
        self.stack.enter_context(mock.patch.object(scorer, "PRIVATE_ROOT", self.root))
        return self

    def __exit__(self, exc_type, exc, traceback):
        return self.stack.__exit__(exc_type, exc, traceback)


def write_initial_durable_run(root: Path, run_id: str) -> tuple[dict, dict, dict]:
    rows = mechanics(run_id)
    outcome_key, split_report = outcome_artifacts(rows["packet"])
    bind_private_hashes(rows, outcome_key, split_report)
    run_root = root / run_id
    for name in ("generation", "commitments", "scoring", "telemetry"):
        (run_root / name).mkdir(parents=True, exist_ok=True)
    files = {
        "commitments/activation_request.json": rows["request"],
        f"commitments/{activation.FORMAL_RECEIPT_FILENAME}": rows["receipt"],
        f"commitments/{activation.FORMAL_LEASE_FILENAME}": rows["lease"],
        "generation/prediction_packet.json": rows["packet"],
        "generation/run_manifest.json": rows["manifest"],
        "generation/execution_capsule.json": rows["capsule"],
        "generation/equation_artifacts.json": rows["bundle"],
        "generation/runtime_snapshot.json": rows["snapshot"],
        "scoring/private_outcome_key.json": outcome_key,
        "scoring/split_report.json": split_report,
    }
    for relative, value in files.items():
        runner._atomic_write_json(run_root / relative, value, exclusive=True)
    return rows, outcome_key, split_report


def attach_exact_m567_artifacts(root: Path, run_id: str, rows: dict) -> tuple[dict, dict]:
    run_root = root / run_id
    telemetry = run_root / "telemetry"
    mode = durable.build_mode_commitment(run_id, rows["lease"]["lease_hash"], telemetry)
    release = durable.build_durable_release(
        run_id,
        mode,
        {
            "submission_hash": rows["submission"]["submission_hash"],
            "commitment_hash": rows["commitment"]["commitment_hash"],
            "scoring_release_hash": rows["release"]["release_hash"],
            "model_call_count": rows["commitment"]["model_call_count"],
        },
    )
    durable._durable_atomic_write_json(telemetry / durable.MODE_FILENAME, mode, exclusive=True)
    durable._durable_atomic_write_json(
        run_root / "commitments" / durable.RELEASE_FILENAME, release, exclusive=True
    )
    return mode, release


class M568DurableReleaseGatedScoringTests(unittest.TestCase):
    def test_contract_and_frozen_dependencies_validate(self):
        report = gated.validate_contract()
        self.assertTrue(report["valid"], report["errors"])
        self.assertEqual(report["binding_count"], 6)

    def test_public_execution_accepts_only_run_id(self):
        self.assertEqual(
            list(inspect.signature(gated.execute_durable_release_gated_formal_scoring).parameters),
            ["run_id"],
        )

    def test_current_live_state_is_denied_and_zero(self):
        audit = gated.build_live_audit()
        self.assertEqual(audit["counts"]["v7_slots_by_ledger"], [0, 0])
        self.assertEqual(audit["counts"]["real_temporal_rows"], 0)
        self.assertFalse(audit["m56_7_durable_release_available"])
        self.assertFalse(audit["m56_8_gate_created"])
        self.assertFalse(audit["formal_scoring_authorized"])
        self.assertEqual(audit["formal_model_calls"], 0)
        self.assertEqual(audit["target_outcome_access_count"], 0)
        self.assertFalse(audit["formal_result_created"])

    def test_historical_m564_can_score_without_m567_but_new_entry_rejects_before_outcome(self):
        rows, outcome_key, split_report = complete_rows("legacy-m564-no-m567")
        with TemporaryDirectory() as temp:
            private = Path(temp) / "private"
            run_root = write_private_run(private, "legacy-m564-no-m567", rows, outcome_key, split_report)
            with m568_private_roots(private):
                historical = scorer.execute_formal_scoring("legacy-m564-no-m567")
                self.assertTrue(historical["formal_result_created"])
                self.assertFalse((run_root / "commitments" / gated.GATE_FILENAME).exists())
                with mock.patch.object(
                    scorer, "load_outcome_inputs", side_effect=AssertionError("new entry must not reopen outcome")
                ), self.assertRaisesRegex(PermissionError, "durable-release authorization failed"):
                    gated.execute_durable_release_gated_formal_scoring("legacy-m564-no-m567")

    def test_missing_or_mutated_m567_release_fails_before_outcome_access(self):
        rows, outcome_key, split_report = complete_rows("missing-or-mutated-m567")
        with TemporaryDirectory() as temp:
            private = Path(temp) / "private"
            run_root = write_private_run(
                private, "missing-or-mutated-m567", rows, outcome_key, split_report
            )
            with m568_private_roots(private), mock.patch.object(
                scorer, "load_outcome_inputs", side_effect=AssertionError("outcome must remain unopened")
            ):
                with self.assertRaisesRegex(PermissionError, "durable-release authorization failed"):
                    gated.execute_durable_release_gated_formal_scoring("missing-or-mutated-m567")
                mode, release = attach_exact_m567_artifacts(private, "missing-or-mutated-m567", rows)
                mode_path = run_root / "telemetry" / durable.MODE_FILENAME
                changed_mode = deepcopy(mode)
                changed_mode["filesystem_device"] = -1
                mode_path.write_text(json.dumps(changed_mode), encoding="utf-8")
                with self.assertRaisesRegex(PermissionError, "m56_7_mode.content_or_hash"):
                    gated.execute_durable_release_gated_formal_scoring("missing-or-mutated-m567")
                mode_path.write_text(json.dumps(mode), encoding="utf-8")
                release_path = run_root / "commitments" / durable.RELEASE_FILENAME
                changed = deepcopy(release)
                changed["submission_hash"] = "0" * 64
                release_path.write_text(json.dumps(changed), encoding="utf-8")
                with self.assertRaisesRegex(PermissionError, "m56_7_release.content_or_hash"):
                    gated.execute_durable_release_gated_formal_scoring("missing-or-mutated-m567")
            self.assertFalse((run_root / "commitments" / gated.GATE_FILENAME).exists())

    def test_preexisting_m564_result_cannot_be_retroactively_certified(self):
        rows, outcome_key, split_report = complete_rows("retroactive-m564-result")
        with TemporaryDirectory() as temp:
            private = Path(temp) / "private"
            run_root = write_private_run(private, "retroactive-m564-result", rows, outcome_key, split_report)
            with m568_private_roots(private):
                attach_exact_m567_artifacts(private, "retroactive-m564-result", rows)
                historical = scorer.execute_formal_scoring("retroactive-m564-result")
                self.assertTrue(historical["formal_result_created"])
                self.assertFalse((run_root / "commitments" / gated.GATE_FILENAME).exists())
                with mock.patch.object(
                    scorer, "load_outcome_inputs", side_effect=AssertionError("outcome must not reopen")
                ), self.assertRaisesRegex(PermissionError, "cannot be retroactively certified"):
                    gated.execute_durable_release_gated_formal_scoring("retroactive-m564-result")

    def test_full_m567_generation_then_m568_gate_precedes_unchanged_scoring_and_is_idempotent(self):
        with TemporaryDirectory() as temp:
            private = Path(temp) / "private"
            run_id = "full-m567-to-m568-no-human"
            write_initial_durable_run(private, run_id)
            provider = DeterministicProvider()
            with m568_private_roots(private), mock.patch.object(
                runner, "_ollama_generate", side_effect=provider
            ):
                generation = durable.execute_full_sync_formal_generation(run_id)
                self.assertEqual(provider.call_count, 180)
                self.assertEqual(generation["model_call_count"], 180)
                events: list[dict] = []
                token = durable._DURABILITY_EVENTS.set(events)
                original_load = scorer.load_outcome_inputs

                def guarded_outcome_load(value: str):
                    gate_path = private / value / "commitments" / gated.GATE_FILENAME
                    self.assertTrue(gate_path.exists())
                    self.assertTrue(any(
                        row["kind"] == "artifact_commit_complete"
                        and Path(row["path"]).resolve() == gate_path.resolve()
                        for row in events
                    ), events)
                    return original_load(value)

                try:
                    with mock.patch.object(scorer, "load_outcome_inputs", side_effect=guarded_outcome_load):
                        first = gated.execute_durable_release_gated_formal_scoring(run_id)
                finally:
                    durable._DURABILITY_EVENTS.reset(token)
                second = gated.execute_durable_release_gated_formal_scoring(run_id)
            self.assertEqual(provider.call_count, 180)
            self.assertEqual(first["status"], "formal_scoring_complete_result_committed")
            self.assertTrue(first["m56_8_scoring_authorized"])
            self.assertEqual(first["m56_8_gate_write"], "created_before_private_outcome_access")
            self.assertEqual(second["m56_8_gate_write"], "validated_existing_identical")
            self.assertEqual(first["m56_8_gate_hash"], second["m56_8_gate_hash"])
            self.assertEqual(first["result_commitment_hash"], second["result_commitment_hash"])
            report = scorer.load_json(private / run_id / "scoring" / scorer.SCORE_REPORT_FILENAME)
            self.assertTrue(scorer.validate_score_report(report)["valid"])
            self.assertEqual(len(report["condition_metrics"]), 7)
            self.assertEqual(first["scorer_model_call_count"], 0)

    def test_changed_existing_gate_fails_closed(self):
        rows, outcome_key, split_report = complete_rows("changed-gate")
        with TemporaryDirectory() as temp:
            private = Path(temp) / "private"
            run_root = write_private_run(private, "changed-gate", rows, outcome_key, split_report)
            with m568_private_roots(private):
                attach_exact_m567_artifacts(private, "changed-gate", rows)
                validation = gated.validate_durable_scoring_authorization("changed-gate")
                gate = gated.build_durable_scoring_gate("changed-gate", validation)
                gate["target_outcome_access_before_gate"] = 1
                (run_root / "commitments" / gated.GATE_FILENAME).write_text(
                    json.dumps(gate), encoding="utf-8"
                )
                with mock.patch.object(
                    scorer, "load_outcome_inputs", side_effect=AssertionError("outcome must remain unopened")
                ), self.assertRaisesRegex(ValueError, "immutable M56.8 scoring gate differs"):
                    gated.execute_durable_release_gated_formal_scoring("changed-gate")

    def test_rehearsal_and_dashboard_are_read_only_graphical_and_honest(self):
        rehearsal = gated.build_synthetic_rehearsal()
        self.assertFalse(rehearsal["historical_m56_4_direct_result_gains_m56_8_authority"])
        self.assertFalse(rehearsal["same_host_historical_api_cryptographically_disabled"])
        self.assertEqual(rehearsal["formal_model_call_count"], 0)
        self.assertEqual(rehearsal["target_outcome_access_count"], 0)
        page = gated.render_dashboard()
        self.assertIn("M56.8", page)
        self.assertIn("先證明預測真的耐久落盤", page)
        self.assertIn("不能事後補證明", page)
        self.assertIn("舊 M56.4", page)
        self.assertIn("0 OUTCOME READS", page)
        self.assertIn("0/18", page)
        self.assertNotIn("<form", page)
        self.assertNotIn("overflow-x", page)

    def test_implementation_freeze_matches_frozen_files(self):
        freeze_path = ROOT / "research/m56_8_durable_release_gated_scoring_implementation_freeze_2026-09-03.json"
        if not freeze_path.exists():
            self.skipTest("implementation freeze is created after pre-freeze verification")
        freeze = gated.load_json(freeze_path)
        self.assertEqual(freeze["schema"], "uruha_m56_durable_release_gated_scoring_implementation_freeze_v1")
        for row in freeze["files"]:
            self.assertEqual(gated.sha256_file(ROOT / row["path"]), row["sha256"], row["path"])


if __name__ == "__main__":
    unittest.main()
