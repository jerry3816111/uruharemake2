import json
import unittest
from pathlib import Path

from audit_semantic_memory_recall_support_v1_evidence_contract import file_sha256


ROOT = Path(__file__).resolve().parent
PREREG = ROOT / "configs/source_preserving_memory_projection_v2_1_development_preregistration.json"


class SourcePreservingMemoryProjectionV21PreregistrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.payload = json.loads(PREREG.read_text(encoding="utf-8"))
        base_path = ROOT / cls.payload["base_preregistration"]["path"]
        cls.base = json.loads(base_path.read_text(encoding="utf-8"))

    def test_base_and_failure_evidence_hashes_are_frozen(self):
        base = self.payload["base_preregistration"]
        self.assertEqual(file_sha256(ROOT / base["path"]), base["sha256"])
        failure = self.payload["failed_construction_evidence"]
        self.assertEqual(file_sha256(ROOT / failure["lock_path"]), failure["lock_sha256"])
        self.assertEqual(file_sha256(ROOT / failure["report_path"]), failure["report_sha256"])
        self.assertEqual(failure["eligible_case_count"], 1)
        self.assertEqual(failure["model_calls"], 0)

    def test_only_three_source_limits_change(self):
        revision = self.payload["single_changed_construction_variable"]
        self.assertEqual(revision["name"], "source_character_limits")
        old = revision["control"]
        new = revision["treatment"]
        base_limits = self.base["case_selection"]["source_size_rules"]
        self.assertEqual(
            old,
            {key: base_limits[key] for key in old},
        )
        self.assertEqual(
            new,
            {
                "maximum_target_characters": 14000,
                "maximum_hard_negative_characters": 10000,
                "maximum_combined_visible_characters": 22000,
            },
        )
        self.assertEqual(len(self.payload["effective_overrides"]), 3)

    def test_experiment_and_success_contract_are_inherited(self):
        inherited = self.payload["inherited_without_change"]
        self.assertIn("source_preservation_contract", inherited)
        self.assertIn("span_gate", inherited)
        self.assertIn("success_gates", inherited)
        self.assertIn("decision_and_authorization", inherited)
        self.assertEqual(self.base["span_gate"]["num_ctx"], 8192)
        self.assertEqual(
            self.base["success_gates"][
                "projected_minus_complete_target_only_support_count_at_least"
            ],
            2,
        )

    def test_revision_does_not_authorize_model_or_runtime(self):
        authorization = self.payload["authorization"]
        self.assertTrue(authorization["build_source_preserving_cases"])
        self.assertFalse(authorization["run_model_evaluation"])
        self.assertFalse(authorization["runtime_change"])
        self.assertFalse(authorization["production_enablement"])
        self.assertFalse(authorization["fresh_holdout_claim"])


if __name__ == "__main__":
    unittest.main()
