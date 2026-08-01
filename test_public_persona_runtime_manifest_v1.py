import ast
import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import public_persona_runtime_manifest_v1 as v1


class PublicPersonaRuntimeManifestV1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.preregistration = v1.load_json(v1.DEFAULT_PREREGISTRATION)
        cls.contract = v1.load_json(v1.DEFAULT_CONDITION_CONTRACT)

    def test_condition_contract_has_exact_declared_conditions(self):
        self.assertEqual([], v1.validate_contract(self.preregistration, self.contract))
        actual = {row["condition_id"] for row in self.contract["conditions"]}
        self.assertEqual(
            set(self.preregistration["condition_contract"]["required_condition_ids"]),
            actual,
        )

    def test_harness_lock_binds_all_frozen_inputs(self):
        harness = v1.load_json(v1.DEFAULT_HARNESS_LOCK)
        self.assertEqual([], v1.validate_harness_lock(harness))

    def test_only_s0_is_currently_executable(self):
        statuses = {
            row["condition_id"]: row["implementation_status"]
            for row in self.contract["conditions"]
        }
        self.assertEqual("executable_now", statuses["s0_current_full_cognitive_persona"])
        self.assertTrue(statuses["c1_matched_direct_control"].startswith("blocked_"))
        self.assertTrue(statuses["c2_matched_persona_disabled"].startswith("blocked_"))
        self.assertEqual("specified_not_implemented", statuses["c3_prompt_only_lower_bound"])

    def test_prompt_only_is_not_mislabeled_as_the_primary_fair_control(self):
        roles = {row["condition_id"]: row["role"] for row in self.contract["conditions"]}
        self.assertEqual("primary_fair_control", roles["c1_matched_direct_control"])
        self.assertIn("not_primary", roles["c3_prompt_only_lower_bound"])

    def test_source_audit_matches_current_production_path(self):
        audit = v1.source_audit()
        failed = [row["check_id"] for row in audit["checks"] if not row["passed"]]
        self.assertEqual([], failed)
        defaults = audit["defaults"]
        self.assertEqual("http://localhost:11434/v1", defaults["ollama_url"])
        self.assertEqual("Qwen/Qwen2.5-7B-Instruct", defaults["rightbrain_base_model"])
        self.assertEqual(5, defaults["working_memory_limit"])
        self.assertEqual(3, defaults["planner_max_ticks"])
        self.assertFalse(defaults["rightbrain_model_blend_enabled"])
        self.assertFalse(defaults["public_persona_conditional_brief_enabled"])
        crosscut = audit["persona_crosscut_evidence"]
        self.assertTrue(crosscut["leftbrain_target_instruction_present"])
        self.assertEqual(
            ["intent_reply_families", "scene_fallbacks"],
            crosscut["rightbrain_fixed_family_attributes"],
        )
        self.assertGreater(crosscut["rightbrain_fixed_reply_literal_count"], 0)

    def test_web_default_constructor_and_sync_turn_are_ast_verified(self):
        web = v1.parse_source(v1.DEFAULT_WEB_SOURCE)
        get_brain = v1._class_function(web, "RuntimeManager", "get_brain")
        self.assertTrue(v1._constructor_calls_without_arguments(get_brain, "UruhaBrainV4_Mac"))
        brain = v1.parse_source(v1.DEFAULT_BRAIN_SOURCE)
        run_turn = v1._class_function(brain, "UruhaBrainV4_Mac", "run_turn_debug")
        calls = v1.function_calls(run_turn)
        self.assertTrue(all(v1._has_call(calls, name) for name in (
            "ingest_event", "cognitive_tick", "emit_response_if_ready"
        )))
        self.assertFalse(v1._has_call(calls, "run_background_cycle"))

    def test_rightbrain_model_and_reflection_defaults_are_not_inferred_from_reports(self):
        audit = v1.source_audit()
        checks = {row["check_id"]: row["passed"] for row in audit["checks"]}
        self.assertTrue(checks["rightbrain_model_default_is_off"])
        self.assertTrue(checks["rightbrain_generation_is_gated"])
        self.assertTrue(checks["typed_reflection_requires_explicit_env_opt_in"])

    def test_persona_disabled_control_cannot_be_enabled_by_one_existing_flag(self):
        row = next(
            row for row in self.contract["conditions"]
            if row["condition_id"] == "c2_matched_persona_disabled"
        )
        self.assertFalse(row["execution_authorized"])
        blockers = " ".join(row["current_blockers"])
        self.assertIn("LeftBrain", blockers)
        self.assertIn("RightBrain", blockers)
        self.assertIn("PUBLIC_PERSONA_CONDITIONAL_BRIEF", blockers)

    def test_each_future_ablation_names_one_component_and_replacement(self):
        rows = self.contract["future_single_component_ablation_candidates"]
        self.assertEqual(7, len(rows))
        self.assertEqual(len(rows), len({row["component_id"] for row in rows}))
        for row in rows:
            self.assertTrue(row["matched_replacement"])
            self.assertTrue(row["primary_outcomes"])

    def test_contract_validator_rejects_fabricated_executable_controls(self):
        changed = copy.deepcopy(self.contract)
        for row in changed["conditions"]:
            if row["condition_id"] == "c1_matched_direct_control":
                row["implementation_status"] = "executable_now"
                row["execution_authorized"] = True
        errors = v1.validate_contract(self.preregistration, changed)
        self.assertIn("c1_must_be_blocked", errors)
        self.assertIn("blocked_condition_execution_authorized", errors)

    def test_report_construction_with_frozen_environment_fixture(self):
        artifacts = {
            "leftbrain_local_model": {
                "name": "qwen2.5:7b",
                "artifact_id": "fixture",
                "reported_size": "4.7 GB",
                "available": True,
                "modelfile_sha256": "a" * 64,
            },
            "rightbrain_candidate_model": {
                "available_on_audited_machine": True,
                "base_model": "Qwen/Qwen2.5-7B-Instruct",
                "adapter_config": v1.binding(v1.DEFAULT_ADAPTER_CONFIG),
                "adapter_weights": {"path": "private", "sha256": "b" * 64},
                "training_run": v1.binding(v1.DEFAULT_ADAPTER_TRAINING_RUN),
                "recorded_adapter_weights_sha256": "b" * 64,
                "weights_match_training_record": True,
                "active_by_default": False,
            },
            "selector_shadow": {
                "model_type": "fixture",
                "schema_version": 2,
                "artifact": v1.binding(v1.DEFAULT_SELECTOR_MODEL),
                "active_by_default": True,
                "changes_output_by_default": False,
            },
        }
        environment = {
            "python": "3.12.10",
            "platform": "fixture",
            "machine": "arm64",
            "hardware_model": "fixture",
            "memory_bytes": 1,
            "logical_cpu_count": 1,
            "mps_available": True,
            "packages": {},
        }
        with mock.patch.object(v1, "local_artifact_snapshot", return_value=artifacts), mock.patch.object(
            v1, "environment_snapshot", return_value=environment
        ):
            report = v1.build_report(self.preregistration, self.contract)
        self.assertEqual("construction_passed", report["status"])
        self.assertEqual(v1.PASS_DECISION, report["decision"])
        self.assertEqual(1, report["counts"]["executable_condition_count"])
        self.assertEqual(2, report["counts"]["blocked_condition_count"])
        self.assertFalse(report["condition_readiness"]["formal_comparative_execution_ready"])
        self.assertEqual(0, report["counts"]["model_call_count"])

    def test_report_validator_rejects_overclaim_or_nonzero_runtime_effects(self):
        with mock.patch.object(v1, "local_artifact_snapshot") as artifacts, mock.patch.object(
            v1, "environment_snapshot"
        ) as environment:
            artifacts.return_value = {
                "leftbrain_local_model": {"available": True},
                "rightbrain_candidate_model": {
                    "available_on_audited_machine": True,
                    "weights_match_training_record": True,
                },
            }
            environment.return_value = {"mps_available": True}
            report = v1.build_report(self.preregistration, self.contract)
        report["condition_readiness"]["formal_comparative_execution_ready"] = True
        report["counts"]["runtime_change_count"] = 1
        errors = v1.validate_report(report, self.preregistration)
        self.assertIn("formal_comparative_execution_must_remain_blocked", errors)
        self.assertIn("runtime_change_count", errors)

    def test_cli_writes_only_requested_outputs(self):
        with tempfile.TemporaryDirectory() as temporary, mock.patch.object(
            v1, "build_report"
        ) as build:
            report = {
                "schema": "uruha_public_persona_runtime_manifest_construction_v1",
                "experiment_id": v1.EXPERIMENT_ID,
                "status": "construction_passed",
                "decision": v1.PASS_DECISION,
                "inputs": {},
                "source_audit": {
                    "defaults": {"working_memory_limit": 5, "planner_max_ticks": 3},
                    "persona_crosscut_evidence": {
                        "rightbrain_fixed_reply_literal_count": 1,
                    },
                },
                "condition_readiness": {
                    "condition_count": 4,
                    "executable_condition_ids": ["s0"],
                },
                "counts": {
                    "check_count": 20,
                    "check_pass_count": 20,
                    "condition_count": 4,
                    "model_call_count": 0,
                    "holdout_content_review_count": 0,
                    "production_memory_write_count": 0,
                    "runtime_change_count": 0,
                    "prompt_change_count": 0,
                    "model_weight_change_count": 0,
                    "persona_score_count": 0,
                },
                "checks": [],
            }
            build.return_value = report
            json_path = Path(temporary) / "report.json"
            md_path = Path(temporary) / "report.md"
            with mock.patch.object(v1, "validate_report", return_value=[]):
                exit_code = v1.main([
                    "build", "--output-json", str(json_path), "--output-md", str(md_path), "--require-pass"
                ])
            self.assertEqual(0, exit_code)
            self.assertTrue(json_path.is_file())
            self.assertTrue(md_path.is_file())

    def test_inactive_adapter_is_not_a_required_s0_dependency(self):
        with mock.patch.object(v1, "DEFAULT_ADAPTER_CONFIG", Path("/missing/config")), mock.patch.object(
            v1, "DEFAULT_ADAPTER_WEIGHTS", Path("/missing/weights")
        ), mock.patch.object(v1, "DEFAULT_ADAPTER_TRAINING_RUN", Path("/missing/training")), mock.patch.object(
            v1, "_run_command", return_value={"available": False, "stdout": ""}
        ):
            snapshot = v1.local_artifact_snapshot()
        candidate = snapshot["rightbrain_candidate_model"]
        self.assertFalse(candidate["available_on_audited_machine"])
        self.assertFalse(candidate["active_by_default"])
        self.assertFalse(candidate["required_for_frozen_s0"])


if __name__ == "__main__":
    unittest.main()
