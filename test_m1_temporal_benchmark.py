import copy
import json
from pathlib import Path
import tempfile
import unittest

from longitudinal_human_model.baselines import BASELINES, predict_baseline
from longitudinal_human_model.metrics import evaluate_predictions
from longitudinal_human_model.registry import verify_lock
from longitudinal_human_model.temporal import (
    TemporalDatasetError,
    build_model_input,
    load_dataset,
    validate_temporal_dataset,
)
from run_m1_temporal_benchmark import run_benchmark


ROOT = Path(__file__).resolve().parent
DATASET_PATH = ROOT / "datasets/m1_temporal_prediction_synthetic_fixture_v1.json"
CONFIG_PATH = ROOT / "configs/m1_temporal_prediction_observatory_fixture_preregistration.json"
GATE_PATH = ROOT / "configs/m1_uruha_temporal_data_gate.json"


class FakeProvider:
    def __call__(self, *, model, prompt, options):
        parsed = json.loads(prompt)
        labels = parsed["candidate_behavior_labels"]
        probabilities = {label: 0.1 for label in labels}
        probabilities[labels[0]] = 0.5
        return {
            "text": json.dumps({"probabilities": probabilities, "brief_evidence": "fixture"}),
            "latency_seconds": 0.01,
            "prompt_tokens": 20,
            "completion_tokens": 12,
            "model_reported": model,
        }


class TemporalDatasetTests(unittest.TestCase):
    def setUp(self):
        self.dataset = load_dataset(DATASET_PATH)

    def test_clean_fixture_passes_and_is_not_formal_evidence(self):
        report = validate_temporal_dataset(self.dataset)
        self.assertTrue(report["valid"])
        self.assertEqual(0, report["future_leakage_violations"])
        self.assertEqual(12, report["prediction_samples"])
        self.assertFalse(report["formal_target_claim"])

    def test_post_cutoff_history_reference_fails_closed(self):
        dataset = copy.deepcopy(self.dataset)
        dataset["history"][0]["available_at"] = "2025-08-01T00:00:00+09:00"
        with self.assertRaisesRegex(TemporalDatasetError, "future leakage"):
            validate_temporal_dataset(dataset)

    def test_outcome_before_prediction_fails_closed(self):
        dataset = copy.deepcopy(self.dataset)
        dataset["samples"][0]["actual_observed_at"] = dataset["samples"][0]["prediction_time"]
        with self.assertRaisesRegex(TemporalDatasetError, "not strictly after"):
            validate_temporal_dataset(dataset)

    def test_model_input_strips_outcome_and_post_prediction_fields(self):
        sample = self.dataset["samples"][0]
        model_input = build_model_input(self.dataset, sample)
        serialized = json.dumps(model_input, sort_keys=True)
        for forbidden_key in (
            "actual_observed_behavior",
            "actual_observed_at",
            "source_timestamp",
            "acceptable_behavior_labels",
            "annotation_confidence",
        ):
            self.assertNotIn(forbidden_key, serialized)
        self.assertNotIn(sample["actual_observed_at"], serialized)


class BaselineAndMetricTests(unittest.TestCase):
    def setUp(self):
        self.dataset = load_dataset(DATASET_PATH)
        self.model_input = build_model_input(self.dataset, self.dataset["samples"][0])

    def test_all_baselines_emit_same_normalized_label_contract(self):
        labels = self.model_input["candidate_behavior_labels"]
        for baseline in BASELINES:
            result = predict_baseline(
                baseline,
                self.model_input,
                model="fake-model",
                provider=FakeProvider(),
                options={"temperature": 0},
            )
            self.assertEqual(set(labels), set(result["probabilities"]))
            self.assertAlmostEqual(1.0, sum(result["probabilities"].values()))

    def test_perfect_predictions_have_perfect_ranking_and_zero_brier(self):
        labels = self.model_input["candidate_behavior_labels"]
        rows = []
        for label in labels:
            rows.append(
                {
                    "actual_observed_behavior": label,
                    "acceptable_behavior_labels": [label],
                    "probabilities": {candidate: float(candidate == label) for candidate in labels},
                }
            )
        metrics = evaluate_predictions(rows, labels, top_k=3, ece_bins=5)
        self.assertEqual(1.0, metrics["top1_accuracy"])
        self.assertEqual(1.0, metrics["macro_f1"])
        self.assertEqual(0.0, metrics["brier_score"])
        self.assertEqual(0.0, metrics["expected_calibration_error"])

    def test_runner_refuses_formal_target_claim(self):
        dataset = copy.deepcopy(self.dataset)
        dataset["authorizations"]["formal_target_claim"] = True
        config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        with self.assertRaisesRegex(PermissionError, "formal target-person claim"):
            run_benchmark(dataset, config, provider=FakeProvider())

    def test_fake_full_run_has_48_rows_and_no_failures(self):
        config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        result = run_benchmark(self.dataset, config, provider=FakeProvider())
        self.assertEqual("complete_fixture_run", result["status"])
        self.assertEqual(48, result["observed_prediction_rows"])
        self.assertEqual([], result["failures"])
        self.assertFalse(result["formal_target_claim"])
        self.assertEqual(36, result["resources"]["model_calls"])


class GovernanceTests(unittest.TestCase):
    def test_uruha_data_gate_is_explicitly_blocked(self):
        gate = json.loads(GATE_PATH.read_text(encoding="utf-8"))
        self.assertEqual("DATA_GATE_BLOCKED", gate["decision"])
        self.assertFalse(gate["model_execution"])
        self.assertFalse(gate["formal_result"])
        self.assertEqual(0, gate["current_counts"]["target_behavior_events"])
        for binding in gate["bound_existing_artifacts"]:
            path = ROOT / binding["path"]
            self.assertTrue(path.is_file())
            lock = {"file_bindings": [binding]}
            self.assertEqual([], verify_lock(lock, repo_root=ROOT))


if __name__ == "__main__":
    unittest.main()
