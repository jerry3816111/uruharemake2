#!/usr/bin/env python3

import hashlib
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
CLOSURE_PATH = ROOT / "configs" / "qwen2b_binary_carrier_v50_closure.json"


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class Qwen2BBinaryCarrierV50ResultTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.closure = json.loads(CLOSURE_PATH.read_text(encoding="utf-8"))
        cls.raw = json.loads(
            (ROOT / cls.closure["raw_report"]).read_text(encoding="utf-8")
        )
        cls.analysis = json.loads(
            (ROOT / cls.closure["analysis_report"]).read_text(encoding="utf-8")
        )

    def test_closure_binds_every_frozen_artifact(self):
        bindings = (
            ("preregistration", "preregistration_sha256"),
            ("dataset", "dataset_sha256"),
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

    def test_all_four_carriers_completed_without_selection(self):
        self.assertIsNotNone(self.raw["completed_at"])
        self.assertEqual(len(self.raw["probe_rows"]), 48)
        self.assertEqual(
            set(self.analysis["carriers"]),
            {
                "boolean_two_field_control",
                "enum_two_field_candidate",
                "enum_single_field_candidate",
                "scalar_enum_candidate",
            },
        )
        self.assertTrue(
            all(
                row["parse_success_rate"] == 0.0
                for row in self.analysis["carriers"].values()
            )
        )
        self.assertIsNone(self.analysis["selected_carrier"])

    def test_negative_result_retires_two_b_role_without_runtime(self):
        self.assertEqual(
            self.analysis["decision"],
            "retire_qwen35_2b_from_binary_gate_role",
        )
        self.assertTrue(self.closure["qwen35_2b_binary_gate_role_retired"])
        self.assertFalse(self.closure["v51_fresh_holdout_construction_authorized"])
        self.assertFalse(self.closure["runtime_change_authorized"])
        self.assertFalse(self.closure["physical_vrm_execution_enabled"])


if __name__ == "__main__":
    unittest.main()
