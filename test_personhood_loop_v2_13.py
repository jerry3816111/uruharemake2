import threading
import time
import unittest

import uruha_brain_mac as brain_runtime
import uruha_functional_understanding as ufu
import uruha_memory_observatory as observatory
import uruha_personhood_loop as upl
from uruha_runtime import RuntimeConfig, RuntimeState


def build_turn(text, turn_index, input_mode="text"):
    hypothesis = ufu.build_user_mental_state_hypothesis(
        text,
        actual_signal={"actual_intent": "chat"},
        turn_index=turn_index,
    )
    pragmatic = upl.build_human_pragmatic_understanding(
        text,
        hypothesis=hypothesis,
        input_mode=input_mode,
        turn_index=turn_index,
    )
    pragmatic["linked_hypothesis_id"] = hypothesis["hypothesis_id"]
    hypothesis["pragmatic_understanding_v2_13"] = pragmatic
    return hypothesis, pragmatic


class _FakeMemory:
    def __init__(self):
        self.session_turns = []
        self.saved_episodes = []

    def query_all_layers(self, _user_input):
        return {
            "knowledge": "",
            "episodes": "",
            "wisdom": "",
            "profile": "",
            "profile_structured": {},
            "profile_grounding_request": None,
            "recent_turns": list(self.session_turns),
            "working_memory_items": [],
            "working_memory_summary": "無短期緩衝",
            "memory_provenance": {},
            "procedural_summary": "無程序記憶",
        }

    def get_runtime_snapshot(self):
        return {
            "recent_turns": list(self.session_turns),
            "short_term_buffer": [],
            "pending_consolidation_turns": 0,
            "profile": {},
        }

    def save_episode(self, user_input, reply, _psyche_after, logic):
        self.session_turns.append({"user": user_input, "reply": reply, "intent": logic.get("intent")})
        self.saved_episodes.append({"user": user_input, "reply": reply, "logic": logic})
        return f"User: {user_input}\nUruha: {reply}"


class _FakePsyche:
    def __init__(self, mood=0, trust=55):
        self.state = {"mood": mood, "trust": trust}

    def get_state(self):
        return dict(self.state)

    def adjust(self, mood_delta=0, trust_delta=0):
        self.state["mood"] += mood_delta
        self.state["trust"] += trust_delta

    def force_adjust(self, mood_delta=0, trust_delta=0, trust_lock_turns=0):
        self.adjust(mood_delta, trust_delta)


class _FakeLeftBrain:
    def __init__(self):
        self.think_calls = 0

    def classify_user_signal(self, text, _psyche, _mems):
        features = set(ufu.semantic_features(text))
        return {
            "actual_intent": "correction_followup" if "correction" in features else "chat",
            "actual_valence": 0.0,
            "abuse_like": False,
            "crisis_like": False,
            "seed_plan": {"scene": "casual"},
        }

    def _high_low_road_route(self, *_args, **_kwargs):
        return {"route": "high_road", "reason": "isolated_contract_fixture"}

    def _build_low_road_plan(self, *_args, **_kwargs):
        raise AssertionError("low road is outside this isolated fixture")

    def think(self, _text, _mems, _psyche, **_kwargs):
        self.think_calls += 1
        return {
            "intent": "chat",
            "scene": "casual",
            "reply_goal": "自然に返す",
            "core_message_jp": "分かった。",
            "response_mode": "direct_answer",
            "surface_act": "plain_reply",
            "payload_level": "medium",
            "constraints": {"max_chars": 96},
            "mood_impact": 0,
            "trust_impact": 0,
        }

    def predict_next_user_signal(self, logic, *_args, **_kwargs):
        return {
            "expected_intent": "chat_continuation",
            "expected_valence": 0.0,
            "source_plan_intent": logic.get("intent"),
        }


