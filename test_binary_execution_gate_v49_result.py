#!/usr/bin/env python3

import hashlib
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
CLOSURE_PATH = ROOT / "configs" / "binary_execution_gate_v49_closure.json"


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class BinaryExecutionGateV49ResultTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.closure = json.loads(CLOSURE_PATH.read_text(encoding="utf-8"))
        cls.raw = json.loads(
            (ROOT / cls.closure["raw_report"]).read_text(encoding="utf-8")
        )
        cls.analysis = json.loads(
            (ROOT / cls.closure["analysis_report"]).read_text(encoding="utf-8")
        )

    def test_closure_binds_code_and_all_reports(self):
        bindings = (
            ("preregistration", "preregistration_sha256"),
            ("implementation", "implementation_sha256"),
            ("runner", "runner_sha256"),
            ("analyzer", "analyzer_sha256"),
            ("raw_report", "raw_report_sha256"),
            ("analysis_report", "analysis_report_sha256"),
            ("markdown_report", "markdown_report_sha256"),
        )
        for path_key, hash_key in bindings:
            self.assertEqual(
                _sha256(ROOT / self.closure[path_key]), self.closure[hash_key]
            )

    def test_all_preregistered_judgments_completed(self):
        self.assertIsNotNone(self.raw["completed_at"])
        self.assertEqual(len(self.raw["judgment_rows"]), 183)

    def test_binary_contract_did_not_improve_four_b(self):
        binary = self.analysis["binary_conditions"]["qwen35_4b_binary"]
        baseline = self.analysis["matched_six_way_baselines_with_v48_compiler"][
            "qwen35_4b_binary"
        ]
        self.assertEqual(binary["compiled_call_exact_count"], 42)
        self.assertEqual(baseline["compiled_call_exact_count"], 43)
        self.assertEqual(binary["false_action_count"], 1)

    def test_smaller_models_fail_for_distinct_reasons(self):
        small = self.analysis["binary_conditions"]["qwen35_0_8b_binary"]
        medium = self.analysis["binary_conditions"]["qwen35_2b_binary"]
        self.assertEqual(small["execute_true_positive"], 3)
        self.assertEqual(medium["parse_success_count"], 0)
        schema_echoes = [
            row
            for row in self.raw["judgment_rows"]
            if row["condition"] == "qwen35_2b_binary"
            and "additionalProperties" in row["result"]["response_message"]["content"]
        ]
        self.assertEqual(len(schema_echoes), 61)

    def test_negative_result_authorizes_probe_not_runtime(self):
        self.assertIsNone(self.analysis["selection"]["selected_condition"])
        self.assertEqual(
            self.analysis["selection"]["decision"],
            "reject_binary_gate_only_hypothesis",
        )
        self.assertTrue(self.closure["v50_nonsemantic_carrier_probe_authorized"])
        self.assertFalse(self.closure["fresh_holdout_authorized"])
        self.assertFalse(self.closure["runtime_change_authorized"])
        self.assertFalse(self.closure["physical_vrm_execution_enabled"])


if __name__ == "__main__":
    unittest.main()
