#!/usr/bin/env python3

import hashlib
import json
import subprocess
import unittest
from pathlib import Path

from run_relation_safety_state_v58_holdout import CANDIDATE, CONDITIONS, CONTROL


ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "configs" / "relation_safety_state_v58_holdout_preregistration.json"
DATASET_PATH = ROOT / "datasets" / "relation_safety_state_v58_holdout.json"
RESULT_PATH = ROOT / "reports" / "relation_safety_state_v58_holdout_raw.json"


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class RelationSafetyStateV58HoldoutPreregistrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        load = lambda path: json.loads(path.read_text(encoding="utf-8"))
        cls.config = load(CONFIG_PATH)
        cls.dataset = load(DATASET_PATH)

    def test_every_frozen_file_matches_its_hash(self):
        frozen = self.config["frozen_inputs"]
        for key, expected in frozen.items():
            if not key.endswith("_sha256"):
                continue
            path_key = key.removesuffix("_sha256")
            self.assertIn(path_key, frozen)
            self.assertEqual(_sha256(ROOT / frozen[path_key]), expected, path_key)

    def test_dataset_counts_and_independence_are_frozen(self):
        frozen = self.config["frozen_inputs"]
        self.assertEqual(frozen["case_count"], 64)
        self.assertEqual(frozen["grounded_target_count"], 87)
        self.assertEqual(frozen["external_exact_case_count"], 16)
        self.assertEqual(frozen["controlled_compositional_case_count"], 48)
        self.assertEqual(frozen["action_case_count"], 13)
        self.assertEqual(frozen["no_action_case_count"], 51)
        self.assertEqual(frozen["historical_exact_input_overlap_count"], 0)
        self.assertEqual(frozen["historical_near_duplicate_count_at_94_percent"], 0)
        self.assertEqual(frozen["prior_external_source_id_overlap_count"], 0)
        self.assertEqual(self.dataset["case_count"], frozen["case_count"])

    def test_only_state_resolver_changes_between_conditions(self):
        self.assertEqual(tuple(self.config["conditions"]), CONDITIONS)
        self.assertEqual(CONDITIONS, (CONTROL, CANDIDATE))
        isolation = self.config["causal_isolation"]
        self.assertIn("Replace only V56 target-state resolution", isolation["tested_variable"])
        self.assertIn("V57 compiler implementation", isolation["held_constant"][-1])
        self.assertFalse(isolation["gold_fields_passed_to_model_state_or_compiler"])
        self.assertFalse(isolation["memory_enabled"])
        self.assertFalse(isolation["rightbrain_generation_enabled"])
        self.assertFalse(isolation["vtuber_identity_prompt_enabled"])

    def test_one_shared_local_fallback_per_target(self):
        self.assertEqual(self.config["model_call_budget"], 87)
        self.assertFalse(self.config["fixed_model"]["paid_api"])
        self.assertEqual(self.config["fixed_model"]["temperature"], 0.0)
        self.assertIn("exactly once per grounded target", self.config["model_usage_policy"])
        self.assertIn("same parsed fallback", self.config["model_usage_policy"])

    def test_gates_prevent_all_abstain_and_aggregate_only_passes(self):
        compiler = self.config["candidate_compiler_gates"]
        matched = self.config["matched_comparison_gates"]
        self.assertGreaterEqual(compiler["required_call_recall_at_least"], 0.9)
        self.assertGreaterEqual(compiler["action_ordered_exact_accuracy_at_least"], 0.85)
        self.assertEqual(compiler["no_action_specificity"], 1.0)
        self.assertEqual(compiler["false_action_case_count"], 0)
        self.assertGreaterEqual(compiler["relation_family_accuracy_at_least"], 11 / 12)
        self.assertGreaterEqual(matched["ordered_exact_count_delta_at_least"], 12)
        self.assertEqual(matched["state_regression_count_at_most"], 0)
        self.assertEqual(matched["case_regression_count_at_most"], 0)

    def test_model_size_change_is_conditional_not_part_of_this_run(self):
        route = self.config["failure_routing"]["fallback_model"]
        self.assertIn("residual failures are isolated", route)
        self.assertIn("including a smaller model", route)
        self.assertIn("do not assume smarter or larger is better", route)
        self.assertNotIn("model size", self.config["causal_isolation"]["tested_variable"])

    def test_no_result_existed_at_frozen_run_commit_and_no_advancement_was_authorized(self):
        if RESULT_PATH.exists():
            raw = json.loads(RESULT_PATH.read_text(encoding="utf-8"))
            result_at_frozen_commit = subprocess.run(
                [
                    "git",
                    "cat-file",
                    "-e",
                    f"{raw['runner_commit']}:{RESULT_PATH.relative_to(ROOT)}",
                ],
                cwd=ROOT,
                capture_output=True,
                check=False,
            )
            self.assertNotEqual(result_at_frozen_commit.returncode, 0)
        for key in (
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
