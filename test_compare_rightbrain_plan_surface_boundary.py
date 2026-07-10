import unittest

from compare_rightbrain_plan_surface_boundary import build_report


def _report(heuristic_review, heuristic_score, heuristic_naturalness, *, learned="learned", s0="s0"):
    def strategy(review_id, score, naturalness):
        return {
            "top_score_hit_rate": 1.0 if score >= 4 else 0.0,
            "selected_mean_human_score_1_5": float(score),
            "selected_mean_naturalness_1_5": float(naturalness),
            "selected_mean_semantic_1_5": float(score),
            "chat_ready_yes_rate": 1.0 if score >= 3 else 0.0,
            "bottom_score_selection_rate": 0.0,
            "selections": [
                {
                    "task_id": "task-1",
                    "selected_review_id": review_id,
                    "selected_output_text": review_id,
                    "human_mean_score_1_5": float(score),
                    "human_naturalness_1_5": float(naturalness),
                }
            ],
        }

    return {
        "data": {
            "strict_task_count": 1,
            "strict_candidate_count": 4,
            "overlapping_task_ids": [],
            "source_summaries": [{"source_id": "source", "hashes": {"ratings": "same"}}],
        },
        "strict_no_exact_text_overlap": {
            "strategies": {
                "learned_selector_v1": strategy(learned, 3, 3),
                "current_runtime_heuristic_proxy": strategy(
                    heuristic_review,
                    heuristic_score,
                    heuristic_naturalness,
                ),
                "s0_full_system_candidate": strategy(s0, 4, 4),
            }
        },
    }


class CompareRightBrainPlanSurfaceBoundaryTest(unittest.TestCase):
    def test_recommends_matched_naturalness_and_top_hit_gain(self):
        baseline = _report("plan", 2, 2)
        candidate = _report("direct", 4, 4)

        report = build_report(baseline, candidate, baseline_ref="base")

        self.assertTrue(report["promotion_recommended"])
        self.assertEqual(report["changed_selection_count"], 1)
        self.assertGreater(report["deltas"]["selected_mean_naturalness_1_5"], 0)

    def test_rejects_when_control_selector_changes(self):
        baseline = _report("plan", 2, 2, learned="learned-old")
        candidate = _report("direct", 4, 4, learned="learned-new")

        with self.assertRaisesRegex(ValueError, "learned_selector_v1"):
            build_report(baseline, candidate)

    def test_rejects_when_naturalness_does_not_improve(self):
        baseline = _report("old", 2, 3)
        candidate = _report("new", 4, 3)

        report = build_report(baseline, candidate)

        self.assertFalse(report["gate"]["mean_naturalness_improved"])
        self.assertFalse(report["promotion_recommended"])


if __name__ == "__main__":
    unittest.main()
