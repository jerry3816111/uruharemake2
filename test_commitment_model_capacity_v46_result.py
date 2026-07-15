#!/usr/bin/env python3

import hashlib
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
CLOSURE_PATH = ROOT / "configs" / "commitment_model_capacity_v46_closure.json"


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class CommitmentModelCapacityV46ResultTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.closure = json.loads(CLOSURE_PATH.read_text(encoding="utf-8"))
        cls.raw = json.loads(
            (ROOT / cls.closure["raw_report"]).read_text(encoding="utf-8")
        )
        cls.analysis = json.loads(
            (ROOT / cls.closure["analysis_report"]).read_text(encoding="utf-8")
        )

    def test_closure_binds_preregistration_and_all_reports(self):
        bindings = (
            ("preregistration", "preregistration_sha256"),
            ("raw_report", "raw_report_sha256"),
            ("analysis_report", "analysis_report_sha256"),
            ("markdown_report", "markdown_report_sha256"),
        )
        for path_key, hash_key in bindings:
            self.assertEqual(_sha256(ROOT / self.closure[path_key]), self.closure[hash_key])

    def test_all_five_models_and_315_judgments_completed(self):
        self.assertEqual(len(self.raw["model_snapshots"]), 5)
        self.assertEqual(len(self.raw["judgment_rows"]), 315)
        self.assertIsNotNone(self.raw["completed_at"])
        self.assertEqual(self.raw["runner_commit"], self.closure["runner_commit"])

    def test_no_model_is_silently_selected_after_failing_safety_gate(self):
        self.assertIsNone(self.analysis["selection"]["selected_condition"])
        self.assertEqual(self.analysis["selection"]["eligible_conditions"], [])
        self.assertEqual(
            self.analysis["selection"]["decision"],
            "reject_model_capacity_only_hypothesis",
        )
        for gate in self.analysis["selection"]["eligibility"].values():
            self.assertFalse(gate["passed"])
        self.assertFalse(self.closure["runtime_change_authorized"])
        self.assertFalse(self.closure["shadow_integration_authorized"])
        self.assertFalse(self.closure["physical_vrm_execution_enabled"])

    def test_four_b_reference_reproduces_exactly_across_seed_change(self):
        reproduction = self.analysis["qwen35_4b_reference_reproduction"]
        self.assertTrue(reproduction["exact_semantic_reproduction"])
        self.assertEqual(reproduction["old_commitment_correct_count"], 51)
        self.assertEqual(reproduction["new_commitment_correct_count"], 51)
        self.assertEqual(reproduction["old_compiled_call_exact_count"], 41)
        self.assertEqual(reproduction["new_compiled_call_exact_count"], 41)


if __name__ == "__main__":
    unittest.main()
