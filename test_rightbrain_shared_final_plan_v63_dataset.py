import hashlib
import json
import unittest
from pathlib import Path

import audit_rightbrain_shared_final_plan_v63_dataset as audit_module


class RightBrainSharedFinalPlanV63DatasetTest(unittest.TestCase):
    def test_frozen_dataset_passes_freshness_and_shape_audit(self):
        report = audit_module.audit()
        self.assertTrue(report["passed"], report)
        self.assertEqual(report["counts"]["case_count"], 14)
        self.assertEqual(report["counts"]["scenario_family_count"], 7)
        self.assertEqual(report["counts"]["exact_prior_text_overlap_count"], 0)
        self.assertEqual(report["counts"]["external_near_duplicate_count"], 0)

    def test_dataset_has_no_model_output_or_benchmark_answer(self):
        dataset = json.loads(
            audit_module.DATASET_PATH.read_text(encoding="utf-8")
        )
        self.assertFalse(dataset["official_benchmark_items"])
        self.assertFalse(dataset["benchmark_answers_present"])
        for case in dataset["cases"]:
            self.assertNotIn("answer", case)
            self.assertNotIn("candidate_output", case)
            self.assertNotIn("control_output", case)
            self.assertTrue(case["required_meaning_propositions"])

    def test_prereg_uses_final_plan_as_unit_not_fixed_model_call_count(self):
        prereg = json.loads(
            audit_module.PREREG_PATH.read_text(encoding="utf-8")
        )
        self.assertEqual(
            prereg["experimental_unit"],
            "one fresh dialogue case with one frozen shared final cognitive plan",
        )
        self.assertEqual(
            set(prereg["plan_source_policy"]["allowed_sources"]),
            {"model_high_road", "rule_low_road"},
        )
        gates = prereg["automatic_advance_gates"]
        self.assertNotIn("leftbrain_call_count_exact", gates)
        self.assertEqual(gates["rightbrain_model_call_count_exact"], 28)

    def test_construction_closure_binds_frozen_artifacts(self):
        root = Path(__file__).resolve().parent
        closure = json.loads(
            (
                root
                / "configs/rightbrain_shared_final_plan_v63_dataset_closure.json"
            ).read_text(encoding="utf-8")
        )
        self.assertTrue(closure["construction_result"]["gate_passed"])
        self.assertFalse(closure["authorizations"]["plan_capture"])
        self.assertFalse(closure["authorizations"]["candidate_inference"])
        for artifact in closure["artifact_bindings"].values():
            path = root / artifact["path"]
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            self.assertEqual(digest, artifact["sha256"])


if __name__ == "__main__":
    unittest.main()
