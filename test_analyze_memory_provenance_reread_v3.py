import json
import unittest

from analyze_memory_provenance_reread_v3 import (
    ADAPTIVE,
    CONTROL,
    DEFAULT_REPORT,
    PROVENANCE,
    SPAN,
    build_analysis,
    render_markdown,
)


class AnalyzeMemoryProvenanceRereadV3Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = json.loads(DEFAULT_REPORT.read_text(encoding="utf-8"))
        cls.analysis = build_analysis(cls.report)

    def test_frozen_report_and_metric_audit_verify(self):
        self.assertTrue(all(self.analysis["verification"].values()))
        self.assertTrue(all(self.analysis["implementation_verification"].values()))
        self.assertEqual(
            self.analysis["source_results_sha256"],
            "703e7b2efd20ae7877ec7b464efcc8b533e1a681b9f79c8d67a54045af4ff12d",
        )
        audit = self.analysis["metric_recompute_audit"]
        self.assertEqual(audit["model_calls_made"], 0)
        self.assertFalse(audit["responses_changed"])

    def test_condition_counts_are_exact(self):
        summary = self.analysis["condition_summary"]
        expected = {
            CONTROL: (31, 0, 31),
            PROVENANCE: (31, 12, 43),
            ADAPTIVE: (31, 12, 43),
            SPAN: (27, 12, 39),
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

    def test_provenance_gain_is_only_unanswerable_abstention(self):
        attribution = self.analysis["provenance_gate_attribution"]
        self.assertEqual(attribution["overall_gain_case_count"], 12)
        self.assertEqual(attribution["gain_unanswerable_case_count"], 12)
        self.assertEqual(attribution["gain_answerable_case_count"], 0)
        self.assertTrue(attribution["answerable_failure_sets_identical_to_control"])
        self.assertTrue(
            all(
                row["assistant_event_count"] == 0
                for row in attribution["source_admission"].values()
            )
        )

    def test_reread_and_span_failures_are_localized(self):
        reread = self.analysis["adaptive_reread"]
        self.assertEqual(reread["trigger_count"], 15)
        self.assertEqual(reread["answerable_trigger_count"], 3)
        self.assertEqual(reread["unanswerable_trigger_count"], 12)
        self.assertEqual(reread["recovery_count"], 0)
        self.assertEqual(len(reread["answerable_false_abstentions"]), 3)
        self.assertAlmostEqual(
            reread["cost_delta"]["adaptive_minus_provenance_evidence_recall"],
            1 / 24,
        )

        span = self.analysis["span_contract"]
        self.assertEqual(span["improvement_count"], 2)
        self.assertEqual(span["regression_count"], 6)
        self.assertEqual(len(span["discourse_marker_polarity_regressions"]), 3)
        self.assertEqual(len(span["frequency_scalar_regressions"]), 3)

    def test_report_rejects_runtime_without_overclaim(self):
        self.assertEqual(self.analysis["decision"], "reject_v3_runtime_integration")
        self.assertEqual(
            set(self.analysis["failed_gates"]),
            {
                "adaptive_answerable_false_abstention_rate_equals_zero",
                "span_overall_cognitive_pass_not_lower_than_adaptive",
            },
        )
        markdown = render_markdown(self.analysis)
        self.assertIn("Reject V3 runtime integration", markdown)
        self.assertIn("not memory reasoning", markdown)
        self.assertIn("recovered `0`", markdown)
        self.assertNotIn("promote V3", markdown)


if __name__ == "__main__":
    unittest.main()
