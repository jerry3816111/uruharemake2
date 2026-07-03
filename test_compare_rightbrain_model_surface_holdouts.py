import unittest

from compare_rightbrain_model_surface_holdouts import build_comparison


def _report(
    adapter,
    accepted,
    reasons=None,
    *,
    initial_accepted=None,
    repair_enabled=False,
    repair_attempts=0,
    repair_accepted=0,
):
    reasons = reasons or []
    initial_accepted = accepted if initial_accepted is None else initial_accepted
    return {
        "scope": "rightbrain_model_blend_surface_holdout_eval",
        "adapter_ref": adapter,
        "load_model": True,
        "seed": 20260624,
        "candidate_count_per_case": 1,
        "repair_enabled": repair_enabled,
        "runtime_contract_version": "plan_surface_contract_v1",
        "case_eval_duration_seconds": 10.0 + repair_attempts,
        "summary": {
            "generated_candidate_count": 10,
            "initial_accepted_candidate_count": initial_accepted,
            "accepted_candidate_count": accepted,
            "raw_candidate_acceptance_rate": initial_accepted / 10,
            "repair_attempt_count": repair_attempts,
            "repair_accepted_count": repair_accepted,
            "repair_success_rate": (
                repair_accepted / repair_attempts if repair_attempts else None
            ),
            "effective_candidate_acceptance_rate": accepted / 10,
            "model_selected_case_count": 1,
            "model_selected_case_rate": 1 / 11,
            "final_quality_pass_rate": 1.0,
            "final_language_clean_rate": 1.0,
            "final_forbidden_surface_leak_rate": 0.0,
            "final_generic_template_hit_rate": 0.0,
            "final_normalized_duplicate_reply_rate": 0.0,
        },
        "cases": [
            {
                "id": "support_case",
                "category": "support",
                "accepted_candidate_count": int(accepted > 4),
                "model_rejection_reasons": reasons,
                "selected_source": "deterministic",
            }
        ],
    }


class CompareRightBrainModelSurfaceHoldoutsTest(unittest.TestCase):
    def setUp(self):
        self.training = {
            "dataset_ref": "rightbrain_repair_curriculum_v1.json",
            "rows": 1061,
            "supplemental_rows": 36,
            "optimizer_updates": 15,
            "nonfinite_skips": 0,
            "initial_eval_loss_probe": 3.06,
            "sampled_eval_loss": 3.05,
            "final_train_loss": 3.21,
            "learning_rate": 3e-7,
            "init_adapter_ref": "v8",
            "output_adapter_ref": "v11",
        }

    def test_builds_matched_delta_and_newly_accepted_case(self):
        baseline = _report(
            "v9",
            4,
            ["polite_tone_drift", "semantic_slots_missing:2/3"],
        )
        trained = _report("v10", 5)

        report = build_comparison(baseline, trained, self.training)

        acceptance = next(
            row
            for row in report["metric_rows"]
            if row["metric"] == "raw_candidate_acceptance_rate"
        )
        self.assertEqual(acceptance["delta"], 0.1)
        self.assertEqual(report["case_diffs"][0]["id"], "support_case")
        self.assertTrue(report["case_diffs"][0]["newly_accepted"])
        self.assertEqual(
            report["case_diffs"][0]["resolved_rejection_reasons"],
            ["polite_tone_drift", "semantic_slots_missing:2/3"],
        )

    def test_rejects_unmatched_seed(self):
        baseline = _report("v9", 4)
        trained = _report("v10", 5)
        trained["seed"] = 99

        with self.assertRaisesRegex(ValueError, "seed"):
            build_comparison(baseline, trained, self.training)

    def test_reports_repair_as_single_independent_variable(self):
        baseline = _report("v10", 5, initial_accepted=5)
        trained = _report(
            "v10",
            8,
            initial_accepted=5,
            repair_enabled=True,
            repair_attempts=5,
            repair_accepted=3,
        )

        report = build_comparison(baseline, trained, self.training)

        self.assertEqual(
            report["independent_variable"],
            {
                "baseline_repair_enabled": False,
                "trained_repair_enabled": True,
            },
        )
        self.assertIn("首次 raw 通過率維持 50.0%", report["conclusion_zh"])
        self.assertIn("50.0% 變為 80.0%", report["conclusion_zh"])
        self.assertEqual(report["runtime"]["case_eval_duration_delta_seconds"], 5.0)

    def test_rejects_non_model_baseline(self):
        baseline = _report("v9", 4)
        trained = _report("v10", 5)
        baseline["load_model"] = False

        with self.assertRaisesRegex(ValueError, "model-loaded"):
            build_comparison(baseline, trained, self.training)

    def test_reports_trained_repair_delta_when_both_runs_enable_repair(self):
        baseline = _report(
            "v8",
            4,
            initial_accepted=4,
            repair_enabled=True,
            repair_attempts=6,
            repair_accepted=0,
        )
        trained = _report(
            "v11",
            7,
            initial_accepted=5,
            repair_enabled=True,
            repair_attempts=5,
            repair_accepted=2,
        )

        report = build_comparison(baseline, trained, self.training)

        self.assertIn("repair 成功數由 0/6 變為 2/5", report["conclusion_zh"])
        self.assertIn("40.0% 變為 70.0%", report["conclusion_zh"])
        self.assertNotIn("不應預設開啟", report["conclusion_zh"])

    def test_carries_curriculum_leakage_boundary(self):
        baseline = _report("v8", 4)
        trained = _report("v11", 5)
        curriculum = {
            "curriculum_row_count": 720,
            "holdout_case_count": 11,
            "holdout_user_input_overlap_count": 0,
            "holdout_contract_overlap_count": 0,
            "holdout_target_overlap_count": 0,
            "runtime_schema": {"previous_draft_in_training_prompt": False},
        }

        report = build_comparison(
            baseline,
            trained,
            self.training,
            curriculum,
        )

        self.assertEqual(report["data_boundary"]["curriculum_row_count"], 720)
        self.assertEqual(report["data_boundary"]["holdout_contract_overlap_count"], 0)
        self.assertFalse(
            report["data_boundary"]["previous_draft_in_training_prompt"]
        )


if __name__ == "__main__":
    unittest.main()
