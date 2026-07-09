import json
import os
import tempfile
import unittest

import torch

from uruha_brain_mac import (
    RIGHT_BRAIN_MODEL_BLEND_ENABLED,
    RIGHT_BRAIN_MODEL_CONTRACT_VERSION,
    RIGHT_BRAIN_MODEL_REPAIR_ENABLED,
    RIGHT_BRAIN_MODEL_SYSTEM_PROMPT,
    RightBrain,
    _default_right_brain_adapter_path,
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
    rightbrain.model_repair_enabled = False
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
    def test_default_adapter_prefers_validated_v10_with_legacy_fallback(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            legacy = os.path.join(tmpdir, "uruha_v10_all_linear_lora")
            promoted = os.path.join(tmpdir, "uruha_rightbrain_plan_sft_lora_v10_expanded_rejection_v1")

            os.makedirs(legacy)
            self.assertEqual(_default_right_brain_adapter_path(tmpdir), legacy)

            os.makedirs(promoted)
            self.assertEqual(_default_right_brain_adapter_path(tmpdir), promoted)

    def test_default_adapter_names_promoted_artifact_when_weights_are_missing(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            expected = os.path.join(tmpdir, "uruha_rightbrain_plan_sft_lora_v10_expanded_rejection_v1")
            self.assertEqual(_default_right_brain_adapter_path(tmpdir), expected)

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
        self.assertIn("audited_memory_brief", payload["context"])
        self.assertIn("persona_expression_brief", payload["context"])

    def test_model_payload_allows_only_audited_memory_surface_cues(self):
        rightbrain = RightBrain(load_model=False)
        logic = reply_anxiety_logic()
        logic.update(
            {
                "memory_anchor": {
                    "kind": "ramen_bad_consequence",
                    "jp_anchor": "ラーメンで腹痛",
                    "terms": ["ラーメンで腹痛", "拉麵", "肚子痛", "ramen"],
                    "source_text": "使用者上週說吃拉麵會肚子痛，這是不能原文丟給右腦的 raw memory。",
                },
                "memory_speakability": "explicit_ok",
                "memory_speakability_reason": "user asks food advice and this memory is relevant",
                "memory_use_expected": True,
            }
        )

        payload_text = rightbrain._build_model_surface_payload(
            logic,
            {"mood": -5, "trust": 74},
            80,
            memory_data={
                "working_memory_summary": "raw summary should not enter model payload",
                "working_memory_items": [
                    {"text": "使用者上週說吃拉麵會肚子痛，這是 raw source text。", "score": 0.95}
                ],
            },
        )
        payload = json.loads(payload_text)
        brief = payload["context"]["audited_memory_brief"]

        self.assertEqual(brief["policy"], "explicit_allowed")
        self.assertEqual(brief["allowed_memory_cues"][0]["jp_anchor"], "ラーメンで腹痛")
        self.assertIn("ラーメンで腹痛", brief["allowed_memory_cues"][0]["terms"])
        self.assertNotIn("拉麵", payload_text)
        self.assertNotIn("肚子痛", payload_text)
        self.assertNotIn("raw source text", payload_text)
        self.assertNotIn("raw summary should not enter model payload", payload_text)

    def test_model_payload_keeps_background_memory_nonverbal(self):
        rightbrain = RightBrain(load_model=False)
        logic = reply_anxiety_logic()
        logic.update(
            {
                "memory_anchor": {
                    "kind": "family_pressure",
                    "jp_anchor": "家庭の話",
                    "terms": ["家庭の話", "家庭壓力"],
                    "source_text": "使用者以前說家庭壓力很大，但這輪不能突然明講。",
                },
                "memory_speakability": "background_only",
                "memory_speakability_reason": "sensitive context should only tune warmth",
                "memory_use_expected": False,
            }
        )

        payload_text = rightbrain._build_model_surface_payload(logic, {"mood": -20, "trust": 55}, 80)
        payload = json.loads(payload_text)
        brief = payload["context"]["audited_memory_brief"]

        self.assertEqual(brief["policy"], "background_only")
        self.assertEqual(brief["allowed_memory_cues"], [])
        self.assertEqual(brief["background_style_cues"][0]["kind"], "family_pressure")
        self.assertNotIn("家庭壓力", payload_text)
        self.assertNotIn("以前說", payload_text)

    def test_model_payload_projects_conflicting_private_plan_to_public_contract(self):
        rightbrain = RightBrain(load_model=False)
        logic = {
            "scene": "casual",
            "intent": "topic_proposal",
            "surface_act": "plain_reply",
            "jp_summary": "ユーザーが普通の雑談をしている。",
            "core_message_jp": "軽い話題なら最近どうしてたかでいい",
            "memory_anchor": {
                "kind": "private_health_context",
                "jp_anchor": "最近は胃が弱い",
                "terms": ["最近は胃が弱い", "体調"],
            },
            "memory_speakability": "private",
            "memory_use_expected": False,
            "required_marker_groups": [["話題", "話"], ["最近", "どうしてた", "近況"]],
            "human_speech_plan": {
                "dialogue_act": "topic_proposal",
                "content_units": ["最近の体調を踏まえる", "無理のない選択に寄せる"],
                "grounding_terms": ["体調"],
                "style_operators": ["casual", "short"],
            },
        }

        payload = json.loads(
            rightbrain._build_model_surface_payload(logic, {"mood": 0, "trust": 32}, 80)
        )

        self.assertEqual(payload["context"]["audited_memory_brief"]["policy"], "do_not_mention")
        self.assertEqual(payload["leftbrain_plan"]["meaning"], "軽い話題なら最近どうしてたかでいい")
        self.assertEqual(payload["leftbrain_plan"]["content_units"], [])
        self.assertEqual(payload["leftbrain_plan"]["grounding_terms"], [])
        self.assertEqual(payload["leftbrain_plan"]["scene"], "")
        self.assertEqual(payload["leftbrain_plan"]["intent"], "")
        self.assertEqual(logic["model_surface_plan_projection"]["mode"], "semantic_contract_only")

    def test_model_payload_keeps_non_memory_plan_units_supported_by_contract(self):
        rightbrain = RightBrain(load_model=False)
        logic = {
            "scene": "support",
            "intent": "friend_no_reply",
            "jp_summary": "既読のまま返事がないことを心配している。",
            "core_message_jp": "理由はまだ未確定なので自分を責めずに少し待つ",
            "memory_speakability": "no_memory",
            "memory_use_expected": False,
            "required_marker_groups": [["既読", "返事"], ["理由", "分から"]],
            "human_speech_plan": {
                "dialogue_act": "emotional_containment",
                "content_units": ["既読の文脈を拾う", "理由は未確定", "少し待つ"],
                "grounding_terms": ["既読"],
            },
        }

        payload = json.loads(
            rightbrain._build_model_surface_payload(logic, {"mood": 0, "trust": 58}, 80)
        )

        self.assertEqual(
            payload["leftbrain_plan"]["content_units"],
            ["既読の文脈を拾う", "理由は未確定", "少し待つ"],
        )
        self.assertEqual(payload["leftbrain_plan"]["grounding_terms"], ["既読"])
        self.assertEqual(payload["leftbrain_plan"]["scene"], "support")
        self.assertEqual(logic["model_surface_plan_projection"]["mode"], "full_plan")

    def test_model_payload_keeps_full_plan_for_explicit_memory(self):
        rightbrain = RightBrain(load_model=False)
        logic = reply_anxiety_logic()
        logic.update(
            {
                "memory_anchor": {
                    "kind": "recent_health_context",
                    "jp_anchor": "最近は胃が弱い",
                    "terms": ["最近は胃が弱い", "体調"],
                },
                "memory_speakability": "explicit_ok",
                "memory_use_expected": True,
            }
        )

        payload = json.loads(
            rightbrain._build_model_surface_payload(logic, {"mood": 0, "trust": 70}, 80)
        )

        self.assertEqual(
            payload["leftbrain_plan"]["content_units"],
            logic["human_speech_plan"]["content_units"],
        )
        self.assertEqual(logic["model_surface_plan_projection"]["mode"], "full_plan")

    def test_default_model_loading_follows_explicit_blend_switch(self):
        self.assertEqual(_resolve_right_brain_model_loading(None), RIGHT_BRAIN_MODEL_BLEND_ENABLED)
        self.assertTrue(_resolve_right_brain_model_loading(True))
        self.assertFalse(_resolve_right_brain_model_loading(False))

    def test_unproven_repair_pass_is_disabled_by_default(self):
        self.assertFalse(RIGHT_BRAIN_MODEL_REPAIR_ENABLED)
        self.assertFalse(RightBrain(load_model=False).model_repair_enabled)

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

    def test_repair_payload_keeps_contract_and_explains_generic_failure(self):
        rightbrain = RightBrain(load_model=False)
        logic = reply_anxiety_logic()
        original = rightbrain._build_model_surface_payload(
            logic,
            {"mood": 0, "trust": 50},
            80,
        )

        repaired = json.loads(
            rightbrain._build_model_surface_repair_payload(
                original,
                ["unexpected_ascii_leak", "semantic_slots_missing:1/3"],
            )
        )

        self.assertEqual(
            repaired["task"],
            "repair_rejected_user_facing_japanese_reply",
        )
        self.assertEqual(
            repaired["required_marker_groups"],
            json.loads(original)["required_marker_groups"],
        )
        self.assertIn("日本語だけ", " ".join(repaired["repair_feedback"]["required_corrections"]))
        self.assertIn(
            "required_marker_groups",
            " ".join(repaired["repair_feedback"]["required_corrections"]),
        )
        self.assertNotIn("previous_draft", repaired["repair_feedback"])

    def test_rejected_candidate_can_be_repaired_once_without_relaxing_gate(self):
        rightbrain = build_rightbrain(
            [
                "好了、既読のままだと気になる。<|im_end|>",
                "既読のままだと気になるよな。でも理由はまだ分からない。自分のせいと決めつけず、少し待て。<|im_end|>",
            ]
        )
        rightbrain.model_candidate_count = 1
        rightbrain.model_repair_enabled = True
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
        self.assertEqual(trace["initial_generated_count"], 1)
        self.assertEqual(trace["initial_accepted_count"], 0)
        self.assertEqual(trace["repair_attempt_count"], 1)
        self.assertEqual(trace["repair_accepted_count"], 1)
        self.assertEqual(trace["accepted"][0]["source"], "repair")
        self.assertEqual(trace["rejected"], [])

    def test_failed_repair_remains_rejected_and_cannot_reach_selection(self):
        rightbrain = build_rightbrain(
            [
                "好了、既読だけ気にするな。<|im_end|>",
                "TODAY PLAN 返事を待つ。<|im_end|>",
            ]
        )
        rightbrain.model_candidate_count = 1
        rightbrain.model_repair_enabled = True
        logic = reply_anxiety_logic()

        candidates = rightbrain._generate_model_surface_candidates(
            user_input="他已讀但沒回，是不是我講錯話？",
            logic_data=logic,
            memory_data={},
            current_psyche={"mood": 0, "trust": 50},
            max_chars=80,
        )

        self.assertEqual(candidates, [])
        trace = logic["model_surface_candidate_trace"]
        self.assertEqual(trace["repair_attempt_count"], 1)
        self.assertEqual(trace["repair_accepted_count"], 0)
        self.assertEqual(len(trace["rejected"]), 1)
        self.assertIn(
            "unexpected_ascii_leak",
            trace["rejected"][0]["repair_rejection_reasons"],
        )

    def test_repair_is_skipped_when_an_initial_candidate_is_already_available(self):
        rightbrain = build_rightbrain(
            [
                "好了、既読だけ気にするな。<|im_end|>",
                "既読のままだと気になるよな。でも理由はまだ分からない。自分のせいと決めつけず、少し待て。<|im_end|>",
            ]
        )
        rightbrain.model_candidate_count = 2
        rightbrain.model_repair_enabled = True
        logic = reply_anxiety_logic()

        candidates = rightbrain._generate_model_surface_candidates(
            user_input="他已讀但沒回，是不是我講錯話？",
            logic_data=logic,
            memory_data={},
            current_psyche={"mood": 0, "trust": 50},
            max_chars=80,
        )

        self.assertEqual(len(candidates), 1)
        trace = logic["model_surface_candidate_trace"]
        self.assertEqual(trace["repair_attempt_count"], 0)
        self.assertEqual(trace["repair_skipped_reason"], "initial_candidate_available")
        self.assertEqual(len(trace["rejected"]), 1)

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

    def test_gate_rejects_simplified_or_nonstandard_cjk_surface(self):
        rightbrain = RightBrain(load_model=False)
        reasons = rightbrain._model_candidate_rejection_reasons(
            "今日の體調を見て、一個だけ話を选ぼう。",
            reply_anxiety_logic(),
            max_chars=80,
        )

        self.assertIn("nonstandard_cjk_surface", reasons)

    def test_gate_rejects_simplified_wu_and_unicode_replacement_character(self):
        rightbrain = RightBrain(load_model=False)
        logic = reply_anxiety_logic()

        simplified = rightbrain._model_candidate_rejection_reasons(
            "今日は无理しないで休め。",
            logic,
            max_chars=80,
        )
        replacement = rightbrain._model_candidate_rejection_reasons(
            "今日は範�だけ決めて休め。",
            logic,
            max_chars=80,
        )

        self.assertIn("nonstandard_cjk_surface", simplified)
        self.assertIn("unicode_replacement_character", replacement)

    def test_gate_rejects_simplified_chinese_residue_seen_in_model_outputs(self):
        rightbrain = RightBrain(load_model=False)
        logic = reply_anxiety_logic()

        reasons = rightbrain._model_candidate_rejection_reasons(
            "後で聞くとかじゃなくて、今日の负荷を减らせばいい。后で戻せる。",
            logic,
            max_chars=90,
        )

        self.assertIn("nonstandard_cjk_surface", reasons)

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

    def test_gate_accepts_colloquial_required_marker_variants(self):
        rightbrain = RightBrain(load_model=False)
        logic = {
            "required_marker_groups": [
                ["既読", "返事", "返信"],
                ["理由", "分から"],
                ["自分", "せい", "悪い"],
            ]
        }

        reasons = rightbrain._model_candidate_rejection_reasons(
            "既読にしててもまだ返事が来んのは分かんねんけど、自分勝手じゃないからな。",
            logic,
            90,
        )

        self.assertFalse(any(reason.startswith("semantic_slots_missing:") for reason in reasons))

    def test_prepare_sanitizes_salvageable_ascii_before_final_gate(self):
        rightbrain = RightBrain(load_model=False)
        logic = {
            "scene": "support",
            "intent": "tired_support",
            "dialogue_act": "emotional_containment",
            "required_marker_groups": [["休", "無理", "疲", "寝", "回復", "しんど"]],
            "constraints": {"max_chars": 80},
        }

        candidate, reasons = rightbrain._prepare_model_surface_candidate(
            "今日は少し早めに rest しろ。疲れてるなら回復優先だろ。",
            logic,
            user_input="疲れた",
            memory_data=MEMORY,
            max_chars=80,
        )

        self.assertEqual(reasons, [])
        self.assertNotIn("rest", candidate.lower())
        self.assertIn("疲", candidate)
        self.assertIn("回復", candidate)

    def test_prepare_localizes_known_ascii_semantic_terms_before_gate(self):
        rightbrain = RightBrain(load_model=False)
        logic = {
            "scene": "memory",
            "intent": "explicit_memory_answer",
            "dialogue_act": "advice",
            "required_marker_groups": [["胃が弱い"], ["コーヒー"], ["控えめ"], ["体調", "胃", "最近"]],
            "constraints": {"max_chars": 80},
        }

        candidate, reasons = rightbrain._prepare_model_surface_candidate(
            "最近は gastric が弱いでしょ、coffee は少なく控えた方がいいよ。",
            logic,
            user_input="最近胃が弱いけど、今日コーヒー飲んでもいい？",
            memory_data=MEMORY,
            max_chars=80,
        )

        self.assertEqual(reasons, [])
        self.assertIn("胃", candidate)
        self.assertIn("コーヒー", candidate)
        self.assertIn("少なく", candidate)
        self.assertIn("控え", candidate)

    def test_prepare_removes_tokenizer_spaces_between_japanese_terms(self):
        rightbrain = RightBrain(load_model=False)
        logic = {
            "scene": "memory",
            "intent": "explicit_memory_answer",
            "dialogue_act": "advice",
            "required_marker_groups": [["胃が弱い"], ["コーヒー"], ["控えめ", "少なめ", "少なく"]],
            "constraints": {"max_chars": 80},
        }

        candidate, reasons = rightbrain._prepare_model_surface_candidate(
            "最近は 胃 が弱いでしょ、 コーヒー は 少なく 控えた方がいいよ。",
            logic,
            user_input="最近胃が弱いけど、今日コーヒー飲んでもいい？",
            memory_data=MEMORY,
            max_chars=80,
        )

        self.assertEqual(reasons, [])
        self.assertIn("胃が弱い", candidate)
        self.assertIn("コーヒーは少なく控え", candidate)

    def test_prepare_accepts_natural_marker_paraphrase_and_normalized_cjk(self):
        rightbrain = RightBrain(load_model=False)
        logic = {
            "scene": "memory",
            "intent": "explicit_memory_answer",
            "dialogue_act": "advice",
            "required_marker_groups": [
                ["最近は辛いものを控えたい", "辛いもの"],
                ["辛いもの", "辛い"],
                ["控えめ", "少なめ", "少し", "やめ", "避け"],
                ["体調", "胃", "最近"],
            ],
            "constraints": {"max_chars": 80},
        }

        candidate, reasons = rightbrain._prepare_model_surface_candidate(
            "最近の體調を考えると、辛いやつはちょっと避けてちょうだい。",
            logic,
            user_input="辛いもの食べたいけど、今日どう思う？",
            memory_data=MEMORY,
            max_chars=80,
        )

        self.assertEqual(reasons, [])
        self.assertIn("体調", candidate)
        self.assertIn("辛いやつ", candidate)
        self.assertIn("避け", candidate)

    def test_gate_rejects_foreign_script_and_nonstandard_punctuation(self):
        rightbrain = RightBrain(load_model=False)
        logic = reply_anxiety_logic()

        thai = rightbrain._model_candidate_rejection_reasons(
            "てか、そのโนリは何だよ、わけわからない。",
            logic,
            80,
        )
        fullwidth_period = rightbrain._model_candidate_rejection_reasons(
            "今日は無理しないで休め．",
            logic,
            80,
        )

        self.assertIn("foreign_script_leak", thai)
        self.assertIn("nonstandard_punctuation", fullwidth_period)

    def test_gate_rejects_model_caregiver_or_customer_service_drift(self):
        rightbrain = RightBrain(load_model=False)
        logic = reply_anxiety_logic()

        for reply in (
            "今日は小さなことから始めようね。大丈夫だよ、手伝ってあげる。",
            "今日は体調に合わせて軽いものから始めてみてはどう？",
            "コーヒーやりませんかね？控えめにして。",
        ):
            with self.subTest(reply=reply):
                reasons = rightbrain._model_candidate_rejection_reasons(reply, logic, 90)
                self.assertIn("polite_tone_drift", reasons)

    def test_prepare_does_not_localize_pure_romaji_sentence(self):
        rightbrain = RightBrain(load_model=False)
        logic = {
            "scene": "memory",
            "intent": "explicit_memory_answer",
            "dialogue_act": "advice",
            "required_marker_groups": [["胃"], ["コーヒー"], ["控え"], ["少"]],
            "constraints": {"max_chars": 80},
        }

        candidate, reasons = rightbrain._prepare_model_surface_candidate(
            "saikin stomach ga yowai kara coffee wa sukoshi hikaeme ni shiro.",
            logic,
            user_input="最近胃が弱いけど、今日コーヒー飲んでもいい？",
            memory_data=MEMORY,
            max_chars=80,
        )

        self.assertEqual(candidate, "")
        self.assertIn("missing_japanese_surface", reasons)

    def test_prepare_keeps_clean_semantically_complete_model_variant(self):
        rightbrain = RightBrain(load_model=False)
        logic = {
            "scene": "daily",
            "intent": "daily_state",
            "dialogue_act": "daily_state_answer",
            "required_marker_groups": [["今", "だら", "ぼー", "休ん"]],
            "constraints": {"max_chars": 80},
        }

        candidate, reasons = rightbrain._prepare_model_surface_candidate(
            "今はちょっと怠け気味かな。",
            logic,
            user_input="今なにしてるの？",
            memory_data=MEMORY,
            max_chars=80,
        )

        self.assertEqual(reasons, [])
        self.assertIn("怠け", candidate)
        self.assertNotIn("だらっとしてる。話すくらいなら普通にいける", candidate)

    def test_prepare_keeps_semantically_incomplete_model_variant_rejected(self):
        rightbrain = RightBrain(load_model=False)
        logic = {
            "scene": "support",
            "intent": "tired_support",
            "dialogue_act": "emotional_containment",
            "required_marker_groups": [["休", "無理", "疲", "寝", "回復", "しんど"]],
            "constraints": {"max_chars": 80},
        }

        candidate, reasons = rightbrain._prepare_model_surface_candidate(
            "今日は少し早めに行こう。",
            logic,
            user_input="疲れた",
            memory_data=MEMORY,
            max_chars=80,
        )

        self.assertEqual(candidate, "")
        self.assertTrue(any(reason.startswith("semantic_slots_missing:") for reason in reasons))

    def test_prepare_keeps_ascii_candidate_with_chinese_pollution_rejected(self):
        rightbrain = RightBrain(load_model=False)
        logic = {
            "required_marker_groups": [["胃"], ["コーヒー"], ["控え"], ["少"]],
            "constraints": {"max_chars": 80},
        }

        candidate, reasons = rightbrain._prepare_model_surface_candidate(
            "最近は gastric なので、コーヒー是少量较好哦。",
            logic,
            user_input="胃が弱いけどコーヒー飲みたい",
            memory_data=MEMORY,
            max_chars=80,
        )

        self.assertEqual(candidate, "")
        self.assertIn("cjk_language_leak", reasons)
        self.assertTrue(any(reason.startswith("semantic_slots_missing:") for reason in reasons))

    def test_surface_semantic_hits_share_colloquial_marker_variants(self):
        rightbrain = RightBrain(load_model=False)
        logic = {
            "required_marker_groups": [
                ["返信"],
                ["分から"],
            ]
        }

        groups, hits = rightbrain._surface_semantic_group_hits(
            "返事がまだ来なくても、理由は分かんねんよな。",
            logic,
        )

        self.assertEqual(groups, [("返信",), ("分から",)])
        self.assertEqual(hits, [True, True])

    def test_gate_rejects_polite_questions_missed_by_previous_pattern(self):
        rightbrain = RightBrain(load_model=False)
        logic = reply_anxiety_logic()
        polite_replies = (
            "今日は体調に合わせて軽いものから始めてみてはどうですか？",
            "その断片について詳しく教えてもらえますか？",
            "今日は早めに休んだ方がいいでしょう。",
            "もう少し待っていただけますか？",
        )

        for reply in polite_replies:
            with self.subTest(reply=reply):
                reasons = rightbrain._model_candidate_rejection_reasons(reply, logic, 80)
                self.assertIn("polite_tone_drift", reasons)

    def test_gate_keeps_casual_question_and_suggestion_forms(self):
        rightbrain = RightBrain(load_model=False)
        logic = reply_anxiety_logic()
        casual_replies = (
            "今日は軽いものから始めてみたら？",
            "その断片、もう少し詳しく教えてくれる？",
            "分からんけど、少し待ってみる？",
        )

        for reply in casual_replies:
            with self.subTest(reply=reply):
                reasons = rightbrain._model_candidate_rejection_reasons(reply, logic, 80)
                self.assertNotIn("polite_tone_drift", reasons)

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
