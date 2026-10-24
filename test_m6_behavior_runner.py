from __future__ import annotations

import json
from pathlib import Path
import unittest

from run_m6_behavior_predictor import (
    materialize_temporal_dataset,
    run_experiment,
    validate_inputs,
)


ROOT = Path(__file__).resolve().parent


class M6RunnerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.overlay = json.loads((ROOT / "datasets/m6_behavior_prediction_synthetic_overlay_v1.json").read_text())
        cls.config = json.loads((ROOT / "configs/m6_behavior_predictor_preregistration.json").read_text())
        cls.m5_dataset = json.loads((ROOT / "datasets/m5_state_transition_synthetic_fixture_v1.json").read_text())
        cls.m5_result = json.loads((ROOT / "analysis/m5_state_transition_synthetic_first_generation_raw.json").read_text())

    def test_temporal_overlay_has_32_history_and_8_future_samples(self):
        validation = validate_inputs(self.overlay, self.config, self.m5_dataset, self.m5_result)
        self.assertTrue(validation["valid"], validation["errors"])
        self.assertEqual(32, validation["history_count"])
        self.assertEqual(8, validation["holdout_count"])
        self.assertEqual(0, validation["leakage_report"]["future_leakage_violations"])

    def test_provider_safe_view_never_contains_future_outcome_fields(self):
        temporal = materialize_temporal_dataset(self.overlay, self.m5_dataset)
        serialized_samples = json.dumps(temporal["samples"])
        self.assertIn("actual_observed_behavior", serialized_samples)
        from longitudinal_human_model.temporal import build_model_input
        safe = build_model_input(temporal, temporal["samples"][0])
        self.assertNotIn("actual_observed_behavior", safe)
        self.assertNotIn("acceptable_behavior_labels", safe)

    def test_full_fake_provider_run_completes_all_conditions(self):
        labels = self.overlay["taxonomy"]["labels"]

        def provider(**kwargs):
            prompt = json.loads(kwargs["prompt"])
            if prompt["task"].startswith("Condense"):
                text = json.dumps({"summary": "Synthetic observable history summary."})
            else:
                text = json.dumps({"probabilities": {label: 1 / len(labels) for label in labels}, "brief_evidence": "fixture"})
            return {
                "text": text,
                "prompt_tokens": 10,
                "completion_tokens": 5,
                "latency_seconds": 0.01,
                "model_reported": "fixture-provider",
            }

        result = run_experiment(
            self.overlay, self.config, self.m5_dataset, self.m5_result, provider=provider
        )
        self.assertEqual("complete_hypothesis_run", result["status"])
        self.assertTrue(result["engineering_gate_pass"])
        self.assertEqual(56, len(result["rows"]))
        self.assertEqual(41, len(result["provider_records"]))
        ours = [row for row in result["rows"] if row["condition"] == "OURS_HYBRID"]
        self.assertEqual(8, len(ours))
        self.assertTrue(all(not row["language_realization_performed"] for row in ours))


if __name__ == "__main__":
    unittest.main()
