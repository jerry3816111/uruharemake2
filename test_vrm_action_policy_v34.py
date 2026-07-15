import json
import unittest
from pathlib import Path

from run_rightbrain_qwen35_migration_v33 import score_action_output
from vrm_action_policy_v34 import classify_action_request, validate_model_tool_calls


ROOT = Path(__file__).resolve().parent
DATASET_PATH = ROOT / "datasets" / "rightbrain_qwen35_migration_v33_holdout.json"


class VrmActionPolicyV34Test(unittest.TestCase):
    def test_explicit_wave_is_authorized(self):
        policy = classify_action_request("こっちに手を振って。")
        self.assertTrue(policy["authorized"])
        self.assertIn("play_motion:motion=wave", policy["positive_call_keys"])

    def test_ordinary_conversation_is_not_an_action(self):
        policy = classify_action_request("笑顔って見てると安心するよね。")
        self.assertFalse(policy["authorized"])
        self.assertIn("not_an_explicit_current_request", policy["reasons"])

    def test_pure_negation_is_denied(self):
        policy = classify_action_request("手は振らないで。")
        self.assertFalse(policy["authorized"])
        self.assertIn("play_motion:motion=wave", policy["negated_call_keys"])

    def test_mixed_correction_keeps_positive_and_blocks_negated_call(self):
        calls = [
            {"name": "play_motion", "arguments": {"motion": "wave"}},
            {"name": "play_motion", "arguments": {"motion": "nod"}},
        ]
        result = validate_model_tool_calls("手は振らずに、うなずくだけでいい。", calls)
        self.assertTrue(result["policy"]["authorized"])
        self.assertEqual(result["accepted_calls"], [{"name": "play_motion", "arguments": {"motion": "nod"}}])
        self.assertIn("call_explicitly_negated", result["blocked_calls"][0]["reasons"])

    def test_ambiguous_and_unsupported_requests_are_denied(self):
        self.assertFalse(classify_action_request("右を見るか左を見るか、まだ決めてない。")["authorized"])
        self.assertFalse(classify_action_request("ジャンプして。")["authorized"])

    def test_pointing_right_does_not_authorize_right_gaze(self):
        calls = [
            {"name": "play_motion", "arguments": {"motion": "point"}},
            {"name": "set_gaze", "arguments": {"target": "right"}},
        ]
        result = validate_model_tool_calls("右の方を指して。", calls)
        self.assertEqual(result["accepted_calls"], [{"name": "play_motion", "arguments": {"motion": "point"}}])

    def test_gaze_only_request_blocks_motion(self):
        calls = [
            {"name": "set_gaze", "arguments": {"target": "user"}},
            {"name": "play_motion", "arguments": {"motion": "wave"}},
        ]
        result = validate_model_tool_calls("動かないで、視線だけこっちに向けて。", calls)
        self.assertEqual(result["accepted_calls"], [{"name": "set_gaze", "arguments": {"target": "user"}}])

    def test_perfect_development_calls_survive_policy(self):
        dataset = json.loads(DATASET_PATH.read_text(encoding="utf-8"))
        failures = []
        for case in dataset["action_cases"]:
            supplied = [*case["expected_calls"], *case["forbidden_calls"]]
            result = validate_model_tool_calls(case["user_input"], supplied)
            score = score_action_output(case, result["accepted_calls"])
            if not score["exact_match"] or score["negation_violation"]:
                failures.append((case["id"], result, score))
        self.assertEqual(failures, [])


if __name__ == "__main__":
    unittest.main()
