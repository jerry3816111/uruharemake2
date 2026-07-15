#!/usr/bin/env python3

import hashlib
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
RAW_PATH = ROOT / "reports" / "v54_abstention_model_size_raw.json"
ANALYSIS_PATH = ROOT / "reports" / "v54_abstention_model_size_analysis.json"
CLOSURE_PATH = ROOT / "configs" / "v54_abstention_model_size_closure.json"


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class V54AbstentionModelSizeResultTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raw = json.loads(RAW_PATH.read_text(encoding="utf-8"))
        cls.analysis = json.loads(ANALYSIS_PATH.read_text(encoding="utf-8"))
        cls.closure = json.loads(CLOSURE_PATH.read_text(encoding="utf-8"))

    def test_call_accounting_is_complete_and_free(self):
        self.assertIsNotNone(self.raw["completed_at"])
        self.assertEqual(len(self.raw["judgment_rows"]), 40)
        self.assertEqual(self.raw["new_model_calls_made"], 30)
        self.assertFalse(self.raw["paid_api_used"])

    def test_closure_binds_raw_and_analysis(self):
        self.assertEqual(_sha256(RAW_PATH), self.closure["raw_report_sha256"])
        self.assertEqual(
            _sha256(ANALYSIS_PATH), self.closure["analysis_report_sha256"]
        )

    def test_frozen_4b_is_best_on_the_diagnostic_subset(self):
        scores = {
            condition: row["correct_count"]
            for condition, row in self.analysis["conditions"].items()
        }
        self.assertEqual(scores["qwen35_0_8b"], 5)
        self.assertEqual(scores["qwen35_2b"], 6)
        self.assertEqual(scores["qwen35_4b_frozen_control"], 8)
        self.assertEqual(scores["qwen35_9b"], 6)

    def test_smaller_models_fail_for_opposite_risk_reasons(self):
        small = self.analysis["conditions"]["qwen35_0_8b"]
        medium = self.analysis["conditions"]["qwen35_2b"]
        self.assertEqual(small["requested_false_negative"], 5)
        self.assertEqual(medium["requested_false_positive"], 4)

    def test_no_candidate_or_runtime_replacement_is_authorized(self):
        self.assertIsNone(self.analysis["selected_candidate"])
        self.assertEqual(
            self.analysis["decision"],
            "reject_model_size_substitution_for_v54_fallback",
        )
        self.assertFalse(self.analysis["fallback_replacement_authorized"])
        self.assertFalse(self.analysis["runtime_change_authorized"])
        self.assertFalse(self.analysis["shadow_integration_authorized"])
        self.assertFalse(self.analysis["physical_vrm_execution_enabled"])


if __name__ == "__main__":
    unittest.main()
