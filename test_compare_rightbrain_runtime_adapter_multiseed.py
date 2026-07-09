import tempfile
import unittest
from pathlib import Path

from compare_rightbrain_runtime_adapter_multiseed import build_report, write_markdown


def _report(adapter, seed, accepted, selected, *, generated=30, quality=1.0, reasons=None):
    return {
        "scope": "rightbrain_model_blend_surface_holdout_eval",
        "adapter_ref": adapter,
        "load_model": True,
        "seed": seed,
        "candidate_count_per_case": 3,
        "runtime_contract_version": "plan_surface_contract_v1",
        "case_eval_duration_seconds": 20.0,
        "summary": {
            "case_count": 11,
            "generated_candidate_count": generated,
            "accepted_candidate_count": accepted,
            "raw_candidate_acceptance_rate": accepted / generated,
            "model_selected_case_count": selected,
            "model_selected_case_rate": selected / 11,
            "final_quality_pass_rate": quality,
            "final_language_clean_rate": 1.0,
            "final_forbidden_surface_leak_rate": 0.0,
            "final_generic_template_hit_rate": 0.0,
        },
        "cases": [
            {
                "id": "same",
                "category": "support",
                "accepted_candidate_count": accepted,
                "selected_source": "model" if selected else "deterministic",
                "model_rejection_reasons": list(reasons or []),
                "deterministic_reply": "今日は休め。",
                "final_reply": "今日は休め。",
            }
        ],
    }


