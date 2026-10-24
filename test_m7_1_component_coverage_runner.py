from __future__ import annotations

import json
from pathlib import Path
import unittest

from run_m7_1_component_coverage import run_remediation, validate_inputs


ROOT = Path(__file__).resolve().parent


class M71CoverageRunnerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = json.loads((ROOT / "configs/m7_1_component_coverage_preregistration.json").read_text())
        cls.m6 = json.loads((ROOT / cls.config["m6_result"]["path"]).read_text())
        cls.m7 = json.loads((ROOT / cls.config["m7_first_result"]["path"]).read_text())
        cls.m5d = json.loads((ROOT / cls.config["m5_dataset"]["path"]).read_text())
        cls.m5r = json.loads((ROOT / cls.config["m5_result"]["path"]).read_text())
        cls.overlay = json.loads((ROOT / cls.config["overlay"]["path"]).read_text())

    def test_inputs_expand_to_28_independent_features(self):
        validation = validate_inputs(self.config, self.m6, self.m7, self.m5d, self.m5r, self.overlay)
        self.assertTrue(validation["valid"], validation["errors"])
        self.assertEqual(28, validation["augmented_feature_count"])

    def test_full_remediation_evaluates_all_ten_components(self):
        result = run_remediation(self.config, self.m6, self.m7, self.m5d, self.m5r, self.overlay)
        self.assertEqual("complete_component_coverage_remediation", result["status"])
        self.assertTrue(result["engineering_gate_pass"])
        self.assertTrue(result["component_coverage_complete"])
        self.assertEqual(10, len(result["ablations"]))
        self.assertTrue(all(row["status"] == "evaluated" for row in result["ablations"].values()))
        self.assertEqual(0, result["model_calls"])
        self.assertFalse(result["predictive_lift_claim_authorized"])


if __name__ == "__main__":
    unittest.main()
