#!/usr/bin/env python3
"""Lock V56 development evidence and prevent runtime overclaiming."""

import hashlib
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
CLOSURE_PATH = ROOT / "configs" / "relation_bound_event_graph_v56_closure.json"


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class RelationBoundEventGraphV56ResultTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.closure = json.loads(CLOSURE_PATH.read_text(encoding="utf-8"))
        cls.analysis = json.loads(
            (ROOT / cls.closure["analysis_report"]).read_text(encoding="utf-8")
        )

    def test_closure_binds_all_result_artifacts(self):
        for path_key in (
            "preregistration",
            "raw_report",
            "analysis_report",
            "human_readable_report",
        ):
            path = ROOT / self.closure[path_key]
            self.assertEqual(_sha256(path), self.closure[f"{path_key}_sha256"])

    def test_every_preregistered_gate_passed(self):
        self.assertTrue(self.analysis["development_gate"]["passed"])
        self.assertEqual(self.analysis["development_gate"]["failed_checks"], [])
        condition = self.analysis["conditions"][
            "v56_selective_relation_graph_with_frozen_v51_fallback"
        ]
        self.assertEqual(condition["commitment_correct_count"], 76)
        self.assertEqual(condition["compiled_call_exact_count"], 62)
        self.assertEqual(condition["false_action_count"], 0)

    def test_matched_effect_has_no_regression(self):
        effect = self.closure["matched_effect_vs_v54"]
        self.assertEqual(effect["semantic_fixes"], 6)
        self.assertEqual(effect["semantic_regressions"], 0)
        self.assertEqual(effect["call_fixes"], 2)
        self.assertEqual(effect["call_regressions"], 0)

    def test_success_only_authorizes_next_experiments(self):
        self.assertTrue(self.closure["fresh_holdout_construction_authorized"])
        self.assertTrue(self.closure["compiler_repair_design_authorized"])
        self.assertFalse(self.closure["runtime_change_authorized"])
        self.assertFalse(self.closure["shadow_integration_authorized"])
        self.assertFalse(self.closure["physical_vrm_execution_enabled"])
        self.assertFalse(self.closure["broad_human_likeness_claim_authorized"])


if __name__ == "__main__":
    unittest.main()
