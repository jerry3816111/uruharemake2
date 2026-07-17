import json
import unittest
from pathlib import Path

import uruha_reflection_runtime as reflection
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
BASELINE = json.loads(
    (ROOT / "reports" / "reflection_classifier_v1_legacy_baseline.json").read_text(
        encoding="utf-8"
    )
)


class ReflectionClassifierV1CandidateTest(unittest.TestCase):
    def test_candidate_passes_frozen_development_gates_without_regression(self):
        predictions = {
            case["id"]: reflection.classify_reflection_type(case["text"])
            for case in DATASET["cases"]
        }
        rows = score_predictions(DATASET["cases"], predictions)
        baseline_by_id = {row["id"]: row for row in BASELINE["rows"]}
        regressions = [
            row["id"]
            for row in rows
            if baseline_by_id[row["id"]]["correct"] and not row["correct"]
        ]
        result = gate_checks(
            summarize(rows), CONFIG["success_gates"], len(regressions)
        )
        self.assertTrue(result["all_gates_pass"])
        self.assertEqual(regressions, [])

    def test_structural_examples_do_not_require_frozen_sentences(self):
        examples = {
            "I feel ill whenever I eat shellfish, so I avoid it.": "semantic",
            "辛い物を食べると胃が痛くなるので避けている。": "semantic",
            "From now on, answer in one sentence before adding details.": "procedural",
            "如果之後我說『再看看』，通常代表我還沒決定。": "interpretive",
            "My sister always needs quiet to work.": "none",
            "我爸爸平常喜歡喝濃茶。": "none",
            "私の母は甘い物が好き。": "none",
            "I need help right now.": "none",
        }
        self.assertEqual(
            {
                text: reflection.classify_reflection_type(text)
                for text in examples
            },
            examples,
        )

    def test_candidate_does_not_enable_runtime_reflection(self):
        self.assertFalse(reflection.typed_reflection_runtime_enabled({}))


if __name__ == "__main__":
    unittest.main()
