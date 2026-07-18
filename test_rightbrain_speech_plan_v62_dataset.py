import hashlib
import json
import unittest
from pathlib import Path

import audit_rightbrain_speech_plan_v62_dataset as audit_module


class RightBrainSpeechPlanV62DatasetTest(unittest.TestCase):
    def test_frozen_dataset_passes_audit(self):
        report = audit_module.audit()
        self.assertTrue(report["passed"], report)
        self.assertEqual(report["counts"]["case_count"], 14)
        self.assertEqual(report["counts"]["scenario_family_count"], 7)
        self.assertEqual(report["counts"]["exact_prior_text_overlap_count"], 0)
        self.assertEqual(report["counts"]["external_near_duplicate_count"], 0)

    def test_dataset_contains_no_model_output_or_benchmark_answer(self):
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

    def test_balanced_families_and_memory_policy_cases_are_present(self):
        dataset = json.loads(
            audit_module.DATASET_PATH.read_text(encoding="utf-8")
        )
        by_family = {}
        for case in dataset["cases"]:
            by_family.setdefault(case["scenario_family"], []).append(case)
        self.assertTrue(all(len(cases) == 2 for cases in by_family.values()))
        memory_cases = by_family["memory_update_or_suppression"]
        self.assertTrue(all(case["memory_fixture"] for case in memory_cases))
        self.assertEqual(
            sum(bool(case["private_memory_terms"]) for case in memory_cases),
            1,
        )

    def test_construction_closure_binds_every_frozen_artifact(self):
        root = Path(__file__).resolve().parent
        closure = json.loads(
            (
                root
                / "configs/rightbrain_speech_plan_payload_v62_dataset_closure.json"
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
