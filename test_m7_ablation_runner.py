from __future__ import annotations

import json
from pathlib import Path
import unittest

from run_m7_ablation_intervention import run_diagnostic, validate_inputs


ROOT = Path(__file__).resolve().parent


class M7DiagnosticRunnerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = json.loads((ROOT / "configs/m7_ablation_intervention_preregistration.json").read_text())
        cls.m6 = json.loads((ROOT / "analysis/m6_behavior_predictor_synthetic_first_generation_raw.json").read_text())
        cls.m5_dataset = json.loads((ROOT / "datasets/m5_state_transition_synthetic_fixture_v1.json").read_text())
        cls.m5_result = json.loads((ROOT / "analysis/m5_state_transition_synthetic_first_generation_raw.json").read_text())

    def test_frozen_inputs_expose_two_structural_gaps(self):
        validation = validate_inputs(self.config, self.m6, self.m5_dataset, self.m5_result)
        self.assertTrue(validation["valid"], validation["errors"])
        self.assertEqual(8, validation["identifiable_component_count"])
        self.assertEqual(2, validation["not_identifiable_component_count"])

    def test_full_diagnostic_is_complete_but_not_full_component_coverage(self):
        result = run_diagnostic(self.config, self.m6, self.m5_dataset, self.m5_result)
        self.assertEqual("complete_diagnostic_run", result["status"])
        self.assertTrue(result["engineering_gate_pass"])
        self.assertFalse(result["component_coverage_complete"])
        self.assertEqual("not_identifiable", result["ablations"]["preference"]["status"])
        self.assertEqual("not_identifiable", result["ablations"]["habit"]["status"])
        self.assertEqual(80, len(result["named_interventions"]))
        self.assertEqual(40, len(result["explanation_faithfulness"]["rows"]))
        self.assertTrue(result["engineering_gate_checks"]["full_prediction_replay_exact"])


if __name__ == "__main__":
    unittest.main()
