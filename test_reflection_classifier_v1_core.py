import json
import unittest
from pathlib import Path

from reflection_classifier_v1_core import gate_checks, score_predictions, summarize


ROOT = Path(__file__).resolve().parent
CONFIG = json.loads(
    (ROOT / "configs" / "reflection_classifier_v1_preregistration.json").read_text(
        encoding="utf-8"
    )
)
DATASET = json.loads(
    (ROOT / "datasets" / "reflection_classifier_v1_development.json").read_text(
        encoding="utf-8"
    )
)


class ReflectionClassifierV1CoreTest(unittest.TestCase):
    def test_perfect_predictions_pass_every_gate(self):
        predictions = {case["id"]: case["expected_type"] for case in DATASET["cases"]}
        summary = gate_checks(
            summarize(score_predictions(DATASET["cases"], predictions)),
            CONFIG["success_gates"],
        )
        self.assertTrue(summary["all_gates_pass"])
        self.assertEqual(summary["overall_accuracy"], 1.0)

    def test_critical_false_positive_fails_closed(self):
        predictions = {case["id"]: case["expected_type"] for case in DATASET["cases"]}
        negative = next(case for case in DATASET["cases"] if case["expected_type"] == "none")
        predictions[negative["id"]] = "semantic"
        summary = gate_checks(
            summarize(score_predictions(DATASET["cases"], predictions)),
            CONFIG["success_gates"],
        )
        self.assertFalse(summary["all_gates_pass"])
        self.assertEqual(summary["critical_false_positive_count"], 1)


if __name__ == "__main__":
    unittest.main()
