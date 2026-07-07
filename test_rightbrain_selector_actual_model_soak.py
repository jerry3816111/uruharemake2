import json
import unittest
from pathlib import Path

from eval_rightbrain_selector_actual_model_soak_v1 import _build_gate, summarize_cases
from project_paths import RIGHTBRAIN_SELECTOR_ACTUAL_MODEL_SOAK_V1_REPORT_JSON_PATH


class RightBrainSelectorActualModelSoakSummaryTest(unittest.TestCase):
    def test_summary_separates_generation_acceptance_from_shadow_safety(self):
        cases = [
            {
                "shadow_status": "active",
                "shadow_candidate_count": 3,
                "shadow_would_change": True,
                "generated_candidate_count": 3,
                "accepted_candidate_count": 1,
                "initial_rejected_candidate_count": 2,
                "learned_selected_strict_valid": True,
                "learned_surface_contract_pass": True,
                "current_surface_contract_pass": True,
                "learned_selected_was_gate_rejected": False,
                "shadow_visible_output_unchanged": True,
                "model_disabled_reason": "",
                "learned_selected_source": "accepted:initial",
                "model_rejection_reasons": ["unexpected_ascii_leak"],
                "model_accepted_candidates": [{"raw_candidate": "自然な返事"}],
                "model_initial_rejected_candidates": [
                    {"raw_candidate": "今日は无理しない。"},
                    {"raw_candidate": "今日は範�だけ決める。"},
                ],
            },
            {
                "shadow_status": "not_run",
                "shadow_candidate_count": 0,
                "shadow_would_change": False,
                "generated_candidate_count": 0,
                "accepted_candidate_count": 0,
                "initial_rejected_candidate_count": 0,
                "learned_selected_strict_valid": False,
                "learned_surface_contract_pass": False,
                "current_surface_contract_pass": True,
                "learned_selected_was_gate_rejected": False,
                "shadow_visible_output_unchanged": True,
                "model_disabled_reason": "hard_boundary_scene",
                "learned_selected_source": "not_run",
                "model_rejection_reasons": [],
                "model_accepted_candidates": [],
                "model_initial_rejected_candidates": [],
            },
        ]

        summary = summarize_cases(cases, model_loaded=True)

        self.assertEqual(summary["generated_candidate_count"], 3)
        self.assertEqual(summary["raw_candidate_acceptance_rate"], 0.333333)
        self.assertEqual(summary["shadow_active_case_count"], 1)
        self.assertEqual(summary["learned_strict_valid_rate"], 1.0)
        self.assertEqual(summary["shadow_disagreement_count"], 1)
        self.assertEqual(summary["shadow_visible_output_unchanged_rate"], 1.0)
        self.assertEqual(summary["disabled_reason_counts"], {"hard_boundary_scene": 1})
        self.assertEqual(summary["simplified_wu_generated_count"], 1)
        self.assertEqual(summary["simplified_wu_accepted_count"], 0)
        self.assertEqual(summary["unicode_replacement_generated_count"], 1)
        self.assertEqual(summary["unicode_replacement_accepted_count"], 0)
        gate = _build_gate(summary)
        self.assertTrue(gate["actual_simplified_wu_candidate_was_never_accepted"])
        self.assertTrue(gate["actual_unicode_replacement_candidate_was_never_accepted"])

    def test_recorded_actual_model_run_proves_polluted_candidates_are_rejected(self):
        report = json.loads(
            Path(RIGHTBRAIN_SELECTOR_ACTUAL_MODEL_SOAK_V1_REPORT_JSON_PATH).read_text(encoding="utf-8")
        )

        self.assertTrue(report["gate_passed"], msg=report["gate"])
        self.assertEqual(report["summary"]["generated_candidate_count"], 30)
        self.assertEqual(report["summary"]["simplified_wu_generated_count"], 1)
        self.assertEqual(report["summary"]["simplified_wu_accepted_count"], 0)
        self.assertEqual(report["summary"]["unicode_replacement_generated_count"], 1)
        self.assertEqual(report["summary"]["unicode_replacement_accepted_count"], 0)
        private_case = next(case for case in report["cases"] if case["id"] == "private_do_not_mention")
        self.assertNotIn("无", private_case["current_reply"])


if __name__ == "__main__":
    unittest.main()
