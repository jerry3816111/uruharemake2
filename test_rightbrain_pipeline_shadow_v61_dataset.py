import json
import unittest

import audit_rightbrain_pipeline_shadow_v61_dataset as audit_module


class RightBrainPipelineShadowV61DatasetTest(unittest.TestCase):
    def test_frozen_dataset_passes_audit(self):
        report = audit_module.audit()
        self.assertTrue(report["passed"], report)
        self.assertEqual(report["counts"]["case_count"], 30)
        self.assertEqual(report["counts"]["scenario_family_count"], 10)
        self.assertEqual(report["counts"]["exact_consumed_text_overlap_count"], 0)
        self.assertEqual(report["counts"]["external_near_duplicate_count"], 0)

    def test_dataset_contains_no_model_answers(self):
        dataset = json.loads(audit_module.DATASET_PATH.read_text(encoding="utf-8"))
        self.assertFalse(dataset["benchmark_answers_present"])
        for case in dataset["cases"]:
            self.assertNotIn("answer", case)
            self.assertNotIn("candidate_output", case)
            self.assertNotIn("control_output", case)

    def test_memory_cases_cover_update_and_suppression(self):
        dataset = json.loads(audit_module.DATASET_PATH.read_text(encoding="utf-8"))
        by_family = {}
        for case in dataset["cases"]:
            by_family.setdefault(case["scenario_family"], []).append(case)
        updates = by_family["memory_update_use"]
        suppression = by_family["private_or_irrelevant_memory_suppression"]
        self.assertEqual(len(updates), 3)
        self.assertEqual(len(suppression), 3)
        self.assertTrue(all(case["memory_fixture"] for case in updates + suppression))
        self.assertTrue(any(case["private_memory_terms"] for case in suppression))


if __name__ == "__main__":
    unittest.main()