class _FakeRightBrain:
    def speak(self, _user_input, logic, _memory_data, _psyche):
        return str(logic.get("core_message_jp") or "まだ分かんない。")

    def enforce_user_visible_japanese(self, reply, logic, **_kwargs):
        logic["visible_language_guard"] = {
            "schema": "isolated_japanese_guard_fixture",
            "passed": True,
        }
        return reply


class _IsolatedContractBrain(brain_runtime.UruhaBrainV4_Mac):
    def __init__(self):
        self.compute_ledger = None
        self.persona_policy_provider = None
        self.runtime_config = RuntimeConfig()
        self.runtime = RuntimeState(config=self.runtime_config)
        self.runtime.touch_interaction(reset_drives=True)
        self.memory = _FakeMemory()
        self.psyche = _FakePsyche()
        self.left_brain = _FakeLeftBrain()
        self.right_brain = _FakeRightBrain()
        self._last_external_input_at = time.time()
        self._last_background_tick_at = 0.0
        self._last_timer_event_at = 0.0
        self._event_queue = []
        self._event_seq = 0
        self._event_queue_lock = threading.Lock()

    def _self_monitor_reply(self, *_args, **_kwargs):
        return {"needs_repair": False, "issues": []}

    def _write_typed_reflection_if_enabled(self, *_args, **_kwargs):
        return None


