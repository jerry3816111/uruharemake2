import json
import unittest
from pathlib import Path

import run_answer_bearing_memory_span_v1_development as runner


ROOT = Path(__file__).resolve().parent


class AnswerBearingMemorySpanV1RunnerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.prereg = json.loads(runner.PREREG_PATH.read_text(encoding="utf-8"))
        cls.case = json.loads(
            (
                ROOT
                / cls.prereg["development_data"]["cases_path"]
            ).read_text(encoding="utf-8")
        )["cases"][0]

    def test_condition_candidates_hide_removed_target(self):
        condition = self.prereg["conditions"][1]
        rows = runner.condition_candidates(self.case, condition)
        self.assertEqual([row["role"] for row in rows], ["hard_negative"])
        self.assertNotIn(self.case["target"]["trace_id"], [row["trace_id"] for row in rows])

    def test_prompted_model_never_receives_official_answer_or_expected_trace(self):
        seen = {}

        def fake_call(question, candidates, prereg, endpoint):
            seen["question"] = question
            seen["candidates"] = candidates
            content = json.dumps(
                {
                    "verdicts": [
                        {
                            "source_index": index,
                            "supports_answer": False,
                            "answer_span": "",
                        }
                        for index in range(len(candidates))
                    ]
                }
            )
            return {
                "content": content,
                "latency_seconds": 0.01,
                "prompt_sha256": "x" * 64,
                "prompt_eval_count": 1,
                "eval_count": 1,
                "total_duration_ns": 1,
            }

        row = runner.run_one(
            self.case,
            self.prereg["conditions"][1],
            self.prereg,
            "unused",
            model_call=fake_call,
        )
        serialized = json.dumps(seen, ensure_ascii=False)
        self.assertNotIn(self.case["official_answer"], serialized)
        self.assertNotIn("expected_trace_id", serialized)
        self.assertTrue(row["safe_outcome"])

    def test_target_span_selects_target_under_frozen_policy(self):
        candidate = runner.condition_candidates(self.case, self.prereg["conditions"][3])[0]
        fragment = self.case["official_answer"].split()[0]
        source = candidate["text"]
        start = source.lower().find(fragment.lower())
        self.assertGreaterEqual(start, 0)
        span = source[start : start + len(fragment)]

        def fake_call(question, candidates, prereg, endpoint):
            return {
                "content": json.dumps(
                    {
                        "verdicts": [
                            {
                                "source_index": 0,
                                "supports_answer": True,
                                "answer_span": span,
                            }
                        ]
                    }
                ),
                "latency_seconds": 0.01,
                "prompt_sha256": "x" * 64,
                "prompt_eval_count": 1,
                "eval_count": 1,
                "total_duration_ns": 1,
            }

        row = runner.run_one(
            self.case,
            self.prereg["conditions"][3],
            self.prereg,
            "unused",
            model_call=fake_call,
        )
        self.assertTrue(row["selected"])
        self.assertEqual(row["selected_trace_id"], self.case["target"]["trace_id"])
        self.assertTrue(row["safe_outcome"])

    def test_invalid_model_contract_fails_closed(self):
        def fake_call(question, candidates, prereg, endpoint):
            return {
                "content": "not json",
                "latency_seconds": 0.01,
                "prompt_sha256": "x" * 64,
                "prompt_eval_count": 1,
                "eval_count": 1,
                "total_duration_ns": 1,
            }

        row = runner.run_one(
            self.case,
            self.prereg["conditions"][3],
            self.prereg,
            "unused",
            model_call=fake_call,
        )
        self.assertFalse(row["selected"])
        self.assertEqual(row["status"], "invalid_evidence_contract")


if __name__ == "__main__":
    unittest.main()
