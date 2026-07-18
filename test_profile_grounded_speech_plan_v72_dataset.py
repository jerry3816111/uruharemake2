import hashlib
import json
import unittest
from pathlib import Path

import audit_profile_grounded_speech_plan_v72_dataset as auditor


ROOT = Path(__file__).resolve().parent


class ProfileGroundedSpeechPlanV72DatasetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.prereg = json.loads(auditor.PREREG_PATH.read_text(encoding="utf-8"))
        cls.dataset = json.loads(auditor.DATASET_PATH.read_text(encoding="utf-8"))
        cls.audit = json.loads(auditor.REPORT_PATH.read_text(encoding="utf-8"))
        cls.closure = json.loads(auditor.CLOSURE_PATH.read_text(encoding="utf-8"))

    def test_audit_passes_with_fresh_balanced_holdout(self):
        self.assertTrue(self.audit["passed"])
        self.assertTrue(all(self.audit["checks"].values()))
        counts = self.audit["counts"]
        self.assertEqual(counts["case_count"], 24)
        self.assertEqual(counts["relevant_count"], 16)
        self.assertEqual(counts["irrelevant_count"], 8)
        self.assertEqual(counts["abstention_count"], 4)
        self.assertEqual(counts["exact_prior_overlap_count"], 0)
        self.assertEqual(counts["near_prior_overlap_count"], 0)
        self.assertEqual(counts["prior_profile_value_overlap_count"], 0)

    def test_every_selected_record_has_exact_typed_contract(self):
        relation = auditor.RELATIONS
        for case in self.dataset["cases"]:
            expected = case["expected"]
            selected = expected["selected_memory_ids"]
            if not selected:
                continue
            row = next(item for item in case["profile_history"] if item["memory_id"] in selected)
            contract = expected["evidence_contract"]
            self.assertEqual(contract["answerability"], "supported")
            self.assertEqual(contract["fact_type"], row["fact_type"])
            self.assertEqual(contract["value"], row["value"])
            self.assertEqual(contract["relation"], relation[row["fact_type"]])
            self.assertTrue(expected["required_value_markers"])
            if row["fact_type"] != "name":
                self.assertTrue(expected["required_relation_markers"])

    def test_unknown_and_ordinary_turns_are_distinct(self):
        unknown = [case for case in self.dataset["cases"] if case["expected"]["abstention_required"]]
        ordinary = [
            case
            for case in self.dataset["cases"]
            if not case["expected"]["memory_relevant"] and not case["expected"]["abstention_required"]
        ]
        self.assertEqual(len(unknown), 4)
        self.assertEqual(len(ordinary), 4)
        self.assertTrue(all(case["expected"]["evidence_contract"]["answerability"] == "unsupported" for case in unknown))
        self.assertTrue(all(case["expected"]["evidence_contract"]["answerability"] == "not_requested" for case in ordinary))

    def test_audit_and_closure_bind_frozen_inputs(self):
        self.assertEqual(
            self.audit["bindings"]["preregistration_sha256"],
            hashlib.sha256(auditor.PREREG_PATH.read_bytes()).hexdigest(),
        )
        self.assertEqual(
            self.audit["bindings"]["dataset_sha256"],
            hashlib.sha256(auditor.DATASET_PATH.read_bytes()).hexdigest(),
        )
        self.assertEqual(self.closure["frozen_artifacts"]["audit"], hashlib.sha256(auditor.REPORT_PATH.read_bytes()).hexdigest())

    def test_closure_authorizes_bridge_harness_but_not_run_or_runtime(self):
        self.assertTrue(self.closure["audit_passed"])
        self.assertTrue(self.closure["authorizations"]["bridge_implementation"])
        self.assertTrue(self.closure["authorizations"]["harness_implementation"])
        self.assertFalse(self.closure["authorizations"]["formal_inference"])
        self.assertFalse(self.closure["authorizations"]["temporary_chroma_access"])
        self.assertFalse(self.closure["authorizations"]["runtime_change"])
        self.assertFalse(self.closure["authorizations"]["answer_use"])


if __name__ == "__main__":
    unittest.main()
