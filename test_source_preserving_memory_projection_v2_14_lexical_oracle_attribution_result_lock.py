import json
import unittest
from collections import Counter
from pathlib import Path

from build_source_preserving_memory_projection_v2_5_locomo_cases import file_sha256


ROOT = Path(__file__).resolve().parent
LOCK = (
    ROOT
    / "configs/source_preserving_memory_projection_v2_14_lexical_oracle_attribution_result_lock.json"
)
REPORT = (
    ROOT
    / "reports/source_preserving_memory_projection_v2_14_lexical_oracle_attribution.json"
)


class LexicalOracleAttributionResultLockV214Tests(unittest.TestCase):
    def setUp(self):
        self.lock = json.loads(LOCK.read_text(encoding="utf-8"))
        self.report = json.loads(REPORT.read_text(encoding="utf-8"))

    def test_locked_artifacts_match(self):
        for relative, expected in self.lock["artifacts"].items():
            self.assertEqual(file_sha256(ROOT / relative), expected, relative)

    def test_locked_metrics_gates_and_decision_match(self):
        self.assertEqual(self.report["metrics"], self.lock["metrics"])
        self.assertEqual(self.report["gates"], self.lock["gates"])
        self.assertEqual(self.report["decision"], self.lock["decision"])
        self.assertTrue(all(self.report["gates"].values()))
        self.assertEqual(self.lock["failed_gates"], [])
        self.assertEqual(self.lock["decision_resolution"]["integrity"], "passed")
        self.assertIn(
            "42 of 48",
            self.lock["decision_resolution"]["semantic_answer_sufficiency"],
        )

    def test_rows_are_unique_and_attribution_is_exhaustive(self):
        rows = self.report["rows"]
        self.assertEqual(len(rows), 57)
        self.assertEqual(len({row["case_id"] for row in rows}), 57)
        allowed = {
            "model_quality_pass",
            "lexical_answer_available_model_miss",
            "partial_lexical_evidence_inference_or_composition_needed",
            "no_lexical_answer_evidence_in_target_session",
        }
        for model in ("qwen3.5:9b", "qwen3.5:27b"):
            counts = Counter(row["conditions"][model]["attribution"] for row in rows)
            self.assertEqual(sum(counts.values()), 57)
            self.assertTrue(set(counts).issubset(allowed))
            self.assertEqual(
                dict(sorted(counts.items())),
                self.lock["metrics"]["conditions"][model]["attribution_counts"],
            )

    def test_report_excludes_raw_official_and_prediction_payloads(self):
        self.assertFalse(self.report["contains_official_questions"])
        self.assertFalse(self.report["contains_official_answers"])
        self.assertFalse(self.report["contains_source_context_text"])
        self.assertFalse(self.report["contains_raw_predictions"])
        forbidden = {"question", "answer", "source_text", "context", "prediction"}
        for row in self.report["rows"]:
            self.assertFalse(forbidden & set(row))
            for condition in row["conditions"].values():
                self.assertFalse(forbidden & set(condition))

    def test_source_unit_diagnostics_match_rows(self):
        rows = self.report["rows"]
        available = [row for row in rows if row["lexical_oracle"]["official_f1"] >= 0.45]
        misses = [
            row
            for row in rows
            if row["conditions"]["qwen3.5:27b"]["attribution"]
            == "lexical_answer_available_model_miss"
        ]

        def source_unit_counts(selected):
            return dict(
                sorted(
                    Counter(
                        "time_line"
                        if row["lexical_oracle"]["source_unit_index"] == 0
                        else "utterance_line"
                        for row in selected
                    ).items()
                )
            )

        diagnostics = self.lock["posthoc_zero_call_source_unit_diagnostics"]
        self.assertEqual(
            source_unit_counts(available),
            diagnostics["lexical_quality_available_best_source_unit"],
        )
        self.assertEqual(
            source_unit_counts(misses),
            diagnostics["candidate_lexical_available_miss_best_source_unit"],
        )
        self.assertEqual(
            dict(sorted(Counter(row["question_operator"] for row in misses).items())),
            diagnostics["candidate_lexical_available_miss_question_operator"],
        )
        self.assertEqual(
            dict(sorted(Counter(row["evidence_transition"] for row in misses).items())),
            diagnostics["candidate_lexical_available_miss_evidence_transition"],
        )

    def test_authorization_stays_at_deterministic_mechanism_level(self):
        authorization = self.lock["authorization"]
        self.assertEqual(authorization, self.report["authorization"])
        self.assertTrue(
            authorization[
                "preregister_source_disjoint_deterministic_span_selection_mechanism"
            ]
        )
        self.assertFalse(authorization["preregister_fresh_model_generation"])
        self.assertFalse(
            authorization["preregister_full_pipeline_memory_intervention"]
        )
        self.assertFalse(authorization["runtime_change"])
        self.assertFalse(authorization["runtime_shadow"])
        self.assertFalse(authorization["production_enablement"])
        self.assertEqual(self.lock["new_model_calls"], 0)
        self.assertEqual(self.lock["network_calls"], 0)


if __name__ == "__main__":
    unittest.main()
