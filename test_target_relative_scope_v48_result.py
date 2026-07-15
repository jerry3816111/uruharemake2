#!/usr/bin/env python3

import hashlib
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
CLOSURE_PATH = ROOT / "configs" / "target_relative_scope_v48_closure.json"


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class TargetRelativeScopeV48ResultTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.closure = json.loads(CLOSURE_PATH.read_text(encoding="utf-8"))
        cls.analysis = json.loads(
            (ROOT / cls.closure["analysis_report"]).read_text(encoding="utf-8")
        )

    def test_closure_binds_preregistration_code_and_reports(self):
        bindings = (
            ("preregistration", "preregistration_sha256"),
            ("implementation", "implementation_sha256"),
            ("evaluator", "evaluator_sha256"),
            ("analysis_report", "analysis_report_sha256"),
            ("markdown_report", "markdown_report_sha256"),
        )
        for path_key, hash_key in bindings:
            self.assertEqual(
                _sha256(ROOT / self.closure[path_key]), self.closure[hash_key]
            )

    def test_all_scope_classes_and_probes_pass(self):
        scope = self.analysis["scope_audit"]
        probes = self.analysis["metamorphic_probes"]
        self.assertEqual(scope["requested_target_safe_anchor_count"], 35)
        self.assertEqual(scope["requested_target_count"], 35)
        self.assertEqual(scope["negated_target_blocked_all_count"], 8)
        self.assertEqual(scope["negated_target_count"], 8)
        self.assertEqual(scope["cancelled_target_blocked_all_count"], 3)
        self.assertEqual(scope["cancelled_target_count"], 3)
        self.assertEqual(probes["passed_count"], 6)
        self.assertEqual(probes["probe_count"], 6)

    def test_scope_fix_closes_compiler_ceiling_without_regression(self):
        compilation = self.analysis["perfect_semantic_compilation"]
        self.assertEqual(compilation["old_exact_count"], 46)
        self.assertEqual(compilation["new_exact_count"], 48)
        self.assertEqual(compilation["case_count"], 48)
        self.assertEqual(compilation["improved_case_count"], 2)
        self.assertEqual(compilation["regressed_case_count"], 0)
        self.assertEqual(compilation["perfect_semantic_false_action_rate"], 0.0)
        self.assertEqual(compilation["perfect_semantic_negation_violation_count"], 0)

    def test_pass_authorizes_next_development_but_not_runtime(self):
        self.assertTrue(self.analysis["gate"]["passed"])
        self.assertTrue(self.closure["v49_selective_router_development_authorized"])
        self.assertFalse(self.closure["runtime_change_authorized"])
        self.assertFalse(self.closure["shadow_integration_authorized"])
        self.assertFalse(self.closure["physical_vrm_execution_enabled"])


if __name__ == "__main__":
    unittest.main()
