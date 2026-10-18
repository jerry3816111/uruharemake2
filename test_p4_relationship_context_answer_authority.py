"""Zero-model contracts; fixtures are disjoint from the frozen six-turn probe."""

import ast
from copy import deepcopy
from pathlib import Path
from unittest import TestCase
from unittest.mock import patch

from uruha_brain_mac import RightBrain
import uruha_relationship_context_answer_authority_p4 as authority
from uruha_trace_history_sync_m41_1 import sync_current_history_m41_1


ROOT = Path(__file__).resolve().parent
RELATIONSHIP_INPUT = "あのさ、こっちのこと今も覚えてる？"
FACTUAL_INPUT = "さっきの改札番号、何だったっけ？"
QUOTE_EDIT_INPUT = "「次も来る？」って台詞、自然かな？"
META_SOURCE = "User:「次も来る？」って台詞、自然かな？ -> Uruha:言い方次第だな。"


def make_brain(*, route="high_road", structured=False):
    runtime = type("Runtime", (), {"last_route": {"route": route}})()
    right = type("Right", (), {"_structured_surface_required": lambda self: structured})()
    return type("Brain", (), {"runtime": runtime, "right_brain": right})()


def generic_anchor(*, source="short_term", trace_id="derived:short_term:fixture", source_text=META_SOURCE):
    return {
        "kind": "context", "source": source, "trace_id": trace_id,
        "source_text": source_text, "value": source_text[:32],
        "jp_anchor": source_text[:24], "score": 2.2, "expected": True,
    }


def memory_with_anchor(anchor, *, source_intent="quoted_line_feedback"):
    return {
        "working_memory_items": [{
            "source": anchor.get("source"),
            "trace_id": anchor.get("trace_id"),
            "text": anchor.get("source_text"),
            "score": 2.2,
            "metadata": {"intent": source_intent},
        }],
        "memory_provenance": {"candidate_pool": [{"trace_id": anchor.get("trace_id"), "rank": 1}]},
    }


def original_gravity_with(anchor, *, expected=True):
    def original(_self, logic, _input, _memory):
        logic.update({
            "memory_anchor": deepcopy(anchor),
            "memory_relevance": 0.81,
            "memory_relevance_label": "high",
            "memory_speakability": "explicit_ok" if expected else "suppressed_sensitive",
            "memory_speakability_reason": "directly_relevant_or_requested" if expected else "sensitive_memory",
            "memory_gravity": 0.81 if expected else 0.0,
            "memory_use_expected": expected,
            "my_hidden_knowledge": "前の知識。 記憶では引用台詞が効く。",
            "user_expectation": "前の期待。 覚えているなら引用台詞に触れる。",
        })
        return logic
    return original


