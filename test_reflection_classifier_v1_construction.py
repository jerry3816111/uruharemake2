import hashlib
import json
import unittest
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parent
CONFIG = ROOT / "configs" / "reflection_classifier_v1_preregistration.json"
DATASET = ROOT / "datasets" / "reflection_classifier_v1_development.json"
LOCK = ROOT / "configs" / "reflection_classifier_v1_construction_lock.json"


class ReflectionClassifierV1ConstructionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = json.loads(CONFIG.read_text(encoding="utf-8"))
        cls.dataset = json.loads(DATASET.read_text(encoding="utf-8"))

    def test_accounting_and_class_balance(self):
        cases = self.dataset["cases"]
        self.assertEqual(len(cases), 30)
        self.assertEqual(len({case["id"] for case in cases}), 30)
        self.assertEqual(Counter(case["expected_type"] for case in cases), {
            "semantic": 6,
            "procedural": 6,
            "interpretive": 6,
            "none": 12,
        })
        self.assertEqual(sum(case["critical_false_positive"] for case in cases), 12)

    def test_candidate_scope_is_classifier_only(self):
        constraints = self.config["candidate_constraints"]
        self.assertIn("no model call", constraints)
        self.assertFalse(self.config["runtime_memory_write_authorized"])
        self.assertFalse(self.config["exact_source_pointer_authorized"])
        self.assertFalse(self.config["model_inference_authorized"])

    def test_baseline_must_precede_candidate(self):
        self.assertTrue(
            self.config["baseline_must_be_frozen_before_candidate_implementation"]
        )
        self.assertFalse(self.config["post_run_case_editing_authorized"])
        self.assertFalse(self.config["post_run_threshold_change_authorized"])

    def test_construction_lock_binds_inputs_before_baseline(self):
        lock = json.loads(LOCK.read_text(encoding="utf-8"))
        for relative, expected in lock["frozen_artifacts"].items():
            actual = hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()
            self.assertEqual(actual, expected, relative)
        self.assertFalse(lock["baseline_collected"])
        self.assertFalse(lock["candidate_implemented"])


if __name__ == "__main__":
    unittest.main()
