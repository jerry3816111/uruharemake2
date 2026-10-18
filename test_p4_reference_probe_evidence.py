"""Zero-model contract checks for opt-in source-qualified reference admission."""

from copy import deepcopy
import hashlib
from pathlib import Path
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch

from uruha_brain_mac import LeftBrain, RightBrain
import uruha_reference_probe_evidence_p4 as gate


ROOT = Path(__file__).resolve().parent


class ReferenceProbeEvidenceTests(TestCase):
    def setUp(self):
        self.left = LeftBrain.__new__(LeftBrain)
        self.psyche = {"mood": 0, "trust": 50}

    def test_frozen_static_false_admissions_are_blocked_and_controls_retained(self):
        cases = {
            "プラネタリウムの受付で働いてる。": (True, False),
            "撮影の予約は何時から？": (True, False),
            "投影幕の置き場、どこ？": (True, False),
            "友達が『霧の中に消えた』って言った。": (True, False),
            "この歌詞は何の曲？": (True, True),
            "夜空": (True, True),
        }
        with patch.object(gate, "_ORIGINAL_RULE_PLAN", LeftBrain._rule_based_plan):
            for text, (old_is_reference, admitted) in cases.items():
                with self.subTest(text=text):
                    original = LeftBrain._rule_based_plan(self.left, text, self.psyche, {})
                    self.assertEqual(gate._is_reference_plan(original), old_is_reference)
                    cert = gate.classify_reference_probe_evidence_p4(text)
                    self.assertEqual(cert["eligible"], admitted)
                    new = gate.rule_plan_with_reference_probe_evidence_p4(
                        self.left, text, self.psyche, {},
                    )
                    self.assertEqual(gate._is_reference_plan(new), admitted)
                    self.assertFalse(cert["raw_dialogue_persisted"])
                    self.assertFalse(cert["private_intent_claimed"])
                    self.assertNotIn(text, str(cert))

    def test_complete_non_source_question_third_party_and_embedded_tokens(self):
        cases = [
            ("プラネタリウムの説明文を直してる。", "ordinary_statement_or_request"),
            ("投影開始は何時？", "non_source_question"),
            ("EDは何時？", "non_source_question"),
            ("影絵を描いた。", "ordinary_statement_or_request"),
            ("友人が『夜空』って言った。", "third_party_report"),
            ("My brother said 'moonlight' yesterday.", "third_party_report"),
            ("My friend said 'What song is this?' yesterday.", "third_party_report"),
            ("友達が『この歌詞は何の曲？』って言った。", "third_party_report"),
            ("「この歌詞は何の曲？」って台詞、自然？", "non_source_question"),
        ]
        for text, expected_act in cases:
            with self.subTest(text=text):
                cert = gate.classify_reference_probe_evidence_p4(text)
                self.assertFalse(cert["eligible"])
                self.assertEqual(cert["speech_act"], expected_act)

    def test_exact_raw_and_normalized_digests_are_distinct_authorities(self):
        raw = "  夜空  "
        cert = gate.classify_reference_probe_evidence_p4(raw)
        self.assertTrue(cert["eligible"])
        self.assertEqual(cert["input_sha256"], hashlib.sha256(raw.encode("utf-8")).hexdigest())
        self.assertEqual(cert["normalized_input_sha256"], gate._sha("夜空"))
        self.assertNotEqual(cert["input_sha256"], cert["normalized_input_sha256"])

    def test_genuine_reference_and_song_slot_evidence_survive(self):
        cases = {
            "第三季 OP 是哪首來著": "ed_op_subject_incomplete",
            "限定活動ED我想不起來。": "ed_op_subject_incomplete",
            "『夜空』": "bare_poetic_fragment",
            "What song are these lyrics from?": "explicit_source_question",
            "この歌詞は何の曲？": "explicit_source_question",
        }
        for text, evidence in cases.items():
            with self.subTest(text=text):
                cert = gate.classify_reference_probe_evidence_p4(text)
                self.assertTrue(cert["eligible"])
                self.assertEqual(cert["source_evidence"], evidence)

    def test_protected_abuse_seed_is_not_changed(self):
        text = "Shut up, that meme is stupid."
        with patch.object(gate, "_ORIGINAL_RULE_PLAN", LeftBrain._rule_based_plan):
            original = LeftBrain._rule_based_plan(self.left, text, self.psyche, {})
            guarded = gate.rule_plan_with_reference_probe_evidence_p4(
                self.left, text, self.psyche, {},
            )
        self.assertEqual(original["intent"], "abuse_pushback")
        self.assertEqual(guarded, original)
        self.assertFalse(gate.classify_reference_probe_evidence_p4(text)["eligible"])

    def test_critique_cannot_reinject_reference_without_source_evidence(self):
        ordinary = "プラネタリウムの説明文を短くした。"
        eligible = "この歌詞は何の曲？"
        plan = {
            "intent": "chat", "scene": "casual", "surface_act": "plain_reply",
            "response_mode": "direct_answer", "payload_level": "medium",
            "hidden_intent": "plain_request", "cognitive_mode": "direct",
        }
        with patch.object(gate, "_ORIGINAL_CRITIQUE", LeftBrain._critique_plan):
            before = LeftBrain._critique_plan(self.left, plan, ordinary, {}, self.psyche)
            after = gate.critique_with_reference_probe_evidence_p4(
                self.left, plan, ordinary, {}, self.psyche,
            )
            true = gate.critique_with_reference_probe_evidence_p4(
                self.left, plan, eligible, {}, self.psyche,
            )
        self.assertIn("missed_reference_behavior", before["issues"])
        self.assertNotIn("missed_reference_behavior", after["issues"])
        self.assertTrue(after["reference_admission_issue_removed_p4"])
        self.assertIn("missed_reference_behavior", true["issues"])

    def test_model_candidate_selection_filters_only_unsupported_reference(self):
        seen = []

        def record(_self, plans, _input, _memory, _psyche, *, internal_monologue="", tick_budget=None):
            seen.append(deepcopy(plans))
            return plans[0]

        ref = {"intent": "reference_probe", "surface_act": "reference_probe"}
        chat = {"intent": "chat", "surface_act": "plain_reply"}
        with patch.object(gate, "_ORIGINAL_MULTITICK", record):
            selected = gate.multitick_with_reference_probe_evidence_p4(
                self.left, [ref, chat], "投影幕の置き場、どこ？", {}, self.psyche,
            )
            self.assertEqual(selected, chat)
            self.assertEqual(seen[-1], [chat])
            allowed = gate.multitick_with_reference_probe_evidence_p4(
                self.left, [ref, chat], "夜空", {}, self.psyche,
            )
            self.assertEqual(allowed, ref)
            self.assertEqual(seen[-1], [ref, chat])
            only_unsupported = gate.multitick_with_reference_probe_evidence_p4(
                self.left, [ref], "投影幕の置き場、どこ？", {}, self.psyche,
            )
            self.assertEqual(only_unsupported["intent"], "chat")
            self.assertEqual(seen[-1][0]["surface_act"], "plain_reply")

    def test_optional_chat_rescue_uses_same_certificate(self):
        class FakeRight:
            _intent_variant = gate.intent_variant_with_reference_probe_evidence_p4
            _chat_rescue_variant = RightBrain._chat_rescue_variant

        fake = FakeRight()
        with patch.object(gate, "_ORIGINAL_INTENT_VARIANT", lambda *_args, **_kwargs: "source-rescue"):
            self.assertIsNone(fake._chat_rescue_variant("投影幕の置き場、どこ？"))
            self.assertEqual(fake._chat_rescue_variant("夜空"), "source-rescue")

    def test_tick_node_reports_actual_selection_without_raw_dialogue(self):
        text = "撮影の予約は何時から？"
        selected = {
            "intent": "reference_probe", "surface_act": "reference_probe", "scene": "casual",
            "mood_impact": -7, "trust_impact": -4, "routing_path": "stale_reference_route",
            "grounding": {"reference_subject_jp": "捏造した元ネタ"},
            "user_belief": "元ネタを知りたい", "my_hidden_knowledge": "歌詞らしい",
            "user_expectation": "曲名を聞きたい", "dialogue_act": "reference_probe",
            "planner_tick_trace": [{"selected_intent": "reference_probe"}],
            "planner_tick_count": 3, "self_correction_applied": True,
            "reference_subject_jp": "捏造した元ネタ",
            "bounded_slow_path_m21": {"route": "deterministic_rule_plan", "stage_seconds": {"cognitive_total": 0.4}},
            "semantic_route_m22": {"selected_type": "general_conversation", "performed_route": "deterministic_rule_plan"},
        }
        runtime = SimpleNamespace(
            blackboard=[
                {"stage": "select", "label": "personhood_action_choice_v2_13", "payload": {"intent": "reference_probe"}},
                {"stage": "plan", "label": "bounded_slow_path_planner_m21", "payload": {"route": "deterministic_rule_plan", "stage_seconds": {"cognitive_total": 0.4}}},
                {"stage": "select", "label": "selected_plan", "payload": {"intent": "reference_probe"}},
                {"stage": "surface", "label": "utterance", "payload": {"reply": "old"}},
            ],
            last_selected_plan={}, active_goal="", last_personhood_loop={"action_choice": {"intent": "reference_probe"}},
        )
        fake = SimpleNamespace(
            left_brain=self.left,
            psyche=SimpleNamespace(get_state=lambda: self.psyche),
            runtime=runtime,
            _plan_trace_summary=lambda logic: {"intent": logic["intent"]},
        )
        event = {"user_input": text, "psyche_before": self.psyche, "memory_data": {}}
        tick = {
            "route_info": {"route": "high_road"},
            "logic": {**selected, "semantic_route_m22": {"selected_type": "general_conversation"}},
        }
        with patch.object(gate, "_ORIGINAL_TICK", lambda _self, _event: tick):
            with patch.object(gate, "_ORIGINAL_RULE_PLAN", LeftBrain._rule_based_plan):
                result = gate.cognitive_tick_with_reference_probe_evidence_p4(fake, event)
        cert = result["logic"][gate.LABEL]
        self.assertEqual(cert["seed_admission"], "rejected")
        self.assertEqual(cert["selected_status"], "unsupported_selected_reference_rejected")
        self.assertEqual(cert["actual_selected_intent"], "chat")
        self.assertTrue(cert["rejected_plan_specific_payload_cleared"])
        self.assertTrue(cert["pre_gate_cognitive_nodes_retained_as_shadow"])
        self.assertEqual(result["logic"]["grounding"], {})
        self.assertEqual(result["logic"]["user_belief"], "")
        self.assertEqual(result["logic"]["dialogue_act"], "direct_chat_answer")
        self.assertEqual(result["logic"]["mood_impact"], 0)
        self.assertEqual(result["logic"]["trust_impact"], 0)
        self.assertEqual(result["logic"]["routing_path"], "high_road")
        self.assertEqual(result["logic"]["planner_tick_count"], 0)
        self.assertFalse(result["logic"]["self_correction_applied"])
        self.assertEqual(result["logic"]["bounded_slow_path_m21"]["stage_seconds"]["cognitive_total"], 0.4)
        self.assertEqual(result["logic"]["bounded_slow_path_m21"]["pre_gate_plan_status"], "shadowed_not_selected")
        self.assertEqual(runtime.last_personhood_loop["action_choice"]["post_gate_status"], "shadowed_not_selected")
        self.assertNotIn("planner_tick_trace", result["logic"])
        self.assertNotIn("reference_subject_jp", result["logic"])
        self.assertEqual(runtime.blackboard[0]["payload"]["post_gate_plan_status"], "shadowed_not_selected")
        self.assertTrue(runtime.blackboard[1]["payload"]["observed_compute_cost_retained"])
        self.assertEqual(runtime.blackboard[2]["label"], gate.LABEL)
        self.assertEqual(runtime.blackboard[3]["payload"]["intent"], "chat")
        self.assertNotIn(text, str(runtime.blackboard[2]["payload"]))
        self.assertFalse(runtime.blackboard[2]["payload"]["private_intent_claimed"])

    def test_tick_preserves_true_reference_and_protected_boundary(self):
        for text, intent, route, expected_status in (
            ("夜空", "reference_probe", "high_road", "eligible_reference_selected"),
            ("Shut up, that meme is stupid.", "abuse_pushback", "low_road", "protected_unchanged"),
        ):
            with self.subTest(text=text):
                runtime = SimpleNamespace(
                    blackboard=[{"stage": "select", "label": "selected_plan", "payload": {"intent": intent}}],
                    last_selected_plan={"intent": intent}, active_goal="unchanged",
                )
                fake = SimpleNamespace(left_brain=self.left, runtime=runtime)
                original = {"intent": intent, "scene": "boundary" if route == "low_road" else "casual",
                            "surface_act": "challenge_mirror" if route == "low_road" else "reference_probe"}
                tick = {"route_info": {"route": route}, "logic": deepcopy(original)}
                event = {"user_input": text, "psyche_before": self.psyche, "memory_data": {}}
                with patch.object(gate, "_ORIGINAL_TICK", lambda _self, _event: tick):
                    with patch.object(gate, "_ORIGINAL_RULE_PLAN", LeftBrain._rule_based_plan):
                        result = gate.cognitive_tick_with_reference_probe_evidence_p4(fake, event)
                self.assertEqual(result["logic"]["intent"], intent)
                self.assertEqual(result["logic"][gate.LABEL]["selected_status"], expected_status)
                self.assertEqual(runtime.blackboard[0]["label"], gate.LABEL)
                self.assertEqual(runtime.active_goal, "unchanged")

    def test_entry_and_controller_use_prior_overlays_before_new_gate(self):
        entry = (ROOT / "uruha_web_ui_product_p4_reference_probe_evidence.py").read_text()
        controller = (ROOT / "p4_reference_probe_evidence_detached_control.py").read_text()
        self.assertIn("install_deterministic_plan_leak_surface_p4()", entry)
        self.assertIn("install_reference_probe_evidence_p4()", entry)
        self.assertLess(
            entry.index("install_deterministic_plan_leak_surface_p4()"),
            entry.index("install_reference_probe_evidence_p4()"),
        )
        self.assertIn("uruha_web_ui_product_p4_reference_probe_evidence.py", controller)