class RelationshipContextAnswerAuthorityTests(TestCase):
    def test_selected_relationship_act_revokes_generic_context_answer_not_retrieval(self):
        anchor = generic_anchor()
        memory = memory_with_anchor(anchor)
        snapshot = deepcopy(memory)
        core = "まあ、少しくらいは気にしてるし。"
        logic = {
            "intent": "ask_miss_me", "scene": "casual", "surface_act": "affection_tease_soften",
            "core_message_jp": core, "my_hidden_knowledge": "前の知識。", "user_expectation": "前の期待。",
            "semantic_route_m22": {"selected_type": "factual_or_memory"},
        }
        with patch.object(authority, "_ORIGINAL_GRAVITY", side_effect=original_gravity_with(anchor)):
            result = authority.attach_relationship_context_answer_authority_p4(
                make_brain(), logic, RELATIONSHIP_INPUT, memory
            )
        self.assertIs(result, logic)
        self.assertEqual(memory, snapshot)
        self.assertEqual(result["core_message_jp"], core)
        self.assertEqual(result["intent"], "ask_miss_me")
        self.assertEqual(result["memory_anchor"], {})
        self.assertFalse(result["memory_use_expected"])
        self.assertEqual(result["my_hidden_knowledge"], "前の知識。")
        self.assertEqual(result["user_expectation"], "前の期待。")
        receipt = result[authority.LABEL]
        self.assertEqual(receipt["source_trace_id"], anchor["trace_id"])
        self.assertEqual(receipt["source_role"], "quoted_line_feedback")
        self.assertEqual(receipt["source_match_count"], 1)
        self.assertFalse(receipt["answer_use_authorized"])
        self.assertFalse(receipt["retrieval_or_ranking_changed"])
        self.assertFalse(receipt["model_call_added"])
        self.assertEqual(RightBrain._memory_grounded_reply(RightBrain.__new__(RightBrain), result, RELATIONSHIP_INPUT), None)

    def test_source_missing_or_ambiguous_does_not_gain_relationship_answer_authority(self):
        for memory in ({"working_memory_items": []}, {"working_memory_items": [
            {"source": "short_term", "trace_id": "derived:short_term:fixture", "text": META_SOURCE, "metadata": {"intent": "chat"}},
            {"source": "short_term", "trace_id": "derived:short_term:fixture", "text": META_SOURCE, "metadata": {"intent": "quoted_line_feedback"}},
        ]}):
            with self.subTest(memory=memory):
                logic = {"intent": "ask_miss_me", "scene": "casual", "core_message_jp": "少しは気にしてる。"}
                with patch.object(authority, "_ORIGINAL_GRAVITY", side_effect=original_gravity_with(generic_anchor())):
                    result = authority.attach_relationship_context_answer_authority_p4(
                        make_brain(), logic, RELATIONSHIP_INPUT, memory
                    )
                self.assertEqual(result["memory_anchor"], {})
                self.assertFalse(result["memory_use_expected"])
                self.assertEqual(result[authority.LABEL]["source_role"], "unavailable")

    def test_long_source_metadata_remains_traceable_without_restoring_answer_authority(self):
        long_text = "User:「次も来る？」って台詞の言い方を相談した。" + "前後の文脈。" * 20
        anchor = generic_anchor(source_text=long_text[:119] + "…")
        memory = memory_with_anchor(anchor)
        memory["working_memory_items"][0]["text"] = long_text
        logic = {"intent": "ask_miss_me", "scene": "casual", "core_message_jp": "少しは気にしてる。"}
        with patch.object(authority, "_ORIGINAL_GRAVITY", side_effect=original_gravity_with(anchor)):
            result = authority.attach_relationship_context_answer_authority_p4(
                make_brain(), logic, RELATIONSHIP_INPUT, memory
            )
        self.assertEqual(result[authority.LABEL]["source_role"], "quoted_line_feedback")
        self.assertFalse(result["memory_use_expected"])

    def test_sensitive_or_third_party_context_is_never_promoted(self):
        for source_text in (
            "User:友達が別の人の気持ちを聞いていた -> Uruha:分からない。",
            "User:秘密の住所を話した -> Uruha:言わない。",
        ):
            with self.subTest(source_text=source_text):
                anchor = generic_anchor(source_text=source_text)
                logic = {"intent": "ask_miss_me", "scene": "casual", "core_message_jp": "少しは気にしてる。"}
                with patch.object(authority, "_ORIGINAL_GRAVITY", side_effect=original_gravity_with(anchor, expected=False)):
                    result = authority.attach_relationship_context_answer_authority_p4(
                        make_brain(), logic, RELATIONSHIP_INPUT, memory_with_anchor(anchor, source_intent="chat")
                    )
                self.assertFalse(result["memory_use_expected"])
                self.assertNotIn(source_text, str(result))
                self.assertEqual(result[authority.LABEL]["source_trace_id"], anchor["trace_id"])

    def test_factual_recall_profile_and_quote_edit_are_unchanged(self):
        cases = (
            ({"intent": "recall_context", "scene": "casual"}, generic_anchor(), FACTUAL_INPUT),
            ({"intent": "ask_miss_me", "scene": "casual"}, generic_anchor(source="profile"), RELATIONSHIP_INPUT),
            ({"intent": "ask_miss_me", "scene": "casual"}, {"kind": "profile_grounded", "source": "profile", "value": "呼び名"}, RELATIONSHIP_INPUT),
            ({"intent": "quoted_line_feedback", "scene": "casual"}, generic_anchor(), QUOTE_EDIT_INPUT),
        )
        for seed, anchor, utterance in cases:
            with self.subTest(seed=seed, anchor=anchor):
                logic = {**seed, "core_message_jp": "元の計画を保つ。"}
                with patch.object(authority, "_ORIGINAL_GRAVITY", side_effect=original_gravity_with(anchor)):
                    result = authority.attach_relationship_context_answer_authority_p4(
                        make_brain(), logic, utterance, memory_with_anchor(anchor)
                    )
                self.assertEqual(result["memory_anchor"], anchor)
                self.assertTrue(result["memory_use_expected"])
                self.assertNotIn(authority.LABEL, result)

    def test_protected_scene_intent_low_road_and_structured_surface_bypass(self):
        anchor = generic_anchor()
        cases = (
            ({"intent": "ask_miss_me", "scene": "support"}, make_brain()),
            ({"intent": "crisis_support", "scene": "casual"}, make_brain()),
            ({"intent": "ask_miss_me", "scene": "casual", "semantic_route_m22": {"selected_type": "safety_sensitive"}}, make_brain()),
            ({"intent": "ask_miss_me", "scene": "casual"}, make_brain(route="low_road")),
            ({"intent": "ask_miss_me", "scene": "casual"}, make_brain(route=None)),
            ({"intent": "ask_miss_me", "scene": "casual"}, make_brain(structured=True)),
        )
        for seed, brain in cases:
            with self.subTest(seed=seed):
                logic = {**seed, "core_message_jp": "選定した中核。"}
                with patch.object(authority, "_ORIGINAL_GRAVITY", side_effect=original_gravity_with(anchor)):
                    result = authority.attach_relationship_context_answer_authority_p4(
                        brain, logic, RELATIONSHIP_INPUT, memory_with_anchor(anchor)
                    )
                self.assertEqual(result["memory_anchor"], anchor)
                self.assertNotIn(authority.LABEL, result)

    def test_no_anchor_is_noop(self):
        logic = {"intent": "ask_miss_me", "scene": "casual", "core_message_jp": "選定した中核。"}
        with patch.object(authority, "_ORIGINAL_GRAVITY", return_value=logic):
            self.assertIs(authority.attach_relationship_context_answer_authority_p4(make_brain(), logic, RELATIONSHIP_INPUT, {}), logic)
        self.assertNotIn(authority.LABEL, logic)

    def test_graph_receipt_links_source_and_final_without_claiming_semantic_pass(self):
        anchor = generic_anchor()
        logic = {"intent": "ask_miss_me", "scene": "casual", "core_message_jp": "少しは気にしてる。"}
        with patch.object(authority, "_ORIGINAL_GRAVITY", side_effect=original_gravity_with(anchor)):
            authority.attach_relationship_context_answer_authority_p4(
                make_brain(), logic, RELATIONSHIP_INPUT, memory_with_anchor(anchor)
            )
        result = {"reply": "まあ、少しは気にしてるし。", "logic": logic, "runtime_trace": {"blackboard": [
            {"label": "selected_plan", "payload": {"intent": "ask_miss_me"}},
            {"label": "utterance", "payload": {"reply": "まあ、少しは気にしてるし。"}},
        ]}}
        authority.materialize_relationship_context_answer_authority_p4(result)
        authority.materialize_relationship_context_answer_authority_p4(result)
        labels = [row["label"] for row in result["runtime_trace"]["blackboard"]]
        self.assertEqual(labels, ["selected_plan", authority.LABEL, "utterance"])
        receipt = result["runtime_trace"][authority.LABEL]
        self.assertEqual(receipt["final_visible_surface_sha256"], authority._sha(result["reply"]))
        self.assertTrue(receipt["selected_core_still_same"])
        self.assertFalse(receipt["final_contains_serialized_memory_role"])
        self.assertEqual(receipt["semantic_product_gate"], "requires_fresh_visible_turn_review")
        result["reply"] = "前にUser:引用の台詞って言ってたろ。"
        authority.materialize_relationship_context_answer_authority_p4(result)
        self.assertTrue(result["runtime_trace"][authority.LABEL]["final_contains_serialized_memory_role"])

    def test_same_cycle_graph_receipt_is_mirrored_without_changing_prior_cycle(self):
        anchor = generic_anchor()
        logic = {"intent": "ask_miss_me", "scene": "casual", "core_message_jp": "少しは気にしてる。"}
        with patch.object(authority, "_ORIGINAL_GRAVITY", side_effect=original_gravity_with(anchor)):
            authority.attach_relationship_context_answer_authority_p4(
                make_brain(), logic, RELATIONSHIP_INPUT, memory_with_anchor(anchor)
            )
        earlier = {"cycle_index": 1, "blackboard": [{"label": "earlier"}]}
        result = {
            "reply": "まあ、少しは気にしてるし。",
            "logic": logic,
            "runtime_trace": {"cycle_index": 2, "blackboard": [
                {"label": "selected_plan"}, {"label": "utterance"},
            ]},
            "runtime_state": {"recent_turn_traces": [deepcopy(earlier), {"cycle_index": 2, "blackboard": []}]},
        }
        authority.materialize_relationship_context_answer_authority_p4(result)
        sync_current_history_m41_1(result)
        self.assertEqual(result["runtime_state"]["blackboard"], result["runtime_trace"]["blackboard"])
        self.assertEqual(result["runtime_state"]["recent_turn_traces"][-1], result["runtime_trace"])
        self.assertEqual(result["runtime_state"]["recent_turn_traces"][0], earlier)

    def test_opt_in_entry_installs_after_prior_scope_and_controller_points_to_it(self):
        entry = ROOT / "uruha_web_ui_product_p4_relationship_context_answer_authority.py"
        tree = ast.parse(entry.read_text(encoding="utf-8"))
        calls = [
            node.func.id for node in ast.walk(tree)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
        ]
        self.assertLess(calls.index("install_quoted_line_act_scope_p4"), calls.index("install_relationship_context_answer_authority_p4"))
        controller = (ROOT / "p4_relationship_context_answer_authority_detached_control.py").read_text(encoding="utf-8")
        self.assertIn(entry.name, controller)
