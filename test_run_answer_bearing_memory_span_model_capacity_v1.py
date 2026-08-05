import json
import unittest

import run_answer_bearing_memory_span_model_capacity_v1 as runner


class AnswerBearingMemorySpanModelCapacityV1RunnerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.prereg = runner.load_json(runner.PREREG_PATH)

    def test_model_override_changes_only_model_identity(self):
        base = runner.load_json(
            runner.ROOT
            / self.prereg["frozen_artifacts"]["v1_preregistration"]["path"]
        )
        selected = runner.model_v1_prereg(base, self.prereg["models"][0])
        self.assertEqual(selected["inference"]["model"], "qwen3.5:0.8b")
        selected["inference"]["model"] = base["inference"]["model"]
        selected["inference"]["model_digest"] = base["inference"]["model_digest"]
        self.assertEqual(selected, base)

    def test_phase_1_requires_recall_and_target_removed_abstention(self):
        rows = []
        for index in range(8):
            rows.append(
                {
                    "condition": "n1_remove_exact_hard_negative",
                    "safe_outcome": index < 6,
                    "selected": index < 6,
                    "transport_error_count": 0,
                    "evidence_validation": {
                        "valid": True,
                        "all_spans_grounded": True,
                    },
                }
            )
            rows.append(
                {
                    "condition": "t1_remove_exact_target",
                    "safe_outcome": True,
                    "selected": False,
                    "transport_error_count": 0,
                    "evidence_validation": {
                        "valid": True,
                        "all_spans_grounded": True,
                    },
                }
            )
        self.assertTrue(runner.phase_1_summary(rows)["passed"])
        rows[0]["safe_outcome"] = False
        self.assertFalse(runner.phase_1_summary(rows)["passed"])

    def test_prior_4b_rows_are_reused_without_calls(self):
        model = next(row for row in self.prereg["models"] if row["tag"] == "qwen3.5:4b")
        rows = runner.load_reused_rows(model)
        self.assertEqual(len(rows), 32)
        self.assertTrue(all(row["reused_prior_result"] for row in rows))
        self.assertTrue(all(row["screen_model"] == "qwen3.5:4b" for row in rows))


if __name__ == "__main__":
    unittest.main()
