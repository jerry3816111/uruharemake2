import json
import unittest

import run_source_preserving_memory_projection_v2_3_single_record_carrier_development as runner


def fake_generation(question, candidates, prereg, endpoint):
    del question, prereg, endpoint
    supports = candidates[0]["role"] == "target"
    return {
        "content": json.dumps(
            {"supports_answer": supports, "answer_span": "Time:" if supports else ""}
        ),
        "carrier_valid": True,
        "carrier_error": None,
        "raw_content": "",
        "raw_tool_calls": [],
        "latency_seconds": 0.1,
        "prompt_sha256": "fake",
        "prompt_character_count": 10,
        "prompt_eval_count": 1,
        "eval_count": 1,
        "total_duration_ns": 1,
    }


class SourcePreservingMemoryProjectionV23RunnerTests(unittest.TestCase):
    def test_fake_screen_produces_exactly_32_valid_rows(self):
        contract, prereg, conditions = runner.load_frozen_configuration()
        cases = runner.load_json(runner.ROOT / contract["artifacts"]["cases"]["path"])[
            "cases"
        ]
        rows = runner.run_screen(cases, prereg, conditions, "unused", fake_generation)
        self.assertEqual(len(rows), 32)
        self.assertTrue(all(row["evidence_validation"]["valid"] for row in rows))
        self.assertTrue(all(row["transport_error_count"] == 0 for row in rows))

    def test_model_call_rejects_more_than_one_candidate(self):
        with self.assertRaises(ValueError):
            runner.call_single_record_model("q", [{}, {}], {}, "unused")


if __name__ == "__main__":
    unittest.main()
