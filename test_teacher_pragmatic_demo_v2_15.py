import inspect
import unittest

import uruha_web_ui
from uruha_teacher_demo import (
    DEFAULT_SCENARIO_ID,
    SCENARIO_SPECS,
    advance_teacher_demo,
    build_teacher_demo_payload,
    frozen_source_integrity,
    render_teacher_demo,
    scenario_choices,
)


class TeacherPragmaticDemoV215Tests(unittest.TestCase):
    def test_frozen_sources_and_raw_result_are_bound(self):
        integrity = frozen_source_integrity()
        self.assertTrue(integrity["passed"])
        self.assertEqual(set(integrity["checks"].values()), {True})
        self.assertEqual(len(integrity["checks"]), 6)
        self.assertEqual(
            integrity["raw_result_sha256"],
            "9005d3495d90e4500409bb1304cc5b68ab62edc134e6b200ecb0fb91a7ed3c22",
        )

    def test_primary_story_visibly_contradicts_and_then_supports(self):
        first = build_teacher_demo_payload(DEFAULT_SCENARIO_ID, 1)
        second = build_teacher_demo_payload(DEFAULT_SCENARIO_ID, 2)
        third = build_teacher_demo_payload(DEFAULT_SCENARIO_ID, 3)

        self.assertEqual(first["cognition"]["general_verification"], "not_available")
        self.assertEqual(second["cognition"]["general_verification"], "contradicted")
        self.assertGreater(second["cognition"]["revision_count"], 0)
        self.assertEqual(third["cognition"]["general_verification"], "supported")
        self.assertIn("読み違えた", second["system"]["reply"])
        self.assertFalse(second["baseline"]["contract_pass"])
        self.assertTrue(second["system"]["contract_pass"])

    def test_preference_retraction_withdraws_stable_model_item(self):
        first = build_teacher_demo_payload("v214_en_preference_retraction_01", 1)
        second = build_teacher_demo_payload("v214_en_preference_retraction_01", 2)
        first_stable = first["cognition"]["model_summary"]["layers"]["stable"]
        second_stable = second["cognition"]["model_summary"]["layers"]["stable"]

        self.assertEqual(first_stable["active"], 1)
        self.assertEqual(second_stable["active"], 0)
        self.assertEqual(second_stable["withdrawn"], 1)
        self.assertEqual(second["cognition"]["last_revision"]["verification"], "explicit_retraction")
        self.assertTrue(second["cognition"]["last_revision"]["original_retained"])
        self.assertNotIn("拿鐵", second["system"]["reply"])

    def test_every_demo_pair_is_token_matched_and_never_writes_production_memory(self):
        for case_id in SCENARIO_SPECS:
            for turn_index in (1, 2, 3):
                payload = build_teacher_demo_payload(case_id, turn_index)
                self.assertLessEqual(
                    abs(
                        int(payload["system"]["prompt_eval_count"])
                        - int(payload["baseline"]["prompt_eval_count"])
                    ),
                    2,
                )
                self.assertEqual(payload["production_memory_write_count"], 0)
                self.assertFalse(payload["claims"]["system_better_than_baseline"])

    def test_renderer_is_node_first_and_keeps_the_claim_boundary_visible(self):
        html = render_teacher_demo(DEFAULT_SCENARIO_ID, "2")

        self.assertIn("teacher-demo-cog-graph", html)
        self.assertGreaterEqual(html.count("teacher-demo-node"), 10)
        self.assertIn("PRAGMATIC HYPOTHESIS", html)
        self.assertIn("NEXT PREDICTION", html)
        self.assertIn("後續證據否定", html)
        self.assertIn("42/54", html)
        self.assertIn("9/54", html)
        self.assertIn("尚缺三位獨立盲評", html)
        self.assertIn("不能主張", html)
        self.assertNotIn("<script", html.lower())

    def test_controls_offer_three_research_stories_and_cycle_steps(self):
        self.assertEqual(len(scenario_choices()), 3)
        step, html = advance_teacher_demo(DEFAULT_SCENARIO_ID, "3")
        self.assertEqual(step, "1")
        self.assertIn("TURN 1 / 3", html)

    def test_web_ui_preserves_v215_evidence_before_chat(self):
        source = inspect.getsource(uruha_web_ui.build_demo)
        self.assertIn('gr.Tab("V2.15 Evidence")', source)
        self.assertLess(source.index('gr.Tab("V2.15 Evidence")'), source.index('gr.Tab("Chat")'))
        self.assertIn("teacher_next_btn.click", source)


if __name__ == "__main__":
    unittest.main()