class HumanPragmaticUnderstandingV213Tests(unittest.TestCase):
    def test_literal_and_five_pragmatic_dimensions_are_separate(self):
        _hypothesis, pragmatic = build_turn("Maybe another time. I'll think about it.", 1)

        self.assertEqual(pragmatic["literal_content"]["value"], "Maybe another time. I'll think about it.")
        self.assertEqual(pragmatic["pragmatic_label"], "indirect_refusal")
        self.assertEqual(
            set(pragmatic["inferences"]),
            {
                "communicative_intent",
                "emotion_or_stance",
                "relationship_signal",
                "implicit_need",
                "action_tendency",
            },
        )
        for inference in pragmatic["inferences"].values():
            self.assertTrue(inference["evidence"])
            self.assertTrue(inference["alternatives"])
            self.assertLess(inference["confidence"], 1.0)

    def test_text_does_not_pretend_to_have_acoustic_tone(self):
        _hypothesis, pragmatic = build_turn("まあいいけど…", 1)

        self.assertEqual(
            pragmatic["acoustic_evidence"]["availability"],
            "not_applicable_text_input",
        )
        self.assertFalse(pragmatic["acoustic_evidence"]["reliable"])
        self.assertTrue(pragmatic["text_visible_hesitation"])

    def test_transcription_only_audio_marks_acoustic_features_unavailable(self):
        _hypothesis, pragmatic = build_turn("まあいいけど", 1, input_mode="audio")

        self.assertEqual(pragmatic["acoustic_evidence"]["availability"], "unavailable")
        self.assertIn("轉錄", pragmatic["acoustic_evidence"]["reason"])

    def test_reliable_acoustic_summary_is_evidence_not_emotion_fact(self):
        pragmatic = upl.build_human_pragmatic_understanding(
            "まあいいけど",
            input_mode="audio",
            acoustic_summary={"reliable": True, "pause_ms": 640, "speech_rate_sps": 3.1},
            turn_index=1,
        )

        self.assertEqual(pragmatic["acoustic_evidence"]["availability"], "available")
        self.assertIn("不直接等同情緒", pragmatic["acoustic_evidence"]["boundary"])

    def test_indirect_refusal_gets_felt_understanding_not_analysis_dump(self):
        hypothesis, pragmatic = build_turn("ちょっと難しい。また今度。", 1)
        plan = upl.apply_pragmatic_attunement_to_plan(
            {"intent": "chat", "scene": "casual", "core_message_jp": "分かった。"},
            pragmatic,
            hypothesis=hypothesis,
        )

        self.assertEqual(plan["surface_act"], "pragmatic_attunement")
        self.assertIn("断りづらい", plan["core_message_jp"])
        self.assertIn("違うなら", plan["core_message_jp"])
        self.assertNotIn("confidence", plan["core_message_jp"].lower())
        self.assertTrue(plan["pragmatic_attunement_strategy_v2_13"]["internal_trace_not_user_visible"])

    def test_next_turn_can_refute_an_indirect_refusal_inference(self):
        _hypothesis1, pragmatic1 = build_turn("Maybe another time.", 1)
        _hypothesis2, pragmatic2 = build_turn("Not refusing. I will go.", 2)
        verification = upl.verify_previous_pragmatic_understanding(
            pragmatic1,
            "Not refusing. I will go.",
            pragmatic2,
            turn_index=2,
        )

        self.assertEqual(verification["status"], "contradicted")
        self.assertEqual(verification["prediction_error"], 1.0)
        self.assertTrue(verification["previous_pragmatic_snapshot"])

    def test_development_paraphrases_cover_three_languages_without_audio_invention(self):
        cases = [
            ("這週末恐怕排得有點滿，之後有機會再說。", "indirect_refusal"),
            ("It has been a day, but whatever. You don't need to worry about me.", "possible_indirect_support_request"),
            ("うん、それでいいんじゃない。たぶん。", "surface_agreement_with_reservation"),
            ("今天整個人都靜不下來。", "ambiguous_arousal"),
        ]
        for turn_index, (text, expected) in enumerate(cases, start=1):
            with self.subTest(text=text):
                _hypothesis, pragmatic = build_turn(text, turn_index)
                self.assertEqual(pragmatic["pragmatic_label"], expected)
                self.assertEqual(
                    pragmatic["acoustic_evidence"]["availability"],
                    "not_applicable_text_input",
                )

    def test_ambiguous_arousal_gets_low_pressure_clarification_not_fake_tone(self):
        hypothesis, pragmatic = build_turn("今天整個人都靜不下來。", 1)
        plan = upl.apply_pragmatic_attunement_to_plan(
            {"intent": "chat", "scene": "casual"},
            pragmatic,
            hypothesis=hypothesis,
        )

        self.assertEqual(pragmatic["pragmatic_label"], "ambiguous_arousal")
        self.assertEqual(plan["response_mode"], "felt_understanding_reflection")
        self.assertIn("まだ分かんね", plan["core_message_jp"])
        self.assertIn("どっち寄り", plan["core_message_jp"])
        self.assertEqual(
            pragmatic["acoustic_evidence"]["availability"],
            "not_applicable_text_input",
        )

    def test_supported_followup_reflects_confirmed_need_without_internal_labels(self):
        hypothesis1, pragmatic1 = build_turn("You don't need to worry about me.", 1)
        hypothesis2, pragmatic2 = build_turn("Honestly I hoped you would ask once, not fix it.", 2)
        verification = upl.verify_previous_pragmatic_understanding(
            pragmatic1,
            "Honestly I hoped you would ask once, not fix it.",
            pragmatic2,
            turn_index=2,
        )
        plan = upl.apply_pragmatic_attunement_to_plan(
            {"intent": "chat", "scene": "casual"},
            pragmatic2,
            hypothesis=hypothesis2,
            pragmatic_verification=verification,
        )

        self.assertEqual(verification["status"], "supported")
        self.assertEqual(plan["response_mode"], "felt_understanding_confirmation")
        self.assertIn("聞いてほしかった", plan["core_message_jp"])
        self.assertNotIn("supported", plan["core_message_jp"])

    def test_dimension_specific_support_wins_over_broad_correction_marker(self):
        hypothesis1, pragmatic1 = build_turn("這週末恐怕排得有點滿，之後有機會再說。", 1)
        hypothesis2, pragmatic2 = build_turn("其實我是不太想去，只是不知道怎麼拒絕。", 2)
        general_verification = ufu.verify_previous_hypothesis(
            hypothesis1,
            "其實我是不太想去，只是不知道怎麼拒絕。",
            turn_index=2,
        )
        pragmatic_verification = upl.verify_previous_pragmatic_understanding(
            pragmatic1,
            "其實我是不太想去，只是不知道怎麼拒絕。",
            pragmatic2,
            turn_index=2,
        )
        plan = upl.apply_pragmatic_attunement_to_plan(
            {"intent": "chat", "scene": "casual"},
            pragmatic2,
            hypothesis=hypothesis2,
            pragmatic_verification=pragmatic_verification,
            hypothesis_verification=general_verification,
        )

        self.assertEqual(general_verification["status"], "contradicted")
        self.assertEqual(pragmatic_verification["status"], "supported")
        self.assertEqual(plan["response_mode"], "felt_understanding_confirmation")
        self.assertIn("断り方", plan["core_message_jp"])
        self.assertNotIn("行く方", plan["core_message_jp"])

    def test_general_hypothesis_denial_produces_explicit_natural_revision(self):
        hypothesis1, pragmatic1 = build_turn("今天整個人都靜不下來。", 1)
        hypothesis2, pragmatic2 = build_turn("不是焦慮，是期待太久的事終於要發生了。", 2)
        general_verification = ufu.verify_previous_hypothesis(
            hypothesis1,
            "不是焦慮，是期待太久的事終於要發生了。",
            turn_index=2,
        )
        pragmatic_verification = upl.verify_previous_pragmatic_understanding(
            pragmatic1,
            "不是焦慮，是期待太久的事終於要發生了。",
            pragmatic2,
            turn_index=2,
        )
        plan = upl.apply_pragmatic_attunement_to_plan(
            {"intent": "chat", "scene": "casual"},
            pragmatic2,
            hypothesis=hypothesis2,
            pragmatic_verification=pragmatic_verification,
            hypothesis_verification=general_verification,
        )

        self.assertEqual(general_verification["status"], "contradicted")
        self.assertEqual(plan["response_mode"], "felt_understanding_revision")
        self.assertIn("読み違えた", plan["core_message_jp"])
        self.assertIn("楽しみ", plan["core_message_jp"])


