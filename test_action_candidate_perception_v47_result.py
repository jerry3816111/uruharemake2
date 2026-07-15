#!/usr/bin/env python3

import hashlib
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
CLOSURE_PATH = ROOT / "configs" / "action_candidate_perception_v47_closure.json"


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class ActionCandidatePerceptionV47ResultTests(unittest.TestCase):
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
            self.assertEqual(_sha256(ROOT / self.closure[path_key]), self.closure[hash_key])

    def test_overlay_removes_only_the_two_false_candidates(self):
        before = self.analysis["baseline"]
        after = self.analysis["candidate"]
        self.assertEqual(before["v45"]["extra_candidate_count"], 2)
        self.assertEqual(after["v45"]["extra_candidate_count"], 0)
        self.assertEqual(after["v45"]["supported_target_recall"], 1.0)
        self.assertEqual(after["v45"]["candidate_precision"], 1.0)
        self.assertEqual(self.analysis["metrics"]["non_point_candidate_set_change_count"], 0)

    def test_pass_authorizes_next_development_but_not_runtime(self):
        self.assertTrue(self.analysis["gate"]["passed"])
        self.assertTrue(self.closure["selective_router_development_authorized"])
        self.assertFalse(self.closure["runtime_change_authorized"])
        self.assertFalse(self.closure["shadow_integration_authorized"])
        self.assertFalse(self.closure["physical_vrm_execution_enabled"])


if __name__ == "__main__":
    unittest.main()
