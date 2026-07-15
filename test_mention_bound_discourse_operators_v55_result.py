#!/usr/bin/env python3
"""Lock the rejected V55 development result and its evidence boundary."""

import hashlib
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
CLOSURE_PATH = ROOT / "configs" / "mention_bound_discourse_operators_v55_closure.json"


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class MentionBoundDiscourseOperatorsV55ResultTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.closure = json.loads(CLOSURE_PATH.read_text(encoding="utf-8"))
        cls.analysis = json.loads(
            (ROOT / cls.closure["analysis_report"]).read_text(encoding="utf-8")
        )

    def test_closure_binds_frozen_artifacts(self):
        for path_key in ("preregistration", "raw_report", "analysis_report", "human_readable_report"):
            path = ROOT / self.closure[path_key]
            self.assertEqual(_sha256(path), self.closure[f"{path_key}_sha256"])

    def test_rejected_result_is_not_presented_as_success(self):
        self.assertFalse(self.analysis["development_gate"]["passed"])
        self.assertEqual(
            self.analysis["decision"], "reject_v55_due_to_semantic_regression"
        )
        effect = self.closure["matched_effect"]
        self.assertEqual(effect["semantic_fixes"], 5)
        self.assertEqual(effect["semantic_regressions"], 7)
        self.assertEqual(effect["commitment_correct_delta"], -2)
        self.assertEqual(effect["exact_call_delta"], -6)

    def test_zero_model_replay_and_no_integration(self):
        self.assertEqual(self.closure["model_accounting"]["model_calls"], 0)
        self.assertFalse(self.closure["post_run_tuning_under_v55_authorized"])
        self.assertFalse(self.closure["fresh_holdout_construction_authorized"])
        self.assertFalse(self.closure["runtime_change_authorized"])
        self.assertFalse(self.closure["shadow_integration_authorized"])
        self.assertFalse(self.closure["physical_vrm_execution_enabled"])


if __name__ == "__main__":
    unittest.main()
