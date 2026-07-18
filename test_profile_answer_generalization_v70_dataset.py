import hashlib
import json
import unittest
from pathlib import Path

import audit_profile_answer_generalization_v70_dataset as audit_module


ROOT = Path(__file__).resolve().parent


class ProfileAnswerGeneralizationV70DatasetTests(unittest.TestCase):
    def test_audit_passes_with_frozen_balance_and_freshness(self):
        audit = audit_module.build_audit()
        self.assertTrue(audit["passed"], audit["failures"])
        self.assertEqual(audit["counts"]["case_count"], 24)
        self.assertEqual(audit["counts"]["relevant_count"], 16)
        self.assertEqual(audit["counts"]["irrelevant_count"], 8)
        self.assertEqual(audit["counts"]["abstention_count"], 4)
        self.assertEqual(set(audit["family_counts"].values()), {4})

    def test_gold_is_separate_from_queries_and_profile_history(self):
        dataset = json.loads((ROOT / "datasets/profile_answer_generalization_v70.json").read_text(encoding="utf-8"))
        for case in dataset["cases"]:
            self.assertNotIn("expected", case["user_input"])
            for record in case["profile_history"]:
                self.assertEqual(set(record), {"memory_id", "fact_type", "value", "timestamp"})

    def test_primary_comparison_changes_only_validity_resolution(self):
        prereg = json.loads((ROOT / "configs/profile_answer_generalization_v70_preregistration.json").read_text(encoding="utf-8"))
        self.assertIn("V67-resolved active candidates", prereg["only_changed_component_for_primary_comparison"])
        self.assertFalse(prereg["authorizations"]["harness_implementation"])
        self.assertFalse(prereg["authorizations"]["answer_use"])

    def test_closure_binds_inputs_and_forbids_inference(self):
        closure = json.loads((ROOT / "configs/profile_answer_generalization_v70_dataset_closure.json").read_text(encoding="utf-8"))
        paths = {"preregistration": "configs/profile_answer_generalization_v70_preregistration.json", "dataset": "datasets/profile_answer_generalization_v70.json", "audit": "reports/profile_answer_generalization_v70_dataset_audit.json"}
        for name, relative in paths.items():
            self.assertEqual(closure["frozen_artifacts"][name], hashlib.sha256((ROOT / relative).read_bytes()).hexdigest())
        self.assertTrue(closure["authorizations"]["harness_implementation"])
        self.assertFalse(closure["authorizations"]["formal_inference"])
        self.assertFalse(closure["authorizations"]["answer_use"])


if __name__ == "__main__":
    unittest.main()
