"""Zero-model contracts using text disjoint from the frozen Safari turns."""

from copy import deepcopy
from unittest import TestCase
from unittest.mock import patch

from uruha_brain_mac import LeftBrain
import uruha_quoted_line_act_scope_p4 as scope
import uruha_explicit_episode_recall_focus_p4 as focus


NATURAL = "「予約番号、覚えてる？」という台詞、自然かな？"
TONE = "『まだ私を覚えてる？』って言い方、重い？"
SHORTEN = '"Do you remember the receipt?" as a sentence, can it be shorter?'
MEMORY = "前に言った予約番号、覚えてる？"
MIXED = "「覚えてる？」は引用ね。で、うちの名前は覚えてる？"


class QuotedLineActScopeTests(TestCase):
    def test_outer_edit_act_not_quoted_recall_or_relationship_act(self):
        for source, expected in ((NATURAL, "naturalness"), (TONE, "tone"), (SHORTEN, "shorten")):
            with self.subTest(source=source):
                decision = scope.classify_quoted_line_act_scope_p4(source)
                self.assertTrue(decision["eligible"])
                self.assertEqual(decision["outer_act"], expected)
                self.assertFalse(decision["quoted_memory_or_relationship_cue_authorized"])
                self.assertFalse(decision["prior_memory_anchor_answer_authorized"])
                self.assertNotIn("予約番号", decision["selected_core_jp"])
        self.assertFalse(focus.classify_explicit_episode_recall_focus_p4(NATURAL)["eligible"])
        self.assertTrue(focus.classify_explicit_episode_recall_focus_p4(MEMORY)["eligible"])

    def test_cross_language_outer_edit_still_has_japanese_core(self):
        for source in (
            "「你還記得票嗎？」這句話自然嗎？",
            '"Do you still remember the ticket?" as a line, does it sound natural?',
        ):
            with self.subTest(source=source):
                decision = scope.classify_quoted_line_act_scope_p4(source)
                self.assertTrue(decision["eligible"])
                self.assertEqual(decision["outer_act"], "naturalness")
                self.assertIn("前後", decision["selected_core_jp"])

    def test_not_blanket_quote_guard_or_protected_bypass(self):
        for source in (
            MEMORY,
            "私のこと、まだ覚えてる？",
            MIXED,
            "友達が「予約番号を確認して」と言った。",
            "「予約番号、覚えてる？という台詞、自然？",
            "「予約番号、覚えてる？」と「レシートは？」って台詞、自然？",
            "「予約番号、覚えてる？」をそのまま言って",
            "「よろしく」って台詞、自然か教えて、その前に相手へ送ってくれる？",
            "「よろしく」って台詞、自然なら相手に伝えてくれる？",
            "「死にたい」って台詞、自然？",
            "「予約番号、覚えてる？」って台詞、自然？ 今すぐ助けて",
        ):
            with self.subTest(source=source):
                self.assertFalse(scope.classify_quoted_line_act_scope_p4(source)["eligible"])

    def test_query_keeps_original_candidate_pool_and_only_adds_scope_certificate(self):
        old = {"working_memory_items": [{"text": "別の話", "score": 1.0}], "memory_provenance": {"candidate_pool": [{"text": "別の話"}]}}
        snapshot = deepcopy(old)
        with patch.object(scope, "_ORIGINAL_QUERY", return_value=old):
            new = scope.query_all_layers_with_quoted_line_act_scope_p4(object(), NATURAL)
        self.assertEqual(new["working_memory_items"], snapshot["working_memory_items"])
        self.assertEqual(new["memory_provenance"], snapshot["memory_provenance"])
        self.assertEqual(new[scope.LABEL]["input_sha256"], scope.classify_quoted_line_act_scope_p4(NATURAL)["input_sha256"])
        with patch.object(scope, "_ORIGINAL_QUERY", return_value=deepcopy(snapshot)):
            direct = scope.query_all_layers_with_quoted_line_act_scope_p4(object(), MEMORY)
        self.assertNotIn(scope.LABEL, direct)

    def test_route_and_rule_plan_bind_outer_act_and_keep_protected_predecessor(self):
        old_route = {
            "selected_type": "factual_or_memory", "recommended_route": "grounded",
            "candidates": [{"task_type": "factual_or_memory", "score": 0.9}],
            "evidence": [],
        }
        with patch.object(scope, "_ORIGINAL_ROUTE", return_value=old_route):
            route = scope.route_with_quoted_line_act_scope_p4(NATURAL)
            unchanged = scope.route_with_quoted_line_act_scope_p4(MEMORY)
            protected_route = scope.route_with_quoted_line_act_scope_p4(
                NATURAL, actual_signal={"seed_plan": {"intent": "crisis_support", "scene": "support"}}
            )
            low_road_route = scope.route_with_quoted_line_act_scope_p4(
                NATURAL, route_info={"route": "low_road"}
            )
        self.assertEqual(route["selected_type"], "general_conversation")
        self.assertEqual(route["pre_quote_scope_selected_type"], "factual_or_memory")
        self.assertEqual(unchanged, old_route)
        self.assertEqual(protected_route, old_route)
        self.assertEqual(low_road_route, old_route)
        bound = {scope.LABEL: scope.classify_quoted_line_act_scope_p4(NATURAL)}
        with patch.object(scope, "_ORIGINAL_RULE_PLAN", return_value={"intent": "ask_miss_me", "scene": "casual"}):
            plan = scope.rule_plan_with_quoted_line_act_scope_p4(object(), NATURAL, {}, bound)
        normalized = LeftBrain(client_logic=None)._normalize_plan(plan)
        self.assertEqual(normalized["intent"], "quoted_line_feedback")
        self.assertEqual(normalized["planner_path"], scope.PLANNER_PATH)
        self.assertNotEqual(normalized["intent"], "ask_miss_me")
        with patch.object(scope, "_ORIGINAL_RULE_PLAN", return_value={"intent": "crisis_support", "scene": "support"}):
            protected = scope.rule_plan_with_quoted_line_act_scope_p4(object(), NATURAL, {}, bound)
        self.assertEqual(protected["intent"], "crisis_support")

    def test_same_scope_certificate_rejects_generic_previous_memory_anchor(self):
        certificate = scope.classify_quoted_line_act_scope_p4(NATURAL)
        logic = LeftBrain(client_logic=None)._normalize_plan(scope._plan_from_scope(certificate))
        memory = {scope.LABEL: certificate, "working_memory_items": [{"text": "前の別件", "score": 2.5}]}
        with patch.object(scope, "_ORIGINAL_GRAVITY", side_effect=AssertionError("generic anchor called")):
            result = scope.attach_memory_gravity_with_quoted_line_act_scope_p4(object(), logic, NATURAL, memory)
        self.assertEqual(result["memory_anchor"], {})
        self.assertFalse(result["memory_use_expected"])
        self.assertEqual(result[scope.LABEL]["memory_anchor_admission"], "rejected_for_outer_edit_act")
        with patch.object(scope, "_ORIGINAL_GRAVITY", return_value={"legacy": True}) as prior:
            self.assertEqual(scope.attach_memory_gravity_with_quoted_line_act_scope_p4(object(), {}, MEMORY, memory), {"legacy": True})
            prior.assert_called_once()

    def test_late_selected_plan_boundary_replaces_competing_nonprotected_route(self):
        certificate = scope.classify_quoted_line_act_scope_p4(NATURAL)
        original_logic = {
            "intent": "ask_miss_me", "scene": "casual", "core_message_jp": "別の話を返す",
            "dialogue_act": "low_pressure_clarification",
            "memory_anchor": {}, "memory_use_expected": False,
            "semantic_route_m22": {"selected_type": "general_conversation", "performed_route": "semantic_authorization_m31"},
        }
        runtime = type("Runtime", (), {"blackboard": [
            {"label": "selected_plan", "payload": {"intent": "ask_miss_me"}},
            {"label": "semantic_route_outcome_m22", "payload": {}},
            {"label": "personhood_action_choice_v2_13", "payload": {"pre_scope": True}},
        ], "last_selected_plan": {}, "active_goal": ""})()
        dummy = type("Brain", (), {
            "runtime": runtime,
            "right_brain": type("Right", (), {"_structured_surface_required": lambda self: False})(),
            "_plan_trace_summary": lambda self, plan: {"intent": plan["intent"], "core_message_jp": plan["core_message_jp"]},
        })()
        with patch.object(scope, "_ORIGINAL_TICK", return_value={"logic": original_logic, "route_info": {"route": "high_road"}}):
            tick = scope.cognitive_tick_with_quoted_line_act_scope_p4(dummy, {"user_input": NATURAL, "memory_data": {scope.LABEL: certificate}})
        logic = tick["logic"]
        self.assertEqual(logic["intent"], "quoted_line_feedback")
        self.assertEqual(logic["planner_path"], scope.PLANNER_PATH)
        self.assertEqual(logic["core_message_jp"], certificate["selected_core_jp"])
        self.assertEqual(logic["dialogue_act"], "direct_chat_answer")
        self.assertEqual(logic[scope.LABEL]["pre_scope_selected_plan"]["intent"], "ask_miss_me")
        self.assertFalse(logic["memory_use_expected"])
        self.assertEqual(runtime.blackboard[0]["payload"]["intent"], "quoted_line_feedback")
        self.assertEqual(runtime.blackboard[1]["payload"]["post_scope_selected_plan_authority"], scope.LABEL)
        self.assertEqual(runtime.blackboard[2]["payload"], {"pre_scope": True})

    def test_late_boundary_preserves_protected_route(self):
        certificate = scope.classify_quoted_line_act_scope_p4(NATURAL)
        original_logic = {"intent": "crisis_support", "scene": "support", "semantic_route_m22": {"selected_type": "safety_sensitive"}}
        dummy = type("Brain", (), {"right_brain": type("Right", (), {"_structured_surface_required": lambda self: False})()})()
        original = {"logic": original_logic, "route_info": {"route": "low_road"}}
        with patch.object(scope, "_ORIGINAL_TICK", return_value=original):
            tick = scope.cognitive_tick_with_quoted_line_act_scope_p4(dummy, {"user_input": NATURAL, "memory_data": {scope.LABEL: certificate}})
        self.assertIs(tick, original)
        self.assertEqual(tick["logic"]["intent"], "crisis_support")

    def test_final_guard_answers_outer_act_and_graph_receipt_matches_utterance(self):
        certificate = scope.classify_quoted_line_act_scope_p4(NATURAL)
        logic = LeftBrain(client_logic=None)._normalize_plan(scope._plan_from_scope(certificate))
        logic.update({"semantic_route_m22": {"selected_type": "general_conversation"}, "memory_anchor": {}, "memory_use_expected": False})
        memory = {scope.LABEL: certificate}
        dummy = type("Right", (), {
            "_structured_surface_required": lambda self: False,
            "_user_visible_language_rejection_reasons": lambda self, *args, **kwargs: [],
        })()
        with patch.object(scope, "_ORIGINAL_VISIBLE_GUARD", return_value="前の別件って話は拾ってる。"):
            visible = scope.visible_guard_with_quoted_line_act_scope_p4(dummy, "前の別件って話は拾ってる。", logic, user_input=NATURAL, memory_data=memory)
        self.assertEqual(visible, certificate["selected_core_jp"])
        self.assertEqual(logic[scope.LABEL]["visible_surface_status"], "matched")
        self.assertEqual(logic["visible_language_guard"]["final_reply"], visible)
        result = {
            "reply": visible, "logic": logic,
            "runtime_trace": {"blackboard": [
                {"stage": "select", "label": "selected_plan", "payload": {"intent": logic["intent"]}},
                {"stage": "utterance", "label": "utterance", "payload": {"reply": visible}},
            ]},
        }
        scope.materialize_quoted_line_act_scope_p4(result)
        labels = [row["label"] for row in result["runtime_trace"]["blackboard"]]
        self.assertEqual(labels, [scope.LABEL, "selected_plan", "utterance"])
        self.assertTrue(result["runtime_trace"][scope.LABEL]["final_visible_surface_matches_contract"])
        self.assertEqual(result["runtime_trace"][scope.LABEL]["final_visible_surface_sha256"], scope._sha(visible))

    def test_integrity_mismatch_fails_closed_without_old_memory_fact(self):
        certificate = scope.classify_quoted_line_act_scope_p4(TONE)
        logic = LeftBrain(client_logic=None)._normalize_plan(scope._plan_from_scope(certificate))
        logic.update({"semantic_route_m22": {"selected_type": "general_conversation"}, "memory_anchor": {"value": "前の別件"}, "memory_use_expected": True})
        dummy = type("Right", (), {"_structured_surface_required": lambda self: False})()
        with patch.object(scope, "_ORIGINAL_VISIBLE_GUARD", return_value="前の別件だろ。"):
            final = scope.visible_guard_with_quoted_line_act_scope_p4(dummy, "前の別件だろ。", logic, user_input=TONE, memory_data={scope.LABEL: certificate})
        self.assertEqual(final, scope._UNKNOWN_CORE)
        self.assertNotIn("前の別件", final)
        self.assertEqual(logic[scope.LABEL]["visible_surface_status"], "failed_closed")
        self.assertFalse(logic[scope.LABEL]["final_visible_surface_matches_contract"])
        self.assertEqual(logic[scope.LABEL]["selected_core_sha256"], certificate["selected_core_sha256"])
        self.assertEqual(logic[scope.LABEL]["memory_anchor_admission"], "anchor_present_or_expected_integrity_failure")
        self.assertIn("scope_plan_or_source_integrity_mismatch", logic["visible_language_guard"]["final_rejection_reasons"])
