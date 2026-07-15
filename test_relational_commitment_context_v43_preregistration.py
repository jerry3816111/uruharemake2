#!/usr/bin/env python3

import hashlib
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
CONFIG = ROOT / "configs" / "relational_commitment_context_v43_preregistration.json"


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class RelationalCommitmentContextV43PreregistrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = json.loads(CONFIG.read_text(encoding="utf-8"))

    def test_fixed_sources_are_hash_bound(self):
        scope = self.config["causal_scope"]
        for source_key, hash_key in (
            ("fixed_v42_raw_control", "fixed_v42_raw_control_sha256"),
            ("fixed_v42_analysis_control", "fixed_v42_analysis_control_sha256"),
            ("fixed_candidate_audit", "fixed_candidate_audit_sha256"),
            ("fixed_development_dataset", "fixed_development_dataset_sha256"),
            ("fixed_ontology_source", "fixed_ontology_source_sha256"),
        ):
            self.assertEqual(_sha256(ROOT / scope[source_key]), scope[hash_key])

    def test_ablation_changes_one_layer_at_a_time(self):
        conditions = self.config["ablation_conditions"]
        self.assertIn("model outputs only commitment", conditions["commitment_only_candidate"])
        self.assertIn("Same commitment-only contract", conditions["relational_context_candidate"])
        self.assertIn("all grounded targets", conditions["relational_context_candidate"])

    def test_evidence_selector_is_gold_independent(self):
        selector = self.config["deterministic_evidence_selector"]
        self.assertTrue(selector["gold_independent"])
        self.assertIn("latest target anchor", selector["requested"])
        self.assertIn("locally negated clause", selector["negated"])

    def test_relational_rules_are_general_and_example_free(self):
        context = self.config["relational_context"]
        self.assertEqual(len(context["general_rules"]), 5)
        self.assertFalse(context["lexical_examples_in_prompt"])
        self.assertFalse(context["gold_fields_in_prompt"])

    def test_only_full_candidate_can_advance(self):
        self.assertIn(
            "Only relational_context_candidate may advance",
            self.config["development_decision_rule"],
        )
        self.assertTrue(
            self.config["fresh_holdout"][
                "freeze_and_commit_before_any_model_inference"
            ]
        )
        self.assertFalse(self.config["runtime_change_authorized"])
        self.assertFalse(self.config["shadow_integration_authorized"])
        self.assertFalse(self.config["physical_vrm_execution_enabled"])


if __name__ == "__main__":
    unittest.main()
