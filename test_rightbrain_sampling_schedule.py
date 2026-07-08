import json
import unittest
from pathlib import Path

from eval_rightbrain_sampling_schedule_v1 import (
    SCHEDULES,
    select_schedule,
    summarize_schedule,
    validate_schedules,
)
from project_paths import (
    RIGHTBRAIN_SAMPLING_SCHEDULE_ABLATION_V1_REPORT_JSON_PATH,
    RIGHTBRAIN_SAMPLING_SCHEDULE_NATURALNESS_AUDIT_V1_JSON_PATH,
)


def _case(accepted, selected="deterministic", final_pass=True, reasons=None):
    return {
        "generated_candidate_count": 3,
        "accepted_candidate_count": len(accepted),
        "accepted_candidates": [{"normalized_reply": text} for text in accepted],
        "rejected_candidates": [
            {"rejection_reasons": row}
            for row in (reasons or [])
        ],
        "selected_source": selected,
        "final_quality_pass": final_pass,
        "final_quality": {"language_clean": final_pass},
    }


class RightBrainSamplingScheduleTest(unittest.TestCase):
    def test_schedule_shapes_are_valid(self):
        self.assertIs(validate_schedules(SCHEDULES), SCHEDULES)

    def test_summary_separates_language_and_semantic_rejections(self):
        summary = summarize_schedule([
            _case(
                ["一つ目"],
                selected="model",
                reasons=[["unexpected_ascii_leak"], ["semantic_slots_missing:0/1"]],
            ),
            _case(
                ["二つ目", "二つ目"],
                reasons=[["nonstandard_cjk_surface", "semantic_slots_missing:1/2"]],
            ),
        ])
        self.assertEqual(summary["generated_candidate_count"], 6)
        self.assertEqual(summary["accepted_candidate_count"], 3)
        self.assertEqual(summary["raw_candidate_acceptance_rate"], 0.5)
        self.assertEqual(summary["candidate_case_coverage_count"], 2)
        self.assertEqual(summary["model_selected_case_count"], 1)
        self.assertAlmostEqual(summary["accepted_duplicate_rate"], 1 / 3, places=6)
        self.assertEqual(summary["language_rejected_candidate_count"], 2)
        self.assertEqual(summary["semantic_rejected_candidate_count"], 2)

    def test_decision_requires_gain_without_quality_or_diversity_regression(self):
        baseline = {
            "raw_candidate_acceptance_rate": 0.2,
            "candidate_case_coverage_count": 4,
            "model_selected_case_count": 1,
            "final_quality_pass_rate": 1.0,
            "final_language_clean_rate": 1.0,
            "accepted_duplicate_rate": 0.0,
            "accepted_candidate_count": 6,
            "semantic_rejected_candidate_count": 10,
        }
        winner = dict(baseline)
        winner.update({
            "raw_candidate_acceptance_rate": 0.4,
            "candidate_case_coverage_count": 6,
            "model_selected_case_count": 2,
            "accepted_candidate_count": 12,
            "semantic_rejected_candidate_count": 6,
        })
        duplicate_regression = dict(winner)
        duplicate_regression["accepted_duplicate_rate"] = 0.2
        decision = select_schedule({
            "runtime_baseline": {"summary": baseline},
            "balanced": {"summary": winner},
            "conservative": {"summary": duplicate_regression},
        })
        self.assertEqual(decision["recommended_schedule"], "balanced")
        self.assertTrue(decision["independent_validation_recommended"])
        self.assertTrue(decision["comparisons"]["balanced"]["eligible_for_runtime_validation"])
        self.assertFalse(decision["comparisons"]["conservative"]["eligible_for_runtime_validation"])

    def test_recorded_naturalness_audit_matches_outputs_and_vetoes_runtime_change(self):
        report = json.loads(
            Path(RIGHTBRAIN_SAMPLING_SCHEDULE_ABLATION_V1_REPORT_JSON_PATH).read_text(encoding="utf-8")
        )
        audit = json.loads(
            Path(RIGHTBRAIN_SAMPLING_SCHEDULE_NATURALNESS_AUDIT_V1_JSON_PATH).read_text(encoding="utf-8")
        )
        source_cases = {
            case["id"]: case["final_reply"]
            for case in report["schedule_results"][audit["schedule"]]["cases"]
        }
        audited_cases = {case["id"]: case for case in audit["cases"]}
        self.assertEqual(set(audited_cases), set(source_cases))
        for case_id, reply in source_cases.items():
            self.assertEqual(audited_cases[case_id]["reply"], reply)
        pass_count = sum(case["verdict"] == "pass" for case in audited_cases.values())
        failure_count = sum(case["verdict"] == "fail" for case in audited_cases.values())
        self.assertEqual(pass_count, audit["pass_count"])
        self.assertEqual(failure_count, audit["failure_count"])
        self.assertEqual(audit["pass_rate"], round(pass_count / len(audited_cases), 6))
        self.assertFalse(audit["runtime_change_approved"])


if __name__ == "__main__":
    unittest.main()
