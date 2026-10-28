from __future__ import annotations

import unittest

from longitudinal_human_model.predictor import (
    fit_softmax_classifier,
    predict_behavior,
    select_temperature,
)


class BehaviorPredictorTests(unittest.TestCase):
    def setUp(self):
        self.labels = ["left", "right"]
        self.features = ["signal"]
        self.rows = [
            {"example_id": "a", "behavior_label": "left", "features": {"signal": 0.0}},
            {"example_id": "b", "behavior_label": "left", "features": {"signal": 0.1}},
            {"example_id": "c", "behavior_label": "right", "features": {"signal": 0.9}},
            {"example_id": "d", "behavior_label": "right", "features": {"signal": 1.0}},
        ]

    def test_fit_predict_and_direct_contribution_explanation(self):
        model = fit_softmax_classifier(
            self.rows, self.labels, self.features,
            l2_alpha=0.001, learning_rate=0.2, epochs=1000,
        )
        result = predict_behavior(
            model, {"signal": 1.0}, temperature=1.0,
            evidence={"memory_ids": ["m1"], "state_features": {"signal": 1.0}},
        )
        self.assertEqual("right", result["selected_behavior"])
        self.assertAlmostEqual(1.0, sum(result["probabilities"].values()))
        self.assertEqual("direct_model_contributions_not_posthoc_llm", result["explanation"]["kind"])
        self.assertFalse(result["language_realization_performed"])

    def test_temperature_selection_includes_no_change_and_does_not_worsen_dev_nll(self):
        model = fit_softmax_classifier(
            self.rows, self.labels, self.features,
            l2_alpha=0.001, learning_rate=0.2, epochs=1000,
        )
        selection = select_temperature(self.rows, model, [0.5, 1.0, 2.0])
        baseline = next(row for row in selection["candidates"] if row["temperature"] == 1.0)
        self.assertLessEqual(selection["candidates"][0]["dev_negative_log_likelihood"], baseline["dev_negative_log_likelihood"])

    def test_rejects_incomplete_feature_vector(self):
        model = fit_softmax_classifier(
            self.rows, self.labels, self.features,
            l2_alpha=0.001, learning_rate=0.2, epochs=10,
        )
        with self.assertRaisesRegex(ValueError, "keys mismatch"):
            predict_behavior(model, {}, temperature=1.0, evidence={})


if __name__ == "__main__":
    unittest.main()
