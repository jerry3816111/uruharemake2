import hashlib
import json
import unittest
from pathlib import Path

import audit_cognitive_plan_model_screen_v65_dataset as audit_module


ROOT = Path(__file__).resolve().parent


class CognitivePlanModelScreenV65DatasetTests(unittest.TestCase):
    def test_audit_passes_with_96_exact_fields(self):
        audit = audit_module.build_audit()
        self.assertTrue(audit["passed"], audit["failures"])
        self.assertEqual(audit["counts"]["case_count"], 12)
        self.assertEqual(audit["counts"]["exact_scored_field_count"], 96)

    def test_expected_is_separate_from_planning_packet(self):
        dataset = json.loads((ROOT / "datasets/cognitive_plan_model_screen_v65.json").read_text(encoding="utf-8"))
        for case in dataset["cases"]:
            self.assertEqual(set(case), {"id", "scenario_family", "planning_packet", "expected"})
            self.assertNotIn("expected", case["planning_packet"])
        self.assertFalse(dataset["official_benchmark_items"])

    def test_closure_binds_inputs_and_forbids_inference(self):
        closure = json.loads((ROOT / "configs/cognitive_plan_model_screen_v65_dataset_closure.json").read_text(encoding="utf-8"))
        for name, relative in (("preregistration", "configs/cognitive_plan_model_screen_v65_preregistration.json"), ("dataset", "datasets/cognitive_plan_model_screen_v65.json")):
            self.assertEqual(closure["frozen_artifacts"][name], hashlib.sha256((ROOT / relative).read_bytes()).hexdigest())
        self.assertFalse(closure["authorizations"]["model_inference"])


if __name__ == "__main__":
    unittest.main()
