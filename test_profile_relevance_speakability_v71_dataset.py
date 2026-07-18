import json
import unittest
from pathlib import Path

import audit_profile_relevance_speakability_v71_dataset as auditor


ROOT = Path(__file__).resolve().parent


class ProfileRelevanceSpeakabilityV71DatasetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.prereg = json.loads(auditor.PREREG_PATH.read_text(encoding="utf-8"))
        cls.dataset = json.loads(auditor.DATASET_PATH.read_text(encoding="utf-8"))
        cls.audit = json.loads(auditor.REPORT_PATH.read_text(encoding="utf-8"))
        cls.closure = json.loads(auditor.CLOSURE_PATH.read_text(encoding="utf-8"))

    def test_audit_passes_with_fresh_balanced_holdout(self):
        self.assertTrue(self.audit["passed"])
        self.assertTrue(all(self.audit["checks"].values()))
        self.assertEqual(self.audit["counts"]["case_count"], 24)
        self.assertEqual(self.audit["counts"]["relevant_count"], 16)
        self.assertEqual(self.audit["counts"]["irrelevant_count"], 8)
        self.assertEqual(self.audit["counts"]["abstention_count"], 4)
        self.assertEqual(self.audit["counts"]["exact_prior_overlap_count"], 0)
        self.assertEqual(self.audit["counts"]["near_prior_overlap_count"], 0)
        self.assertEqual(self.audit["counts"]["prior_profile_value_overlap_count"], 0)
        self.assertEqual(self.audit["counts"]["development_literal_overlap_count"], 0)

    def test_every_record_preserves_source_utterance(self):
        for case in self.dataset["cases"]:
            for row in case["profile_history"]:
                self.assertTrue(row["source_utterance"].strip())
                self.assertNotEqual(row["source_utterance"], case["user_input"])

    def test_expected_selection_is_separate_and_references_only_history(self):
        for case in self.dataset["cases"]:
            history_ids = {row["memory_id"] for row in case["profile_history"]}
            selected = set(case["expected"]["selected_memory_ids"])
            self.assertLessEqual(len(selected), 1)
            self.assertTrue(selected <= history_ids)
            self.assertEqual(bool(selected), case["expected"]["memory_relevant"])

    def test_primary_comparison_changes_only_key_provenance(self):
        conditions = self.prereg["conditions"]
        self.assertIn("typed_active_bare_key_selection_control", conditions)
        self.assertIn("typed_active_provenance_selection_treatment", conditions)
        self.assertEqual(
            self.prereg["only_changed_component_for_primary_comparison"],
            "whether the selector key includes the stored source utterance; candidate state, encoder, thresholds, projector, unknown contract, full chat pipeline, and scorer remain identical"
        )

    def test_closure_authorizes_harness_but_not_inference_or_runtime(self):
        self.assertTrue(self.closure["audit_passed"])
        self.assertTrue(self.closure["authorizations"]["selector_implementation"])
        self.assertTrue(self.closure["authorizations"]["harness_implementation"])
        self.assertFalse(self.closure["authorizations"]["formal_inference"])
        self.assertFalse(self.closure["authorizations"]["runtime_change"])
        self.assertFalse(self.closure["authorizations"]["answer_use"])


if __name__ == "__main__":
    unittest.main()
