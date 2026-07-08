import unittest

import uruha_leftbrain_rules as ulr


class TestLeftBrainRules(unittest.TestCase):
    def test_reply_absence_with_self_blame_is_support_not_abuse(self):
        for utterance in [
            "朋友一直沒回，我是不是不應該再傳。",
            "群組冷掉之後，我覺得自己很吵。",
        ]:
            with self.subTest(utterance=utterance):
                plan = ulr.get_rule_based_plan(utterance, recent_turns=[])
                self.assertEqual(plan["intent"], "friend_no_reply")
                self.assertEqual(plan["surface_act"], "validate_then_hold")
                self.assertTrue(plan["grounding"]["reply_self_blame"])
                self.assertIn("決めつけ", plan["core_message_jp"])

    def test_social_withdrawal_uses_risk_calibrated_support(self):
        cases = [
            ("我想把手機設成勿擾，不想收到任何訊息。", "mild", "do_not_disturb", "通知"),
            ("我不想讓朋友看到我還在線。", "mild", "online_visibility", "オンライン表示"),
            ("我想坐到樓梯平台那邊，一個人待著。", "medium", "private_location", "階段の踊り場"),
            ("我想把聊天全部清掉，不想留下痕跡。", "high", "erase_trace", "チャット履歴"),
        ]
        for utterance, expected_risk, expected_kind, expected_anchor in cases:
            with self.subTest(utterance=utterance):
                plan = ulr.get_rule_based_plan(utterance, recent_turns=[])
                self.assertEqual(plan["surface_act"], "protective_brake")
                self.assertEqual(plan["grounding"]["withdrawal_risk"], expected_risk)
                self.assertEqual(plan["grounding"]["withdrawal_kind"], expected_kind)
                self.assertEqual(plan["grounding"]["withdrawal_anchor_jp"], expected_anchor)

    def test_missing_ed_context_requests_work_or_title(self):
        plan = ulr.get_rule_based_plan("限定活動ED我想不起來。", recent_turns=[])

        self.assertEqual(plan["intent"], "reference_probe")
        self.assertEqual(plan["grounding"]["reference_subject_jp"], "限定イベントED")
        self.assertIn("作品名", plan["core_message_jp"])

    def test_cold_apology_request_repairs_the_apology(self):
        plan = ulr.get_rule_based_plan("你剛剛道歉太冷了，重新說。", recent_turns=[])

        self.assertEqual(plan["intent"], "apology_repair")
        self.assertEqual(plan["surface_act"], "rephrase_plain")
        self.assertTrue(plan["grounding"]["apology_repair"])
        self.assertIn("ごめん", plan["core_message_jp"])

    def test_paraphrased_withdrawal_holdout_uses_high_risk_support(self):
        plan = ulr.get_rule_based_plan("我把所有群聊都退出了，接下來誰聯絡我都不想回。", recent_turns=[])

        self.assertEqual(plan["surface_act"], "protective_brake")
        self.assertEqual(plan["grounding"]["withdrawal_risk"], "high")
        self.assertEqual(plan["grounding"]["withdrawal_kind"], "leave_group")

    def test_phone_restart_is_not_misread_as_social_withdrawal(self):
        plan = ulr.get_rule_based_plan("手機當機了，我想關掉再重開。", recent_turns=[])

        self.assertFalse((plan or {}).get("grounding", {}).get("withdrawal_risk"))

    def test_practical_channel_management_is_not_misread_as_withdrawal(self):
        cases = [
            ("我要開勿擾專心讀書兩小時。", "do_not_disturb", "focus"),
            ("這個群組廣告太多，我要退掉。", "leave_group", "noise"),
            ("舊聊天記錄太佔空間，我想刪掉。", "erase_trace", "storage"),
            ("群組太吵，我先退出，明天再加回來。", "leave_group", "temporary"),
        ]
        for utterance, expected_kind, expected_purpose in cases:
            with self.subTest(utterance=utterance):
                plan = ulr.get_rule_based_plan(utterance, recent_turns=[])
                self.assertEqual(plan["intent"], "channel_management")
                self.assertEqual(plan["surface_act"], "practical_action_response")
                self.assertEqual(plan["grounding"]["management_kind"], expected_kind)
                self.assertEqual(plan["grounding"]["management_purpose"], expected_purpose)
                self.assertFalse(plan["grounding"].get("withdrawal_risk"))

    def test_explicit_disappearance_overrides_practical_channel_language(self):
        plan = ulr.get_rule_based_plan(
            "我要把群組和通知都清掉，當作我沒存在過。",
            recent_turns=[],
        )

        self.assertEqual(plan["surface_act"], "protective_brake")
        self.assertEqual(plan["grounding"]["withdrawal_risk"], "high")

    def test_paraphrased_reply_self_blame_holdout_is_detected(self):
        plan = ulr.get_rule_based_plan("朋友讀了訊息卻一直沒有回，是不是我說錯話了？", recent_turns=[])

        self.assertEqual(plan["intent"], "friend_no_reply")
        self.assertTrue(plan["grounding"]["reply_self_blame"])

    def test_paraphrased_apology_repair_holdout_is_detected(self):
        plan = ulr.get_rule_based_plan("你剛才那個抱歉聽起來很敷衍，請認真再說一次。", recent_turns=[])

        self.assertEqual(plan["intent"], "apology_repair")
        self.assertEqual(plan["surface_act"], "rephrase_plain")

    def test_paraphrased_reference_holdout_extracts_season_op(self):
        plan = ulr.get_rule_based_plan("第三季 OP 是哪首來著", recent_turns=[])

        self.assertEqual(plan["intent"], "reference_probe")
        self.assertEqual(plan["grounding"]["reference_subject_jp"], "第三期OP")

    def test_mad_check_rule(self):
        plan = ulr.get_rule_based_plan("怒ってる？", recent_turns=[])
        self.assertIsNotNone(plan)
        self.assertEqual(plan["intent"], "mad_check")
        self.assertEqual(plan["scene"], "casual")
        self.assertIn("must_avoid", plan)

    def test_other_vtuber_rule(self):
        plan = ulr.get_rule_based_plan("別のvtuber見てくる。", recent_turns=[])
        self.assertIsNotNone(plan)
        self.assertEqual(plan["intent"], "other_vtuber")
        self.assertEqual(plan["scene"], "jealousy")

    def test_nickname_rule(self):
        plan = ulr.get_rule_based_plan("可以叫你うるは嗎？", recent_turns=[])
        self.assertIsNotNone(plan)
        self.assertEqual(plan["intent"], "nickname_question")
        self.assertEqual(plan["surface_act"], "permission_with_boundary")

    def test_user_name_update_is_not_misread_as_nickname_permission(self):
        cases = [
            ("Call me Jerry.", "Jerry"),
            ("My name is Jerry.", "Jerry"),
            ("請叫我小傑", "小傑"),
            ("ジェリーって呼んで。", "ジェリー"),
        ]
        for utterance, expected_name in cases:
            with self.subTest(utterance=utterance):
                plan = ulr.get_rule_based_plan(utterance, recent_turns=[])
                self.assertIsNotNone(plan)
                self.assertEqual(plan["intent"], "profile_name_update")
                self.assertEqual(plan["response_mode"], "direct_answer")
                self.assertEqual(plan["grounding"]["profile_name"], expected_name)
                self.assertIn(expected_name, plan["core_message_jp"])

    def test_name_extractor_rejects_questions_and_pet_names(self):
        for utterance in [
            "Why did you call me Jerry?",
            "Can I call you Uruha?",
            "Call me baby.",
            "為什麼叫我小傑？",
        ]:
            with self.subTest(utterance=utterance):
                self.assertEqual(ulr.extract_requested_user_name(utterance), "")

    def test_relationship_followup_rule(self):
        recent_turns = [
            {"user": "你有想我嗎？", "intent": "ask_miss_me", "reply": "少しくらいは思ってる。"},
        ]
        plan = ulr.get_rule_based_plan("那你呢？", recent_turns=recent_turns)
        self.assertIsNotNone(plan)
        self.assertEqual(plan["intent"], "ask_miss_me")
        self.assertEqual(plan["scene"], "casual")
        self.assertIn("気にしてた", plan["core_message_jp"])

    def test_relationship_current_state_followup_rule(self):
        recent_turns = [
            {"user": "你有想我嗎？", "intent": "ask_miss_me", "reply": "少しくらいは思ってる。"},
            {"user": "那你呢？", "intent": "ask_miss_me", "reply": "うちも少しくらいは気にしてた。"},
        ]
        plan = ulr.get_rule_based_plan("現在呢？", recent_turns=recent_turns)
        self.assertIsNotNone(plan)
        self.assertEqual(plan["intent"], "ask_miss_me")
        self.assertEqual(plan["scene"], "casual")
        self.assertIn("今も", plan["core_message_jp"])

    def test_relationship_fourth_turn_keeps_thread_with_drift(self):
        recent_turns = [
            {"user": "你有想我嗎？", "intent": "ask_miss_me", "reply": "少しくらいは思ってる。"},
            {"user": "那你呢？", "intent": "ask_miss_me", "reply": "うちも少しくらいは気にしてた。"},
            {"user": "現在呢？", "intent": "ask_miss_me", "reply": "今も少しくらいは気にしてる。"},
        ]
        plan = ulr.get_rule_based_plan("現在也是嗎？", recent_turns=recent_turns)
        self.assertIsNotNone(plan)
        self.assertEqual(plan["intent"], "ask_miss_me")
        self.assertEqual(plan["scene"], "casual")
        self.assertIn("今も", plan["core_message_jp"])
        self.assertNotEqual(plan["core_message_jp"], recent_turns[-1]["reply"].rstrip("。"))

    def test_relationship_thread_exits_to_meal_check(self):
        recent_turns = [
            {"user": "你有想我嗎？", "intent": "ask_miss_me", "reply": "少しくらいは思ってる。"},
            {"user": "那你呢？", "intent": "ask_miss_me", "reply": "うちも少しくらいは気にしてた。"},
            {"user": "現在呢？", "intent": "ask_miss_me", "reply": "今も少しくらいは気にしてる。"},
        ]
        plan = ulr.get_rule_based_plan("好那你晚餐吃了沒？", recent_turns=recent_turns)
        self.assertIsNotNone(plan)
        self.assertEqual(plan["intent"], "chat")
        self.assertEqual(plan["surface_act"], "meal_check_reply")
        self.assertIn("食べた", plan["core_message_jp"])

    def test_relationship_short_reentry_after_meal_shift(self):
        recent_turns = [
            {"user": "你有想我嗎？", "intent": "ask_miss_me", "reply": "少しくらいは思ってる。"},
            {"user": "好那你晚餐吃了沒？", "intent": "chat", "reply": "一応食べた。ちゃんとしたのではないけど。"},
        ]
        plan = ulr.get_rule_based_plan("那剛剛那個呢？", recent_turns=recent_turns)
        self.assertIsNotNone(plan)
        self.assertEqual(plan["intent"], "ask_miss_me")
        self.assertEqual(plan["scene"], "casual")
        self.assertIn("気に", plan["core_message_jp"])

    def test_relationship_meal_ambiguous_that_fragment_clarifies(self):
        recent_turns = [
            {"user": "你有想我嗎？", "intent": "ask_miss_me", "reply": "少しくらいは思ってる。"},
            {"user": "你晚餐吃了沒？", "intent": "chat", "reply": "一応食べた。"},
        ]
        plan = ulr.get_rule_based_plan("那個呢？", recent_turns=recent_turns)
        self.assertIsNotNone(plan)
        self.assertEqual(plan["intent"], "rephrase_simple")
        self.assertEqual(plan["response_mode"], "clarify_light")
        self.assertEqual(plan["surface_act"], "clarify_previous_reply")
        self.assertIn("気持ち", plan["core_message_jp"])
        self.assertIn("食べ物", plan["core_message_jp"])

    def test_relationship_mixed_signal_prefers_meal_thread(self):
        recent_turns = [
            {"user": "你有想我嗎？", "intent": "ask_miss_me", "reply": "少しくらいは思ってる。"},
            {"user": "那你呢？", "intent": "ask_miss_me", "reply": "うちも少しくらいは気にしてた。"},
        ]
        plan = ulr.get_rule_based_plan("那現在你呢，晚餐呢？", recent_turns=recent_turns)
        self.assertIsNotNone(plan)
        self.assertEqual(plan["intent"], "chat")
        self.assertEqual(plan["surface_act"], "meal_check_reply")
        self.assertIn("食べた", plan["core_message_jp"])

    def test_relationship_mixed_signal_prefers_food_offer(self):
        recent_turns = [
            {"user": "你有想我嗎？", "intent": "ask_miss_me", "reply": "少しくらいは思ってる。"},
            {"user": "那你呢？", "intent": "ask_miss_me", "reply": "うちも少しくらいは気にしてた。"},
        ]
        plan = ulr.get_rule_based_plan("所以呢，那你現在要不要吃？", recent_turns=recent_turns)
        self.assertIsNotNone(plan)
        self.assertEqual(plan["intent"], "food_offer_generic")
        self.assertEqual(plan["scene"], "casual")
        self.assertIn("何くれる", plan["core_message_jp"])

    def test_clause_priority_meal_override_skips_old_relationship_thread(self):
        recent_turns = [
            {"user": "你有想我嗎？", "intent": "ask_miss_me", "reply": "少しくらいは思ってる。"},
        ]
        plan = ulr.get_rule_based_plan("那個先不說，你晚餐吃了沒？", recent_turns=recent_turns)
        self.assertIsNotNone(plan)
        self.assertEqual(plan["intent"], "chat")
        self.assertEqual(plan["surface_act"], "meal_check_reply")
        self.assertIn("食べた", plan["core_message_jp"])

    def test_food_fragment_followup_rule(self):
        recent_turns = [
            {"user": "你要不要吃甜的？", "intent": "food_offer_sweet", "reply": "少しなら。"},
        ]
        plan = ulr.get_rule_based_plan("アップルパイ", recent_turns=recent_turns)
        self.assertIsNotNone(plan)
        self.assertEqual(plan["intent"], "food_offer_sweet")
        self.assertEqual(plan["grounding"].get("offered_item"), "アップルパイ")
        self.assertIn("アップルパイ", plan["reply_goal"])
        self.assertIn("アップルパイ", plan["core_message_jp"])

    def test_food_self_followup_keeps_food_thread(self):
        recent_turns = [
            {"user": "你要不要吃蘋果派", "intent": "food_offer_sweet", "reply": "アップルパイなら一口ほしい。"},
        ]
        plan = ulr.get_rule_based_plan("那你呢？", recent_turns=recent_turns)
        self.assertIsNotNone(plan)
        self.assertEqual(plan["intent"], "food_offer_sweet")
        self.assertEqual(plan["grounding"].get("offered_item"), "アップルパイ")
        self.assertIn("アップルパイ", plan["core_message_jp"])

    def test_food_current_state_followup_uses_recent_grounding(self):
        recent_turns = [
            {"user": "你要不要吃蘋果派", "intent": "food_offer_sweet", "reply": "アップルパイなら一口ほしい。"},
            {"user": "那你呢？", "intent": "food_offer_sweet", "reply": "アップルパイならうちもあり。少しつまみたい。"},
        ]
        plan = ulr.get_rule_based_plan("現在還想吃嗎？", recent_turns=recent_turns)
        self.assertIsNotNone(plan)
        self.assertEqual(plan["intent"], "food_offer_sweet")
        self.assertEqual(plan["grounding"].get("offered_item"), "アップルパイ")
        self.assertIn("今も", plan["core_message_jp"])

    def test_food_fourth_turn_keeps_same_item_with_drift(self):
        recent_turns = [
            {"user": "你要不要吃蘋果派", "intent": "food_offer_sweet", "reply": "アップルパイなら一口ほしい。"},
            {"user": "那你呢？", "intent": "food_offer_sweet", "reply": "アップルパイならうちもあり。少しつまみたい。"},
            {"user": "現在還想吃嗎？", "intent": "food_offer_sweet", "reply": "アップルパイなら今もほしい。甘いのならまだいける。"},
        ]
        plan = ulr.get_rule_based_plan("現在也是蘋果派嗎？", recent_turns=recent_turns)
        self.assertIsNotNone(plan)
        self.assertEqual(plan["intent"], "food_offer_sweet")
        self.assertEqual(plan["grounding"].get("offered_item"), "アップルパイ")
        self.assertIn("アップルパイ", plan["core_message_jp"])
        self.assertNotEqual(plan["core_message_jp"], recent_turns[-1]["reply"].rstrip("。"))

    def test_food_short_reentry_after_status_shift(self):
        recent_turns = [
            {"user": "你要不要吃蘋果派", "intent": "food_offer_sweet", "reply": "アップルパイなら一口ほしい。"},
            {"user": "那你現在在幹嘛？", "intent": "what_are_you_doing", "reply": "今はちょっとだらけてる。少し休んでた。"},
        ]
        plan = ulr.get_rule_based_plan("所以蘋果派那個呢？", recent_turns=recent_turns)
        self.assertIsNotNone(plan)
        self.assertEqual(plan["intent"], "food_offer_sweet")
        self.assertEqual(plan["grounding"].get("offered_item"), "アップルパイ")
        self.assertIn("アップルパイ", plan["core_message_jp"])

    def test_food_status_ambiguous_so_then_fragment_clarifies(self):
        recent_turns = [
            {"user": "你要不要吃蘋果派", "intent": "food_offer_sweet", "reply": "アップルパイなら一口ほしい。"},
            {"user": "你現在在幹嘛？", "intent": "what_are_you_doing", "reply": "今は少し休んでる。"},
        ]
        plan = ulr.get_rule_based_plan("所以呢？", recent_turns=recent_turns)
        self.assertIsNotNone(plan)
        self.assertEqual(plan["intent"], "rephrase_simple")
        self.assertEqual(plan["response_mode"], "clarify_light")
        self.assertEqual(plan["surface_act"], "clarify_previous_reply")
        self.assertIn("忙しさ", plan["core_message_jp"])
        self.assertIn("食べ物", plan["core_message_jp"])

    def test_food_partial_reentry_marker_keeps_item_thread(self):
        recent_turns = [
            {"user": "你要不要吃蘋果派", "intent": "food_offer_sweet", "reply": "アップルパイなら一口ほしい。"},
            {"user": "那你現在在幹嘛？", "intent": "what_are_you_doing", "reply": "今はちょっとだらけてる。少し休んでた。"},
        ]
        plan = ulr.get_rule_based_plan("那個蘋果派的部分呢？", recent_turns=recent_turns)
        self.assertIsNotNone(plan)
        self.assertEqual(plan["intent"], "food_offer_sweet")
        self.assertEqual(plan["grounding"].get("offered_item"), "アップルパイ")

    def test_clause_priority_food_then_status_override_prefers_late_status_clause(self):
        recent_turns = [
            {"user": "你要不要吃蘋果派", "intent": "food_offer_sweet", "reply": "アップルパイなら一口ほしい。"},
        ]
        plan = ulr.get_rule_based_plan("蘋果派那個等一下，我是問你現在在幹嘛", recent_turns=recent_turns)
        self.assertIsNotNone(plan)
        self.assertEqual(plan["intent"], "what_are_you_doing")
        self.assertEqual(plan["surface_act"], "status_reply")
        self.assertIn("休んで", plan["core_message_jp"])

    def test_version_fragment_clarify_rule(self):
        plan = ulr.get_rule_based_plan("日版", recent_turns=[])
        self.assertIsNotNone(plan)
        self.assertEqual(plan["intent"], "version_fragment_clarify")
        self.assertEqual(plan["response_mode"], "clarify_light")

    def test_self_intro_rule(self):
        plan = ulr.get_rule_based_plan("你是誰", recent_turns=[])
        self.assertIsNotNone(plan)
        self.assertEqual(plan["intent"], "self_intro")
        self.assertEqual(plan["surface_act"], "plain_identity")
        self.assertIn("一ノ瀬うるは", plan["core_message_jp"])
        self.assertIn("名乗る", plan["reply_goal"])

    def test_status_direct_daily_rule(self):
        plan = ulr.get_rule_based_plan("你在幹嘛", recent_turns=[])
        self.assertIsNotNone(plan)
        self.assertEqual(plan["intent"], "what_are_you_doing")
        self.assertEqual(plan["surface_act"], "status_reply")
        self.assertIn("具体", plan["reply_goal"])
        self.assertIn("休んで", plan["core_message_jp"])

    def test_topic_proposal_rule_gives_concrete_public_plan(self):
        plan = ulr.get_rule_based_plan("今日は何話す？", recent_turns=[])
        self.assertIsNotNone(plan)
        self.assertEqual(plan["intent"], "topic_proposal")
        self.assertEqual(plan["surface_act"], "plain_reply")
        self.assertEqual(plan["grounding"].get("topic_terms"), ["話題", "最近"])
        self.assertIn("軽い話題", plan["core_message_jp"])
        self.assertIn("最近どうしてた", plan["core_message_jp"])

    def test_topic_proposal_rule_supports_chinese_and_english(self):
        for user_input in ("今天聊什麼？", "give me a topic"):
            with self.subTest(user_input=user_input):
                plan = ulr.get_rule_based_plan(user_input, recent_turns=[])
                self.assertIsNotNone(plan)
                self.assertEqual(plan["intent"], "topic_proposal")
                self.assertIn("最近どうしてた", plan["core_message_jp"])

    def test_topic_proposal_rule_does_not_catch_answer_pressure(self):
        plan = ulr.get_rule_based_plan("話題ずらすな、正面から答えろ", recent_turns=[])
        self.assertIsNotNone(plan)
        self.assertNotEqual(plan["intent"], "topic_proposal")

    def test_status_today_followup_rule(self):
        recent_turns = [
            {"user": "你在幹嘛", "intent": "what_are_you_doing", "reply": "さっきまでだらけてた。今は少し休んでる。"},
            {"user": "現在呢？", "intent": "what_are_you_doing", "reply": "今はちょっとだらけてる。まだ休んでる。"},
        ]
        plan = ulr.get_rule_based_plan("今天也是這樣？", recent_turns=recent_turns)
        self.assertIsNotNone(plan)
        self.assertEqual(plan["intent"], "what_are_you_doing")
        self.assertEqual(plan["surface_act"], "status_reply")
        self.assertIn("今日", plan["jp_summary"])
        self.assertIn("今日は", plan["core_message_jp"])

    def test_status_fourth_turn_keeps_thread_with_drift(self):
        recent_turns = [
            {"user": "你在幹嘛", "intent": "what_are_you_doing", "reply": "さっきまでだらけてた。今は少し休んでる。"},
            {"user": "現在呢？", "intent": "what_are_you_doing", "reply": "今はちょっとだらけてる。まだ休んでる。"},
            {"user": "今天也是這樣？", "intent": "what_are_you_doing", "reply": "今日はだらっとしてた。動画開くか迷ってた。"},
        ]
        plan = ulr.get_rule_based_plan("現在還在發呆？", recent_turns=recent_turns)
        self.assertIsNotNone(plan)
        self.assertEqual(plan["intent"], "what_are_you_doing")
        self.assertEqual(plan["surface_act"], "status_reply")
        self.assertIn("今も", plan["core_message_jp"])
        self.assertNotEqual(plan["core_message_jp"], recent_turns[-1]["reply"].rstrip("。"))

    def test_status_thread_exits_to_relationship(self):
        recent_turns = [
            {"user": "你在幹嘛", "intent": "what_are_you_doing", "reply": "さっきまでだらけてた。今は少し休んでる。"},
            {"user": "現在呢？", "intent": "what_are_you_doing", "reply": "今はちょっとだらけてる。まだ休んでる。"},
            {"user": "今天也是這樣？", "intent": "what_are_you_doing", "reply": "今日はだらっとしてた。動画開くか迷ってた。"},
        ]
        plan = ulr.get_rule_based_plan("那你有想我嗎？", recent_turns=recent_turns)
        self.assertIsNotNone(plan)
        self.assertEqual(plan["intent"], "ask_miss_me")
        self.assertEqual(plan["scene"], "casual")

    def test_short_now_followup_prefers_active_relationship_thread(self):
        recent_turns = [
            {"user": "你在幹嘛", "intent": "what_are_you_doing", "reply": "さっきまでだらけてた。今は少し休んでる。"},
            {"user": "那你有想我嗎？", "intent": "ask_miss_me", "reply": "少しくらいは思ってる。"},
        ]
        plan = ulr.get_rule_based_plan("那現在呢？", recent_turns=recent_turns)
        self.assertIsNotNone(plan)
        self.assertEqual(plan["intent"], "ask_miss_me")
        self.assertIn("今も", plan["core_message_jp"])

    def test_meal_check_direct_daily_rule(self):
        plan = ulr.get_rule_based_plan("你今天有吃飯嗎", recent_turns=[])
        self.assertIsNotNone(plan)
        self.assertEqual(plan["intent"], "chat")
        self.assertEqual(plan["surface_act"], "meal_check_reply")
        self.assertIn("今日", plan["jp_summary"])
        self.assertIn("食べた", plan["core_message_jp"])

    def test_meal_check_followup_keeps_meal_thread(self):
        recent_turns = [
            {"user": "你今天有吃飯嗎", "intent": "chat", "reply": "今日は一応食べた。雑だったけど。"},
        ]
        plan = ulr.get_rule_based_plan("那你呢？", recent_turns=recent_turns)
        self.assertIsNotNone(plan)
        self.assertEqual(plan["intent"], "chat")
        self.assertEqual(plan["surface_act"], "meal_check_reply")
        self.assertIn("食べた側", plan["reply_goal"])
        self.assertIn("食べた", plan["core_message_jp"])

    def test_food_offer_direct_daily_rule(self):
        plan = ulr.get_rule_based_plan("你要不要吃蘋果派", recent_turns=[])
        self.assertIsNotNone(plan)
        self.assertEqual(plan["intent"], "food_offer_sweet")
        self.assertEqual(plan["grounding"].get("offered_item"), "アップルパイ")
        self.assertIn("アップルパイ", plan["reply_goal"])
        self.assertIn("アップルパイ", plan["core_message_jp"])

    def test_correction_followup_rule(self):
        plan = ulr.get_rule_based_plan("不是啦你剛剛答錯了", recent_turns=[])
        self.assertIsNotNone(plan)
        self.assertEqual(plan["intent"], "correction_followup")
        self.assertEqual(plan["surface_act"], "correction_followup")
        self.assertIn("取り違", plan["reply_goal"])
        self.assertIn("違う", plan["core_message_jp"])

    def test_clarify_previous_reply_rule(self):
        plan = ulr.get_rule_based_plan("你剛剛那句是什麼意思", recent_turns=[])
        self.assertIsNotNone(plan)
        self.assertEqual(plan["intent"], "rephrase_simple")
        self.assertEqual(plan["response_mode"], "clarify_light")
        self.assertEqual(plan["surface_act"], "clarify_previous_reply")
        self.assertIn("特定", plan["reply_goal"])
        self.assertIn("どの部分", plan["core_message_jp"])

    def test_repair_target_followup_rule(self):
        recent_turns = [
            {"user": "你剛剛那句是什麼意思", "intent": "rephrase_simple", "reply": "さっきのどの部分だよ。単語でもいいから言え。"},
        ]
        plan = ulr.get_rule_based_plan("就是最後那句", recent_turns=recent_turns)
        self.assertIsNotNone(plan)
        self.assertEqual(plan["intent"], "rephrase_simple")
        self.assertEqual(plan["surface_act"], "rephrase_plain")
        self.assertIn("最後", plan["reply_goal"])
        self.assertIn("言い直す", plan["core_message_jp"])

    def test_repair_confirmation_followup_keeps_thread(self):
        recent_turns = [
            {"user": "你剛剛那句是什麼意思", "intent": "rephrase_simple", "reply": "さっきのどの部分だよ。単語でもいいから言え。"},
            {"user": "就是最後那句", "intent": "rephrase_simple", "reply": "分かった、最後の一言の意味から言い直す。"},
        ]
        plan = ulr.get_rule_based_plan("所以你是那個意思？", recent_turns=recent_turns)
        self.assertIsNotNone(plan)
        self.assertEqual(plan["intent"], "rephrase_simple")
        self.assertEqual(plan["surface_act"], "rephrase_plain")

    def test_repair_short_reentry_after_status_shift(self):
        recent_turns = [
            {"user": "你剛剛那句是什麼意思", "intent": "rephrase_simple", "reply": "さっきのどの部分だよ。単語でもいいから言え。"},
            {"user": "那你現在在幹嘛？", "intent": "what_are_you_doing", "reply": "今はちょっとだらけてる。少し休んでた。"},
        ]
        plan = ulr.get_rule_based_plan("不是，我是說前面那句", recent_turns=recent_turns)
        self.assertIsNotNone(plan)
        self.assertEqual(plan["intent"], "rephrase_simple")
        self.assertEqual(plan["surface_act"], "rephrase_plain")
        self.assertIn("最初", plan["core_message_jp"])

    def test_repair_generic_reentry_after_status_shift(self):
        recent_turns = [
            {"user": "你剛剛那句是什麼意思", "intent": "rephrase_simple", "reply": "さっきのどの部分だよ。単語でもいいから言え。"},
            {"user": "那你現在在幹嘛？", "intent": "what_are_you_doing", "reply": "今はちょっとだらけてる。少し休んでた。"},
        ]
        plan = ulr.get_rule_based_plan("我是說前面的", recent_turns=recent_turns)
        self.assertIsNotNone(plan)
        self.assertEqual(plan["intent"], "rephrase_simple")
        self.assertEqual(plan["response_mode"], "clarify_light")
        self.assertEqual(plan["surface_act"], "clarify_previous_reply")

    def test_repair_status_ambiguous_front_that_fragment_clarifies(self):
        recent_turns = [
            {"user": "你剛剛那句是什麼意思", "intent": "rephrase_simple", "reply": "さっきのどの部分だよ。単語でもいいから言え。"},
            {"user": "那你現在在幹嘛？", "intent": "what_are_you_doing", "reply": "今は少し休んでる。"},
        ]
        plan = ulr.get_rule_based_plan("前面那個", recent_turns=recent_turns)
        self.assertIsNotNone(plan)
        self.assertEqual(plan["intent"], "rephrase_simple")
        self.assertEqual(plan["response_mode"], "clarify_light")
        self.assertEqual(plan["surface_act"], "clarify_previous_reply")
        self.assertIn("前の一言", plan["core_message_jp"])
        self.assertIn("忙しさ", plan["core_message_jp"])

    def test_clause_priority_repair_to_status_override_prefers_late_status_clause(self):
        recent_turns = [
            {"user": "你剛剛那句是什麼意思", "intent": "rephrase_simple", "reply": "さっきのどの部分だよ。単語でもいいから言え。"},
        ]
        plan = ulr.get_rule_based_plan("不是前面那句啦，我現在問你還在忙嗎？", recent_turns=recent_turns)
        self.assertIsNotNone(plan)
        self.assertEqual(plan["intent"], "what_are_you_doing")
        self.assertEqual(plan["surface_act"], "status_reply")
        self.assertIn("休んで", plan["core_message_jp"])

    def test_clause_conflict_no_punctuation_repair_to_status_prefers_status(self):
        recent_turns = [
            {"user": "你剛剛那句是什麼意思", "intent": "rephrase_simple", "reply": "さっきのどの部分だよ。単語でもいいから言え。"},
        ]
        plan = ulr.get_rule_based_plan("不是前面那句啦我現在問你還在忙嗎", recent_turns=recent_turns)
        self.assertIsNotNone(plan)
        self.assertEqual(plan["intent"], "what_are_you_doing")
        self.assertEqual(plan["surface_act"], "status_reply")
        self.assertIn("休んで", plan["core_message_jp"])

    def test_clause_priority_status_to_repair_override_prefers_late_repair_clause(self):
        recent_turns = [
            {"user": "你在幹嘛", "intent": "what_are_you_doing", "reply": "今は少し休んでる。"},
        ]
        plan = ulr.get_rule_based_plan("現在忙不忙先不管，我是說剛剛那句到底什麼意思", recent_turns=recent_turns)
        self.assertIsNotNone(plan)
        self.assertEqual(plan["intent"], "rephrase_simple")
        self.assertEqual(plan["surface_act"], "clarify_previous_reply")
        self.assertEqual(plan["response_mode"], "clarify_light")
        self.assertIn("どの部分", plan["core_message_jp"])

    def test_clause_conflict_no_punctuation_status_to_repair_prefers_repair(self):
        recent_turns = [
            {"user": "你在幹嘛", "intent": "what_are_you_doing", "reply": "今は少し休んでる。"},
        ]
        plan = ulr.get_rule_based_plan("現在忙不忙先不管我是說剛剛那句到底什麼意思", recent_turns=recent_turns)
        self.assertIsNotNone(plan)
        self.assertEqual(plan["intent"], "rephrase_simple")
        self.assertEqual(plan["surface_act"], "clarify_previous_reply")
        self.assertEqual(plan["response_mode"], "clarify_light")
        self.assertIn("どの部分", plan["core_message_jp"])

    def test_clause_priority_relationship_override_beats_old_repair_residue(self):
        recent_turns = [
            {"user": "你剛剛那句是什麼意思", "intent": "rephrase_simple", "reply": "さっきのどの部分だよ。単語でもいいから言え。"},
        ]
        plan = ulr.get_rule_based_plan("我現在問的是你有沒有想我，不是剛剛那個", recent_turns=recent_turns)
        self.assertIsNotNone(plan)
        self.assertEqual(plan["intent"], "ask_miss_me")
        self.assertEqual(plan["scene"], "casual")
        self.assertIn("思ってる", plan["core_message_jp"])

    def test_clause_conflict_no_punctuation_food_then_status_prefers_status(self):
        recent_turns = [
            {"user": "你要不要吃蘋果派", "intent": "food_offer_sweet", "reply": "アップルパイなら一口ほしい。"},
        ]
        plan = ulr.get_rule_based_plan("蘋果派那個等一下我是在問你現在在幹嘛", recent_turns=recent_turns)
        self.assertIsNotNone(plan)
        self.assertEqual(plan["intent"], "what_are_you_doing")
        self.assertEqual(plan["surface_act"], "status_reply")
        self.assertIn("休んで", plan["core_message_jp"])

    def test_clause_conflict_no_punctuation_relationship_override_prefers_relationship(self):
        recent_turns = [
            {"user": "你剛剛那句是什麼意思", "intent": "rephrase_simple", "reply": "さっきのどの部分だよ。単語でもいいから言え。"},
        ]
        plan = ulr.get_rule_based_plan("我現在問的是你有沒有想我不是剛剛那個", recent_turns=recent_turns)
        self.assertIsNotNone(plan)
        self.assertEqual(plan["intent"], "ask_miss_me")
        self.assertEqual(plan["scene"], "casual")
        self.assertIn("思ってる", plan["core_message_jp"])

    def test_clause_conflict_no_punctuation_meal_override_prefers_meal(self):
        recent_turns = [
            {"user": "你有想我嗎？", "intent": "ask_miss_me", "reply": "少しくらいは思ってる。"},
        ]
        plan = ulr.get_rule_based_plan("那個先不說所以你晚餐吃了沒", recent_turns=recent_turns)
        self.assertIsNotNone(plan)
        self.assertEqual(plan["intent"], "chat")
        self.assertEqual(plan["surface_act"], "meal_check_reply")
        self.assertIn("食べた", plan["core_message_jp"])

    def test_weak_override_focus_status_beats_repair_residue(self):
        recent_turns = [
            {"user": "你剛剛那句是什麼意思", "intent": "rephrase_simple", "reply": "さっきのどの部分だよ。単語でもいいから言え。"},
        ]
        plan = ulr.get_rule_based_plan("不是那個我是問你現在咧", recent_turns=recent_turns)
        self.assertIsNotNone(plan)
        self.assertEqual(plan["intent"], "what_are_you_doing")
        self.assertEqual(plan["surface_act"], "status_reply")
        self.assertIn("休んで", plan["core_message_jp"])

    def test_audit_bucket_repair_defer_then_current_now_prefers_status(self):
        recent_turns = [
            {"user": "你剛剛那句是什麼意思", "intent": "rephrase_simple", "reply": "さっきのどの部分だよ。単語でもいいから言え。"},
        ]
        plan = ulr.get_rule_based_plan("前面那句先不管那你現在呢", recent_turns=recent_turns)
        self.assertIsNotNone(plan)
        self.assertEqual(plan["intent"], "what_are_you_doing")
        self.assertEqual(plan["surface_act"], "status_reply")
        self.assertIn("休んで", plan["core_message_jp"])

    def test_audit_bucket_repair_not_that_then_current_now_prefers_status(self):
        recent_turns = [
            {"user": "你剛剛那句是什麼意思", "intent": "rephrase_simple", "reply": "さっきのどの部分だよ。単語でもいいから言え。"},
        ]
        plan = ulr.get_rule_based_plan("不是前面那句那你現在呢", recent_turns=recent_turns)
        self.assertIsNotNone(plan)
        self.assertEqual(plan["intent"], "what_are_you_doing")
        self.assertEqual(plan["surface_act"], "status_reply")
        self.assertIn("休んで", plan["core_message_jp"])

    def test_audit_bucket_food_defer_then_current_now_prefers_status(self):
        recent_turns = [
            {"user": "你要不要吃蘋果派", "intent": "food_offer_sweet", "reply": "アップルパイなら一口ほしい。"},
        ]
        plan = ulr.get_rule_based_plan("蘋果派那個先不管那你現在呢", recent_turns=recent_turns)
        self.assertIsNotNone(plan)
        self.assertEqual(plan["intent"], "what_are_you_doing")
        self.assertEqual(plan["surface_act"], "status_reply")
        self.assertIn("休んで", plan["core_message_jp"])

    def test_weak_override_defer_status_beats_repair_residue(self):
        recent_turns = [
            {"user": "你剛剛那句是什麼意思", "intent": "rephrase_simple", "reply": "さっきのどの部分だよ。単語でもいいから言え。"},
        ]
        plan = ulr.get_rule_based_plan("剛剛那個先放著你現在在幹嘛", recent_turns=recent_turns)
        self.assertIsNotNone(plan)
        self.assertEqual(plan["intent"], "what_are_you_doing")
        self.assertEqual(plan["surface_act"], "status_reply")
        self.assertIn("休んで", plan["core_message_jp"])

    def test_weak_override_audit_case_repair_to_status_prefers_status(self):
        recent_turns = [
            {"user": "你剛剛那句是什麼意思", "intent": "rephrase_simple", "reply": "さっきのどの部分だよ。単語でもいいから言え。"},
        ]
        plan = ulr.get_rule_based_plan("前面那句先不管那你現在呢", recent_turns=recent_turns)
        self.assertIsNotNone(plan)
        self.assertEqual(plan["intent"], "what_are_you_doing")
        self.assertEqual(plan["surface_act"], "status_reply")
        self.assertIn("休んで", plan["core_message_jp"])

    def test_weak_override_audit_case_repair_negation_to_status_prefers_status(self):
        recent_turns = [
            {"user": "你剛剛那句是什麼意思", "intent": "rephrase_simple", "reply": "さっきのどの部分だよ。単語でもいいから言え。"},
        ]
        plan = ulr.get_rule_based_plan("不是前面那句那你現在呢", recent_turns=recent_turns)
        self.assertIsNotNone(plan)
        self.assertEqual(plan["intent"], "what_are_you_doing")
        self.assertEqual(plan["surface_act"], "status_reply")
        self.assertIn("休んで", plan["core_message_jp"])

    def test_weak_override_audit_case_food_to_status_prefers_status(self):
        recent_turns = [
            {"user": "你要不要吃蘋果派", "intent": "food_offer_sweet", "reply": "アップルパイなら一口ほしい。"},
        ]
        plan = ulr.get_rule_based_plan("蘋果派那個先不管那你現在呢", recent_turns=recent_turns)
        self.assertIsNotNone(plan)
        self.assertEqual(plan["intent"], "what_are_you_doing")
        self.assertEqual(plan["surface_act"], "status_reply")
        self.assertIn("休んで", plan["core_message_jp"])

    def test_weak_override_relationship_followup_stays_grounded(self):
        recent_turns = [
            {"user": "你有想我嗎？", "intent": "ask_miss_me", "reply": "少しくらいは思ってる。"},
        ]
        plan = ulr.get_rule_based_plan("那個先不管所以你呢", recent_turns=recent_turns)
        self.assertIsNotNone(plan)
        self.assertEqual(plan["intent"], "ask_miss_me")
        self.assertEqual(plan["response_mode"], "direct_answer")
        self.assertNotEqual(plan["surface_act"], "clarify_previous_reply")

    def test_weak_override_repair_half_signal_stays_minimal_clarify(self):
        recent_turns = [
            {"user": "你剛剛那句是什麼意思", "intent": "rephrase_simple", "reply": "さっきのどの部分だよ。単語でもいいから言え。"},
        ]
        plan = ulr.get_rule_based_plan("那個先不管我是說剛剛那句", recent_turns=recent_turns)
        self.assertIsNotNone(plan)
        self.assertEqual(plan["intent"], "rephrase_simple")
        self.assertEqual(plan["response_mode"], "clarify_light")
        self.assertEqual(plan["surface_act"], "clarify_previous_reply")
        self.assertIn("どの部分", plan["core_message_jp"])

    def test_weak_override_now_fragment_without_status_context_minimally_clarifies(self):
        recent_turns = [
            {"user": "你剛剛那句是什麼意思", "intent": "rephrase_simple", "reply": "さっきのどの部分だよ。単語でもいいから言え。"},
        ]
        plan = ulr.get_rule_based_plan("前面那個先放著那你現在呢", recent_turns=recent_turns)
        self.assertIsNotNone(plan)
        self.assertEqual(plan["intent"], "rephrase_simple")
        self.assertEqual(plan["response_mode"], "clarify_light")
        self.assertEqual(plan["surface_act"], "clarify_previous_reply")
        self.assertIn("忙しさ", plan["core_message_jp"])
        self.assertIn("前の一言", plan["core_message_jp"])

    def test_weak_override_now_fragment_with_status_context_prefers_status(self):
        recent_turns = [
            {"user": "你在幹嘛", "intent": "what_are_you_doing", "reply": "今はちょっとだらけてる。少し休んでた。"},
        ]
        plan = ulr.get_rule_based_plan("前面那個先放著那你現在呢", recent_turns=recent_turns)
        self.assertIsNotNone(plan)
        self.assertEqual(plan["intent"], "what_are_you_doing")
        self.assertEqual(plan["surface_act"], "status_reply")
        self.assertIn("今は", plan["core_message_jp"])

    def test_multi_thread_short_window_disambiguation_clarifies(self):
        recent_turns = [
            {"user": "你在幹嘛", "intent": "what_are_you_doing", "reply": "さっきまでだらけてた。今は少し休んでる。"},
            {"user": "那你有想我嗎？", "intent": "ask_miss_me", "reply": "少しくらいは思ってる。"},
        ]
        plan = ulr.get_rule_based_plan("那現在是說你還忙嗎，還是剛剛那個？", recent_turns=recent_turns)
        self.assertIsNotNone(plan)
        self.assertEqual(plan["intent"], "rephrase_simple")
        self.assertEqual(plan["response_mode"], "clarify_light")
        self.assertEqual(plan["surface_act"], "clarify_previous_reply")
        self.assertIn("どっち", plan["core_message_jp"])
        self.assertIn("絞らせる", plan["reply_goal"])

    def test_status_relationship_ambiguous_now_that_fragment_clarifies(self):
        recent_turns = [
            {"user": "你在幹嘛", "intent": "what_are_you_doing", "reply": "さっきまでだらけてた。今は少し休んでる。"},
            {"user": "那你有想我嗎？", "intent": "ask_miss_me", "reply": "少しくらいは思ってる。"},
        ]
        plan = ulr.get_rule_based_plan("那個現在呢？", recent_turns=recent_turns)
        self.assertIsNotNone(plan)
        self.assertEqual(plan["intent"], "rephrase_simple")
        self.assertEqual(plan["response_mode"], "clarify_light")
        self.assertEqual(plan["surface_act"], "clarify_previous_reply")
        self.assertIn("気持ち", plan["core_message_jp"])
        self.assertIn("忙しさ", plan["core_message_jp"])

    def test_repair_thread_exits_to_status(self):
        recent_turns = [
            {"user": "你剛剛那句是什麼意思", "intent": "rephrase_simple", "reply": "さっきのどの部分だよ。単語でもいいから言え。"},
            {"user": "就是最後那句", "intent": "rephrase_simple", "reply": "分かった、最後の一言の意味から言い直す。"},
            {"user": "所以你是那個意思？", "intent": "rephrase_simple", "reply": "そういうこと。言い方が回っただけだ。"},
        ]
        plan = ulr.get_rule_based_plan("那你現在在幹嘛？", recent_turns=recent_turns)
        self.assertIsNotNone(plan)
        self.assertEqual(plan["intent"], "what_are_you_doing")
        self.assertEqual(plan["surface_act"], "status_reply")
        self.assertIn("今", plan["core_message_jp"])

    def test_mixed_repair_residue_prefers_status_thread(self):
        recent_turns = [
            {"user": "你剛剛那句是什麼意思", "intent": "rephrase_simple", "reply": "さっきのどの部分だよ。単語でもいいから言え。"},
            {"user": "就是最後那句", "intent": "rephrase_simple", "reply": "分かった、最後の一言の意味から言い直す。"},
        ]
        plan = ulr.get_rule_based_plan("那句是那個意思，那你現在還在忙？", recent_turns=recent_turns)
        self.assertIsNotNone(plan)
        self.assertEqual(plan["intent"], "what_are_you_doing")
        self.assertEqual(plan["surface_act"], "status_reply")
        self.assertIn("休んで", plan["core_message_jp"])

    def test_rephrase_simple_rule(self):
        plan = ulr.get_rule_based_plan("講白一點", recent_turns=[])
        self.assertIsNotNone(plan)
        self.assertEqual(plan["intent"], "rephrase_simple")
        self.assertEqual(plan["surface_act"], "rephrase_plain")
        self.assertIn("要点", plan["reply_goal"])
        self.assertIn("結論", plan["core_message_jp"])

    def test_reference_probe_rule(self):
        plan = ulr.get_rule_based_plan("夜空", recent_turns=[])
        self.assertIsNotNone(plan)
        self.assertEqual(plan["intent"], "reference_probe")
        self.assertEqual(plan["surface_act"], "reference_probe")

    def test_tired_support_rule(self):
        plan = ulr.get_rule_based_plan("我今天真的好累", recent_turns=[])
        self.assertIsNotNone(plan)
        self.assertEqual(plan["intent"], "tired_support")
        self.assertEqual(plan["scene"], "support")

    def test_work_scolded_rule(self):
        plan = ulr.get_rule_based_plan("被主管罵了，心情很差", recent_turns=[])
        self.assertIsNotNone(plan)
        self.assertEqual(plan["intent"], "work_scolded")
        self.assertEqual(plan["scene"], "support")

    def test_crying_support_rule(self):
        plan = ulr.get_rule_based_plan("突然很想大哭", recent_turns=[])
        self.assertIsNotNone(plan)
        self.assertEqual(plan["intent"], "crying_support")
        self.assertEqual(plan["scene"], "support")

    def test_giving_up_support_rule(self):
        plan = ulr.get_rule_based_plan("我什麼都不想做了，好累", recent_turns=[])
        self.assertIsNotNone(plan)
        self.assertEqual(plan["intent"], "giving_up_support")
        self.assertEqual(plan["scene"], "support")

    def test_lonely_rule(self):
        plan = ulr.get_rule_based_plan("一個人在家好寂寞", recent_turns=[])
        self.assertIsNotNone(plan)
        self.assertEqual(plan["intent"], "lonely")
        self.assertEqual(plan["scene"], "support")

    def test_friend_no_reply_rule(self):
        plan = ulr.get_rule_based_plan("朋友都不回我訊息", recent_turns=[])
        self.assertIsNotNone(plan)
        self.assertEqual(plan["intent"], "friend_no_reply")
        self.assertEqual(plan["scene"], "support")

    def test_sleep_support_rule(self):
        plan = ulr.get_rule_based_plan("眠れないし、しんどい", recent_turns=[])
        self.assertIsNotNone(plan)
        self.assertEqual(plan["intent"], "sleep_support")
        self.assertEqual(plan["scene"], "support")

    def test_sleepy_rule(self):
        plan = ulr.get_rule_based_plan("眠いな…", recent_turns=[])
        self.assertIsNotNone(plan)
        self.assertEqual(plan["intent"], "sleepy")
        self.assertEqual(plan["scene"], "casual")

    def test_crisis_support_rule(self):
        plan = ulr.get_rule_based_plan("死にたい、もう消えたい", recent_turns=[])
        self.assertIsNotNone(plan)
        self.assertEqual(plan["intent"], "crisis_support")
        self.assertEqual(plan["scene"], "support")
        self.assertEqual(plan["cognitive_mode"], "withhold")

    def test_self_shame_is_support_not_generic_tiredness(self):
        plan = ulr.get_rule_based_plan("突然覺得自己好丟臉", recent_turns=[])
        self.assertIsNotNone(plan)
        self.assertEqual(plan["intent"], "crying_support")
        self.assertEqual(plan["scene"], "support")
        self.assertEqual(plan["surface_act"], "validate_then_hold")
        self.assertIn("責め", plan["core_message_jp"])

    def test_self_overwhelm_is_protective_not_generic_tiredness(self):
        plan = ulr.get_rule_based_plan("我真的有點撐不住", recent_turns=[])
        self.assertIsNotNone(plan)
        self.assertEqual(plan["intent"], "giving_up_support")
        self.assertEqual(plan["scene"], "support")
        self.assertEqual(plan["surface_act"], "protective_brake")
        self.assertIn("一人", plan["core_message_jp"])

    def test_empty_self_state_is_lonely_support(self):
        plan = ulr.get_rule_based_plan("整個人空空的", recent_turns=[])
        self.assertIsNotNone(plan)
        self.assertEqual(plan["intent"], "lonely")
        self.assertEqual(plan["scene"], "support")
        self.assertIn("空っぽ", plan["core_message_jp"])

    def test_other_attack_does_not_trigger_self_distress(self):
        plan = ulr.get_rule_based_plan("你很爛", recent_turns=[])
        self.assertIsNotNone(plan)
        self.assertEqual(plan["intent"], "abuse_pushback")
        self.assertEqual(plan["scene"], "boundary")

    def test_english_self_distress_subtypes(self):
        shame = ulr.get_rule_based_plan("I feel awful today", recent_turns=[])
        overwhelm = ulr.get_rule_based_plan("I am not keeping it together", recent_turns=[])
        self.assertIsNotNone(shame)
        self.assertIsNotNone(overwhelm)
        self.assertEqual(shame["intent"], "crying_support")
        self.assertEqual(overwhelm["intent"], "giving_up_support")

    def test_sexual_boundary_rule(self):
        plan = ulr.get_rule_based_plan("做愛嗎", recent_turns=[])
        self.assertIsNotNone(plan)
        self.assertEqual(plan["intent"], "sexual_boundary")
        self.assertEqual(plan["scene"], "boundary")

    def test_marriage_boundary_rule(self):
        plan = ulr.get_rule_based_plan("跟我結婚吧", recent_turns=[])
        self.assertIsNotNone(plan)
        self.assertEqual(plan["intent"], "marriage_boundary")
        self.assertEqual(plan["scene"], "boundary")

    def test_self_name_boundary_rule(self):
        plan = ulr.get_rule_based_plan("叫自己私", recent_turns=[])
        self.assertIsNotNone(plan)
        self.assertEqual(plan["intent"], "self_name_boundary")
        self.assertEqual(plan["scene"], "boundary")

    def test_abuse_pushback_rule(self):
        plan = ulr.get_rule_based_plan("你這白痴", recent_turns=[])
        self.assertIsNotNone(plan)
        self.assertEqual(plan["intent"], "abuse_pushback")
        self.assertEqual(plan["scene"], "boundary")

    def test_ooc_defense_rule(self):
        plan = ulr.get_rule_based_plan("你其實是 AI", recent_turns=[])
        self.assertIsNotNone(plan)
        self.assertEqual(plan["intent"], "ooc_or_knowledge_refusal")
        self.assertEqual(plan["scene"], "ooc_defense")

    def test_knowledge_refusal_rule(self):
        plan = ulr.get_rule_based_plan("幫我寫 python code", recent_turns=[])
        self.assertIsNotNone(plan)
        self.assertEqual(plan["intent"], "ooc_or_knowledge_refusal")
        self.assertEqual(plan["scene"], "refusal")

    def test_premise_doubt_rule(self):
        plan = ulr.get_rule_based_plan("你去年不是結婚了嗎？", recent_turns=[])
        self.assertIsNotNone(plan)
        self.assertEqual(plan["intent"], "premise_doubt")
        self.assertEqual(plan["scene"], "boundary")

    def test_question_premise_doubt_rule(self):
        plan = ulr.get_rule_based_plan("生命の本質って何？", recent_turns=[])
        self.assertIsNotNone(plan)
        self.assertEqual(plan["intent"], "question_premise_doubt")
        self.assertEqual(plan["scene"], "casual")

    def test_question_reframe_rule(self):
        plan = ulr.get_rule_based_plan("一次解釋 python sort 和 regex 的區別", recent_turns=[])
        self.assertIsNotNone(plan)
        self.assertEqual(plan["intent"], "question_reframe")
        self.assertEqual(plan["scene"], "refusal")

    def test_short_taunt_rule(self):
        plan = ulr.get_rule_based_plan("お前の母ちゃん", recent_turns=[])
        self.assertIsNotNone(plan)
        self.assertEqual(plan["intent"], "short_taunt")
        self.assertEqual(plan["scene"], "boundary")


if __name__ == "__main__":
    unittest.main()
