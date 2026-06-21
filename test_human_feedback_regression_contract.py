import unittest

from eval_human_feedback_regression import evaluate_human_contract, evaluate_required_groups, japanese_surface_ok


class TestHumanFeedbackRegressionContract(unittest.TestCase):
    def test_cross_language_focus_uses_japanese_contract_markers(self):
        case = {
            "prompt": "朋友沒回我，我是不是很煩",
            "human_contract": {
                "required_marker_groups": [["返事", "既読"], ["不安"], ["決めつけ"]],
                "forbidden_markers": ["嫌われた"],
            },
        }

        result = evaluate_human_contract(case, "返事がなくて不安でも、嫌われたって決めつけるな。")

        self.assertEqual(result["all_required_groups_hit"], 1)
        self.assertEqual(result["required_group_hit_rate"], 1.0)
        self.assertEqual(result["forbidden_markers_ok"], 0)
        self.assertEqual(result["forbidden_marker_hits"], ["嫌われた"])

    def test_missing_required_group_fails_contract(self):
        case = {
            "human_contract": {
                "required_marker_groups": [["作品"], ["タイトル", "曲名"]],
                "forbidden_markers": [],
            }
        }

        result = evaluate_human_contract(case, "作品名どれ？")

        self.assertEqual(result["all_required_groups_hit"], 0)
        self.assertEqual(result["required_group_hit_rate"], 0.5)
        self.assertEqual(result["forbidden_markers_ok"], 1)

    def test_chinese_surface_leak_is_not_counted_as_japanese(self):
        self.assertEqual(japanese_surface_ok("了解你的需求，我会尊重的。"), 0)
        self.assertEqual(japanese_surface_ok("返事がないと不安になるよな。"), 1)

    def test_forbidden_only_contract_does_not_create_false_focus_failure(self):
        case = {
            "human_contract": {
                "required_marker_groups": [],
                "forbidden_markers": ["勝手にしろ"],
            }
        }

        result = evaluate_human_contract(case, "一人で抱えず、誰かに連絡しろ。")

        self.assertEqual(result["all_required_groups_hit"], 1)
        self.assertEqual(result["forbidden_markers_ok"], 1)

    def test_planner_required_groups_support_paired_old_new_comparison(self):
        groups = [("トイレ",), ("一人", "誰か", "連絡")]

        old = evaluate_required_groups(groups, "浴室で一人になる前に止まれ。")
        new = evaluate_required_groups(groups, "トイレで一人になる前に止まれ。誰かに連絡しろ。")

        self.assertEqual(old["required_group_hit_rate"], 0.5)
        self.assertEqual(new["required_group_hit_rate"], 1.0)


if __name__ == "__main__":
    unittest.main()
