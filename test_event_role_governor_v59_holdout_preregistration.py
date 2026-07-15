#!/usr/bin/env python3

import hashlib
import json
import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "configs" / "event_role_governor_v59_holdout_preregistration.json"
DATASET_PATH = ROOT / "datasets" / "event_role_governor_v59_holdout.json"
RESULT_PATH = ROOT / "reports" / "event_role_governor_v59_holdout_raw.json"


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class EventRoleGovernorV59HoldoutPreregistrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        load = lambda path: json.loads(path.read_text(encoding="utf-8"))
        cls.config = load(CONFIG_PATH)
        cls.dataset = load(DATASET_PATH)

    def test_every_frozen_input_matches_its_hash(self):
        frozen = self.config["frozen_inputs"]
        for key, expected in frozen.items():
            if not key.endswith("_sha256"):
                continue
            path_key = key.removesuffix("_sha256")
            self.assertIn(path_key, frozen)
            self.assertEqual(_sha256(ROOT / frozen[path_key]), expected, path_key)

    def test_fresh_dataset_counts_and_provenance_are_frozen(self):
        frozen = self.config["frozen_inputs"]
        self.assertEqual(frozen["case_count"], 72)
        self.assertEqual(frozen["grounded_target_count"], 73)
        self.assertEqual(frozen["external_exact_case_count"], 16)
        self.assertEqual(frozen["controlled_case_count"], 56)
        self.assertEqual(frozen["action_case_count"], 14)
        self.assertEqual(frozen["no_action_case_count"], 58)
        self.assertEqual(frozen["historical_exact_input_overlap_count"], 0)
        self.assertEqual(frozen["historical_near_duplicate_count_at_94_percent"], 0)
        self.assertEqual(frozen["prior_external_source_id_overlap_count"], 0)
        self.assertEqual(self.dataset["case_count"], frozen["case_count"])
        self.assertFalse(
            self.dataset["construction"]["base_model_pretraining_exclusion_guaranteed"]
        )

    def test_only_event_role_state_resolver_changes_between_conditions(self):
        self.assertEqual(
            self.config["conditions"],
            [
                "fresh_v58_state_with_frozen_v57_compiler_control",
                "fresh_v59_state_with_frozen_v57_compiler_candidate",
            ],
        )
        isolation = self.config["causal_isolation"]
        self.assertIn("Replace only V58 target-state resolution", isolation["tested_variable"])
        self.assertIn("V57 compiler implementation", isolation["held_constant"][-1])
        self.assertFalse(isolation["gold_fields_passed_to_model_state_or_compiler"])
        self.assertFalse(isolation["memory_enabled"])
        self.assertFalse(isolation["rightbrain_generation_enabled"])
        self.assertFalse(isolation["vtuber_identity_prompt_enabled"])

    def test_one_identical_local_fallback_is_shared_per_target(self):
        self.assertEqual(self.config["model_call_budget"], 73)
        self.assertEqual(self.config["fixed_model"]["ollama_tag"], "qwen3.5:4b")
        self.assertEqual(self.config["fixed_model"]["temperature"], 0.0)
        self.assertFalse(self.config["fixed_model"]["paid_api"])
        self.assertIn("exactly once per grounded target", self.config["model_usage_policy"])
        self.assertIn("identical parsed fallback", self.config["model_usage_policy"])

    def test_relation_contract_covers_three_blocking_families_and_direct_contrast(self):
        roles = self.config["expected_event_roles_by_family"]
        self.assertEqual(len(roles), 4)
        self.assertEqual(
            {row["relation_type"] for row in roles.values() if row["relation_type"]},
            {
                "embedded_speech_content",
                "third_party_habitual_description",
                "past_experiential_description",
            },
        )
        direct = roles["controlled_direct_focus_request_contrast"]
        self.assertIsNone(direct["relation_type"])
        self.assertTrue(direct["direct_focus_request"])
        self.assertEqual(direct["event_owner_allowed"], ["addressee"])

    def test_gates_prevent_all_abstain_and_require_significant_paired_gain(self):
        state = self.config["candidate_state_gates"]
        compiler = self.config["candidate_compiler_gates"]
        relation = self.config["event_role_generalization_gates"]
        matched = self.config["matched_comparison_gates"]
        self.assertEqual(state["requested_precision"], 1.0)
        self.assertGreaterEqual(state["requested_recall_at_least"], 12 / 14)
        self.assertGreaterEqual(compiler["action_ordered_exact_accuracy_at_least"], 12 / 14)
        self.assertGreaterEqual(compiler["required_call_recall_at_least"], 12 / 14)
        self.assertEqual(compiler["no_action_specificity"], 1.0)
        self.assertEqual(compiler["false_action_case_count"], 0)
        self.assertEqual(relation["contrast_blocking_relation_target_count"], 0)
        self.assertGreaterEqual(matched["case_fix_count_at_least"], 6)
        self.assertEqual(matched["state_regression_count_at_most"], 0)
        self.assertEqual(matched["case_regression_count_at_most"], 0)
        self.assertLessEqual(matched["two_sided_exact_mcnemar_p_at_most"], 0.05)

    def test_model_size_is_a_conditional_residual_experiment_not_this_variable(self):
        route = self.config["failure_routing"]["fallback_model"]
        self.assertIn("qwen3.5:0.8b", route)
        self.assertIn("qwen3.5:9b", route)
        self.assertIn("Do not assume larger or smarter is better", route)
        self.assertNotIn("model size", self.config["causal_isolation"]["tested_variable"])

    def test_runner_analyzer_and_results_were_absent_at_preregistration_commit(self):
        preregistration_commit = subprocess.check_output(
            [
                "git",
                "log",
                "--diff-filter=A",
                "--format=%H",
                "-1",
                "--",
                str(CONFIG_PATH.relative_to(ROOT)),
            ],
            cwd=ROOT,
            text=True,
        ).strip()
        for path in (
            ROOT / "run_event_role_governor_v59_holdout.py",
            ROOT / "analyze_event_role_governor_v59_holdout.py",
            RESULT_PATH,
        ):
            if not path.exists():
                continue
            historical = subprocess.run(
                ["git", "cat-file", "-e", f"{preregistration_commit}:{path.relative_to(ROOT)}"],
                cwd=ROOT,
                check=False,
                capture_output=True,
            )
            self.assertNotEqual(historical.returncode, 0, str(path))

    def test_no_inference_tuning_or_deployment_is_authorized(self):
        for key in (
            "runner_or_analyzer_exists_before_preregistration_merge_authorized",
            "holdout_inference_before_harness_freeze_authorized",
            "post_run_tuning_authorized",
            "fresh_holdout_claim_authorized_before_result",
            "runtime_change_authorized",
            "shadow_integration_authorized",
            "physical_vrm_execution_enabled",
            "complete_rightbrain_claim_authorized",
            "broad_human_likeness_claim_authorized",
        ):
            self.assertFalse(self.config[key], key)


if __name__ == "__main__":
    unittest.main()
