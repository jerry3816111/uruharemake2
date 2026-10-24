from __future__ import annotations

from copy import deepcopy
import inspect
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

import m56_4_separate_formal_scorer as scorer_m56
import m56_7_mac_full_sync_generation as durable_m56
import m56_8_durable_release_gated_scoring as gated_m56
import m56_10_crash_safe_outcome_join as crash_safe_m56
import m56_12_outcome_artifact_public_projection as projection_m56
from test_m56_9_single_writer_formal_scoring import (
    materialize_scoring_run,
    m569_private_roots,
)


ROOT = Path(__file__).resolve().parent


def _write(path: Path, value: dict) -> None:
    durable_m56._durable_atomic_write_json(path, value, exclusive=True)


def _materialize_phase(root: Path, run_id: str, phase: str) -> tuple[Path, dict[str, dict]]:
    run_root = materialize_scoring_run(root, run_id)
    values: dict[str, dict] = {}
    if phase == "pre_outcome_not_started":
        return run_root, values

    authorization = gated_m56.validate_durable_scoring_authorization(run_id)
    assert authorization["valid"] and authorization["scoring_ready"]
    paths = crash_safe_m56._paths(run_id)
    mode = crash_safe_m56.build_mode_commitment(run_id, authorization)
    _write(paths["m56_10_mode"], mode)
    values["mode"] = mode
    if phase == "pre_outcome_mode_committed":
        return run_root, values

    gate = gated_m56.build_durable_scoring_gate(run_id, authorization)
    _write(paths["m56_8_gate"], gate)
    rows = authorization["rows"]
    prescore = scorer_m56.build_prescore_audit(run_id, rows, authorization["prescore"])
    _write(paths["telemetry"] / scorer_m56.PRESCORE_AUDIT_FILENAME, prescore)
    receipt = scorer_m56.build_scoring_access_receipt(run_id, rows, prescore)
    _write(paths["commitments"] / scorer_m56.ACCESS_RECEIPT_FILENAME, receipt)
    intent = crash_safe_m56.build_join_intent(run_id, mode, gate, rows, receipt)
    _write(paths["m56_10_intent"], intent)
    values.update(gate=gate, prescore=prescore, receipt=receipt, intent=intent)
    if phase == "private_join_incomplete_unknown_access":
        return run_root, values
    if phase == "terminal_ambiguous_no_result":
        failure = crash_safe_m56.build_terminal_failure(run_id, mode, intent)
        _write(paths["m56_10_failure"], failure)
        values["failure"] = failure
        return run_root, values

    outcome_rows = scorer_m56.load_outcome_inputs(run_id)
    report = scorer_m56.build_score_report(
        run_id, rows, authorization["prescore"], receipt,
        outcome_rows["outcome_key"], outcome_rows["split_report"],
    )
    checkpoint = crash_safe_m56.build_score_checkpoint(run_id, mode, gate, intent, report)
    _write(paths["m56_10_checkpoint"], checkpoint)
    values.update(report=report, checkpoint=checkpoint)
    if phase == "private_checkpoint_committed":
        return run_root, values

    _write(paths["scoring"] / scorer_m56.SCORE_REPORT_FILENAME, report)
    if phase == "private_report_committed":
        return run_root, values
    result = scorer_m56.build_result_commitment(report)
    _write(paths["commitments"] / scorer_m56.RESULT_COMMITMENT_FILENAME, result)
    values["result"] = result
    return run_root, values