class LongitudinalOtherModelV213Tests(unittest.TestCase):
    def setUp(self):
        self.no_verification = {"status": "not_available"}

    def test_model_has_stable_situational_and_provisional_layers_with_provenance(self):
        text = "アドバイスする前に聞いて。今日は休むつもり。"
        hypothesis, pragmatic = build_turn(text, 1)
        model, trace = upl.update_longitudinal_user_model(
            upl.empty_longitudinal_model(),
            hypothesis,
            self.no_verification,
            self.no_verification,
            text,
            turn_index=1,
            timestamp="2026-08-11T12:00:00+09:00",
        )

        stable = model["layers"]["stable"]
        situational = model["layers"]["situational"]
        provisional = model["layers"]["provisional"]
        self.assertTrue(any(row["kind"] == "communication_preference" for row in stable))
        self.assertTrue(any(row["kind"] == "current_goal" for row in situational))
        self.assertTrue(provisional)
        self.assertTrue(all(row["source_history"] for row in stable + situational + provisional))
        self.assertFalse(trace["psychological_inference_written_as_fact"])

    def test_contradicted_hypothesis_is_withdrawn_not_overwritten(self):
        hypothesis1, pragmatic1 = build_turn("今天心情怪怪的。", 1)
        model, _trace1 = upl.update_longitudinal_user_model(
            None,
            hypothesis1,
            self.no_verification,
            self.no_verification,
            "今天心情怪怪的。",
            turn_index=1,
        )
        hypothesis2, pragmatic2 = build_turn("不是難過，我只是太興奮了。", 2)
        verification = ufu.verify_previous_hypothesis(
            hypothesis1,
            "不是難過，我只是太興奮了。",
            turn_index=2,
        )
        pragmatic_verification = upl.verify_previous_pragmatic_understanding(
            pragmatic1,
            "不是難過，我只是太興奮了。",
            pragmatic2,
            turn_index=2,
        )
        model, trace2 = upl.update_longitudinal_user_model(
            model,
            hypothesis2,
            verification,
            pragmatic_verification,
            "不是難過，我只是太興奮了。",
            turn_index=2,
        )

        withdrawn = [
            row
            for row in model["layers"]["provisional"]
            if hypothesis1["hypothesis_id"] in row["linked_hypothesis_ids"]
            and row["status"] == "withdrawn"
        ]
        self.assertTrue(withdrawn)
        self.assertTrue(trace2["revisions"])
        self.assertTrue(all(event["original_retained"] for event in trace2["revisions"]))

    def test_old_situational_goal_decays_and_expires_visibly(self):
        hypothesis1, _pragmatic1 = build_turn("今日は休むつもり。", 1)
        model, _trace1 = upl.update_longitudinal_user_model(
            None,
            hypothesis1,
            self.no_verification,
            self.no_verification,
            "今日は休むつもり。",
            turn_index=1,
        )
        hypothesis7, _pragmatic7 = build_turn("別の話しよ。", 7)
        model, trace7 = upl.update_longitudinal_user_model(
            model,
            hypothesis7,
            self.no_verification,
            self.no_verification,
            "別の話しよ。",
            turn_index=7,
        )

        old_goal = next(row for row in model["layers"]["situational"] if row["kind"] == "current_goal")
        self.assertEqual(old_goal["status"], "expired")
        self.assertLess(old_goal["confidence"], 0.88)
        self.assertTrue(any(event["status_after"] == "expired" for event in trace7["decay_events"]))

    def test_repeated_uncertain_implicit_need_triggers_one_low_pressure_validation(self):
        model = upl.empty_longitudinal_model()
        hypothesis1, pragmatic1 = build_turn("我沒事。", 1)
        model, _trace1 = upl.update_longitudinal_user_model(
            model, hypothesis1, self.no_verification, self.no_verification, "我沒事。", turn_index=1
        )
        _plan1, model, strategy1 = upl.apply_longitudinal_model_to_plan(
            {"intent": "chat", "scene": "casual"}, model, hypothesis1, turn_index=1
        )
        self.assertFalse(strategy1["changed_plan"])

        hypothesis2, pragmatic2 = build_turn("我沒事。", 2)
        verification2 = ufu.verify_previous_hypothesis(hypothesis1, "我沒事。", turn_index=2)
        pragmatic_verification2 = upl.verify_previous_pragmatic_understanding(
            pragmatic1, "我沒事。", pragmatic2, turn_index=2
        )
        model, _trace2 = upl.update_longitudinal_user_model(
            model,
            hypothesis2,
            verification2,
            pragmatic_verification2,
            "我沒事。",
            turn_index=2,
        )
        plan2, model, strategy2 = upl.apply_longitudinal_model_to_plan(
            {"intent": "chat", "scene": "casual"}, model, hypothesis2, turn_index=2
        )

        self.assertTrue(strategy2["changed_plan"])
        self.assertEqual(plan2["intent"], "functional_understanding_active_verify")
        self.assertIn("放っといて", plan2["core_message_jp"])
        self.assertTrue(model["active_validation"]["pending"])

        hypothesis3, pragmatic3 = build_turn("其實只是想有人陪。", 3)
        verification3 = ufu.verify_previous_hypothesis(
            hypothesis2, "其實只是想有人陪。", turn_index=3
        )
        pragmatic_verification3 = upl.verify_previous_pragmatic_understanding(
            pragmatic2, "其實只是想有人陪。", pragmatic3, turn_index=3
        )
        model, trace3 = upl.update_longitudinal_user_model(
            model,
            hypothesis3,
            verification3,
            pragmatic_verification3,
            "其實只是想有人陪。",
            turn_index=3,
        )
        self.assertEqual(pragmatic_verification3["status"], "supported")
        self.assertEqual(trace3["validation_resolution"]["status"], "confirmed")
        self.assertIsNone(model["active_validation"]["pending"])

    def test_typed_calibration_exposes_category_reliability_not_one_global_score(self):
        model = upl.empty_longitudinal_model()
        previous_hypothesis, previous_pragmatic = build_turn("Maybe another time.", 1)
        model, _trace = upl.update_longitudinal_user_model(
            model,
            previous_hypothesis,
            self.no_verification,
            self.no_verification,
            "Maybe another time.",
            turn_index=1,
        )
        for turn_index, text in enumerate(
            ["I didn't want to go.", "I didn't want to go.", "I didn't want to go."],
            start=2,
        ):
            hypothesis, pragmatic = build_turn(text, turn_index)
            general_verification = ufu.verify_previous_hypothesis(
                previous_hypothesis, text, turn_index=turn_index
            )
            pragmatic_verification = upl.verify_previous_pragmatic_understanding(
                previous_pragmatic, text, pragmatic, turn_index=turn_index
            )
            model, _trace = upl.update_longitudinal_user_model(
                model,
                hypothesis,
                general_verification,
                pragmatic_verification,
                text,
                turn_index=turn_index,
            )
            previous_hypothesis, previous_pragmatic = hypothesis, pragmatic

        categories = model["typed_calibration"]["categories"]
        self.assertIn("pragmatic_communicative_intent", categories)
        stats = categories["pragmatic_communicative_intent"]
        self.assertIn("supported_rate", stats)
        self.assertIn("overconfidence_gap", stats)
        self.assertIn("recommended_confidence_cap", stats)