class RuntimeAdapterMultiseedTest(unittest.TestCase):
    def test_recommends_only_repeated_noninferior_quality_preserving_gain(self):
        baselines = [_report("old", 1, 5, 0), _report("old", 2, 9, 1)]
        promoted = [_report("new", 1, 8, 1), _report("new", 2, 10, 2)]

        report = build_report(baselines, promoted)

        self.assertTrue(report["promotion_recommended"])
        self.assertEqual(report["aggregate"]["baseline"]["accepted_candidate_count"], 14)
        self.assertEqual(report["aggregate"]["promoted"]["accepted_candidate_count"], 18)
        self.assertEqual(report["aggregate"]["raw_candidate_acceptance_delta"], 0.0667)

    def test_same_adapter_gain_is_reported_as_runtime_gate_adoption(self):
        baselines = [_report("same-adapter", 1, 5, 1), _report("same-adapter", 2, 9, 2)]
        promoted = [_report("same-adapter", 1, 8, 1), _report("same-adapter", 2, 10, 2)]

        report = build_report(baselines, promoted)

        self.assertTrue(report["promotion_recommended"])
        self.assertEqual(report["comparison_mode"], "same_adapter_runtime_gate_check")
        self.assertIn("建議採用 runtime gate 改動", report["decision_zh"])
        self.assertIn("模型接管數維持 3", report["decision_zh"])

    def test_rejects_promotion_when_one_seed_regresses(self):
        baselines = [_report("old", 1, 5, 0), _report("old", 2, 9, 1)]
        promoted = [_report("new", 1, 4, 1), _report("new", 2, 12, 2)]

        report = build_report(baselines, promoted)

        self.assertFalse(report["all_seed_noninferior"])
        self.assertFalse(report["promotion_recommended"])

    def test_rejects_promotion_when_final_quality_drops(self):
        baselines = [_report("old", 1, 5, 0), _report("old", 2, 9, 1)]
        promoted = [
            _report("new", 1, 8, 1),
            _report("new", 2, 10, 2, quality=0.9),
        ]

        report = build_report(baselines, promoted)

        self.assertFalse(report["quality_guard_pass"])
        self.assertFalse(report["promotion_recommended"])

    def test_curriculum_holdout_overlap_blocks_promotion_even_when_metrics_pass(self):
        baselines = [_report("old", 1, 5, 0), _report("old", 2, 9, 1)]
        promoted = [_report("new", 1, 8, 1), _report("new", 2, 10, 2)]
        curriculum = [
            {
                "source_case_id": "same",
                "messages": [
                    {"role": "system", "content": "x"},
                    {"role": "user", "content": "{}"},
                    {"role": "assistant", "content": "今日は休め。"},
                ],
            }
        ]

        report = build_report(baselines, promoted, curriculum=curriculum)

        self.assertTrue(report["metric_gate_pass"])
        self.assertTrue(report["data_boundary"]["diagnostic_only"])
        self.assertEqual(report["data_boundary"]["holdout_case_overlap_count"], 1)
        self.assertEqual(report["data_boundary"]["holdout_target_overlap_count"], 1)
        self.assertFalse(report["promotion_recommended"])

    def test_curriculum_summary_report_can_be_rendered(self):
        baselines = [_report("old", 1, 5, 0), _report("old", 2, 9, 1)]
        promoted = [_report("new", 1, 8, 1), _report("new", 2, 10, 2)]
        curriculum_report = {
            "curriculum_row_count": 32,
            "data_boundary": {
                "holdout_case_count": 11,
                "training_source_case_count": 8,
                "holdout_case_overlap_count": 0,
                "holdout_case_overlap_ids": [],
                "holdout_target_overlap_count": 0,
                "holdout_target_overlap_examples": [],
                "diagnostic_only": False,
            },
        }

        report = build_report(baselines, promoted, curriculum=curriculum_report)

        self.assertEqual(report["data_boundary"]["training_row_count"], 32)
        self.assertIn("No holdout case", report["data_boundary"]["boundary_reason"])
        with tempfile.TemporaryDirectory() as tmpdir:
            output = Path(tmpdir) / "report.md"
            write_markdown(report, output)
            self.assertIn("training rows | 32", output.read_text(encoding="utf-8"))

    def test_case_diagnostics_surface_regressed_cases_and_new_reasons(self):
        baselines = [_report("old", 1, 5, 1, reasons=["unexpected_ascii_leak"])]
        promoted = [
            _report(
                "new",
                1,
                2,
                0,
                reasons=["unexpected_ascii_leak", "polite_tone_drift"],
            )
        ]

        report = build_report(baselines, promoted)

        self.assertEqual(report["case_diagnostics"][0]["id"], "same")
        self.assertEqual(report["case_diagnostics"][0]["accepted_candidate_delta"], -3)
        self.assertEqual(report["case_diagnostics"][0]["model_selected_seed_delta"], -1)
        self.assertEqual(report["case_diagnostics"][0]["new_rejection_reasons"], ["polite_tone_drift"])

    def test_rejection_reason_deltas_group_semantic_slot_families(self):
        baselines = [
            _report(
                "old",
                1,
                5,
                1,
                reasons=["unexpected_ascii_leak", "semantic_slots_missing:1/3"],
            ),
            _report("old", 2, 5, 0, reasons=["semantic_slots_missing:2/3"]),
        ]
        promoted = [
            _report(
                "new",
                1,
                3,
                0,
                reasons=[
                    "unexpected_ascii_leak",
                    "polite_tone_drift",
                    "semantic_slots_missing:0/3",
                ],
            ),
            _report(
                "new",
                2,
                4,
                0,
                reasons=["polite_tone_drift", "semantic_slots_missing:0/3"],
            ),
        ]

        report = build_report(baselines, promoted)

        exact = {row["reason"]: row for row in report["rejection_reason_deltas"]["exact"]}
        family = {row["reason"]: row for row in report["rejection_reason_deltas"]["family"]}
        self.assertEqual(exact["polite_tone_drift"]["delta"], 2)
        self.assertEqual(exact["semantic_slots_missing:0/3"]["delta"], 2)
        self.assertEqual(exact["semantic_slots_missing:1/3"]["delta"], -1)
        self.assertNotIn("semantic_slots_missing", family)
        self.assertEqual(family["polite_tone_drift"]["direction"], "regressed")


if __name__ == "__main__":
    unittest.main()
