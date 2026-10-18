"""Zero-model admission and existing source-bound recall contracts.

The examples here are fixtures, not the frozen prospective Web utterances.
"""

import ast
from copy import deepcopy
import hashlib
from pathlib import Path
from unittest import TestCase
from unittest.mock import patch

import uruha_explicit_episode_recall_focus_p4 as focus
import uruha_temporal_specific_recall_admission_p4 as temporal
from test_p4_explicit_episode_recall_focus import OTHER, SOURCE, episode, memory_data, top_five_plus_target
from uruha_brain_mac import LeftBrain
from uruha_memory_observatory import collect_memory_nodes


FIRST_QUERY = "少し前に言った出発駅、覚えてる？"
SECOND_QUERY = "ちょっと前に話した出発駅、覚えてる？"
ROOT = Path(__file__).resolve().parent


def raw_sha(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class TemporalSpecificRecallAdmissionTests(TestCase):
    def test_opt_in_web_entry_order_and_detached_controller_target(self):
        entry = ROOT / "uruha_web_ui_product_p4_temporal_specific_recall_admission.py"
        tree = ast.parse(entry.read_text(encoding="utf-8"))
        calls = [
            node.func.id for node in ast.walk(tree)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
        ]
        self.assertLess(
            calls.index("install_explicit_episode_recall_focus_p4"),
            calls.index("install_temporal_specific_recall_admission_p4"),
        )
        self.assertLess(
            calls.index("install_quoted_line_act_scope_p4"),
            calls.index("install_temporal_specific_recall_admission_p4"),
        )
        controller = (ROOT / "p4_temporal_specific_recall_admission_detached_control.py").read_text(encoding="utf-8")
        self.assertIn(entry.name, controller)

    def test_uninstalled_focus_is_unchanged_and_old_grammars_are_preserved(self):
        self.assertIs(focus.classify_explicit_episode_recall_focus_p4, temporal._BASE_CLASSIFIER)
        self.assertFalse(focus.classify_explicit_episode_recall_focus_p4(FIRST_QUERY)["eligible"])
        for text in (
            "さっき言った出発駅、覚えてる？",
            "前に話した出発駅、覚えてる？",
            "以前決めた出発駅、覚えてる？",
        ):
            with self.subTest(text=text):
                self.assertEqual(
                    temporal.classify_temporal_specific_recall_admission_p4(text),
                    focus.classify_explicit_episode_recall_focus_p4(text),
                )

    def test_only_two_exact_unquoted_temporal_modifiers_are_admitted(self):
        for text, phrase in ((FIRST_QUERY, "少し前に"), (SECOND_QUERY, "ちょっと前に")):
            with self.subTest(text=text):
                decision = temporal.classify_temporal_specific_recall_admission_p4(text)
                self.assertTrue(decision["eligible"])
                self.assertEqual(decision["focus_key"], "出発駅")
                self.assertEqual(decision["input_sha256"], raw_sha(text))
                cert = decision[temporal.CERTIFICATE_KEY]
                self.assertEqual(cert["temporal_phrase"], phrase)
                self.assertEqual(cert["input_sha256"], raw_sha(text))
                self.assertTrue(cert["retrieval_input_unchanged"])
                self.assertNotIn(text, str(cert))
                self.assertNotIn("出発駅", str(cert))
        for text in (
            "『少し前に言った出発駅、覚えてる？』って言い方、自然？",
            "少し前に言った出発駅、覚えてる？ 今すぐ助けて",
            "少し前に兄が言った出発駅、覚えてる？",
            "少し前に言った私のこと、覚えてる？",
            "ちょっと前に話したうちのこと、覚えてる？",
            "少し前に聞いた出発駅、覚えてる？",
            "少し前に言った出発駅は何？",
            "昨日言った出発駅、覚えてる？",
            "少し前に言ったパスワード、覚えてる？",
        ):
            with self.subTest(text=text):
                self.assertFalse(temporal.classify_temporal_specific_recall_admission_p4(text)["eligible"])

    def test_retriever_gets_raw_query_and_rank_six_source_receipt_reaches_graph(self):
        data, target = top_five_plus_target()
        before = deepcopy(data["memory_provenance"])
        seen = []

        def retrieved(_, text):
            seen.append(text)
            return data

        with patch.object(focus, "classify_explicit_episode_recall_focus_p4", temporal.classify_temporal_specific_recall_admission_p4):
            with patch.object(focus, "_ORIGINAL_QUERY", side_effect=retrieved):
                returned = focus.query_all_layers_with_explicit_episode_recall_focus_p4(object(), FIRST_QUERY)
            contract = returned[focus.LABEL]
            self.assertEqual(seen, [FIRST_QUERY])
            self.assertEqual(contract["status"], "selected_unique_user_episode")
            self.assertEqual(contract["input_sha256"], raw_sha(FIRST_QUERY))
            self.assertEqual(contract[temporal.CERTIFICATE_KEY]["temporal_phrase"], "少し前に")
            self.assertEqual(contract["trace_id"], target["trace_id"])
            self.assertEqual(contract["candidate_rank"], 6)
            self.assertFalse(contract["ordinary_working_memory_selected"])
            self.assertEqual(returned["memory_provenance"]["candidate_pool"], before["candidate_pool"])
            self.assertEqual(
                returned["memory_provenance"]["selected_working_memory_trace_ids"],
                before["selected_working_memory_trace_ids"],
            )
            graph_memory = next(
                row for row in collect_memory_nodes({"memory_data": returned})
                if row["trace_id"] == target["trace_id"]
            )
            self.assertTrue(graph_memory["passed"])
            self.assertFalse(graph_memory["selected"])

            plan = LeftBrain(client_logic=None)._normalize_plan(focus._plan_from_contract(contract))
            self.assertEqual(plan["intent"], "recall_context")
            self.assertEqual(plan["memory_recall_contract"]["input_sha256"], raw_sha(FIRST_QUERY))
            plan["semantic_route_m22"] = {"selected_type": "factual_or_memory"}
            right = type("Right", (), {
                "_structured_surface_required": lambda self: False,
                "_user_visible_language_rejection_reasons": lambda self, *args, **kwargs: [],
            })()
            with patch.object(focus, "_ORIGINAL_VISIBLE_GUARD", return_value="元の候補。"):
                visible = focus.visible_guard_with_explicit_episode_recall_focus_p4(
                    right, "元の候補。", plan, user_input=FIRST_QUERY, memory_data=returned
                )
            self.assertEqual(visible, contract["selected_core_jp"])
            self.assertIn("東口の改札", visible)
            result = {
                "reply": visible,
                "logic": plan,
                "runtime_trace": {"blackboard": [
                    {"stage": "select", "label": "selected_plan", "payload": {}},
                    {"stage": "utterance", "label": "utterance", "payload": {"reply": visible}},
                ]},
            }
            focus.materialize_explicit_episode_recall_focus_p4(result)
            node = next(row for row in result["runtime_trace"]["blackboard"] if row["label"] == focus.LABEL)
            self.assertEqual(node["payload"]["trace_id"], target["trace_id"])
            self.assertEqual(node["payload"]["input_sha256"], raw_sha(FIRST_QUERY))
            self.assertEqual(node["payload"][temporal.CERTIFICATE_KEY]["temporal_phrase"], "少し前に")
            self.assertTrue(node["payload"]["final_visible_surface_matches_contract"])

    def test_absent_conflicting_retracted_sensitive_and_bad_source_fail_closed(self):
        with patch.object(focus, "classify_explicit_episode_recall_focus_p4", temporal.classify_temporal_specific_recall_admission_p4):
            cases = (
                (memory_data(episode(OTHER, 1, selected=True)), "unavailable"),
                (memory_data(episode(SOURCE, 1, selected=True), episode("出発する駅は西口の改札だよ。", 2, selected=True)), "conflicting_or_nonunique"),
                (memory_data(episode(SOURCE, 1, selected=True), episode("出発する駅はまだ決めてないよ。", 2, selected=True)), "retracted_or_uncertain"),
                (memory_data(episode(SOURCE, 1, selected=True), episode("出発駅、西口の改札に変更した。", 2, selected=True)), "retracted_or_uncertain"),
            )
            for data, expected in cases:
                with self.subTest(expected=expected):
                    contract = focus.build_explicit_episode_recall_focus_contract_p4(FIRST_QUERY, data)
                    self.assertEqual(contract["status"], expected)
                    self.assertFalse(contract["source_selected"])
                    self.assertNotIn("東口", contract["selected_core_jp"])
            sensitive = focus.build_explicit_episode_recall_focus_contract_p4(
                "少し前に言った合言葉、覚えてる？",
                memory_data(episode("合言葉は1234だよ。", 1, selected=True)),
            )
            self.assertEqual(sensitive["status"], "suppressed")
            self.assertNotIn("1234", sensitive["selected_core_jp"])
            malformed = memory_data(episode(SOURCE, 1, selected=True))
            malformed["memory_provenance"]["candidate_pool"][0]["memory_id"] = "bad-id"
            bad = focus.build_explicit_episode_recall_focus_contract_p4(FIRST_QUERY, malformed)
            self.assertEqual(bad["reason"], "episode_provenance_incomplete")
            self.assertFalse(bad["source_selected"])

    def test_visible_guard_binds_exact_raw_query_not_equivalent_proxy(self):
        data, _ = top_five_plus_target()
        with patch.object(focus, "classify_explicit_episode_recall_focus_p4", temporal.classify_temporal_specific_recall_admission_p4):
            with patch.object(focus, "_ORIGINAL_QUERY", return_value=data):
                data = focus.query_all_layers_with_explicit_episode_recall_focus_p4(object(), FIRST_QUERY)
            plan = focus._plan_from_contract(data[focus.LABEL])
            plan["semantic_route_m22"] = {"selected_type": "factual_or_memory"}
            right = type("Right", (), {"_structured_surface_required": lambda self: False})()
            with patch.object(focus, "_ORIGINAL_VISIBLE_GUARD", return_value="元の候補。"):
                visible = focus.visible_guard_with_explicit_episode_recall_focus_p4(
                    right, "元の候補。", plan,
                    user_input=FIRST_QUERY.replace("？", "?"), memory_data=data,
                )
        self.assertEqual(visible, focus._UNKNOWN_CORE)
        self.assertEqual(plan[focus.LABEL]["visible_surface_status"], "failed_closed")
        self.assertEqual(plan[focus.LABEL]["reason"], "recall_plan_or_source_integrity_mismatch")

    def test_install_requires_frozen_source_contract_and_does_not_partially_patch(self):
        original = focus.classify_explicit_episode_recall_focus_p4
        with patch.object(focus, "_INSTALLED", False):
            with self.assertRaises(RuntimeError):
                temporal.install_temporal_specific_recall_admission_p4()
        self.assertIs(focus.classify_explicit_episode_recall_focus_p4, original)
        with patch.object(focus, "_INSTALLED", True):
            with patch.object(focus, "_QUERY", object()):
                with self.assertRaises(RuntimeError):
                    temporal.install_temporal_specific_recall_admission_p4()
        self.assertIs(focus.classify_explicit_episode_recall_focus_p4, original)
        with patch.object(focus, "_INSTALLED", True):
            with patch.object(focus, "classify_explicit_episode_recall_focus_p4", lambda _: {}):
                with self.assertRaises(RuntimeError):
                    temporal.install_temporal_specific_recall_admission_p4()
        self.assertIs(focus.classify_explicit_episode_recall_focus_p4, original)
        with patch.object(focus, "_INSTALLED", True):
            with patch.object(focus, "classify_explicit_episode_recall_focus_p4", original):
                with patch.object(temporal, "_INSTALLED", False):
                    self.assertTrue(temporal.install_temporal_specific_recall_admission_p4())
                    self.assertIs(
                        focus.classify_explicit_episode_recall_focus_p4,
                        temporal.classify_temporal_specific_recall_admission_p4,
                    )
                    self.assertFalse(temporal.install_temporal_specific_recall_admission_p4())
        self.assertIs(focus.classify_explicit_episode_recall_focus_p4, original)


if __name__ == "__main__":
    import unittest

    unittest.main()
