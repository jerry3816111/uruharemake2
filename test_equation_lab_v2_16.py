import inspect
import unittest

import uruha_web_ui
from uruha_equation_lab import (
    DEFAULT_CASE_ID,
    build_equation_lab_payload,
    case_choices,
    render_equation_lab,
    show_feedback_correction,
)


class EquationLabV216Tests(unittest.TestCase):
    def test_same_input_routes_to_six_visible_reference_person_policies(self):
        selected = []
        inputs = []
        for _label, case_id in case_choices():
            payload = build_equation_lab_payload(case_id, "1")
            selected.append(payload["solution"]["selected"]["policy_id"])
            inputs.append(payload["case"]["current_input"])
        self.assertEqual(len(set(inputs)), 1)
        self.assertEqual(len(set(selected)), 6)

    def test_feedback_correction_changes_named_atoms_and_selected_policy(self):
        payload = build_equation_lab_payload(DEFAULT_CASE_ID, "2")
        self.assertEqual(payload["base_solution"]["selected"]["policy_id"], "calibrate_need")
        self.assertEqual(payload["solution"]["selected"]["policy_id"], "playful_tease")
        self.assertEqual(
            {row["atom"] for row in payload["changes"]},
            {"humor_invitation", "relationship_familiarity", "solution_request", "physical_strain", "uncertainty"},
        )
        self.assertEqual(payload["production_memory_write_count"], 0)

    def test_renderer_is_node_dominant_and_keeps_evidence_boundary_visible(self):
        html = render_equation_lab(DEFAULT_CASE_ID, "2")
        self.assertIn("eq-flow", html)
        self.assertGreaterEqual(html.count("eq-node"), 4)
        self.assertIn("Mₜ｜本輪真正流入決策的記憶／前置訊號", html)
        self.assertEqual(html.count("eq-atom is-changed"), 5)
        self.assertIn("θ<sub>Uruha</sub>", html)
        self.assertIn("六個候選回覆政策", html)
        self.assertIn("5/6", html)
        self.assertIn("不是人類理解證據", html)
        self.assertIn("deterministic mechanism replay", html)
        self.assertIn("禁止宣稱", html)
        self.assertNotIn("<script", html.lower())

    def test_feedback_button_jumps_to_falsifiable_story(self):
        case_id, phase, html = show_feedback_correction("ignored", "1")
        self.assertEqual(case_id, DEFAULT_CASE_ID)
        self.assertEqual(phase, "2")
        self.assertIn("校正", html)
        self.assertIn("資訊不足，確認真正想要的接法 → 接受邀請，熟人式吐槽", html)

    def test_web_ui_places_equation_lab_before_chat_and_preserves_v215(self):
        source = inspect.getsource(uruha_web_ui.build_demo)
        self.assertIn('gr.Tab("Equation Lab")', source)
        self.assertLess(source.index('gr.Tab("Equation Lab")'), source.index('gr.Tab("Chat")'))
        self.assertIn('gr.Tab("V2.15 Evidence")', source)


if __name__ == "__main__":
    unittest.main()
