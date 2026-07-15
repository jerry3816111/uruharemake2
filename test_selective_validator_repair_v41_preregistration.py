#!/usr/bin/env python3

import hashlib
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
CONFIG = ROOT / "configs" / "selective_validator_repair_v41_preregistration.json"


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class SelectiveValidatorRepairV41PreregistrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = json.loads(CONFIG.read_text(encoding="utf-8"))

    def test_fixed_sources_are_hash_bound(self):
        scope = self.config["causal_scope"]
        for source_key, hash_key in (
            ("fixed_primary_output_source", "fixed_primary_output_sha256"),
            ("fixed_v39_analysis_source", "fixed_v39_analysis_sha256"),
            ("fixed_development_dataset", "fixed_development_dataset_sha256"),
            ("fixed_v39_compiler_source", "fixed_v39_compiler_sha256"),
        ):
            self.assertEqual(_sha256(ROOT / scope[source_key]), scope[hash_key])

    def test_feedback_excludes_gold_and_benchmark_identity(self):
        feedback = self.config["external_feedback"]
        self.assertIn("validator frame-local warnings", feedback["inputs"])
        self.assertIn("gold frames", feedback["does_not_include"])
        self.assertIn("gold action calls", feedback["does_not_include"])
        self.assertIn("benchmark label", feedback["does_not_include"])

    def test_repair_is_selective_and_preserves_calls(self):
        trigger = self.config["repair_trigger"]
        policy = self.config["repair_acceptance_policy"]
        self.assertEqual(trigger["expected_development_attempt_count"], 4)
        self.assertTrue(trigger["valid_primary_outputs_must_not_be_rewritten"])
        self.assertIn(
            "repair accepted calls exactly equal the original V39 accepted calls",
            policy["all_required"],
        )

    def test_model_ladder_is_smallest_first(self):
        models = list(self.config["repair_model_conditions"].values())
        sizes = [model["blob_bytes"] for model in models]
        self.assertEqual(sizes, sorted(sizes))
        self.assertEqual(models[0]["ollama_tag"], "qwen3.5:0.8b")
        self.assertEqual(models[-1]["ollama_tag"], "qwen3.5:4b")

    def test_no_fresh_or_runtime_authorization_exists(self):
        self.assertTrue(
            self.config["fresh_holdout"][
                "authorized_only_after_development_model_selection"
            ]
        )
        self.assertFalse(self.config["runtime_change_authorized"])
        self.assertFalse(self.config["shadow_integration_authorized"])
        self.assertFalse(self.config["physical_vrm_execution_enabled"])


if __name__ == "__main__":
    unittest.main()
