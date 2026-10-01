from __future__ import annotations

import json
from pathlib import Path
import unittest

from longitudinal_human_model.interventions import (
    NOT_IDENTIFIABLE_ABLATIONS,
    ablate_component,
    intervene_feature,
    reconstruct_features,
)
from run_m5_state_transitions import expand_fixture


ROOT = Path(__file__).resolve().parent


class InterventionContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m6 = json.loads((ROOT / "analysis/m6_behavior_predictor_synthetic_first_generation_raw.json").read_text())
        cls.m5 = json.loads((ROOT / "datasets/m5_state_transition_synthetic_fixture_v1.json").read_text())
        cls.examples = {item.example_id: item for item in expand_fixture(cls.m5)}
        cls.transition_model = cls.m6["experiment_lock"] and json.loads((ROOT / "analysis/m5_state_transition_synthetic_first_generation_raw.json").read_text())["selected_models"]["T3_HYBRID"]
        cls.row = next(row for row in cls.m6["rows"] if row["condition"] == "OURS_HYBRID")

    def test_reconstructs_exact_frozen_predictor_feature_set(self):
        features = reconstruct_features(self.row)
        self.assertEqual(set(self.m6["predictor_features"]), set(features))

    def test_upstream_event_intervention_recomputes_state(self):
        features = reconstruct_features(self.row)
        changed = intervene_feature(
            features, "event.repetition", 0.0,
            example=self.examples[self.row["sample_id"]],
            transition_model=self.transition_model,
            state_dimensions=self.m5["state_dimensions"],
        )
        self.assertEqual(0.0, changed["event.repetition"])
        self.assertNotEqual(
            [features[f"state.{name}"] for name in self.m5["state_dimensions"]],
            [changed[f"state.{name}"] for name in self.m5["state_dimensions"]],
        )

    def test_temporal_dynamics_ablation_uses_previous_state(self):
        features = reconstruct_features(self.row)
        example = self.examples[self.row["sample_id"]]
        changed = ablate_component(
            "temporal_dynamics", features,
            example=example, transition_model=self.transition_model,
            state_dimensions=self.m5["state_dimensions"],
        )
        self.assertEqual(example.previous_state["arousal"], changed["state.arousal"])

    def test_missing_preference_and_habit_are_explicitly_not_identifiable(self):
        self.assertEqual({"preference", "habit"}, set(NOT_IDENTIFIABLE_ABLATIONS))


if __name__ == "__main__":
    unittest.main()
