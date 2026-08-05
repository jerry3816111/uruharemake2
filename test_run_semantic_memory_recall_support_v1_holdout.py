import json
import unittest
from copy import deepcopy
from pathlib import Path

import run_semantic_memory_recall_support_v1_holdout as runner


ROOT = Path(__file__).resolve().parent
CONTRACT = json.loads(
    (ROOT / "configs/semantic_memory_recall_support_v1_holdout_evaluation_contract.json").read_text(
        encoding="utf-8"
    )
)
PREREG = json.loads(
    (ROOT / "configs/semantic_memory_recall_support_v1_holdout_preregistration.json").read_text(
        encoding="utf-8"
    )
)


def case(index, language="English", hard_text="I bought oranges yesterday."):
    return {
        "case_id": f"synthetic-{index}",
        "official_question_id": f"q-{index}",
        "language": language,
        "question": "Where did I leave the blue folder?",
        "official_answer": "unused",
        "target": {
            "trace_id": f"q-{index}:target",
            "text": "The blue folder is in the reading room.",
            "score": 0.9,
        },
        "hard_negative": {
            "trace_id": f"q-{index}:negative",
            "text": hard_text,
            "score": 0.82,
        },
        "replacement": {
            "trace_id": f"q-{index}:replacement",
            "text": "The reading room is where the blue folder was left.",
            "score": 0.9,
        },
    }


def metadata():
    return {
        "boundary_probes": {
            "sensitive": {"selected": False},
            "non_recall": {"selected": False},
            "broad_presence": {"selected": False},
        }
    }


class RunSemanticMemoryRecallSupportV1HoldoutTests(unittest.TestCase):
    def test_unrelated_negative_fixture_passes_all_gates(self):
        cases = [case(index) for index in range(8)]
        rows = [row for item in cases for row in runner.evaluate_case(item, CONTRACT)]
        report = runner.build_report(
            rows,
            {"case_count": 8},
            PREREG,
            CONTRACT,
            metadata(),
        )

        self.assertEqual(report["decision"], "holdout_pass_production_still_disabled")
        self.assertTrue(all(report["gates"].values()))
        self.assertFalse(report["authorization"]["production_default_enablement"])

    def test_same_topic_negative_is_caught_after_target_removal(self):
        cases = [
            case(index, hard_text="The blue folder cover was repaired yesterday.")
            for index in range(8)
        ]
        rows = [row for item in cases for row in runner.evaluate_case(item, CONTRACT)]
        report = runner.build_report(
            rows,
            {"case_count": 8},
            PREREG,
            CONTRACT,
            metadata(),
        )

        self.assertEqual(report["decision"], "holdout_reject_or_inconclusive")
        self.assertGreater(report["target_removed_selection_count"], 0)

    def test_official_answer_is_not_used_by_evaluator(self):
        original = case(1)
        changed = deepcopy(original)
        changed["official_answer"] = "a completely different hidden answer"

        self.assertEqual(
            runner.evaluate_case(original, CONTRACT),
            runner.evaluate_case(changed, CONTRACT),
        )


if __name__ == "__main__":
    unittest.main()
