import json
from pathlib import Path
import unittest

from longitudinal_human_model.baselines import ProviderError
from longitudinal_human_model.baselines_v1_1 import predict_baseline
from longitudinal_human_model.temporal import build_model_input, load_dataset


ROOT = Path(__file__).resolve().parent


class Provider:
    def __init__(self, mode):
        self.mode = mode

    def __call__(self, *, model, prompt, options):
        labels = json.loads(prompt)["candidate_behavior_labels"]
        probabilities = {label: 1.0 / len(labels) for label in labels}
        if self.mode == "direct":
            text = json.dumps(probabilities)
        elif self.mode == "wrapped":
            text = json.dumps({"probabilities": probabilities, "brief_evidence": "ok"})
        elif self.mode == "missing":
            text = json.dumps({label: probabilities[label] for label in labels[:-1]})
        else:
            text = json.dumps({"answer": "not a distribution"})
        return {"text": text, "model_reported": model}


class TransportCompatibilityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        dataset = load_dataset(ROOT / "datasets/m1_temporal_prediction_synthetic_fixture_v1.json")
        cls.model_input = build_model_input(dataset, dataset["samples"][0])

    def predict(self, mode):
        return predict_baseline(
            "B2_PERSONA_PROMPT",
            self.model_input,
            model="fake",
            provider=Provider(mode),
            options={},
        )

    def test_accepts_frozen_wrapped_contract(self):
        self.assertAlmostEqual(1.0, sum(self.predict("wrapped")["probabilities"].values()))

    def test_accepts_exact_direct_label_map(self):
        self.assertAlmostEqual(1.0, sum(self.predict("direct")["probabilities"].values()))

    def test_rejects_partial_direct_label_map(self):
        with self.assertRaises(ProviderError):
            self.predict("missing")

    def test_rejects_unrelated_json_object(self):
        with self.assertRaises(ProviderError):
            self.predict("unrelated")


if __name__ == "__main__":
    unittest.main()
