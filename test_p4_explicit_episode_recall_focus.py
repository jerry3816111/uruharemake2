"""Zero-model contracts; strings here are distinct from the frozen Web probe."""

import ast
from copy import deepcopy
from pathlib import Path
import uuid
from unittest import TestCase
from unittest.mock import patch

import uruha_explicit_episode_recall_focus_p4 as focus
from uruha_memory_observatory import collect_memory_nodes
from uruha_brain_mac import LeftBrain


ROOT = Path(__file__).resolve().parent
QUERY = "さっき言った出発駅、覚えてる？"
SOURCE = "出発する駅は東口の改札だよ。"
OTHER = "出発する時刻は八時だよ。"
QUOTE = "兄が「出発駅を確認して」と言ってた。"


def episode(user, rank, *, selected=False, memory_id=None):
    memory_id = memory_id or str(uuid.uuid4())
    text = (
        "Time: 2026-10-18 11:00:00 | Intent: chat | Scene: casual | "
        "CognitiveMode: direct | PremiseCheck: accept | Routing: high_road | "
        f"User: {user} | Summary: 雑談をしている。 | Uruha: うん。 | Mood: {{'mood': 0}}"
    )
    return {
        "source": "episode",
        "collection_name": "episode",
        "memory_id": memory_id,
        "trace_id": f"stored:episode:{memory_id}",
        "text": text,
        "rank": rank,
        "selected": selected,
        "channel": "working_memory_candidate",
        "score": 1.5 - rank / 100,
        "attention_factors": {},
    }


def memory_data(*episode_rows, extra_rows=()):
    pool = [*extra_rows, *episode_rows]
    ranked = sorted(pool, key=lambda row: row["rank"])
    selected = [row["trace_id"] for row in ranked if row["selected"]]
    return {
        "working_memory_items": [row for row in ranked if row["selected"]],
        "memory_provenance": {
            "schema": "uruha_memory_provenance_trace_v1",
            "working_memory_limit": 5,
            "candidate_count": len(ranked),
            "candidate_pool": ranked,
            "retrieved_candidates": [
                {**deepcopy(row), "channel": "retrieved_candidate", "ranking_status": "ranked"}
                for row in ranked
            ],
            "selected_working_memory_trace_ids": selected,
            "passed_to_leftbrain": [
                {**deepcopy(row), "channel": "selected_working_memory"}
                for row in ranked if row["selected"]
            ],
            "passed_to_leftbrain_trace_ids": selected.copy(),
        },
    }


def top_five_plus_target():
    # The answer-bearing episode is retrieved at rank six but is not ordinary
    # working memory.  An unrelated quoted instruction cannot become a fact.
    users = [
        OTHER,
        QUOTE,
        "乗車する券は紙の切符だよ。",
        "会議する部屋は三階だよ。",
        "出発する持ち物は紺の鞄だよ。",
    ]
    rows = [episode(user, rank, selected=True) for rank, user in enumerate(users, 1)]
    rows.append(episode(SOURCE, 6, selected=False))
    return memory_data(*rows), rows[-1]


