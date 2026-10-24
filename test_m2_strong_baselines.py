import json
from pathlib import Path
import unittest

from longitudinal_human_model.baselines import ProviderError
from longitudinal_human_model.strong_baselines import (
    STRONG_BASELINES,
    _prediction_prompt,
    build_structured_history,
    history_signature,
    predict_strong_baseline,
    summarize_full_history,
)
from longitudinal_human_model.temporal import build_model_input, load_dataset
from run_m2_strong_baselines import run_strong_baselines


ROOT = Path(__file__).resolve().parent
DATASET = load_dataset(ROOT / "datasets/m1_temporal_prediction_synthetic_fixture_v1.json")
CONFIG = json.loads(
    (ROOT / "configs/m2_strong_temporal_baselines_preregistration.json").read_text(encoding="utf-8")
)
M1 = json.loads(
    (ROOT / "analysis/m1_temporal_prediction_observatory_synthetic_v1_1_raw.json").read_text(encoding="utf-8")
)


class FakeProvider:
    def __init__(self, prediction_mode="direct"):
        self.calls = []
        self.prediction_mode = prediction_mode

    def __call__(self, *, model, prompt, options):
        parsed = json.loads(prompt)
        self.calls.append(parsed)
        if parsed["task"].startswith("Condense"):
            text = json.dumps({"summary": "Synthetic evidence-grounded history summary."})
        else:
            labels = parsed["candidate_behavior_labels"]
            probabilities = {label: 1.0 / len(labels) for label in labels}
            if self.prediction_mode == "direct":
                text = json.dumps(probabilities)
            elif self.prediction_mode == "wrapped":
                text = json.dumps({"probabilities": probabilities, "brief_evidence": "fixture"})
            else:
                text = json.dumps({"probabilities": {labels[0]: 1.0}})
        return {
            "text": text,
            "latency_seconds": 0.01,
            "prompt_tokens": 100,
            "completion_tokens": 20,
            "model_reported": model,
        }


class StrongBaselineTests(unittest.TestCase):
    def setUp(self):
        self.inputs = [build_model_input(DATASET, sample) for sample in DATASET["samples"]]

    def test_identical_authorized_history_reuses_one_signature(self):
        self.assertEqual(1, len({history_signature(item) for item in self.inputs}))

    def test_summary_uses_history_but_no_event_or_outcome(self):
        provider = FakeProvider()
        summary = summarize_full_history(
            self.inputs[0], model="fake", provider=provider, options={}
        )
        prompt = provider.calls[0]
        serialized = json.dumps(prompt, sort_keys=True)
        self.assertEqual(12, len(summary["history_ids"]))
        self.assertNotIn("event_context", serialized)
        self.assertNotIn("actual_observed_behavior", serialized)
        self.assertNotIn("actual_observed_at", serialized)

    def test_b4_contains_summary_not_raw_history(self):
        summary = {
            "summary": "summary-only-marker",
            "history_ids": [row["history_id"] for row in self.inputs[0]["available_history"]],
        }
        prompt = json.loads(
            _prediction_prompt("B4_FULL_HISTORY_SUMMARY", self.inputs[0], summary_artifact=summary)
        )
        self.assertEqual("summary-only-marker", prompt["full_history_summary"])
        self.assertNotIn("structured_full_history", prompt)
        self.assertNotIn("persona_summary", json.dumps(prompt))

    def test_b5_contains_all_history_in_structured_groups(self):
        structured = build_structured_history(self.inputs[0])
        evidence_ids = {
            row["history_id"]
            for group in structured["behavior_patterns"]
            for row in group["evidence"]
        }
        self.assertEqual({f"h{index:02d}" for index in range(1, 13)}, evidence_ids)
        self.assertEqual(12, structured["history_record_count"])

    def test_b4_and_b5_accept_direct_and_wrapped_probability_contracts(self):
        summary = {
            "summary": "safe summary",
            "history_ids": [row["history_id"] for row in self.inputs[0]["available_history"]],
        }
        for baseline, mode in zip(STRONG_BASELINES, ("direct", "wrapped")):
            result = predict_strong_baseline(
                baseline,
                self.inputs[0],
                summary_artifact=summary,
                model="fake",
                provider=FakeProvider(mode),
                options={},
            )
            self.assertAlmostEqual(1.0, sum(result["probabilities"].values()))

    def test_partial_probability_map_fails_closed(self):
        with self.assertRaises(ProviderError):
            predict_strong_baseline(
                "B5_STRUCTURED_HISTORY",
                self.inputs[0],
                summary_artifact=None,
                model="fake",
                provider=FakeProvider("partial"),
                options={},
            )

    def test_fake_full_run_emits_24_rows_one_summary_and_b0_b5_metrics(self):
        provider = FakeProvider()
        result = run_strong_baselines(DATASET, CONFIG, provider=provider, inherited_result=M1)
        self.assertEqual("complete_fixture_run", result["status"])
        self.assertEqual(24, result["observed_prediction_rows"])
        self.assertEqual(1, len(result["summaries"]))
        self.assertEqual(25, result["resources"]["model_calls"])
        self.assertEqual(6, len(result["combined_b0_b5_metrics"]))
        self.assertFalse(result["formal_target_claim"])


if __name__ == "__main__":
    unittest.main()