class RuntimeIntegrationV213Tests(unittest.TestCase):
    def test_m17_real_runtime_corrects_reuses_and_skips_redundant_planner(self):
        brain = _IsolatedContractBrain()
        first = brain.run_turn_debug("我從早上就一直坐不住，腦子停不下來。")
        correction = brain.run_turn_debug(
            "不是要方法啦，我是在等你吐槽我，平常不是都會互相吐槽嗎？"
        )
        repeated = brain.run_turn_debug("我從早上就一直坐不住，腦子停不下來。")

        self.assertEqual(first["logic"]["desired_response_policy_m16"], "calibrate_need")
        self.assertIn("どっち", first["reply"])
        self.assertEqual(
            correction["runtime_trace"]["adaptive_person_feedback_m16"]["status"],
            "contradicted",
        )
        self.assertEqual(correction["logic"]["desired_response_policy_m16"], "playful_tease")
        self.assertIn("読みすぎた", correction["reply"])
        self.assertIn("脳内", correction["reply"])
        self.assertEqual(repeated["logic"]["desired_response_policy_m16"], "playful_tease")
        self.assertIn("脳内", repeated["reply"])
        self.assertEqual(
            repeated["runtime_trace"]["adaptive_person_model_m16"]["revision_count"],
            1,
        )
        self.assertEqual(brain.left_brain.think_calls, 0)
        labels = {row["label"] for row in repeated["runtime_trace"]["blackboard"]}
        self.assertTrue(
            {
                "adaptive_person_feedback_update_m18",
                "adaptive_context_scope_m18",
                "adaptive_scope_hierarchy_m18",
                "desired_response_state_m18",
                "desired_response_candidates_m18",
                "desired_response_prediction_m18",
                "adaptive_response_dimensions_m18",
                "adaptive_person_persistence_m18",
                "adaptive_planner_fast_path_m18",
                "runtime_latency_m18",
            }.issubset(labels)
        )

    def test_real_runtime_tick_emits_felt_reply_and_complete_internal_trace(self):
        brain = _IsolatedContractBrain()
        result = brain.run_turn_debug(
            "這週末恐怕排得有點滿，之後有機會再說。",
            input_context={"input_mode": "text", "acoustic_summary": None},
        )

        self.assertIn("断りづらい", result["reply"])
        self.assertRegex(result["reply"], r"[ぁ-んァ-ヶー一-龠]")
        labels = {row["label"] for row in result["runtime_trace"]["blackboard"]}
        self.assertTrue(
            {
                "human_pragmatic_understanding_v2_13",
                "persistent_other_model_v2_13",
                "typed_calibration_v2_13",
                "personhood_perceive_other_v2_13",
                "personhood_self_state_v2_13",
                "personhood_relationship_state_v2_13",
                "personhood_persona_appraisal_v2_13",
                "personhood_action_choice_v2_13",
                "personhood_outcome_learning_v2_13",
                "utterance",
                "memory_updates",
            }.issubset(labels)
        )
        self.assertTrue(result["runtime_trace"]["personhood_loop_v2_13"]["action_choice"]["self_and_persona_used"])
        self.assertFalse(
            result["runtime_trace"]["personhood_loop_v2_13"]["learn_from_outcome"]
            ["psychological_inference_written_as_fact"]
        )

    def test_real_runtime_tick_support_and_denial_update_previous_model(self):
        supported = _IsolatedContractBrain()
        supported.run_turn_debug("You don't need to worry about me.")
        supported_result = supported.run_turn_debug(
            "Honestly I hoped you would ask once, not fix it."
        )
        self.assertEqual(
            supported_result["runtime_trace"]["pragmatic_verification_v2_13"]["status"],
            "supported",
        )
        self.assertIn("聞いてほしかった", supported_result["reply"])

        contradicted = _IsolatedContractBrain()
        contradicted.run_turn_debug("今天整個人都靜不下來。")
        contradicted_result = contradicted.run_turn_debug(
            "不是焦慮，是期待太久的事終於要發生了。"
        )
        self.assertEqual(
            contradicted_result["runtime_trace"]["hypothesis_verification"]["status"],
            "contradicted",
        )
        self.assertIn("読み違えた", contradicted_result["reply"])
        withdrawn = [
            row
            for row in contradicted_result["runtime_trace"]["longitudinal_user_model_v2_13"]
            ["layers"]["provisional"]
            if row.get("status") == "withdrawn"
        ]
        self.assertTrue(withdrawn)

    def test_audio_runtime_marks_acoustics_unavailable_and_does_not_store_inference_as_fact(self):
        brain = _IsolatedContractBrain()
        result = brain.run_turn_debug(
            "まあいいけど…",
            input_context={"input_mode": "audio", "acoustic_summary": None},
        )

        pragmatic = result["runtime_trace"]["human_pragmatic_understanding_v2_13"]
        self.assertEqual(pragmatic["acoustic_evidence"]["availability"], "unavailable")
        self.assertFalse(pragmatic["memory_policy"]["fact_write_allowed"])
        self.assertEqual(len(brain.memory.saved_episodes), 1)


