import unittest

from eval_rightbrain_model_surface_holdout import build_report
from uruha_brain_mac import RightBrain


class RightBrainModelSurfaceHoldoutTest(unittest.TestCase):
    def test_no_model_run_is_explicit_fallback_baseline(self):
        report = build_report(load_model=False, candidate_count=1)
        summary = report["summary"]

        self.assertFalse(report["load_model"])
        self.assertFalse(summary["model_loaded"])
        self.assertEqual(summary["generated_candidate_count"], 0)
        self.assertEqual(summary["accepted_candidate_count"], 0)
        self.assertEqual(summary["model_selected_case_rate"], 0.0)
        self.assertEqual(summary["raw_candidate_acceptance_rate"], None)

    def test_final_quality_gate_matches_surface_holdout_without_model(self):
        report = build_report(load_model=False, candidate_count=1)
        summary = report["summary"]

        self.assertEqual(summary["case_count"], 11)
        self.assertEqual(summary["deterministic_quality_pass_rate"], 1.0)
        self.assertEqual(summary["final_quality_pass_rate"], 1.0)
        self.assertEqual(summary["final_language_clean_rate"], 1.0)
        self.assertEqual(summary["final_forbidden_surface_leak_rate"], 0.0)
        self.assertEqual(summary["final_generic_template_hit_rate"], 0.0)

    def test_report_keeps_deterministic_and_final_replies_separate(self):
        report = build_report(load_model=False, candidate_count=1)
        row = report["cases"][0]

        self.assertIn("deterministic_reply", row)
        self.assertIn("final_reply", row)
        self.assertIn("deterministic_quality", row)
        self.assertIn("final_quality", row)
        self.assertEqual(row["selected_source"], "deterministic")
        self.assertTrue(row["final_quality_pass"])

    def test_explicit_required_marker_groups_feed_model_contract(self):
        rightbrain = RightBrain(load_model=False)
        rightbrain.model_blend_enabled = True
        rightbrain.model = object()
        rightbrain.tokenizer = object()
        logic = {
            "required_marker_groups": [["既読", "返事"], ["理由", "分から"]],
            "human_speech_plan": {"dialogue_act": "emotional_containment"},
        }

        self.assertEqual(
            rightbrain._model_required_semantic_groups(logic),
            [("既読", "返事"), ("理由", "分から")],
        )
        self.assertEqual(rightbrain._model_surface_disabled_reason(logic), "")


if __name__ == "__main__":
    unittest.main()
