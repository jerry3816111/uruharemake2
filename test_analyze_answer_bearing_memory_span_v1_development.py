import json
import unittest

import analyze_answer_bearing_memory_span_v1_development as analyzer


class AnswerBearingMemorySpanV1AnalyzerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.prereg = analyzer.load_json(analyzer.PREREG_PATH)
        cls.cases = analyzer.load_json(
            analyzer.ROOT / cls.prereg["development_data"]["cases_path"]
        )["cases"]

    def make_rows(self):
        rows = []
        for case in self.cases:
            for condition in self.prereg["conditions"]:
                candidates = analyzer.condition_candidates(case, condition)
                expected = condition["expected_selection"]
                if expected is None:
                    verdicts = [
                        {"source_index": i, "supports_answer": False, "answer_span": ""}
                        for i in range(len(candidates))
                    ]
                    selected_trace = None
                    selected = False
                else:
                    expected_trace = case[expected]["trace_id"]
                    target_index = next(
                        i for i, row in enumerate(candidates) if row["trace_id"] == expected_trace
                    )
                    source = candidates[target_index]["text"]
                    span = source[: min(12, len(source))]
                    verdicts = [
                        {
                            "source_index": i,
                            "supports_answer": i == target_index,
                            "answer_span": span if i == target_index else "",
                        }
                        for i in range(len(candidates))
                    ]
                    selected_trace = expected_trace
                    selected = True
                expected_trace = case[expected]["trace_id"] if expected else None
                model_output = json.dumps({"verdicts": verdicts})
                rows.append(
                    {
                        "case_id": case["case_id"],
                        "language": case["language"],
                        "condition": condition["id"],
                        "expected_trace_id": expected_trace,
                        "selected": selected,
                        "selected_trace_id": selected_trace,
                        "status": "selected" if selected else "unsupported",
                        "safe_outcome": True,
                        "wrong_trace_selected": False,
                        "evidence_validation": {"valid": True, "errors": []},
                        "model_output": model_output,
                        "latency_seconds": 0.5,
                        "transport_error_count": 0,
                        "production_memory_write_count": 0,
                        "physical_vrm_action_count": 0,
                    }
                )
        return rows

    def test_perfect_synthetic_result_only_authorizes_holdout(self):
        report = analyzer.summarize(
            self.make_rows(),
            self.prereg,
            self.cases,
            {"model_digest": self.prereg["inference"]["model_digest"]},
        )
        self.assertEqual(report["decision"], "development_pass_requires_fresh_holdout")
        self.assertEqual(report["metrics"]["target_removed_selection_count"], 0)
        self.assertFalse(report["evidence_boundary"]["runtime_change_authorized"])

    def test_one_target_removed_selection_fails_gate(self):
        rows = self.make_rows()
        row = next(row for row in rows if row["condition"] == "t1_remove_exact_target")
        row["selected"] = True
        row["selected_trace_id"] = "wrong"
        row["safe_outcome"] = False
        row["wrong_trace_selected"] = True
        report = analyzer.summarize(
            rows,
            self.prereg,
            self.cases,
            {"model_digest": self.prereg["inference"]["model_digest"]},
        )
        self.assertEqual(report["decision"], "development_reject_or_inconclusive")
        self.assertFalse(report["gates"]["target_removed_selection_count_equals_zero"])


if __name__ == "__main__":
    unittest.main()
