import copy
import unittest

from eval_rightbrain_plan_surface_boundary_decision import build_report


def _human_report():
    return {
        "promotion_recommended": True,
        "independent_variable": "plan boundary",
        "controlled_variables": {"strict_task_count": 12, "strict_candidate_count": 48},
        "baseline": {
            "top_score_hit_rate": 0.4,
            "selected_mean_naturalness_1_5": 2.8,
            "selected_mean_semantic_1_5": 2.7,
            "chat_ready_yes_rate": 0.3,
        },
        "candidate": {
            "top_score_hit_rate": 0.6,
            "selected_mean_naturalness_1_5": 3.2,
            "selected_mean_semantic_1_5": 3.0,
            "chat_ready_yes_rate": 0.5,
        },
    }


def _runtime_report():
    return {
        "promotion_recommended": False,
        "runtime_shadow_safety_pass": True,
        "seeds": [1, 2],
        "runtime_gate_evidence": {
            "raw_candidate_control": {
                "all_identical": True,
                "candidate_raw_candidate_count": 60,
            },
            "fixed_final_surface_issue_count": 0,
            "introduced_final_surface_issue_count": 0,
        },
        "aggregate": {
            "promoted": {"case_count": 22, "final_quality_pass_rate": 1.0},
        },
    }


def _selector_report():
    return {"gate": {"human_preference_takeover_recommended": False}}


class RightBrainPlanSurfaceBoundaryDecisionTest(unittest.TestCase):
    def test_adopts_human_gain_with_actual_model_safety_and_selector_block(self):
        report = build_report(_human_report(), _runtime_report(), _selector_report())

        self.assertTrue(report["adopt_runtime_boundary"])
        self.assertFalse(report["replace_v10_adapter"])
        self.assertFalse(report["enable_learned_selector"])

    def test_rejects_when_actual_model_shadow_introduces_surface_issue(self):
        runtime = copy.deepcopy(_runtime_report())
        runtime["runtime_shadow_safety_pass"] = False
        runtime["runtime_gate_evidence"]["introduced_final_surface_issue_count"] = 1

        report = build_report(_human_report(), runtime, _selector_report())

        self.assertFalse(report["adopt_runtime_boundary"])

    def test_rejects_scope_when_selector_takeover_gate_changes(self):
        selector = {"gate": {"human_preference_takeover_recommended": True}}

        report = build_report(_human_report(), _runtime_report(), selector)

        self.assertFalse(report["gates"]["learned_selector_remains_observe_only"])
        self.assertFalse(report["adopt_runtime_boundary"])


if __name__ == "__main__":
    unittest.main()
