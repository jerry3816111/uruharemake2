import json
import unittest
from pathlib import Path

from analyze_memory_highlight_span_v2 import (
    CONTROL,
    HIGHLIGHT,
    SPAN,
    build_analysis,
    classify_failure,
    render_markdown,
    verify_report,
)


ROOT = Path(__file__).resolve().parent
REPORT = ROOT / "reports" / "memory_highlight_span_v2_report.json"


class AnalyzeMemoryHighlightSpanV2Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = json.loads(REPORT.read_text(encoding="utf-8"))
        cls.analysis = build_analysis(cls.report)

    def test_frozen_report_and_all_bound_implementation_hashes_verify(self):
        checks, implementation = verify_report(self.report)
        self.assertTrue(all(checks.values()))
        self.assertTrue(all(implementation.values()))

    def test_two_root_failures_are_localized_without_relabeling_results(self):
        categories = {
            (row["case_id"], row["condition"]): row["category"]
            for row in self.analysis["failure_rows"]
        }
        self.assertEqual(
            categories[("dev_therapy_current_time__end", CONTROL)],
            "assistant_acknowledgement_misread_as_user_fact",
        )
        self.assertEqual(
            categories[("transfer_grocery_previous_frequency__middle", HIGHLIGHT)],
            "controller_markup_copied_into_quote",
        )
        self.assertEqual(
            categories[("transfer_grocery_previous_frequency__middle", SPAN)],
            "controller_markup_copied_into_quote",
        )

    def test_control_and_highlight_failures_are_complementary(self):
        complement = self.analysis["paired_complementarity"]
        self.assertEqual(complement["both_pass"], 34)
        self.assertEqual(complement["control_only"], 1)
        self.assertEqual(complement["highlight_only"], 1)
        self.assertEqual(complement.get("neither_pass", 0), 0)
        self.assertEqual(complement["evidence_union_coverage_count"], 36)

    def test_span_contract_is_perfect_conditioned_on_upstream_evidence(self):
        span = self.analysis["span_contract"]
        self.assertEqual(span["upstream_available_count"], 35)
        self.assertEqual(span["valid_when_upstream_available_count"], 35)
        self.assertEqual(span["semantic_when_upstream_available_count"], 35)
        self.assertEqual(span["valid_when_upstream_available_rate"], 1.0)

    def test_verdict_remains_rejection_and_runtime_is_unchanged(self):
        self.assertEqual(self.analysis["decision"], "reject_v2_runtime_integration")
        self.assertFalse(self.report["research_boundary"]["runtime_change_authorized"])
        self.assertFalse(self.report["all_gates_pass"])
        markdown = render_markdown(self.analysis, self.report)
        self.assertIn("Reject V2 runtime integration", markdown)
        self.assertIn("No runtime file was changed", markdown)

    def test_classification_does_not_call_a_semantic_pass_a_failure(self):
        passing = next(
            row
            for row in self.report["results"]
            if row["conditions"][CONTROL]["metrics"]["semantic_case_pass"]
        )
        self.assertEqual(classify_failure(passing, CONTROL), "semantic_pass")


if __name__ == "__main__":
    unittest.main()
