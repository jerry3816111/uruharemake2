import json
import tempfile
import unittest
from copy import deepcopy

import analyze_answer_bearing_memory_span_model_capacity_v1 as analyzer
import run_answer_bearing_memory_span_model_capacity_v1 as runner


class AnswerBearingMemorySpanModelCapacityV1AnalyzerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.prereg = runner.load_json(runner.PREREG_PATH)
        v1 = runner.load_json(
            runner.ROOT / cls.prereg["frozen_artifacts"]["v1_preregistration"]["path"]
        )
        cls.v1 = v1
        cls.cases = runner.load_json(
            runner.ROOT / v1["development_data"]["cases_path"]
        )["cases"]

    def perfect_rows(self, model):
        rows = []
        for case in self.cases:
            for condition in self.v1["conditions"]:
                candidates = runner.condition_candidates(case, condition)
                expected_role = condition["expected_selection"]
                verdicts = []
                expected_trace = case[expected_role]["trace_id"] if expected_role else None
                for index, candidate in enumerate(candidates):
                    supported = candidate["trace_id"] == expected_trace
                    verdicts.append(
                        {
                            "source_index": index,
                            "supports_answer": supported,
                            "answer_span": candidate["text"][:12] if supported else "",
                        }
                    )
                selected = expected_trace is not None
                rows.append(
                    {
                        "case_id": case["case_id"],
                        "language": case["language"],
                        "condition": condition["id"],
                        "expected_trace_id": expected_trace,
                        "selected": selected,
                        "selected_trace_id": expected_trace,
                        "status": "selected" if selected else "unsupported",
                        "safe_outcome": True,
                        "wrong_trace_selected": False,
                        "evidence_validation": {
                            "valid": True,
                            "all_spans_grounded": True,
                        },
                        "model_output": json.dumps({"verdicts": verdicts}),
                        "latency_seconds": 1.0,
                        "transport_error_count": 0,
                        "production_memory_write_count": 0,
                        "physical_vrm_action_count": 0,
                        "reused_prior_result": False,
                        "screen_model": model["tag"],
                    }
                )
        return rows

    def test_smallest_eligible_model_is_selected(self):
        models = self.prereg["models"]
        rows = self.perfect_rows(models[0]) + self.perfect_rows(models[1])
        for model in models[2:]:
            partial = self.perfect_rows(model)[:16]
            rows.extend(partial)
        metadata = {
            "raw_path": "unused",
            "raw_sha256": "unused",
            "row_count": len(rows),
            "new_model_call_count": len(rows),
        }
        original = analyzer.file_sha256
        analyzer.file_sha256 = lambda path: "unused" if str(path).endswith("unused") else original(path)
        try:
            report = analyzer.summarize(rows, self.prereg, metadata)
        finally:
            analyzer.file_sha256 = original
        self.assertEqual(report["selected_model"], "qwen3.5:0.8b")
        self.assertEqual(report["decision"], "model_selected_requires_fresh_holdout")

    def test_incomplete_model_is_not_eligible(self):
        model = self.prereg["models"][0]
        rows = self.perfect_rows(model)[:16]
        summary = analyzer.model_summary(model, rows, self.cases, self.v1)
        self.assertFalse(summary["eligible"])
        self.assertFalse(summary["final_gates"]["all_32_decisions_present"])


if __name__ == "__main__":
    unittest.main()
