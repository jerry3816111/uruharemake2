from __future__ import annotations

import unittest

from longitudinal_human_model.component_features import (
    PREFERENCE_FEATURES,
    augment_component_features,
    fit_habit_centroids,
)


class ComponentFeatureTests(unittest.TestCase):
    def test_preference_and_habit_are_separate_feature_groups(self):
        base = {
            "event.boundary_threat": 0.8,
            "event.ambiguity": 0.2,
            "event.public_pressure": 0.4,
            "event.support": 0.6,
            "event.technical_failure": 0.1,
            "event.repetition": 0.3,
            "person.boundary_directness": 0.9,
            "person.reassessment_tendency": 0.7,
            "person.pressure_sensitivity": 0.5,
            "state.relationship_tension": 0.2,
            "state.task_focus": 0.8,
        }
        centroids = {"a": {name: 0.5 for name in ("boundary_threat", "ambiguity", "public_pressure", "support", "technical_failure", "repetition")}}
        augmented = augment_component_features(base, centroids, list(centroids["a"]))
        self.assertEqual(set(PREFERENCE_FEATURES), {name for name in augmented if name.startswith("preference.")})
        self.assertIn("habit.similarity.a", augmented)
        self.assertAlmostEqual(0.72, augmented["preference.boundary_safety"])

    def test_habit_centroids_use_training_rows_only(self):
        rows = [
            {"behavior_label": "a", "features": {"event.x": 0.0}},
            {"behavior_label": "a", "features": {"event.x": 1.0}},
            {"behavior_label": "b", "features": {"event.x": 0.2}},
        ]
        centroids = fit_habit_centroids(rows, ["a", "b"], ["x"])
        self.assertEqual(0.5, centroids["a"]["x"])
        self.assertEqual(0.2, centroids["b"]["x"])


if __name__ == "__main__":
    unittest.main()
