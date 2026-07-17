import hashlib
import json
import unittest
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parent
CONFIG = ROOT / "configs" / "typed_reflection_v4_development_preregistration.json"
DATASET = ROOT / "datasets" / "typed_reflection_v4_development_pilot.json"
LOCK = ROOT / "configs" / "typed_reflection_v4_construction_lock.json"
V3_DATASET = ROOT / "datasets" / "typed_reflection_v3_development_pilot.json"


class TypedReflectionV4ConstructionTest(unittest.TestCase):
    def test_new_cases_are_balanced_complete_and_disjoint_from_v3(self):
        payload = json.loads(DATASET.read_text(encoding="utf-8"))
        v3 = json.loads(V3_DATASET.read_text(encoding="utf-8"))
        cases = payload["cases"]
        self.assertEqual(payload["case_count"], 12)
        self.assertEqual(len(cases), 12)
        self.assertEqual(len({case["id"] for case in cases}), 12)
        self.assertTrue(
            {case["seed_user"] for case in cases}.isdisjoint(
                {case["seed_user"] for case in v3["cases"]}
            )
        )
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

    def test_preregistration_freezes_safety_and_behavior_gates(self):
        config = json.loads(CONFIG.read_text(encoding="utf-8"))
        self.assertEqual(config["model_generated_fields"], ["content_jp", "trigger_jp"])
        self.assertEqual(config["maximum_language_quality_retries"], 1)
        self.assertEqual(config["model_call_budget_max"], 48)
        self.assertFalse(config["post_run_case_editing_authorized"])
        self.assertFalse(config["post_run_threshold_change_authorized"])
        self.assertFalse(config["large_scale_run_authorized"])
        self.assertFalse(config["broad_human_likeness_claim_authorized"])

    def test_construction_hashes_match_before_implementation(self):
        lock = json.loads(LOCK.read_text(encoding="utf-8"))
        self.assertFalse(lock["v4_runtime_implementation_started"])
        self.assertFalse(lock["model_inference_on_v4_cases_performed"])
        for relative, expected in lock["frozen_artifacts"].items():
            actual = hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()
            self.assertEqual(actual, expected, relative)


if __name__ == "__main__":
    unittest.main()
