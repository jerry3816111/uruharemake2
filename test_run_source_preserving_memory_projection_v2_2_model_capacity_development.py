import json
import unittest

import run_source_preserving_memory_projection_v2_2_model_capacity_development as runner


def fake_generation(question, candidates, prereg, endpoint):
    del question, prereg, endpoint
    verdicts = []
    for index, candidate in enumerate(candidates):
        supports = candidate["role"] == "target"
        verdicts.append(
            {
                "source_index": index,
                "supports_answer": supports,
                "answer_span": "answer" if supports else "",
            }
        )
    if candidates and candidates[0]["role"] == "target":
        candidates[0]["text"] += " answer"
    return {
        "content": json.dumps({"verdicts": verdicts}),
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


class SourcePreservingMemoryProjectionV22CapacityRunnerTests(unittest.TestCase):
    def test_runtime_configuration_preserves_call_matrix_and_changes_model(self):
        _contract, prereg, runtime = runner.load_frozen_configuration()
        self.assertEqual(runtime["span_gate"]["model"], "qwen3.5:9b")
        self.assertEqual(runtime["staged_execution"]["phase_1_call_count"], 32)
        self.assertEqual(
            runtime["staged_execution"]["phase_1_conditions"],
            prereg["controlled_variables"]["conditions"],
        )

    def test_fake_screen_produces_exactly_32_rows(self):
        contract, _prereg, runtime = runner.load_frozen_configuration()
        cases = runner.load_json(runner.ROOT / contract["artifacts"]["cases"]["path"])[
            "cases"
        ]
        rows, passed = runner.run_screen(
            cases, runtime, "unused", model_call=fake_generation
        )
        self.assertEqual(len(rows), 32)
        self.assertTrue(passed)
        self.assertTrue(all(row["experiment_id"] == runtime["experiment_id"] for row in rows))


if __name__ == "__main__":
    unittest.main()