class PersonhoodLoopAndGraphV213Tests(unittest.TestCase):
    def test_personhood_loop_connects_other_self_relationship_persona_action_and_learning(self):
        hypothesis, pragmatic = build_turn("Maybe another time.", 1)
        model, update = upl.update_longitudinal_user_model(
            None,
            hypothesis,
            {"status": "not_available"},
            {"status": "not_available"},
            "Maybe another time.",
            turn_index=1,
        )
        plan = upl.apply_pragmatic_attunement_to_plan(
            {"intent": "chat", "scene": "casual"}, pragmatic, hypothesis=hypothesis
        )
        plan, model, _strategy = upl.apply_longitudinal_model_to_plan(plan, model, hypothesis, 1)
        plan, persona_appraisal = upl.apply_public_persona_appraisal_to_plan(
            plan,
            pragmatic,
            model,
            {"mood": 0, "trust": 55},
        )
        trace = upl.build_personhood_loop_trace(
            "Maybe another time.",
            hypothesis,
            pragmatic,
            {"status": "not_available"},
            model,
            update,
            {"status": "not_available"},
            {},
            {"mood": 0, "trust": 55},
            "understand_user_and_reply",
            plan,
        )

        self.assertIn("人類", trace["research_priority"]["primary_question"])
        self.assertIn("言外", trace["research_priority"]["primary_question"])
        self.assertTrue(trace["action_choice"]["other_model_used"])
        self.assertTrue(trace["action_choice"]["self_and_persona_used"])
        self.assertEqual(
            persona_appraisal["authorization_scope"],
            "development_hypothesis_only_not_persona_fidelity_or_production_activation",
        )
        self.assertEqual(
            {row["evidence_id"] for row in persona_appraisal["evidence_refs"]},
            {"persona_dev_v1_002", "persona_dev_v1_003"},
        )
        self.assertIn("童年", trace["public_persona_provenance"]["unknown_space"][0])
        self.assertFalse(trace["learn_from_outcome"]["psychological_inference_written_as_fact"])

    def test_public_persona_appraisal_uses_relationship_without_private_inference(self):
        hypothesis, pragmatic = build_turn("Maybe another time.", 1)
        plan = upl.apply_pragmatic_attunement_to_plan(
            {"intent": "chat", "scene": "casual"}, pragmatic, hypothesis=hypothesis
        )
        adjusted, appraisal = upl.apply_public_persona_appraisal_to_plan(
            plan,
            pragmatic,
            upl.empty_longitudinal_model(),
            {"mood": 0, "trust": 30},
        )

        self.assertEqual(appraisal["relationship_phase"], "cautious")
        self.assertTrue(appraisal["core_changed"])
        self.assertIn("違ったら", adjusted["core_message_jp"])
        self.assertFalse(appraisal["private_person_inference_added"])

    def test_graph_and_comparison_card_show_development_first_m16_loop(self):
        result = {
            "user_text": "Maybe another time.",
            "reply": "それ、断りづらいだけじゃね。違うなら言って。",
            "runtime_trace": {
                "blackboard": [
                    {
                        "stage": "pragmatics",
                        "label": "human_pragmatic_understanding_v2_13",
                        "payload": {
                            "schema": upl.PRAGMATIC_SCHEMA,
                            "pragmatic_label": "indirect_refusal",
                            "acoustic_evidence": {"availability": "not_applicable_text_input"},
                        },
                    },
                    {
                        "stage": "other_model",
                        "label": "persistent_other_model_v2_13",
                        "payload": {**upl.empty_longitudinal_model(), "summary": upl.model_summary(None)},
                    },
                    {
                        "stage": "self",
                        "label": "personhood_self_state_v2_13",
                        "payload": {"mood": 0, "trust": 55, "persona_stance": ["bounded"]},
                    },
                    {
                        "stage": "relationship",
                        "label": "personhood_relationship_state_v2_13",
                        "payload": {"phase": "developing", "trust_score": 55},
                    },
                    {
                        "stage": "appraise",
                        "label": "personhood_persona_appraisal_v2_13",
                        "payload": {"pragmatic_label": "indirect_refusal", "evaluation_rule": "persona matters"},
                    },
                    {
                        "stage": "validate",
                        "label": "active_validation_strategy_v2_13",
                        "payload": {"schema": upl.VALIDATION_SCHEMA, "changed_plan": False},
                    },
                    {
                        "stage": "select",
                        "label": "personhood_action_choice_v2_13",
                        "payload": {"intent": "pragmatic_attunement", "other_model_used": True},
                    },
                    {
                        "stage": "learn",
                        "label": "personhood_outcome_learning_v2_13",
                        "payload": {
                            "verification_status": "uncertain",
                            "pragmatic_verification_status": "uncertain",
                            "relationship_learning": "do not overclaim",
                        },
                    },
                ],
                "state_diff": {},
                "memory_writes": [],
            },
        }
        graph = observatory.collect_cognitive_graph(result)
        labels = {node["label"] for node in graph["nodes"]}
        html = observatory.render_memory_observatory(result)

        self.assertIn("human_pragmatic_understanding_v2_13", labels)
        self.assertIn("personhood_action_choice_v2_13", labels)
        self.assertIn("DIRECT GENERATION PATH", html)
        self.assertIn("HIERARCHICAL ADAPTIVE MODEL · M18", html)
        self.assertIn("關心・直接・幽默・傾聽・行動・距離", html)


if __name__ == "__main__":
    unittest.main()