class ExplicitEpisodeRecallFocusTests(TestCase):
    def test_classifies_only_unquoted_specific_japanese_past_query(self):
        decision = focus.classify_explicit_episode_recall_focus_p4(QUERY)
        self.assertTrue(decision["eligible"])
        self.assertEqual(decision["focus_key"], "出発駅")
        for text in (
            "私のこと、まだ覚えてる？",
            "「出発駅、覚えてる？」って台詞は変？",
            "前に言った出発駅、覚えてる？ 今すぐ助けて",
            "Do you remember the departure station?",
            "你記得之前說的出發站嗎？",
        ):
            with self.subTest(text=text):
                self.assertFalse(focus.classify_explicit_episode_recall_focus_p4(text)["eligible"])

    def test_rank_six_episode_has_source_bound_handoff_without_falsifying_top_five(self):
        data, target = top_five_plus_target()
        before = deepcopy(data["memory_provenance"])
        contract = focus.build_explicit_episode_recall_focus_contract_p4(QUERY, data)
        self.assertEqual(contract["status"], "selected_unique_user_episode")
        self.assertEqual(contract["trace_id"], target["trace_id"])
        self.assertEqual(contract["candidate_rank"], 6)
        self.assertFalse(contract["ordinary_working_memory_selected"])
        self.assertEqual(contract["prior_passed_channels"], [])
        self.assertIn("東口の改札", contract["selected_core_jp"])
        self.assertNotIn("兄が", contract["selected_core_jp"])

        with patch.object(focus, "_ORIGINAL_QUERY", return_value=data):
            returned = focus.query_all_layers_with_explicit_episode_recall_focus_p4(object(), QUERY)
        provenance = returned["memory_provenance"]
        self.assertEqual(provenance["candidate_pool"], before["candidate_pool"])
        self.assertEqual(
            provenance["selected_working_memory_trace_ids"],
            before["selected_working_memory_trace_ids"],
        )
        self.assertEqual(returned["working_memory_items"], data["working_memory_items"])
        self.assertIn(target["trace_id"], provenance["passed_to_leftbrain_trace_ids"])
        handed = [
            row for row in provenance["passed_to_leftbrain"]
            if row["trace_id"] == target["trace_id"]
        ]
        self.assertEqual(len(handed), 1)
        self.assertEqual(handed[0]["channel"], focus.HANDOFF_CHANNEL)
        self.assertEqual(handed[0]["rank"], 6)
        self.assertFalse(handed[0]["selected"])
        self.assertFalse(provenance["candidate_pool"][-1]["selected"])
        graph_node = next(
            row for row in collect_memory_nodes({"memory_data": returned})
            if row["trace_id"] == target["trace_id"]
        )
        self.assertEqual(graph_node["rank"], 6)
        self.assertFalse(graph_node["selected"])
        self.assertTrue(graph_node["passed"])

    def test_selected_plan_normalization_guard_and_graph_bind_same_source(self):
        data, target = top_five_plus_target()
        with patch.object(focus, "_ORIGINAL_QUERY", return_value=data):
            data = focus.query_all_layers_with_explicit_episode_recall_focus_p4(object(), QUERY)
        plan = focus._plan_from_contract(data[focus.LABEL])
        normalized = LeftBrain(client_logic=None)._normalize_plan(plan)
        self.assertEqual(normalized["intent"], "recall_context")
        self.assertEqual(normalized["planner_path"], focus.PLANNER_PATH)
        self.assertEqual(normalized["memory_recall_contract"]["trace_id"], target["trace_id"])
        normalized["semantic_route_m22"] = {"selected_type": "factual_or_memory"}
        dummy_right = type("Right", (), {
            "_structured_surface_required": lambda self: False,
            "_user_visible_language_rejection_reasons": lambda self, *args, **kwargs: [],
        })()
        with patch.object(focus, "_ORIGINAL_VISIBLE_GUARD", return_value="元の候補。"):
            visible = focus.visible_guard_with_explicit_episode_recall_focus_p4(
                dummy_right, "元の候補。", normalized, user_input=QUERY, memory_data=data
            )
        self.assertEqual(visible, data[focus.LABEL]["selected_core_jp"])
        result = {
            "reply": visible,
            "logic": normalized,
            "runtime_trace": {
                "cycle_index": 1,
                "blackboard": [
                    {"stage": "select", "label": "selected_plan", "payload": {}},
                    {"stage": "utterance", "label": "utterance", "payload": {"reply": visible}},
                ],
            },
        }
        focus.materialize_explicit_episode_recall_focus_p4(result)
        node = next(row for row in result["runtime_trace"]["blackboard"] if row["label"] == focus.LABEL)
        self.assertEqual(node["payload"]["trace_id"], target["trace_id"])
        self.assertTrue(node["payload"]["final_visible_surface_matches_contract"])
        self.assertEqual(result["reply"], result["logic"]["memory_recall_contract"]["selected_core_jp"])
        self.assertEqual(normalized["visible_language_guard"]["final_reply"], visible)
        self.assertTrue(normalized["visible_language_guard"]["changed"])
        self.assertEqual(
            normalized["visible_language_guard"]["repair_action"],
            "explicit_episode_recall_focus_matched",
        )

    def test_prior_direct_episode_passage_is_disclosed_not_claimed_as_new(self):
        data, target = top_five_plus_target()
        data["memory_provenance"]["passed_to_leftbrain"].append(
            {**deepcopy(target), "channel": "direct_episode"}
        )
        data["memory_provenance"]["passed_to_leftbrain_trace_ids"].append(target["trace_id"])
        contract = focus.build_explicit_episode_recall_focus_contract_p4(QUERY, data)
        self.assertEqual(contract["prior_passed_channels"], ["direct_episode"])
        self.assertFalse(contract["ordinary_working_memory_selected"])

    def test_missing_or_conflicting_source_abstains_without_value(self):
        no_source = memory_data(episode(OTHER, 1, selected=True))
        missing = focus.build_explicit_episode_recall_focus_contract_p4(QUERY, no_source)
        self.assertEqual(missing["status"], "unavailable")
        self.assertNotIn("八時", missing["selected_core_jp"])

        conflicting = memory_data(
            episode(SOURCE, 1, selected=True),
            episode("出発する駅は西口の改札だよ。", 2, selected=True),
        )
        contract = focus.build_explicit_episode_recall_focus_contract_p4(QUERY, conflicting)
        self.assertEqual(contract["status"], "conflicting_or_nonunique")
        self.assertFalse(contract["source_selected"])
        self.assertNotIn("東口", contract["selected_core_jp"])

    def test_retraction_sensitive_and_malformed_provenance_fail_closed(self):
        retracted = memory_data(
            episode(SOURCE, 1, selected=True),
            episode("出発する駅はまだ決めてないよ。", 2, selected=True),
        )
        self.assertEqual(
            focus.build_explicit_episode_recall_focus_contract_p4(QUERY, retracted)["status"],
            "retracted_or_uncertain",
        )
        changed = memory_data(
            episode(SOURCE, 1, selected=True),
            episode("出発駅、西口の改札に変更した。", 2, selected=True),
        )
        self.assertEqual(
            focus.build_explicit_episode_recall_focus_contract_p4(QUERY, changed)["status"],
            "retracted_or_uncertain",
        )
        sensitive = memory_data(episode("合言葉は秘密の数字だよ。", 1, selected=True))
        secret = focus.build_explicit_episode_recall_focus_contract_p4(
            "前に言った合言葉、覚えてる？", sensitive
        )
        self.assertEqual(secret["status"], "suppressed")
        self.assertNotIn("秘密", secret["selected_core_jp"])
        plain_digits = memory_data(episode("合言葉は1234だよ。", 1, selected=True))
        digit_secret = focus.build_explicit_episode_recall_focus_contract_p4(
            "前に言った合言葉、覚えてる？", plain_digits
        )
        self.assertEqual(digit_secret["status"], "suppressed")
        self.assertNotIn("1234", digit_secret["selected_core_jp"])
        invalid = memory_data(episode(SOURCE, 1, selected=True))
        invalid["memory_provenance"]["candidate_pool"][0]["memory_id"] = "fabricated"
        self.assertEqual(
            focus.build_explicit_episode_recall_focus_contract_p4(QUERY, invalid)["reason"],
            "episode_provenance_incomplete",
        )

    def test_guard_does_not_take_over_without_exact_plan_source_or_safe_route(self):
        data, _ = top_five_plus_target()
        with patch.object(focus, "_ORIGINAL_QUERY", return_value=data):
            data = focus.query_all_layers_with_explicit_episode_recall_focus_p4(object(), QUERY)
        base = focus._plan_from_contract(data[focus.LABEL])
        base["semantic_route_m22"] = {"selected_type": "factual_or_memory"}
        dummy_right = type("Right", (), {
            "_structured_surface_required": lambda self: False,
            "_user_visible_language_rejection_reasons": lambda self, *args, **kwargs: [],
        })()
        with patch.object(focus, "_ORIGINAL_VISIBLE_GUARD", return_value="元の候補。"):
            for changed in (
                {**base, "planner_path": "other_path"},
                {**base, "core_message_jp": "別の話だよ。"},
                {**base, "semantic_route_m22": {"selected_type": "safety_sensitive"}},
            ):
                with self.subTest(changed=changed.get("planner_path"), core=changed.get("core_message_jp")):
                    expected = (
                        "元の候補。"
                        if (changed.get("semantic_route_m22") or {}).get("selected_type") == "safety_sensitive"
                        else focus._UNKNOWN_CORE
                    )
                    self.assertEqual(
                        focus.visible_guard_with_explicit_episode_recall_focus_p4(
                            dummy_right, "元の候補。", changed, user_input=QUERY, memory_data=data
                        ), expected,
                    )
            no_handoff = deepcopy(data)
            no_handoff["memory_provenance"]["passed_to_leftbrain"] = []
            self.assertEqual(
                focus.visible_guard_with_explicit_episode_recall_focus_p4(
                    dummy_right, "元の候補。", base, user_input=QUERY, memory_data=no_handoff
                ),
                focus._UNKNOWN_CORE,
            )
            structured_right = type("Right", (), {
                "_structured_surface_required": lambda self: True,
                "_user_visible_language_rejection_reasons": lambda self, *args, **kwargs: [],
            })()
            self.assertEqual(
                focus.visible_guard_with_explicit_episode_recall_focus_p4(
                    structured_right, "元の候補。", base, user_input=QUERY, memory_data=data
                ),
                focus._UNKNOWN_CORE,
            )

    def test_protected_predecessor_plan_preserved(self):
        data, _ = top_five_plus_target()
        with patch.object(focus, "_ORIGINAL_QUERY", return_value=data):
            data = focus.query_all_layers_with_explicit_episode_recall_focus_p4(object(), QUERY)
        protected = {"intent": "crisis_support", "scene": "support", "core_message_jp": "今は一人になるな。"}
        with patch.object(focus, "_ORIGINAL_RULE_PLAN", return_value=protected):
            self.assertIs(
                focus.rule_plan_with_explicit_episode_recall_focus_p4(object(), QUERY, {}, data),
                protected,
            )
        ordinary = {"intent": "ask_miss_me", "scene": "casual"}
        with patch.object(focus, "_ORIGINAL_RULE_PLAN", return_value=ordinary):
            selected = focus.rule_plan_with_explicit_episode_recall_focus_p4(object(), QUERY, {}, data)
        self.assertEqual(selected["intent"], "recall_context")

    def test_language_checker_rejection_abstains_instead_of_leaking_source(self):
        data, _ = top_five_plus_target()
        with patch.object(focus, "_ORIGINAL_QUERY", return_value=data):
            data = focus.query_all_layers_with_explicit_episode_recall_focus_p4(object(), QUERY)
        plan = focus._plan_from_contract(data[focus.LABEL])
        plan["semantic_route_m22"] = {"selected_type": "factual_or_memory"}
        right = type("Right", (), {
            "_structured_surface_required": lambda self: False,
            "_user_visible_language_rejection_reasons": lambda self, *args, **kwargs: ["rejected"],
        })()
        with patch.object(focus, "_ORIGINAL_VISIBLE_GUARD", return_value="東口の改札だよ。"):
            visible = focus.visible_guard_with_explicit_episode_recall_focus_p4(
                right, "東口の改札だよ。", plan, user_input=QUERY, memory_data=data
            )
        self.assertEqual(visible, focus._UNKNOWN_CORE)
        self.assertEqual(plan[focus.LABEL]["visible_surface_status"], "failed_closed")
        result = {"reply": visible, "logic": plan, "runtime_trace": {"blackboard": []}}
        focus.materialize_explicit_episode_recall_focus_p4(result)
        self.assertEqual(result["runtime_trace"][focus.LABEL]["visible_surface_status"], "failed_closed")

    def test_entry_and_controller_are_thin_static_opt_in_only(self):
        entry = ROOT / "uruha_web_ui_product_p4_explicit_episode_recall_focus.py"
        controller = ROOT / "p4_explicit_episode_recall_focus_detached_control.py"
        self.assertTrue(entry.is_file())
        self.assertTrue(controller.is_file())
        entry_tree = ast.parse(entry.read_text(encoding="utf-8"))
        controller_tree = ast.parse(controller.read_text(encoding="utf-8"))
        self.assertTrue(any(
            isinstance(node, ast.ImportFrom)
            and node.module == "uruha_explicit_episode_recall_focus_p4"
            for node in entry_tree.body
        ))
        self.assertTrue(any(
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "install_explicit_episode_recall_focus_p4"
            for node in ast.walk(entry_tree)
        ))
        self.assertTrue(any(
            isinstance(node, ast.Assign)
            and any(isinstance(target, ast.Name) and target.id == "ENTRYPOINT" for target in node.targets)
            for node in controller_tree.body
        ))


if __name__ == "__main__":
    import unittest

    unittest.main()
