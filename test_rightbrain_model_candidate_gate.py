import json
import unittest

import torch

from uruha_brain_mac import (
    RIGHT_BRAIN_MODEL_BLEND_ENABLED,
    RIGHT_BRAIN_MODEL_CONTRACT_VERSION,
    RIGHT_BRAIN_MODEL_SYSTEM_PROMPT,
    RightBrain,
    _normalize_right_brain_adapter_path,
    _resolve_right_brain_model_loading,
)


MEMORY = {
    "wisdom": "",
    "episodes": "",
    "profile": "",
    "recent_dialogue": "",
    "working_memory_summary": "",
    "working_memory_items": [],
    "recent_turns": [],
    "profile_structured": {},
}


class FakeTokenizer:
    eos_token_id = 0

    def __init__(self, outputs):
        self.outputs = list(outputs)
        self.index = 0

    def apply_chat_template(self, messages, tokenize=False, add_generation_prompt=True):
        return "prompt"

    def __call__(self, prompt, return_tensors="pt"):
        return {"input_ids": torch.tensor([[1, 2, 3]])}

    def decode(self, token_ids, skip_special_tokens=False):
        output = self.outputs[self.index]
        self.index += 1
        return output


class FakeModel:
    def generate(self, **kwargs):
        return torch.tensor([[1, 2, 3, 4]])


def build_rightbrain(outputs):
    rightbrain = RightBrain(load_model=False)
    rightbrain.model = FakeModel()
    rightbrain.tokenizer = FakeTokenizer(outputs)
    rightbrain.device = "cpu"
    rightbrain.model_blend_enabled = True
    rightbrain.model_candidate_count = len(outputs)
    return rightbrain


def reply_anxiety_logic():
    return {
        "scene": "support",
        "intent": "friend_no_reply",
        "surface_act": "validate_then_hold",
        "dialogue_act": "emotional_containment",
        "jp_summary": "既読のまま返事がないことを心配している。",
        "core_message_jp": "既読のまま返事がなくて不安でも、自分のせいと決めつけず少し待つ",
        "grounding": {
            "reply_self_blame": True,
            "reply_context": "direct_reply",
            "reply_signal": "read_receipt",
        },
        "constraints": {"max_chars": 80, "sentence_count": 2},
        "human_speech_plan": {
            "dialogue_act": "emotional_containment",
            "content_units": ["既読の文脈を拾う", "理由は未確定", "自責を止める", "少し待つ"],
            "speech_moves": [
                {"role": "context_acknowledgement", "signal": "read_receipt"},
                {"role": "uncertainty_tolerance", "target": "reason_for_silence"},
                {"role": "self_blame_boundary", "target": "premature_self_blame"},
                {"role": "next_action", "action": "wait_before_followup"},
            ],
            "grounding_terms": [],
            "style_operators": ["warm"],
        },
    }