class M5612OutcomeArtifactPublicProjectionTests(unittest.TestCase):
    def test_contract_and_frozen_dependencies_validate(self):
        report = projection_m56.validate_contract()
        self.assertTrue(report["valid"], report["errors"])
        self.assertEqual(report["binding_count"], 6)
        self.assertEqual(
            report["contract_hash"],
            "300b1a58039c9f00bfe49239f544f5a01106a0e015be2e7d6e87b5464be57b90",
        )

    def test_every_public_surface_accepts_only_run_id(self):
        for name in (
            "build_public_scoring_projection", "build_public_log_record",
            "build_public_telemetry_record", "render_public_dashboard",
        ):
            self.assertEqual(list(inspect.signature(getattr(projection_m56, name)).parameters), ["run_id"])

    def test_all_seven_private_states_map_to_frozen_coarse_phases(self):
        phases = projection_m56.load_contract()["projection_schema"]["allowed_phases"]
        with TemporaryDirectory(prefix="uruha-m56-12-phases-") as temp:
            root = Path(temp)
            with m569_private_roots(root):
                for index, phase in enumerate(phases):
                    run_id = f"m56-12-phase-{index}"
                    _materialize_phase(root, run_id, phase)
                    projection = projection_m56.build_public_scoring_projection(run_id)
                    self.assertEqual(projection["phase"], phase)
                    validation = projection_m56.validate_public_projection(projection)
                    self.assertTrue(validation["valid"], (phase, validation["errors"]))

    def test_completed_projection_log_telemetry_and_dashboard_have_no_private_canary(self):
        with TemporaryDirectory(prefix="uruha-m56-12-surfaces-") as temp:
            root = Path(temp)
            run_id = "m56-12-private-canary-run"
            with m569_private_roots(root):
                _, values = _materialize_phase(root, run_id, "formal_result_committed")
                projection = projection_m56.build_public_scoring_projection(run_id)
                log = projection_m56.build_public_log_record(run_id)
                telemetry = projection_m56.build_public_telemetry_record(run_id)
                page = projection_m56.render_public_dashboard(run_id)
            self.assertEqual(projection_m56.canonical(projection), projection_m56.canonical(log))
            self.assertEqual(projection_m56.canonical(projection), projection_m56.canonical(telemetry))
            combined = projection_m56.canonical({"projection": projection, "log": log, "telemetry": telemetry, "page": page})
            for canary in projection_m56._private_canaries(values["checkpoint"], values["report"]):
                self.assertNotIn(canary, combined)
            self.assertEqual(projection_m56._find_forbidden_public_keys(projection), [])
            self.assertNotIn(run_id, combined)
            self.assertNotIn("<form", page)
            self.assertNotIn("overflow-x", page)

    def test_private_report_mutation_fails_closed_before_projection(self):
        with TemporaryDirectory(prefix="uruha-m56-12-mutated-private-") as temp:
            root = Path(temp)
            run_id = "m56-12-mutated-private"
            with m569_private_roots(root):
                run_root, values = _materialize_phase(root, run_id, "formal_result_committed")
                report_path = run_root / "scoring" / scorer_m56.SCORE_REPORT_FILENAME
                mutated = deepcopy(values["report"])
                mutated["decision"] = "tampered_after_result"
                report_path.write_text(json.dumps(mutated, ensure_ascii=False), encoding="utf-8")
                with self.assertRaises(ValueError):
                    projection_m56.build_public_scoring_projection(run_id)

    def test_public_projection_mutation_and_forbidden_injection_fail_closed(self):
        with TemporaryDirectory(prefix="uruha-m56-12-mutated-public-") as temp:
            root = Path(temp)
            run_id = "m56-12-mutated-public"
            with m569_private_roots(root):
                _materialize_phase(root, run_id, "formal_result_committed")
                projection = projection_m56.build_public_scoring_projection(run_id)
            mutated = deepcopy(projection)
            mutated["decision"] = "formal_gate_pass"
            validation = projection_m56.validate_public_projection(mutated)
            self.assertFalse(validation["valid"])
            self.assertIn("projection.fields", validation["errors"])
            with self.assertRaises(PermissionError):
                projection_m56._render_projection(mutated)

    def test_rehearsal_measures_naive_exposure_and_zero_public_exposure(self):
        result = projection_m56.build_synthetic_containment_rehearsal()
        validation = projection_m56.validate_rehearsal(result)
        self.assertTrue(validation["valid"], validation["errors"])
        self.assertGreater(result["before"]["naive_checkpoint_plus_report_utf8_bytes"], 50000)
        self.assertEqual(result["before"]["sample_id_occurrences"], 60)
        self.assertEqual(result["before"]["primary_pair_record_occurrences"], 60)
        self.assertEqual(result["before"]["condition_metric_blocks"], 14)
        self.assertEqual(result["after"]["sample_id_occurrences"], 0)
        self.assertEqual(result["after"]["primary_pair_record_occurrences"], 0)
        self.assertEqual(result["after"]["condition_metric_blocks"], 0)
        self.assertEqual(result["surfaces"]["all_surface_private_canary_hit_count"], 0)

    def test_live_audit_and_demo_are_honest_and_read_only(self):
        audit = projection_m56.build_live_audit()
        self.assertEqual(audit["counts"]["v7_slots_by_ledger"], [0, 0])
        self.assertEqual(audit["counts"]["real_temporal_rows"], 0)
        self.assertFalse(audit["formal_scoring_authorized"])
        result = projection_m56.build_synthetic_containment_rehearsal()
        page = projection_m56.render_demo_dashboard(result)
        self.assertIn("Naive", page)
        self.assertIn("validated state-only projection", page)
        self.assertIn("private canary hits", page)
        self.assertIn("0 REAL OUTCOME READS", page)
        self.assertNotIn("<form", page)
        self.assertNotIn("overflow-x", page)

    def test_implementation_freeze_matches_frozen_files(self):
        freeze_path = ROOT / "research/m56_12_outcome_artifact_public_projection_implementation_freeze_2026-09-03.json"
        if not freeze_path.exists():
            self.skipTest("implementation freeze is created after pre-freeze verification")
        freeze = projection_m56.load_json(freeze_path)
        self.assertEqual(freeze["schema"], "uruha_m56_outcome_artifact_public_projection_implementation_freeze_v1")
        self.assertEqual(freeze["status"], "frozen_before_any_real_m56_target_outcome_access")
        for row in freeze["files"]:
            self.assertEqual(projection_m56.sha256_file(ROOT / row["path"]), row["sha256"], row["path"])


if __name__ == "__main__":
    unittest.main()
