#!/usr/bin/env python3

import hashlib
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
CONFIG = ROOT / "configs" / "grounded_commitment_classifier_v42_preregistration.json"


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class GroundedCommitmentClassifierV42PreregistrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = json.loads(CONFIG.read_text(encoding="utf-8"))

    def test_audit_and_fixed_sources_are_hash_bound(self):
        audit = self.config["feasibility_audit"]
        scope = self.config["causal_scope"]
        self.assertEqual(_sha256(ROOT / audit["source"]), audit["sha256"])
        for source_key, hash_key in (
            ("fixed_development_dataset", "fixed_development_dataset_sha256"),
            ("fixed_ontology_source", "fixed_ontology_source_sha256"),
            ("fixed_ontology_config", "fixed_ontology_config_sha256"),
            ("fixed_v39_primary_control_source", "fixed_v39_primary_control_sha256"),
        ):
            self.assertEqual(_sha256(ROOT / scope[source_key]), scope[hash_key])

    def test_classifier_receives_grounding_but_no_gold(self):
        unit = self.config["classification_unit"]
        self.assertIn("one grounded domain-value target", unit["input_fields"])
        self.assertEqual(unit["output_fields"], ["commitment", "evidence_index"])
        self.assertIn("gold commitment", unit["gold_exclusion"])
        self.assertIn("benchmark identity", unit["gold_exclusion"])
        self.assertFalse(unit["examples_in_prompt"])
        self.assertIn("fail closed", unit["case_failure_rule"])

    def test_unsupported_detection_is_explicitly_separate(self):
        audit = self.config["feasibility_audit"]
        self.assertEqual(audit["unsupported_frames_out_of_scope"], 6)
        self.assertIn(
            "open-set unsupported-action discovery",
            self.config["project_scope"]["not_measured"],
        )

    def test_model_ladder_is_smallest_first(self):
        models = list(self.config["model_conditions"].values())
        sizes = [row["blob_bytes"] for row in models]
        self.assertEqual(sizes, sorted(sizes))
        self.assertEqual(models[0]["ollama_tag"], "qwen3.5:0.8b")

    def test_fresh_data_and_runtime_are_not_authorized(self):
        holdout = self.config["fresh_holdout"]
        self.assertTrue(holdout["freeze_and_commit_before_any_model_inference"])
        self.assertTrue(holdout["no_ontology_tuning_after_freeze"])
        self.assertFalse(self.config["runtime_change_authorized"])
        self.assertFalse(self.config["shadow_integration_authorized"])
        self.assertFalse(self.config["physical_vrm_execution_enabled"])


if __name__ == "__main__":
    unittest.main()