class TestRightBrainModelCandidateGate(unittest.TestCase):
    def test_adapter_path_supports_explicit_base_only_ablation(self):
        self.assertEqual(_normalize_right_brain_adapter_path("base-only", "/tmp/default"), "")
        self.assertEqual(_normalize_right_brain_adapter_path("none", "/tmp/default"), "")
        self.assertEqual(_normalize_right_brain_adapter_path(None, "/tmp/default"), "/tmp/default")

    def test_model_payload_matches_plan_sft_contract_without_raw_user_text(self):
        rightbrain = RightBrain(load_model=False)
        logic = reply_anxiety_logic()

        payload_text = rightbrain._build_model_surface_payload(logic, {"mood": -3, "trust": 62}, 80)
        payload = json.loads(payload_text)

        self.assertEqual(payload["contract_version"], RIGHT_BRAIN_MODEL_CONTRACT_VERSION)
        self.assertEqual(payload["task"], "write_one_user_facing_japanese_reply")
        self.assertEqual(payload["user_input"], logic["jp_summary"])
        self.assertEqual(payload["leftbrain_plan"]["meaning"], logic["core_message_jp"])
        self.assertEqual(
            payload["required_marker_groups"],
            [list(group) for group in rightbrain._model_required_semantic_groups(logic)],
        )
        self.assertEqual(payload["context"]["max_chars"], 80)
        self.assertNotIn("required_semantic_groups", payload)
        self.assertNotIn("他已讀但沒回", payload_text)
        self.assertIn("required_marker_group", RIGHT_BRAIN_MODEL_SYSTEM_PROMPT)

    def test_default_model_loading_follows_explicit_blend_switch(self):
        self.assertEqual(_resolve_right_brain_model_loading(None), RIGHT_BRAIN_MODEL_BLEND_ENABLED)
        self.assertTrue(_resolve_right_brain_model_loading(True))
        self.assertFalse(_resolve_right_brain_model_loading(False))

    def test_gate_accepts_only_clean_semantically_complete_candidate(self):
        rightbrain = build_rightbrain(
            [
                "既読のままだと気になるよな。でも理由はまだ分からない。自分のせいと決めつけず、少し待て。<|im_end|>",
                "好了、既読のままだと気になる。自分のせいと決めつけず少し待て。<|im_end|>",
                "既読のままだと気になるよな。少し待て。<|im_end|>",
            ]
        )
        logic = reply_anxiety_logic()

        candidates = rightbrain._generate_model_surface_candidates(
            user_input="他已讀但沒回，是不是我講錯話？",
            logic_data=logic,
            memory_data={},
            current_psyche={"mood": 0, "trust": 50},
            max_chars=80,
        )

        self.assertEqual(len(candidates), 1)
        self.assertIn("理由はまだ分からない", candidates[0])
        trace = logic["model_surface_candidate_trace"]
        self.assertEqual(len(trace["accepted"]), 1)
        self.assertEqual(len(trace["rejected"]), 2)
        reasons = [reason for row in trace["rejected"] for reason in row["rejection_reasons"]]
        self.assertIn("cjk_language_leak", reasons)
        self.assertTrue(any(reason.startswith("semantic_slots_missing:") for reason in reasons))

    def test_speak_can_select_a_better_gated_model_candidate(self):
        model_reply = "既読のままだと気になるよな。でも理由はまだ分からない。自分のせいと決めつけず、急がず少し待て。"
        rightbrain = build_rightbrain([model_reply + "<|im_end|>"])
        rightbrain.model_selection_margin = 0.1
        original_score = rightbrain._score_candidate
        rightbrain._score_candidate = lambda reply, logic: original_score(reply, logic) + (5.0 if "急がず" in reply else 0.0)
        logic = reply_anxiety_logic()

        reply = rightbrain.speak(
            "他已讀但沒回，是不是我講錯話？",
            logic,
            MEMORY,
            {"mood": 0, "trust": 50},
        )

        self.assertIn("急がず", reply)
        self.assertEqual(logic["model_surface_selection"]["selected_source"], "model")
        self.assertEqual(len(logic["model_surface_candidate_trace"]["accepted"]), 1)

    def test_rejected_model_candidates_leave_deterministic_reply_in_control(self):
        rightbrain = build_rightbrain(["好了、既読だけ気にするな。<|im_end|>"])
        logic = reply_anxiety_logic()

        reply = rightbrain.speak(
            "他已讀但沒回，是不是我講錯話？",
            logic,
            MEMORY,
            {"mood": 0, "trust": 50},
        )

        self.assertNotIn("好了", reply)
        self.assertEqual(logic["model_surface_selection"]["selected_source"], "deterministic")
        self.assertEqual(len(logic["model_surface_candidate_trace"]["accepted"]), 0)

    def test_high_risk_withdrawal_never_enters_model_generation(self):
        rightbrain = build_rightbrain(["モデル出力。<|im_end|>"])
        logic = reply_anxiety_logic()
        logic["grounding"] = {
            "withdrawal_risk": "high",
            "withdrawal_kind": "contact_cutoff",
        }
        logic["intent"] = "anxious_support"

        candidates = rightbrain._generate_model_surface_candidates(
            user_input="誰傳訊息我都不想回，我想斷聯。",
            logic_data=logic,
            memory_data={},
            current_psyche={"mood": -20, "trust": 50},
            max_chars=80,
        )

        self.assertEqual(candidates, [])
        self.assertEqual(logic["model_surface_candidate_trace"]["disabled_reason"], "high_withdrawal_risk")
        self.assertEqual(rightbrain.tokenizer.index, 0)

    def test_japanese_han_characters_are_not_misclassified_as_chinese_leak(self):
        rightbrain = RightBrain(load_model=False)
        logic = reply_anxiety_logic()
        reasons = rightbrain._model_candidate_rejection_reasons(
            "連絡を切る前に止まれ。まず一人に話せ。",
            logic,
            max_chars=80,
            user_input="誰かに話す",
        )

        self.assertNotIn("cjk_language_leak", reasons)

    def test_gate_rejects_extended_latin_pollution(self):
        rightbrain = RightBrain(load_model=False)
        reasons = rightbrain._model_candidate_rejection_reasons(
            "返事ないと気になるcá？少し待て。",
            reply_anxiety_logic(),
            max_chars=80,
        )

        self.assertIn("unexpected_ascii_leak", reasons)

    def test_model_is_disabled_without_structured_semantic_contract(self):
        rightbrain = build_rightbrain(["今日は休め。<|im_end|>"])
        logic = {
            "scene": "support",
            "intent": "tired_support",
            "surface_act": "empathic_rest_suggestion",
            "core_message_jp": "今日は無理すんな、休め",
            "human_speech_plan": {"dialogue_act": "emotional_containment"},
        }

        self.assertEqual(rightbrain._model_surface_disabled_reason(logic), "missing_semantic_contract")

    def test_gate_rejects_polite_drift_and_benign_overreaction(self):
        rightbrain = RightBrain(load_model=False)
        logic = {
            "intent": "channel_management",
            "grounding": {"management_kind": "do_not_disturb"},
            "must_avoid": [],
        }
        reply = "通知を切ってもいいです。一人で思い詰めないでください。後で戻せます。"

        reasons = rightbrain._model_candidate_rejection_reasons(reply, logic, 80)

        self.assertIn("polite_tone_drift", reasons)
        self.assertIn("benign_action_overreaction", reasons)

    def test_gate_rejects_polite_sentence_particles(self):
        rightbrain = RightBrain(load_model=False)
        logic = reply_anxiety_logic()

        reasons = rightbrain._model_candidate_rejection_reasons(
            "返事来ないのは気になりますよね。ちょっと待ってみて。",
            logic,
            80,
        )

        self.assertIn("polite_tone_drift", reasons)

    def test_mild_withdrawal_rejects_unnecessary_isolation_language(self):
        rightbrain = RightBrain(load_model=False)
        logic = reply_anxiety_logic()
        logic["grounding"] = {
            "withdrawal_risk": "mild",
            "withdrawal_kind": "do_not_disturb",
        }

        reasons = rightbrain._model_candidate_rejection_reasons(
            "通知は止めていい。でも一人だけで悩むな。連絡は残しとけ。",
            logic,
            80,
        )

        self.assertIn("risk_overreaction", reasons)

    def test_mild_withdrawal_rejects_unrequested_social_intervention(self):
        rightbrain = RightBrain(load_model=False)
        logic = reply_anxiety_logic()
        logic["grounding"] = {"withdrawal_risk": "mild", "withdrawal_kind": "do_not_disturb"}

        reasons = rightbrain._model_candidate_rejection_reasons(
            "通知は切っていい。でも今も友達と話してみて。",
            logic,
            80,
        )

        self.assertIn("risk_overreaction", reasons)


if __name__ == "__main__":
    unittest.main()
