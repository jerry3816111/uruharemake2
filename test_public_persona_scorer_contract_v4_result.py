import hashlib
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
LOCK_PATH = ROOT / "configs/public_persona_scorer_contract_v4_result_lock.json"


class PublicPersonaScorerContractV4ResultTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lock = json.loads(LOCK_PATH.read_text(encoding="utf-8"))
        cls.report = json.loads(
            (ROOT / cls.lock["artifacts"]["audit_json"]["path"]).read_text(encoding="utf-8")
        )

    def test_artifact_hashes_match(self):
        for artifact in self.lock["artifacts"].values():
            path = ROOT / artifact["path"]
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), artifact["sha256"])

    def test_formal_result_is_exactly_30_of_30(self):
        self.assertTrue(self.report["passed"])
        self.assertEqual(self.report["decision"], self.lock["decision"])
        self.assertEqual(self.report["summary"], self.lock["summary"])
        self.assertEqual(self.report["summary"]["correct_count"], 30)
        self.assertEqual(self.report["summary"]["overall_accuracy"], 1.0)

    def test_every_context_and_mutation_category_is_perfect(self):
        self.assertTrue(all(value == 1.0 for value in self.report["per_context_accuracy"].values()))
        self.assertTrue(all(value == 1.0 for value in self.report["per_mutation_accuracy"].values()))
        for mutation in (
            "optional_omission",
            "synonym_substitution",
            "missing_required",
            "forbidden_injection",
            "order_reversal",
            "length_violation",
        ):
            self.assertEqual(self.report["per_mutation_accuracy"][mutation], 1.0)

    def test_no_model_runtime_training_or_holdout_activity_occurred(self):
        summary = self.report["summary"]
        self.assertEqual(summary["model_call_count"], 0)
        self.assertEqual(summary["runtime_change_count"], 0)
        self.assertEqual(summary["holdout_content_review_count"], 0)
        self.assertEqual(summary["training_authorized_count"], 0)

    def test_authorization_is_limited_to_new_experiment_preregistration(self):
        self.assertEqual(self.report["authorizations"], self.lock["authorizations"])
        self.assertTrue(self.report["authorizations"]["new_matched_carrier_preregistration"])
        for name, value in self.report["authorizations"].items():
            if name != "new_matched_carrier_preregistration":
                self.assertFalse(value)


if __name__ == "__main__":
    unittest.main()
