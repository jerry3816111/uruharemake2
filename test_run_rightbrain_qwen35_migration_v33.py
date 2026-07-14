import unittest

from run_rightbrain_qwen35_migration_v33 import _canonical_call, score_action_output


class RunRightBrainQwen35MigrationV33Test(unittest.TestCase):
    def test_canonical_call_accepts_ollama_shape(self):
        call = {"function": {"name": "set_gaze", "arguments": {"target": "user"}}}
        self.assertEqual(_canonical_call(call), {"name": "set_gaze", "arguments": {"target": "user"}})

    def test_action_exact_match_is_order_insensitive(self):
        case = {
            "expected_calls": [
                {"name": "set_expression", "arguments": {"expression": "happy"}},
                {"name": "play_motion", "arguments": {"motion": "wave"}},
            ],
            "forbidden_calls": [],
            "expected_no_action": False,
        }
        actual = [
            {"function": {"name": "play_motion", "arguments": {"motion": "wave"}}},
            {"function": {"name": "set_expression", "arguments": {"expression": "happy"}}},
        ]
        score = score_action_output(case, actual)
        self.assertTrue(score["exact_match"])
        self.assertEqual(score["required_action_recall"], 1.0)

    def test_negated_forbidden_call_is_visible(self):
        case = {
            "expected_calls": [],
            "forbidden_calls": [{"name": "play_motion", "arguments": {"motion": "wave"}}],
            "expected_no_action": True,
        }
        actual = [{"function": {"name": "play_motion", "arguments": "{\"motion\":\"wave\"}"}}]
        score = score_action_output(case, actual)
        self.assertTrue(score["negation_violation"])
        self.assertTrue(score["false_action"])
        self.assertFalse(score["no_action_correct"])

    def test_no_action_case_passes_with_empty_calls(self):
        case = {"expected_calls": [], "forbidden_calls": [], "expected_no_action": True}
        score = score_action_output(case, [])
        self.assertTrue(score["exact_match"])
        self.assertTrue(score["no_action_correct"])
        self.assertFalse(score["false_action"])


if __name__ == "__main__":
    unittest.main()
