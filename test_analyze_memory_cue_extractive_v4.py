import json
import unittest

from analyze_memory_cue_extractive_v4 import (
    CONTROL,
    CUE,
    DEFAULT_REPORT,
    PROVENANCE,
    REREAD,
    build_analysis,
    render_markdown,
)


class AnalyzeMemoryCueExtractiveV4Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = json.loads(DEFAULT_REPORT.read_text(encoding="utf-8"))
        cls.analysis = build_analysis(cls.report)

    def test_frozen_report_and_implementation_verify(self):
        self.assertTrue(all(self.analysis["verification"].values()))
        self.assertTrue(all(self.analysis["implementation_verification"].values()))
        self.assertEqual(
            self.analysis["source_results_sha256"],
            "fb5745139d4557363e03676332770512f216eb137f3976f20b45942c2e5e8f98",
        )

    def test_condition_counts_are_exact(self):
        summary = self.analysis["condition_summary"]
        expected = {
            CONTROL: (28, 0, 28),
            PROVENANCE: (25, 12, 37),
            REREAD: (26, 12, 38),
            CUE: (26, 12, 38),
        }
        for condition, counts in expected.items():
            self.assertEqual(
                (
                    summary[condition]["answerable_pass_count"],
                    summary[condition]["unanswerable_abstention_count"],
                    summary[condition]["overall_pass_count"],
                ),
                counts,
            )

    def test_cue_gain_is_one_recovery_without_regression(self):
        pair = self.analysis["paired_effects"]["cue_vs_provenance"]
        self.assertEqual(pair["treatment_only"], 1)
        self.assertEqual(pair["control_only"], 0)
        self.assertEqual(
            pair["treatment_win_case_ids"],
            ["transfer_dentist_current_time__end"],
        )
        formal = self.analysis["paired_effects"]["cue_vs_provenance_formal"]
        self.assertAlmostEqual(formal["delta"], 1 / 48)
        self.assertEqual(formal["mcnemar"]["p_value"], 1.0)
        self.assertLessEqual(formal["paired_bootstrap_95_ci"][0], 0.0)

    def test_fallback_attribution_and_source_integrity_are_exact(self):
        fallback = self.analysis["fallback_attribution"]
        self.assertEqual(fallback["trigger_count"], 16)
        self.assertEqual(fallback["answerable_trigger_count"], 4)
        self.assertEqual(fallback["unanswerable_trigger_count"], 12)
        self.assertEqual(fallback["candidate_sufficient_count"], 1)
        self.assertEqual(fallback["cue_recovery_count"], 1)
        self.assertEqual(fallback["reread_recovery_count"], 1)
        self.assertEqual(fallback["exact_user_source_rate"], 1.0)
        self.assertEqual(fallback["assistant_admission_rate"], 0.0)

    def test_cue_matches_reread_accuracy_with_lower_cost(self):
        comparison = self.analysis["cue_vs_reread"]
        self.assertTrue(comparison["semantic_pass_vectors_identical"])
        self.assertEqual(comparison["response_difference_count"], 1)
        self.assertGreater(comparison["mean_latency_seconds_saved"], 2.0)
        self.assertGreater(comparison["mean_prompt_tokens_saved"], 300.0)

    def test_remaining_failures_are_not_hidden(self):
        failures = self.analysis["remaining_answerable_failures"]
        self.assertEqual(failures["count"], 10)
        self.assertEqual(
            {
                key: row["count"] for key, row in failures["groups"].items()
            },
            {
                "current_count_scope_mismatch": 3,
                "previous_frequency_normalization": 3,
                "historical_yes_no_answer_contract": 4,
            },
        )

    def test_markdown_preserves_evidence_boundary(self):
        markdown = render_markdown(self.analysis)
        self.assertIn("Runtime integration remains unauthorized", markdown)
        self.assertIn("weak positive development evidence", markdown)
        self.assertIn("not statistically persuasive", markdown)
        self.assertIn("a cheaper fallback, not a more accurate fallback", markdown)
        self.assertNotIn("promote to runtime", markdown)


if __name__ == "__main__":
    unittest.main()
