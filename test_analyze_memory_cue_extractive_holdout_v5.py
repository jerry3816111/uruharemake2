import json
import unittest

from analyze_memory_cue_extractive_holdout_v5 import (
    CONTROL,
    CUE,
    DEFAULT_REPORT,
    PROVENANCE,
    REREAD,
    build_analysis,
    render_markdown,
)


class AnalyzeMemoryCueExtractiveHoldoutV5Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = json.loads(DEFAULT_REPORT.read_text(encoding="utf-8"))
        cls.analysis = build_analysis(cls.report)

    def test_frozen_report_and_implementation_verify(self):
        self.assertTrue(all(self.analysis["verification"].values()))
        self.assertTrue(all(self.analysis["implementation_verification"].values()))
        self.assertEqual(
            self.analysis["source_results_sha256"],
            "36af4799b6da4d6eb75a179e79ef7448f696e4e1f4971f91d72fc3d178f3bd1d",
        )

    def test_condition_counts_are_exact(self):
        summary = self.analysis["condition_summary"]
        expected = {
            CONTROL: (42, 0, 42),
            PROVENANCE: (36, 18, 54),
            REREAD: (36, 17, 53),
            CUE: (38, 18, 56),
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

    def test_recovery_is_local_not_broad(self):
        pair = self.analysis["paired_effects"]["cue_vs_provenance"]
        self.assertEqual(pair["treatment_only"], 2)
        self.assertEqual(pair["control_only"], 0)
        fallback = self.analysis["fallback_attribution"]
        self.assertEqual(fallback["semantic_recovery_count"], 2)
        self.assertEqual(fallback["distinct_recovered_scenario_count"], 1)
        self.assertEqual(fallback["recovery_splits"], ["holdout_b"])
        self.assertEqual(
            self.analysis["failed_preregistered_gates"],
            [
                "cue_vs_provenance_distinct_recovered_scenario_count_at_least_two",
                "cue_recovery_represented_in_both_holdout_splits",
            ],
        )

    def test_fallback_attribution_and_layered_safety_are_exact(self):
        fallback = self.analysis["fallback_attribution"]
        self.assertEqual(fallback["trigger_count"], 26)
        self.assertEqual(fallback["answerable_trigger_count"], 8)
        self.assertEqual(fallback["unanswerable_trigger_count"], 18)
        self.assertEqual(fallback["candidate_sufficient_count"], 8)
        self.assertEqual(
            fallback["candidate_gate_false_sufficient_unanswerable_count"], 6
        )
        self.assertEqual(
            fallback["final_abstention_after_false_sufficient_gate_count"], 6
        )
        self.assertEqual(fallback["candidate_exact_user_source_rate"], 1.0)
        self.assertEqual(fallback["candidate_assistant_admission_rate"], 0.0)

    def test_cue_beats_reread_locally_with_lower_cost(self):
        pair = self.analysis["paired_effects"]["cue_vs_reread"]
        self.assertEqual(pair["treatment_only"], 3)
        self.assertEqual(pair["control_only"], 0)
        efficiency = self.analysis["cue_vs_reread_efficiency"]
        self.assertGreater(efficiency["mean_latency_seconds_saved"], 3.5)
        self.assertGreater(efficiency["mean_prompt_tokens_saved"], 390.0)

    def test_remaining_failures_are_separated_by_layer(self):
        failures = self.analysis["remaining_answerable_failures"]
        self.assertEqual(failures["count"], 16)
        self.assertEqual(
            failures["counts"],
            {
                "answer_realization_incomplete": 7,
                "candidate_sufficiency_false_negative": 6,
                "exact_span_order_sensitivity": 3,
            },
        )

    def test_markdown_preserves_negative_decision_and_score_boundary(self):
        markdown = render_markdown(self.analysis)
        self.assertIn("不進入正式聊天 runtime", markdown)
        self.assertIn("未達預註冊的泛化廣度", markdown)
        self.assertIn("正式分數不回改", markdown)
        self.assertIn("安全不是單一 gate 的功勞", markdown)
        self.assertNotIn("進入正式 runtime", markdown)


if __name__ == "__main__":
    unittest.main()
