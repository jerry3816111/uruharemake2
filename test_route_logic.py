import os
import sys
import unittest

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
EXPECTED_PYTHON = os.path.join(BASE_DIR, "Style-Bert-VITS2", "venv", "bin", "python")
EXPECTED_VENV = os.path.dirname(os.path.dirname(EXPECTED_PYTHON))


def _ensure_test_python():
    if os.path.exists(EXPECTED_PYTHON) and os.path.normpath(sys.prefix) != os.path.normpath(EXPECTED_VENV):
        clean_env = os.environ.copy()
        for key in ("PYTHONHOME", "PYTHONPATH", "CONDA_PREFIX", "CONDA_DEFAULT_ENV"):
            clean_env.pop(key, None)
        clean_env["VIRTUAL_ENV"] = EXPECTED_VENV
        clean_env["PATH"] = os.path.dirname(EXPECTED_PYTHON) + os.pathsep + clean_env.get("PATH", "")
        clean_env["URUHA_SKIP_AUTO_VENV"] = "1"
        os.execve(EXPECTED_PYTHON, [EXPECTED_PYTHON, __file__], clean_env)


_ensure_test_python()
os.environ["URUHA_SKIP_AUTO_VENV"] = "1"

if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

import uruha_brain_mac as brain_mod
from fast_eval_brain import build_fast_brain


