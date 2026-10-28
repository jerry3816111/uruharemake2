from __future__ import annotations

import unittest
import json
from pathlib import Path

from longitudinal_human_model.transitions import (
    TransitionExample,
    extract_event_features,
    fit_ridge_transition,
    learned_transition,
    static_transition,
    transition_metrics,
    weighted_transition,
)
from run_m5_state_transitions import expand_fixture, run_experiment, validate_inputs


DIMS = ("focus", "uncertainty")
EVENTS = ("failure", "ambiguity")
MEMORY = ("matching",)
PERSON = ("sensitivity",)


def example(example_id, failure, ambiguity, next_focus, next_uncertainty):
    return TransitionExample(
        example_id=example_id,
        split="train",
        event_text="fixture event",
        previous_state={"focus": 0.4, "uncertainty": 0.4},
        event_features={"failure": failure, "ambiguity": ambiguity},
        memory_signals={"matching": 0.5},
        person_parameters={"sensitivity": 0.5},
        next_state={"focus": next_focus, "uncertainty": next_uncertainty},
    )


class TransitionContractTests(unittest.TestCase):
    def test_t0_is_exactly_static(self):
        row = static_transition(example("x", 1, 0, 0.8, 0.2), DIMS)
        self.assertEqual(row["previous_state"], row["next_state"])
        self.assertFalse(row["behavior_prediction_performed"])

    def test_t1_coefficients_are_inspectable(self):
        coefficients = {
            "focus": {"previous.focus": 1.0, "event.failure": 0.2},
            "uncertainty": {"previous.uncertainty": 1.0, "event.ambiguity": 0.3},
        }
        row = weighted_transition(example("x", 1, 0, 0.6, 0.4), DIMS, coefficients)
        self.assertAlmostEqual(0.6, row["next_state"]["focus"])
        self.assertIn("event.failure", row["contributions"]["focus"])

    def test_ridge_fit_reconstructs_simple_linear_transition(self):
        rows = [
            example("a", 0.0, 0.0, 0.4, 0.4),
            example("b", 1.0, 0.0, 0.8, 0.4),
            example("c", 0.0, 1.0, 0.4, 0.8),
            example("d", 1.0, 1.0, 0.8, 0.8),
        ]
        names = ["bias", "previous.focus", "previous.uncertainty", "event.failure", "event.ambiguity"]
        model = fit_ridge_transition(rows, DIMS, names, ridge_alpha=0.001)
        prediction = learned_transition(
            "T2_LINEAR", rows[-1], model, DIMS, feature_source="gold"
        )
        self.assertAlmostEqual(0.8, prediction["next_state"]["focus"], places=2)
        self.assertAlmostEqual(0.8, prediction["next_state"]["uncertainty"], places=2)

    def test_feature_extractor_requires_exact_map(self):
        def provider(**_):
            return {"text": '{"features":{"failure":0.8}}'}
        with self.assertRaisesRegex(Exception, "keys mismatch"):
            extract_event_features(
                "event",
                EVENTS,
                model="fixture",
                provider=provider,
                options={},
            )

    def test_transition_metrics_measure_state_not_behavior(self):
        rows = [{
            "previous_state": {"focus": 0.4, "uncertainty": 0.4},
            "prediction": {"focus": 0.6, "uncertainty": 0.2},
            "actual_next_state": {"focus": 0.6, "uncertainty": 0.2},
        }]
        metrics = transition_metrics(rows, DIMS)
        self.assertEqual(0.0, metrics["rmse"])
        self.assertEqual(1.0, metrics["direction_accuracy"])


class FrozenFixtureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        root = Path(__file__).resolve().parent
        cls.dataset = json.loads((root / "datasets/m5_state_transition_synthetic_fixture_v1.json").read_text())
        cls.config = json.loads((root / "configs/m5_state_transition_preregistration.json").read_text())

    def test_fixture_expands_without_overlap_or_future_label_input(self):
        validation = validate_inputs(self.dataset, self.config)
        self.assertTrue(validation["valid"], validation["errors"])
        self.assertEqual({"train": 24, "dev": 8, "holdout": 8}, validation["split_counts"])
        self.assertEqual(0, validation["event_text_overlap_count"])

    def test_full_run_with_exact_fixture_feature_provider(self):
        lookup = {row.event_text: row.event_features for row in expand_fixture(self.dataset)}

        def provider(**kwargs):
            prompt = json.loads(kwargs["prompt"])
            return {
                "text": json.dumps({"features": lookup[prompt["event_text"]]}),
                "prompt_tokens": 10,
                "completion_tokens": 5,
                "latency_seconds": 0.01,
                "model_reported": "fixture-provider",
            }

        result = run_experiment(self.dataset, self.config, provider=provider)
        self.assertEqual("complete_mechanism_run", result["status"])
        self.assertTrue(result["gate_pass"])
        self.assertEqual(40, result["resource_accounting"]["model_call_count"])
        self.assertLess(
            result["families"]["T2_LINEAR"]["metrics"]["rmse"],
            result["families"]["T1_WEIGHTED"]["metrics"]["rmse"],
        )
        self.assertFalse(any(
            trace["behavior_prediction_performed"]
            for family in result["families"].values()
            for trace in family["traces"]
        ))


if __name__ == "__main__":
    unittest.main()
