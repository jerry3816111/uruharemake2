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

    def test_explicit_memory_anchor_becomes_model_contract(self):
        rightbrain = RightBrain(load_model=False)
        rightbrain.model_blend_enabled = True
        rightbrain.model = object()
        rightbrain.tokenizer = object()
        logic = {
            "memory_use_expected": True,
            "memory_speakability": "explicit_ok",
            "memory_anchor": {
                "jp_anchor": "最近は胃が弱い",
                "terms": ["最近は胃が弱い", "胃が弱い", "coffee", "胃不舒服"],
            },
            "core_message_jp": "最近は胃が弱いことを踏まえて、コーヒーは控えめにする",
            "human_speech_plan": {"content_units": ["最近の体調を踏まえる"]},
        }

        groups = rightbrain._model_required_semantic_groups(logic)

        self.assertIn(("最近は胃が弱い", "胃が弱い"), groups)
        self.assertIn(("コーヒー", "珈琲"), groups)
        self.assertIn(("控えめ", "少なめ", "少し", "やめ", "避け"), groups)
        self.assertEqual(rightbrain._model_surface_disabled_reason(logic), "")

    def test_background_memory_anchor_is_gate_forbidden_not_required(self):
        rightbrain = RightBrain(load_model=False)
        rightbrain.model_blend_enabled = True
        rightbrain.model = object()
        rightbrain.tokenizer = object()
        logic = {
            "memory_use_expected": False,
            "memory_speakability": "background_only",
            "memory_anchor": {
                "jp_anchor": "家庭の話",
                "terms": ["家庭の話", "家庭壓力", "家人"],
            },
            "core_message_jp": "責めずに、今日は負荷を下げる方向へ寄せる",
        }

        groups = rightbrain._model_required_semantic_groups(logic)
        reasons = rightbrain._model_candidate_rejection_reasons(
            "家庭の話があるから今日は休め。",
            logic,
            80,
        )

        self.assertNotIn(("家庭の話",), groups)
        self.assertIn(("負荷", "軽", "小さ", "休", "責め"), groups)
        self.assertEqual(rightbrain._model_surface_disabled_reason(logic), "")
        self.assertIn("audited_memory_policy_violation", reasons)

    def test_no_memory_plan_can_supply_non_memory_contract(self):
        rightbrain = RightBrain(load_model=False)
        rightbrain.model_blend_enabled = True
        rightbrain.model = object()
        rightbrain.tokenizer = object()
        logic = {
            "memory_use_expected": False,
            "memory_speakability": "no_memory",
            "core_message_jp": "分かる範囲で短く答え、分からない部分は決めつけない",
        }

        self.assertIn(
            ("分かる範囲", "分から", "決めつけ", "後で"),
            rightbrain._model_required_semantic_groups(logic),
        )
        self.assertEqual(rightbrain._model_surface_disabled_reason(logic), "")


if __name__ == "__main__":
    unittest.main()