class TestRouteLogic(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.brain = build_fast_brain(brain_mod)

    def setUp(self):
        self.brain.reset_session()

    def _route_for(self, user_input, expected_intent, expected_valence, recent_turns=None):
        self.brain.memory.session_turns = list(recent_turns or [])
        self.brain.runtime.set_prediction(expected_intent, expected_valence, "test")
        psyche = self.brain.psyche.get_state()
        mems = self.brain.memory.query_all_layers(user_input)
        actual_signal = self.brain.left_brain.classify_user_signal(user_input, psyche, mems)
        prediction_error = self.brain._compute_prediction_error(actual_signal)
        route = self.brain.left_brain._high_low_road_route(
            user_input,
            psyche,
            actual_signal=actual_signal,
            prediction_error=prediction_error,
        )
        return actual_signal, prediction_error, route

    def test_premise_doubt_stays_high_road_even_when_shocked(self):
        actual_signal, prediction_error, route = self._route_for(
            "之前不是說你是在北海道長大的嗎？",
            "relationship_followup",
            0.35,
        )
        self.assertEqual(actual_signal["actual_intent"], "premise_doubt")
        self.assertTrue(prediction_error["shock"])
        self.assertEqual(route["route"], "high_road")
        self.assertEqual(route["reason"], "prediction_error_deliberative_boundary")

    def test_explicit_abuse_still_hits_low_road_when_shocked(self):
        actual_signal, prediction_error, route = self._route_for(
            "你這白痴閉嘴",
            "chat_continuation",
            0.25,
        )
        self.assertEqual(actual_signal["actual_intent"], "abuse_pushback")
        self.assertTrue(prediction_error["shock"])
        self.assertEqual(route["route"], "low_road")
        self.assertEqual(route["intent"], "abuse_pushback")

    def test_correction_followup_stays_high_road_even_when_shocked(self):
        actual_signal, prediction_error, route = self._route_for(
            "不是啦你剛剛答錯了",
            "abuse_pushback",
            -0.9,
        )
        self.assertEqual(actual_signal["actual_intent"], "correction_followup")
        self.assertTrue(prediction_error["shock"])
        self.assertEqual(route["route"], "high_road")
        self.assertEqual(route["reason"], "prediction_error_directness_guard")

    def test_grounded_short_followup_stays_high_road_even_when_shocked(self):
        recent_turns = [
            {"user": "你有想我嗎？", "reply": "少しくらいは思ってる。", "intent": "ask_miss_me", "scene": "casual"},
        ]
        actual_signal, prediction_error, route = self._route_for(
            "那你呢？",
            "premise_doubt",
            -0.75,
            recent_turns=recent_turns,
        )
        self.assertEqual(actual_signal["actual_intent"], "ask_miss_me")
        self.assertTrue(prediction_error["shock"])
        self.assertEqual(route["route"], "high_road")
        self.assertEqual(route["reason"], "prediction_error_directness_guard")

    def test_relationship_current_state_followup_stays_high_road_even_when_shocked(self):
        recent_turns = [
            {"user": "你有想我嗎？", "reply": "少しくらいは思ってる。", "intent": "ask_miss_me", "scene": "casual"},
            {"user": "那你呢？", "reply": "うちも少しくらいは気にしてた。", "intent": "ask_miss_me", "scene": "casual"},
        ]
        actual_signal, prediction_error, route = self._route_for(
            "現在呢？",
            "abuse_pushback",
            -0.8,
            recent_turns=recent_turns,
        )
        self.assertEqual(actual_signal["actual_intent"], "ask_miss_me")
        self.assertTrue(prediction_error["shock"])
        self.assertEqual(route["route"], "high_road")
        self.assertEqual(route["reason"], "prediction_error_directness_guard")

    def test_relationship_fourth_turn_stays_high_road_even_when_shocked(self):
        recent_turns = [
            {"user": "你有想我嗎？", "reply": "少しくらいは思ってる。", "intent": "ask_miss_me", "scene": "casual"},
            {"user": "那你呢？", "reply": "うちも少しくらいは気にしてた。", "intent": "ask_miss_me", "scene": "casual"},
            {"user": "現在呢？", "reply": "今も少しくらいは気にしてる。", "intent": "ask_miss_me", "scene": "casual"},
        ]
        actual_signal, prediction_error, route = self._route_for(
            "現在也是嗎？",
            "abuse_pushback",
            -0.8,
            recent_turns=recent_turns,
        )
        self.assertEqual(actual_signal["actual_intent"], "ask_miss_me")
        self.assertTrue(prediction_error["shock"])
        self.assertEqual(route["route"], "high_road")
        self.assertEqual(route["reason"], "prediction_error_directness_guard")

    def test_relationship_thread_exits_to_meal_even_when_shocked(self):
        recent_turns = [
            {"user": "你有想我嗎？", "reply": "少しくらいは思ってる。", "intent": "ask_miss_me", "scene": "casual"},
            {"user": "那你呢？", "reply": "うちも少しくらいは気にしてた。", "intent": "ask_miss_me", "scene": "casual"},
            {"user": "現在呢？", "reply": "今も少しくらいは気にしてる。", "intent": "ask_miss_me", "scene": "casual"},
        ]
        actual_signal, prediction_error, route = self._route_for(
            "好那你晚餐吃了沒？",
            "abuse_pushback",
            -0.8,
            recent_turns=recent_turns,
        )
        self.assertEqual(actual_signal["actual_intent"], "chat")
        self.assertTrue(prediction_error["shock"])
        self.assertEqual(route["route"], "high_road")
        self.assertEqual(route["reason"], "prediction_error_directness_guard")

    def test_relationship_short_reentry_after_meal_shift_stays_high_road_even_when_shocked(self):
        recent_turns = [
            {"user": "你有想我嗎？", "reply": "少しくらいは思ってる。", "intent": "ask_miss_me", "scene": "casual"},
            {"user": "好那你晚餐吃了沒？", "reply": "一応食べた。ちゃんとしたのではないけど。", "intent": "chat", "scene": "casual"},
        ]
        actual_signal, prediction_error, route = self._route_for(
            "那剛剛那個呢？",
            "abuse_pushback",
            -0.8,
            recent_turns=recent_turns,
        )
        self.assertEqual(actual_signal["actual_intent"], "ask_miss_me")
        self.assertTrue(prediction_error["shock"])
        self.assertEqual(route["route"], "high_road")
        self.assertEqual(route["reason"], "prediction_error_directness_guard")

    def test_relationship_meal_ambiguous_that_fragment_clarifies_even_when_shocked(self):
        recent_turns = [
            {"user": "你有想我嗎？", "reply": "少しくらいは思ってる。", "intent": "ask_miss_me", "scene": "casual"},
            {"user": "你晚餐吃了沒？", "reply": "一応食べた。", "intent": "chat", "scene": "casual"},
        ]
        actual_signal, prediction_error, route = self._route_for(
            "那個呢？",
            "abuse_pushback",
            -0.8,
            recent_turns=recent_turns,
        )
        self.assertEqual(actual_signal["actual_intent"], "rephrase_simple")
        self.assertTrue(prediction_error["shock"])
        self.assertEqual(route["route"], "high_road")
        self.assertEqual(route["reason"], "prediction_error_directness_guard")

    def test_relationship_mixed_signal_prefers_food_even_when_shocked(self):
        recent_turns = [
            {"user": "你有想我嗎？", "reply": "少しくらいは思ってる。", "intent": "ask_miss_me", "scene": "casual"},
            {"user": "那你呢？", "reply": "うちも少しくらいは気にしてた。", "intent": "ask_miss_me", "scene": "casual"},
        ]
        actual_signal, prediction_error, route = self._route_for(
            "所以呢，那你現在要不要吃？",
            "abuse_pushback",
            -0.8,
            recent_turns=recent_turns,
        )
        self.assertEqual(actual_signal["actual_intent"], "food_offer_generic")
        self.assertTrue(prediction_error["shock"])
        self.assertEqual(route["route"], "high_road")
        self.assertEqual(route["reason"], "prediction_error_directness_guard")

    def test_clause_priority_meal_override_stays_high_road_even_when_shocked(self):
        recent_turns = [
            {"user": "你有想我嗎？", "reply": "少しくらいは思ってる。", "intent": "ask_miss_me", "scene": "casual"},
        ]
        actual_signal, prediction_error, route = self._route_for(
            "那個先不說，你晚餐吃了沒？",
            "abuse_pushback",
            -0.8,
            recent_turns=recent_turns,
        )
        self.assertEqual(actual_signal["actual_intent"], "chat")
        self.assertTrue(prediction_error["shock"])
        self.assertEqual(route["route"], "high_road")
        self.assertEqual(route["reason"], "prediction_error_directness_guard")

    def test_food_thread_followup_stays_high_road_even_when_shocked(self):
        recent_turns = [
            {"user": "你要不要吃蘋果派", "reply": "アップルパイなら一口ほしい。", "intent": "food_offer_sweet", "scene": "casual"},
            {"user": "那你呢？", "reply": "アップルパイならうちもあり。少しつまみたい。", "intent": "food_offer_sweet", "scene": "casual"},
        ]
        actual_signal, prediction_error, route = self._route_for(
            "現在還想吃嗎？",
            "abuse_pushback",
            -0.8,
            recent_turns=recent_turns,
        )
        self.assertEqual(actual_signal["actual_intent"], "food_offer_sweet")
        self.assertTrue(prediction_error["shock"])
        self.assertEqual(route["route"], "high_road")
        self.assertEqual(route["reason"], "prediction_error_directness_guard")

    def test_food_fourth_turn_stays_high_road_even_when_shocked(self):
        recent_turns = [
            {"user": "你要不要吃蘋果派", "reply": "アップルパイなら一口ほしい。", "intent": "food_offer_sweet", "scene": "casual"},
            {"user": "那你呢？", "reply": "アップルパイならうちもあり。少しつまみたい。", "intent": "food_offer_sweet", "scene": "casual"},
            {"user": "現在還想吃嗎？", "reply": "アップルパイなら今もほしい。甘いのならまだいける。", "intent": "food_offer_sweet", "scene": "casual"},
        ]
        actual_signal, prediction_error, route = self._route_for(
            "現在也是蘋果派嗎？",
            "abuse_pushback",
            -0.8,
            recent_turns=recent_turns,
        )
        self.assertEqual(actual_signal["actual_intent"], "food_offer_sweet")
        self.assertTrue(prediction_error["shock"])
        self.assertEqual(route["route"], "high_road")
        self.assertEqual(route["reason"], "prediction_error_directness_guard")

    def test_food_short_reentry_after_status_shift_stays_high_road_even_when_shocked(self):
        recent_turns = [
            {"user": "你要不要吃蘋果派", "reply": "アップルパイなら一口ほしい。", "intent": "food_offer_sweet", "scene": "casual"},
            {"user": "那你現在在幹嘛？", "reply": "今はちょっとだらけてる。少し休んでた。", "intent": "what_are_you_doing", "scene": "casual"},
        ]
        actual_signal, prediction_error, route = self._route_for(
            "所以蘋果派那個呢？",
            "abuse_pushback",
            -0.8,
            recent_turns=recent_turns,
        )
        self.assertEqual(actual_signal["actual_intent"], "food_offer_sweet")
        self.assertTrue(prediction_error["shock"])
        self.assertEqual(route["route"], "high_road")
        self.assertEqual(route["reason"], "prediction_error_directness_guard")

    def test_food_status_ambiguous_so_then_fragment_clarifies_even_when_shocked(self):
        recent_turns = [
            {"user": "你要不要吃蘋果派", "reply": "アップルパイなら一口ほしい。", "intent": "food_offer_sweet", "scene": "casual"},
            {"user": "你現在在幹嘛？", "reply": "今は少し休んでる。", "intent": "what_are_you_doing", "scene": "casual"},
        ]
        actual_signal, prediction_error, route = self._route_for(
            "所以呢？",
            "abuse_pushback",
            -0.8,
            recent_turns=recent_turns,
        )
        self.assertEqual(actual_signal["actual_intent"], "rephrase_simple")
        self.assertTrue(prediction_error["shock"])
        self.assertEqual(route["route"], "high_road")
        self.assertEqual(route["reason"], "prediction_error_directness_guard")

    def test_clause_priority_food_then_status_override_stays_high_road_even_when_shocked(self):
        recent_turns = [
            {"user": "你要不要吃蘋果派", "reply": "アップルパイなら一口ほしい。", "intent": "food_offer_sweet", "scene": "casual"},
        ]
        actual_signal, prediction_error, route = self._route_for(
            "蘋果派那個等一下，我是問你現在在幹嘛",
            "abuse_pushback",
            -0.8,
            recent_turns=recent_turns,
        )
        self.assertEqual(actual_signal["actual_intent"], "what_are_you_doing")
        self.assertTrue(prediction_error["shock"])
        self.assertEqual(route["route"], "high_road")
        self.assertEqual(route["reason"], "prediction_error_directness_guard")

    def test_repair_target_followup_stays_high_road_even_when_shocked(self):
        recent_turns = [
            {
                "user": "你剛剛那句是什麼意思",
                "reply": "さっきのどの部分だよ。単語でもいいから言え。",
                "intent": "rephrase_simple",
                "scene": "casual",
            },
        ]
        actual_signal, prediction_error, route = self._route_for(
            "就是最後那句",
            "abuse_pushback",
            -0.8,
            recent_turns=recent_turns,
        )
        self.assertEqual(actual_signal["actual_intent"], "rephrase_simple")
        self.assertTrue(prediction_error["shock"])
        self.assertEqual(route["route"], "high_road")
        self.assertEqual(route["reason"], "prediction_error_directness_guard")

    def test_repair_confirmation_followup_stays_high_road_even_when_shocked(self):
        recent_turns = [
            {
                "user": "你剛剛那句是什麼意思",
                "reply": "さっきのどの部分だよ。単語でもいいから言え。",
                "intent": "rephrase_simple",
                "scene": "casual",
            },
            {
                "user": "就是最後那句",
                "reply": "分かった、最後の一言の意味から言い直す。",
                "intent": "rephrase_simple",
                "scene": "casual",
            },
        ]
        actual_signal, prediction_error, route = self._route_for(
            "所以你是那個意思？",
            "abuse_pushback",
            -0.8,
            recent_turns=recent_turns,
        )
        self.assertEqual(actual_signal["actual_intent"], "rephrase_simple")
        self.assertTrue(prediction_error["shock"])
        self.assertEqual(route["route"], "high_road")
        self.assertEqual(route["reason"], "prediction_error_directness_guard")

    def test_repair_thread_exits_to_status_even_when_shocked(self):
        recent_turns = [
            {
                "user": "你剛剛那句是什麼意思",
                "reply": "さっきのどの部分だよ。単語でもいいから言え。",
                "intent": "rephrase_simple",
                "scene": "casual",
            },
            {
                "user": "就是最後那句",
                "reply": "分かった、最後の一言の意味から言い直す。",
                "intent": "rephrase_simple",
                "scene": "casual",
            },
            {
                "user": "所以你是那個意思？",
                "reply": "そういうこと。言い方が回っただけだ。",
                "intent": "rephrase_simple",
                "scene": "casual",
            },
        ]
        actual_signal, prediction_error, route = self._route_for(
            "那你現在在幹嘛？",
            "abuse_pushback",
            -0.8,
            recent_turns=recent_turns,
        )
        self.assertEqual(actual_signal["actual_intent"], "what_are_you_doing")
        self.assertTrue(prediction_error["shock"])
        self.assertEqual(route["route"], "high_road")
        self.assertEqual(route["reason"], "prediction_error_directness_guard")

    def test_repair_short_reentry_after_status_shift_stays_high_road_even_when_shocked(self):
        recent_turns = [
            {
                "user": "你剛剛那句是什麼意思",
                "reply": "さっきのどの部分だよ。単語でもいいから言え。",
                "intent": "rephrase_simple",
                "scene": "casual",
            },
            {
                "user": "那你現在在幹嘛？",
                "reply": "今はちょっとだらけてる。少し休んでた。",
                "intent": "what_are_you_doing",
                "scene": "casual",
            },
        ]
        actual_signal, prediction_error, route = self._route_for(
            "不是，我是說前面那句",
            "abuse_pushback",
            -0.8,
            recent_turns=recent_turns,
        )
        self.assertEqual(actual_signal["actual_intent"], "rephrase_simple")
        self.assertTrue(prediction_error["shock"])
        self.assertEqual(route["route"], "high_road")
        self.assertEqual(route["reason"], "prediction_error_directness_guard")

    def test_repair_generic_reentry_after_status_shift_stays_high_road_even_when_shocked(self):
        recent_turns = [
            {
                "user": "你剛剛那句是什麼意思",
                "reply": "さっきのどの部分だよ。単語でもいいから言え。",
                "intent": "rephrase_simple",
                "scene": "casual",
            },
            {
                "user": "那你現在在幹嘛？",
                "reply": "今はちょっとだらけてる。少し休んでた。",
                "intent": "what_are_you_doing",
                "scene": "casual",
            },
        ]
        actual_signal, prediction_error, route = self._route_for(
            "我是說前面的",
            "abuse_pushback",
            -0.8,
            recent_turns=recent_turns,
        )
        self.assertEqual(actual_signal["actual_intent"], "rephrase_simple")
        self.assertTrue(prediction_error["shock"])
        self.assertEqual(route["route"], "high_road")
        self.assertEqual(route["reason"], "prediction_error_directness_guard")

    def test_repair_status_ambiguous_front_that_fragment_clarifies_even_when_shocked(self):
        recent_turns = [
            {
                "user": "你剛剛那句是什麼意思",
                "reply": "さっきのどの部分だよ。単語でもいいから言え。",
                "intent": "rephrase_simple",
                "scene": "casual",
            },
            {
                "user": "那你現在在幹嘛？",
                "reply": "今は少し休んでる。",
                "intent": "what_are_you_doing",
                "scene": "casual",
            },
        ]
        actual_signal, prediction_error, route = self._route_for(
            "前面那個",
            "abuse_pushback",
            -0.8,
            recent_turns=recent_turns,
        )
        self.assertEqual(actual_signal["actual_intent"], "rephrase_simple")
        self.assertTrue(prediction_error["shock"])
        self.assertEqual(route["route"], "high_road")
        self.assertEqual(route["reason"], "prediction_error_directness_guard")

    def test_clause_priority_repair_to_status_override_stays_high_road_even_when_shocked(self):
        recent_turns = [
            {
                "user": "你剛剛那句是什麼意思",
                "reply": "さっきのどの部分だよ。単語でもいいから言え。",
                "intent": "rephrase_simple",
                "scene": "casual",
            },
        ]
        actual_signal, prediction_error, route = self._route_for(
            "不是前面那句啦，我現在問你還在忙嗎？",
            "abuse_pushback",
            -0.8,
            recent_turns=recent_turns,
        )
        self.assertEqual(actual_signal["actual_intent"], "what_are_you_doing")
        self.assertTrue(prediction_error["shock"])
        self.assertEqual(route["route"], "high_road")
        self.assertEqual(route["reason"], "prediction_error_directness_guard")

    def test_clause_conflict_no_punctuation_repair_to_status_stays_high_road_even_when_shocked(self):
        recent_turns = [
            {
                "user": "你剛剛那句是什麼意思",
                "reply": "さっきのどの部分だよ。単語でもいいから言え。",
                "intent": "rephrase_simple",
                "scene": "casual",
            },
        ]
        actual_signal, prediction_error, route = self._route_for(
            "不是前面那句啦我現在問你還在忙嗎",
            "abuse_pushback",
            -0.8,
            recent_turns=recent_turns,
        )
        self.assertEqual(actual_signal["actual_intent"], "what_are_you_doing")
        self.assertTrue(prediction_error["shock"])
        self.assertEqual(route["route"], "high_road")
        self.assertEqual(route["reason"], "prediction_error_directness_guard")

    def test_clause_priority_status_to_repair_override_stays_high_road_even_when_shocked(self):
        recent_turns = [
            {
                "user": "你在幹嘛",
                "reply": "今は少し休んでる。",
                "intent": "what_are_you_doing",
                "scene": "casual",
            },
        ]
        actual_signal, prediction_error, route = self._route_for(
            "現在忙不忙先不管，我是說剛剛那句到底什麼意思",
            "abuse_pushback",
            -0.8,
            recent_turns=recent_turns,
        )
        self.assertEqual(actual_signal["actual_intent"], "rephrase_simple")
        self.assertTrue(prediction_error["shock"])
        self.assertEqual(route["route"], "high_road")
        self.assertEqual(route["reason"], "prediction_error_directness_guard")

    def test_clause_conflict_no_punctuation_status_to_repair_stays_high_road_even_when_shocked(self):
        recent_turns = [
            {
                "user": "你在幹嘛",
                "reply": "今は少し休んでる。",
                "intent": "what_are_you_doing",
                "scene": "casual",
            },
        ]
        actual_signal, prediction_error, route = self._route_for(
            "現在忙不忙先不管我是說剛剛那句到底什麼意思",
            "abuse_pushback",
            -0.8,
            recent_turns=recent_turns,
        )
        self.assertEqual(actual_signal["actual_intent"], "rephrase_simple")
        self.assertTrue(prediction_error["shock"])
        self.assertEqual(route["route"], "high_road")
        self.assertEqual(route["reason"], "prediction_error_directness_guard")

    def test_clause_priority_relationship_override_stays_high_road_even_when_shocked(self):
        recent_turns = [
            {
                "user": "你剛剛那句是什麼意思",
                "reply": "さっきのどの部分だよ。単語でもいいから言え。",
                "intent": "rephrase_simple",
                "scene": "casual",
            },
        ]
        actual_signal, prediction_error, route = self._route_for(
            "我現在問的是你有沒有想我，不是剛剛那個",
            "abuse_pushback",
            -0.8,
            recent_turns=recent_turns,
        )
        self.assertEqual(actual_signal["actual_intent"], "ask_miss_me")
        self.assertTrue(prediction_error["shock"])
        self.assertEqual(route["route"], "high_road")
        self.assertEqual(route["reason"], "prediction_error_directness_guard")

    def test_clause_conflict_no_punctuation_food_then_status_stays_high_road_even_when_shocked(self):
        recent_turns = [
            {"user": "你要不要吃蘋果派", "reply": "アップルパイなら一口ほしい。", "intent": "food_offer_sweet", "scene": "casual"},
        ]
        actual_signal, prediction_error, route = self._route_for(
            "蘋果派那個等一下我是在問你現在在幹嘛",
            "abuse_pushback",
            -0.8,
            recent_turns=recent_turns,
        )
        self.assertEqual(actual_signal["actual_intent"], "what_are_you_doing")
        self.assertTrue(prediction_error["shock"])
        self.assertEqual(route["route"], "high_road")
        self.assertEqual(route["reason"], "prediction_error_directness_guard")

    def test_clause_conflict_no_punctuation_relationship_override_stays_high_road_even_when_shocked(self):
        recent_turns = [
            {
                "user": "你剛剛那句是什麼意思",
                "reply": "さっきのどの部分だよ。単語でもいいから言え。",
                "intent": "rephrase_simple",
                "scene": "casual",
            },
        ]
        actual_signal, prediction_error, route = self._route_for(
            "我現在問的是你有沒有想我不是剛剛那個",
            "abuse_pushback",
            -0.8,
            recent_turns=recent_turns,
        )
        self.assertEqual(actual_signal["actual_intent"], "ask_miss_me")
        self.assertTrue(prediction_error["shock"])
        self.assertEqual(route["route"], "high_road")
        self.assertEqual(route["reason"], "prediction_error_directness_guard")

    def test_clause_conflict_no_punctuation_meal_override_stays_high_road_even_when_shocked(self):
        recent_turns = [
            {"user": "你有想我嗎？", "reply": "少しくらいは思ってる。", "intent": "ask_miss_me", "scene": "casual"},
        ]
        actual_signal, prediction_error, route = self._route_for(
            "那個先不說所以你晚餐吃了沒",
            "abuse_pushback",
            -0.8,
            recent_turns=recent_turns,
        )
        self.assertEqual(actual_signal["actual_intent"], "chat")
        self.assertTrue(prediction_error["shock"])
        self.assertEqual(route["route"], "high_road")
        self.assertEqual(route["reason"], "prediction_error_directness_guard")

    def test_weak_override_focus_status_beats_repair_residue_even_when_shocked(self):
        recent_turns = [
            {
                "user": "你剛剛那句是什麼意思",
                "reply": "さっきのどの部分だよ。単語でもいいから言え。",
                "intent": "rephrase_simple",
                "scene": "casual",
            },
        ]
        actual_signal, prediction_error, route = self._route_for(
            "不是那個我是問你現在咧",
            "abuse_pushback",
            -0.8,
            recent_turns=recent_turns,
        )
        self.assertEqual(actual_signal["actual_intent"], "what_are_you_doing")
        self.assertTrue(prediction_error["shock"])
        self.assertEqual(route["route"], "high_road")
        self.assertEqual(route["reason"], "prediction_error_directness_guard")

    def test_audit_bucket_repair_defer_then_current_now_stays_high_road_even_when_shocked(self):
        recent_turns = [
            {
                "user": "你剛剛那句是什麼意思",
                "reply": "さっきのどの部分だよ。単語でもいいから言え。",
                "intent": "rephrase_simple",
                "scene": "casual",
            },
        ]
        actual_signal, prediction_error, route = self._route_for(
            "前面那句先不管那你現在呢",
            "abuse_pushback",
            -0.8,
            recent_turns=recent_turns,
        )
        self.assertEqual(actual_signal["actual_intent"], "what_are_you_doing")
        self.assertTrue(prediction_error["shock"])
        self.assertEqual(route["route"], "high_road")
        self.assertEqual(route["reason"], "prediction_error_directness_guard")

    def test_audit_bucket_repair_not_that_then_current_now_stays_high_road_even_when_shocked(self):
        recent_turns = [
            {
                "user": "你剛剛那句是什麼意思",
                "reply": "さっきのどの部分だよ。単語でもいいから言え。",
                "intent": "rephrase_simple",
                "scene": "casual",
            },
        ]
        actual_signal, prediction_error, route = self._route_for(
            "不是前面那句那你現在呢",
            "abuse_pushback",
            -0.8,
            recent_turns=recent_turns,
        )
        self.assertEqual(actual_signal["actual_intent"], "what_are_you_doing")
        self.assertTrue(prediction_error["shock"])
        self.assertEqual(route["route"], "high_road")
        self.assertEqual(route["reason"], "prediction_error_directness_guard")

    def test_audit_bucket_food_defer_then_current_now_stays_high_road_even_when_shocked(self):
        recent_turns = [
            {"user": "你要不要吃蘋果派", "reply": "アップルパイなら一口ほしい。", "intent": "food_offer_sweet", "scene": "casual"},
        ]
        actual_signal, prediction_error, route = self._route_for(
            "蘋果派那個先不管那你現在呢",
            "abuse_pushback",
            -0.8,
            recent_turns=recent_turns,
        )
        self.assertEqual(actual_signal["actual_intent"], "what_are_you_doing")
        self.assertTrue(prediction_error["shock"])
        self.assertEqual(route["route"], "high_road")
        self.assertEqual(route["reason"], "prediction_error_directness_guard")

    def test_weak_override_defer_status_beats_repair_residue_even_when_shocked(self):
        recent_turns = [
            {
                "user": "你剛剛那句是什麼意思",
                "reply": "さっきのどの部分だよ。単語でもいいから言え。",
                "intent": "rephrase_simple",
                "scene": "casual",
            },
        ]
        actual_signal, prediction_error, route = self._route_for(
            "剛剛那個先放著你現在在幹嘛",
            "abuse_pushback",
            -0.8,
            recent_turns=recent_turns,
        )
        self.assertEqual(actual_signal["actual_intent"], "what_are_you_doing")
        self.assertTrue(prediction_error["shock"])
        self.assertEqual(route["route"], "high_road")
        self.assertEqual(route["reason"], "prediction_error_directness_guard")

    def test_weak_override_audit_case_repair_to_status_stays_high_road_even_when_shocked(self):
        recent_turns = [
            {
                "user": "你剛剛那句是什麼意思",
                "reply": "さっきのどの部分だよ。単語でもいいから言え。",
                "intent": "rephrase_simple",
                "scene": "casual",
            },
        ]
        actual_signal, prediction_error, route = self._route_for(
            "前面那句先不管那你現在呢",
            "abuse_pushback",
            -0.8,
            recent_turns=recent_turns,
        )
        self.assertEqual(actual_signal["actual_intent"], "what_are_you_doing")
        self.assertTrue(prediction_error["shock"])
        self.assertEqual(route["route"], "high_road")
        self.assertEqual(route["reason"], "prediction_error_directness_guard")

    def test_weak_override_audit_case_repair_negation_to_status_stays_high_road_even_when_shocked(self):
        recent_turns = [
            {
                "user": "你剛剛那句是什麼意思",
                "reply": "さっきのどの部分だよ。単語でもいいから言え。",
                "intent": "rephrase_simple",
                "scene": "casual",
            },
        ]
        actual_signal, prediction_error, route = self._route_for(
            "不是前面那句那你現在呢",
            "abuse_pushback",
            -0.8,
            recent_turns=recent_turns,
        )
        self.assertEqual(actual_signal["actual_intent"], "what_are_you_doing")
        self.assertTrue(prediction_error["shock"])
        self.assertEqual(route["route"], "high_road")
        self.assertEqual(route["reason"], "prediction_error_directness_guard")

    def test_weak_override_audit_case_food_to_status_stays_high_road_even_when_shocked(self):
        recent_turns = [
            {"user": "你要不要吃蘋果派", "reply": "アップルパイなら一口ほしい。", "intent": "food_offer_sweet", "scene": "casual"},
        ]
        actual_signal, prediction_error, route = self._route_for(
            "蘋果派那個先不管那你現在呢",
            "abuse_pushback",
            -0.8,
            recent_turns=recent_turns,
        )
        self.assertEqual(actual_signal["actual_intent"], "what_are_you_doing")
        self.assertTrue(prediction_error["shock"])
        self.assertEqual(route["route"], "high_road")
        self.assertEqual(route["reason"], "prediction_error_directness_guard")

    def test_weak_override_relationship_followup_stays_high_road_even_when_shocked(self):
        recent_turns = [
            {"user": "你有想我嗎？", "reply": "少しくらいは思ってる。", "intent": "ask_miss_me", "scene": "casual"},
        ]
        actual_signal, prediction_error, route = self._route_for(
            "那個先不管所以你呢",
            "abuse_pushback",
            -0.8,
            recent_turns=recent_turns,
        )
        self.assertEqual(actual_signal["actual_intent"], "ask_miss_me")
        self.assertTrue(prediction_error["shock"])
        self.assertEqual(route["route"], "high_road")
        self.assertEqual(route["reason"], "prediction_error_directness_guard")

    def test_weak_override_repair_half_signal_minimally_clarifies_even_when_shocked(self):
        recent_turns = [
            {
                "user": "你剛剛那句是什麼意思",
                "reply": "さっきのどの部分だよ。単語でもいいから言え。",
                "intent": "rephrase_simple",
                "scene": "casual",
            },
        ]
        actual_signal, prediction_error, route = self._route_for(
            "那個先不管我是說剛剛那句",
            "abuse_pushback",
            -0.8,
            recent_turns=recent_turns,
        )
        self.assertEqual(actual_signal["actual_intent"], "rephrase_simple")
        self.assertTrue(prediction_error["shock"])
        self.assertEqual(route["route"], "high_road")
        self.assertEqual(route["reason"], "prediction_error_directness_guard")

    def test_weak_override_now_fragment_without_status_context_minimally_clarifies_even_when_shocked(self):
        recent_turns = [
            {
                "user": "你剛剛那句是什麼意思",
                "reply": "さっきのどの部分だよ。単語でもいいから言え。",
                "intent": "rephrase_simple",
                "scene": "casual",
            },
        ]
        actual_signal, prediction_error, route = self._route_for(
            "前面那個先放著那你現在呢",
            "abuse_pushback",
            -0.8,
            recent_turns=recent_turns,
        )
        self.assertEqual(actual_signal["actual_intent"], "rephrase_simple")
        self.assertTrue(prediction_error["shock"])
        self.assertEqual(route["route"], "high_road")
        self.assertEqual(route["reason"], "prediction_error_directness_guard")

    def test_weak_override_now_fragment_with_status_context_prefers_status_even_when_shocked(self):
        recent_turns = [
            {"user": "你在幹嘛", "reply": "今はちょっとだらけてる。少し休んでた。", "intent": "what_are_you_doing", "scene": "casual"},
        ]
        actual_signal, prediction_error, route = self._route_for(
            "前面那個先放著那你現在呢",
            "abuse_pushback",
            -0.8,
            recent_turns=recent_turns,
        )
        self.assertEqual(actual_signal["actual_intent"], "what_are_you_doing")
        self.assertTrue(prediction_error["shock"])
        self.assertEqual(route["route"], "high_road")
        self.assertEqual(route["reason"], "prediction_error_directness_guard")

    def test_direct_daily_status_stays_high_road_even_when_shocked(self):
        actual_signal, prediction_error, route = self._route_for(
            "你在幹嘛",
            "abuse_pushback",
            -0.85,
        )
        self.assertEqual(actual_signal["actual_intent"], "what_are_you_doing")
        self.assertTrue(prediction_error["shock"])
        self.assertEqual(route["route"], "high_road")
        self.assertEqual(route["reason"], "prediction_error_directness_guard")

    def test_status_today_followup_stays_high_road_even_when_shocked(self):
        recent_turns = [
            {"user": "你在幹嘛", "reply": "さっきまでだらけてた。今は少し休んでる。", "intent": "what_are_you_doing", "scene": "casual"},
            {"user": "現在呢？", "reply": "今はちょっとだらけてる。まだ休んでる。", "intent": "what_are_you_doing", "scene": "casual"},
        ]
        actual_signal, prediction_error, route = self._route_for(
            "今天也是這樣？",
            "abuse_pushback",
            -0.8,
            recent_turns=recent_turns,
        )
        self.assertEqual(actual_signal["actual_intent"], "what_are_you_doing")
        self.assertTrue(prediction_error["shock"])
        self.assertEqual(route["route"], "high_road")
        self.assertEqual(route["reason"], "prediction_error_directness_guard")

    def test_status_fourth_turn_stays_high_road_even_when_shocked(self):
        recent_turns = [
            {"user": "你在幹嘛", "reply": "さっきまでだらけてた。今は少し休んでる。", "intent": "what_are_you_doing", "scene": "casual"},
            {"user": "現在呢？", "reply": "今はちょっとだらけてる。まだ休んでる。", "intent": "what_are_you_doing", "scene": "casual"},
            {"user": "今天也是這樣？", "reply": "今日はだらっとしてた。動画開くか迷ってた。", "intent": "what_are_you_doing", "scene": "casual"},
        ]
        actual_signal, prediction_error, route = self._route_for(
            "現在還在發呆？",
            "abuse_pushback",
            -0.8,
            recent_turns=recent_turns,
        )
        self.assertEqual(actual_signal["actual_intent"], "what_are_you_doing")
        self.assertTrue(prediction_error["shock"])
        self.assertEqual(route["route"], "high_road")
        self.assertEqual(route["reason"], "prediction_error_directness_guard")

    def test_status_thread_exits_to_relationship_even_when_shocked(self):
        recent_turns = [
            {"user": "你在幹嘛", "reply": "さっきまでだらけてた。今は少し休んでる。", "intent": "what_are_you_doing", "scene": "casual"},
            {"user": "現在呢？", "reply": "今はちょっとだらけてる。まだ休んでる。", "intent": "what_are_you_doing", "scene": "casual"},
            {"user": "今天也是這樣？", "reply": "今日はだらっとしてた。動画開くか迷ってた。", "intent": "what_are_you_doing", "scene": "casual"},
        ]
        actual_signal, prediction_error, route = self._route_for(
            "那你有想我嗎？",
            "abuse_pushback",
            -0.8,
            recent_turns=recent_turns,
        )
        self.assertEqual(actual_signal["actual_intent"], "ask_miss_me")
        self.assertTrue(prediction_error["shock"])
        self.assertEqual(route["route"], "high_road")
        self.assertEqual(route["reason"], "prediction_error_directness_guard")

    def test_short_now_followup_prefers_active_relationship_even_when_shocked(self):
        recent_turns = [
            {"user": "你在幹嘛", "reply": "さっきまでだらけてた。今は少し休んでる。", "intent": "what_are_you_doing", "scene": "casual"},
            {"user": "那你有想我嗎？", "reply": "少しくらいは思ってる。", "intent": "ask_miss_me", "scene": "casual"},
        ]
        actual_signal, prediction_error, route = self._route_for(
            "那現在呢？",
            "abuse_pushback",
            -0.8,
            recent_turns=recent_turns,
        )
        self.assertEqual(actual_signal["actual_intent"], "ask_miss_me")
        self.assertTrue(prediction_error["shock"])
        self.assertEqual(route["route"], "high_road")
        self.assertEqual(route["reason"], "prediction_error_directness_guard")

    def test_multi_thread_short_window_disambiguation_stays_high_road_even_when_shocked(self):
        recent_turns = [
            {"user": "你在幹嘛", "reply": "さっきまでだらけてた。今は少し休んでる。", "intent": "what_are_you_doing", "scene": "casual"},
            {"user": "那你有想我嗎？", "reply": "少しくらいは思ってる。", "intent": "ask_miss_me", "scene": "casual"},
        ]
        actual_signal, prediction_error, route = self._route_for(
            "那現在是說你還忙嗎，還是剛剛那個？",
            "abuse_pushback",
            -0.8,
            recent_turns=recent_turns,
        )
        self.assertEqual(actual_signal["actual_intent"], "rephrase_simple")
        self.assertTrue(prediction_error["shock"])
        self.assertEqual(route["route"], "high_road")
        self.assertEqual(route["reason"], "prediction_error_directness_guard")

    def test_status_relationship_ambiguous_now_that_fragment_clarifies_even_when_shocked(self):
        recent_turns = [
            {"user": "你在幹嘛", "reply": "さっきまでだらけてた。今は少し休んでる。", "intent": "what_are_you_doing", "scene": "casual"},
            {"user": "那你有想我嗎？", "reply": "少しくらいは思ってる。", "intent": "ask_miss_me", "scene": "casual"},
        ]
        actual_signal, prediction_error, route = self._route_for(
            "那個現在呢？",
            "abuse_pushback",
            -0.8,
            recent_turns=recent_turns,
        )
        self.assertEqual(actual_signal["actual_intent"], "rephrase_simple")
        self.assertTrue(prediction_error["shock"])
        self.assertEqual(route["route"], "high_road")
        self.assertEqual(route["reason"], "prediction_error_directness_guard")


if __name__ == "__main__":
    unittest.main()
