#!/usr/bin/env python3

import hashlib
import json
import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "configs" / "predicate_morphology_v60_preregistration.json"
IMPLEMENTATION_PATH = ROOT / "predicate_morphology_v60.py"


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class PredicateMorphologyV60PreregistrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))

    def test_every_frozen_input_matches_its_hash(self):
        frozen = self.config["frozen_inputs"]
        for key, expected in frozen.items():
            if not key.endswith("_sha256"):
                continue
            path_key = key.removesuffix("_sha256")
            self.assertIn(path_key, frozen)
            self.assertEqual(_sha256(ROOT / frozen[path_key]), expected, path_key)

    def test_exactly_one_answer_free_state_variable_is_added(self):
        variable = self.config["single_variable"]
        self.assertEqual(variable["name"], "focus_predicate_morphology")
        self.assertEqual(
            set(variable["added_fields"]),
            {"predicate_force", "event_aspect", "request_governor", "predicate_span"},
        )
        forbidden = set(variable["forbidden_inputs"])
        self.assertIn("case IDs", forbidden)
        self.assertIn("gold commitments or calls", forbidden)
        self.assertIn("exact holdout sentence lookup", forbidden)
        self.assertIn("model output", forbidden)

    def test_replay_changes_no_model_prompt_or_compiler(self):
        replay = self.config["development_replay"]
        self.assertEqual(replay["model_calls_authorized"], 0)
        self.assertTrue(replay["reuse_frozen_fallbacks"])
        self.assertFalse(replay["compiler_change_authorized"])
        self.assertFalse(replay["model_change_authorized"])
        self.assertFalse(replay["prompt_change_authorized"])
        self.assertFalse(replay["case_or_gold_visibility_to_candidate"])

    def test_expected_effect_fixes_four_false_actions_without_hiding_two_residuals(self):
        expected = self.config["expected_replay_effect"]
        self.assertEqual(expected["correct_commitment_count"], 71)
        self.assertEqual(expected["ordered_exact_count"], 72)
        self.assertEqual(expected["false_action_case_count"], 0)
        self.assertEqual(expected["direct_focus_request_detected_count"], 14)
        self.assertEqual(expected["role_slot_correct_count"], 280)
        self.assertEqual(expected["state_fix_count"], 4)
        self.assertEqual(expected["state_regression_count"], 0)
        self.assertEqual(expected["case_fix_count"], 4)
        self.assertEqual(expected["case_regression_count"], 0)
        residuals = self.config["known_residuals_kept_separate"]
        self.assertIn("compositional_negation", residuals)
        self.assertIn("shared_fallback_label", residuals)

    def test_general_probes_cover_past_direct_negative_embedded_and_declarative_forms(self):
        probes = self.config["required_general_probes"]
        self.assertEqual(len(probes), 6)
        self.assertEqual(
            set(probes),
            {
                "completed_benefactive_without_time_adverb",
                "current_benefactive_request",
                "benefactive_negation",
                "embedded_speech",
                "full_expression_predicate",
                "third_party_declarative",
            },
        )

    def test_model_size_is_explicitly_not_the_current_cause_or_variable(self):
        residual = self.config["known_residuals_kept_separate"]["model_size"]
        self.assertIn("deterministic", residual)
        self.assertIn("No model-size change", residual)
        self.assertNotIn("model", self.config["single_variable"]["name"])

    def test_implementation_was_absent_at_preregistration_commit(self):
        if not IMPLEMENTATION_PATH.exists():
            self.assertFalse(IMPLEMENTATION_PATH.exists())
            return
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
        self.assertTrue(preregistration_commit)
        historical = subprocess.run(
            [
                "git",
                "cat-file",
                "-e",
                f"{preregistration_commit}:{IMPLEMENTATION_PATH.relative_to(ROOT)}",
            ],
            cwd=ROOT,
            check=False,
            capture_output=True,
        )
        self.assertNotEqual(historical.returncode, 0)

    def test_replay_cannot_be_misreported_as_fresh_or_deployable(self):
        self.assertTrue(self.config["independent_confirmation_required_after_replay"])
        for key in (
            "implementation_before_preregistration_merge_authorized",
            "post_replay_threshold_change_authorized",
            "post_replay_case_exclusion_authorized",
            "runtime_change_authorized",
            "shadow_integration_authorized",
            "physical_vrm_execution_enabled",
            "complete_rightbrain_claim_authorized",
            "broad_human_likeness_claim_authorized",
        ):
            self.assertFalse(self.config[key], key)


if __name__ == "__main__":
    unittest.main()
