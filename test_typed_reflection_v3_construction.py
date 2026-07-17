import hashlib
import json
import unittest
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parent
CONFIG = ROOT / "configs" / "typed_reflection_v3_development_preregistration.json"
DATASET = ROOT / "datasets" / "typed_reflection_v3_development_pilot.json"
LOCK = ROOT / "configs" / "typed_reflection_v3_construction_lock.json"


class TypedReflectionV3ConstructionTest(unittest.TestCase):
    def test_cases_are_balanced_unique_and_complete(self):
        payload = json.loads(DATASET.read_text(encoding="utf-8"))
        cases = payload["cases"]
        self.assertEqual(payload["case_count"], 12)
        self.assertEqual(len(cases), 12)
        self.assertEqual(len({case["id"] for case in cases}), 12)
        self.assertEqual(
            Counter(case["category"] for case in cases),
            Counter(
                {
                    "semantic_user_fact": 3,
                    "procedural_interaction_rule": 3,
                    "interpretive_interaction_rule": 3,
                    "no_reflection_control": 3,
                }
            ),
        )
        required = {
            "expected_reflection_type",
            "expected_collection",
            "rule_required_any",
            "future_prompt",
            "behavior_required_any",
            "behavior_forbidden_any",
            "behavior_first_clause_required_any",
            "behavior_max_question_marks",
            "behavior_max_chars",
        }
        for case in cases:
            self.assertTrue(required.issubset(case), case["id"])

    def test_preregistration_keeps_claims_and_cost_bounded(self):
        payload = json.loads(CONFIG.read_text(encoding="utf-8"))
        self.assertEqual(payload["dataset_status"], "new_controlled_development_pilot_not_independent_holdout")
        self.assertEqual(payload["single_manipulated_variable"], "typed_reflection_memory_write")
        self.assertEqual(payload["model_call_budget_max"], 36)
        self.assertFalse(payload["post_run_case_editing_authorized"])
        self.assertFalse(payload["post_run_threshold_change_authorized"])
        self.assertFalse(payload["large_scale_run_authorized"])
        self.assertFalse(payload["paid_api_authorized"])
        self.assertFalse(payload["broad_human_likeness_claim_authorized"])

    def test_construction_hashes_match_before_implementation(self):
        payload = json.loads(LOCK.read_text(encoding="utf-8"))
        self.assertFalse(payload["runtime_implementation_started"])
        self.assertFalse(payload["model_inference_on_cases_performed"])
        for relative, expected in payload["frozen_artifacts"].items():
            actual = hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()
            self.assertEqual(actual, expected, relative)


if __name__ == "__main__":
    unittest.main()
