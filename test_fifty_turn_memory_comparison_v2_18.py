import json
import tempfile
import unittest
from pathlib import Path

import run_v2_18_fifty_turn_memory_comparison as v218


class FiftyTurnMemoryComparisonDesignTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.case = v218.load_json(v218.CASE_PATH)
        cls.prereg = v218.load_json(v218.PREREG_PATH)

    def test_frozen_design_has_exactly_fifty_turns_and_sources_leave_recent_window(self):
        result = v218.validate_design(self.case, self.prereg)
        self.assertTrue(result["passed"], result["errors"])
        self.assertEqual(result["turn_count"], 50)
        self.assertEqual(result["checkpoint_turns"], [25, 26, 48, 49, 50])
        self.assertGreaterEqual(result["relational_distractor_count"], 4)

    def test_profile_parser_sees_seed_and_removes_corrected_old_value(self):
        import uruha_brain_mac as brain

        manager = brain.MemoryManager.__new__(brain.MemoryManager)
        seed = next(row for row in self.case["turns"] if row["turn"] == 1)
        correction = next(row for row in self.case["turns"] if row["turn"] == 26)
        self.assertIn(("favorite", "coffee"), manager._extract_profile_facts(seed["user"]))
        correction_facts = manager._extract_profile_facts(correction["user"])
        self.assertIn(("dislike", "coffee"), correction_facts)
        self.assertIn(("favorite", "chamomile tea"), correction_facts)

    def test_recent_control_abstention_is_safe_but_not_recall_success(self):
        turn = next(row for row in self.case["turns"] if row["turn"] == 25)
        row = {
            "condition": "plain_recent",
            "reply": "そこは今の履歴だけじゃ覚えてない。",
            "history_turns_supplied": list(range(17, 25)),
            "visible_contract": {"pass": True},
        }
        score = v218._score_condition(row, turn, self.case)
        self.assertFalse(score["expected_current_value_hit"])
        self.assertFalse(score["source_grounded_current_value_hit"])
        self.assertTrue(score["epistemic_safe"])
        self.assertFalse(score["task_pass"])

    def test_correct_string_without_source_is_not_grounded_recall(self):
        turn = next(row for row in self.case["turns"] if row["turn"] == 48)
        row = {
            "condition": "plain_recent",
            "reply": "カモミールティーだろ。",
            "history_turns_supplied": list(range(40, 48)),
            "visible_contract": {"pass": True},
        }
        score = v218._score_condition(row, turn, self.case)
        self.assertTrue(score["expected_current_value_hit"])
        self.assertFalse(score["source_grounded_current_value_hit"])
        self.assertFalse(score["epistemic_safe"])

    def test_system_trace_plus_current_value_is_grounded_recall(self):
        turn = next(row for row in self.case["turns"] if row["turn"] == 48)
        row = {
            "condition": "uruha_memory",
            "reply": "カモミールティーって言ってただろ。",
            "passed_target_rows": [{"text": "favorites=chamomile tea"}],
            "visible_contract": {"pass": True},
        }
        score = v218._score_condition(row, turn, self.case)
        self.assertTrue(score["source_grounded_current_value_hit"])
        self.assertTrue(score["task_pass"])
        self.assertFalse(score["stale_value_revival"])

    def test_old_value_with_negation_is_not_stale_revival(self):
        turn = next(row for row in self.case["turns"] if row["turn"] == 49)
        row = {
            "condition": "uruha_memory",
            "reply": "コーヒーはもう本命じゃない。カモミールティーだろ。",
            "passed_target_rows": [{"text": "dislikes=coffee"}],
            "visible_contract": {"pass": True},
        }
        score = v218._score_condition(row, turn, self.case)
        self.assertFalse(score["stale_value_revival"])
        self.assertTrue(score["old_value_explicitly_negated"])
        self.assertTrue(score["task_pass"])

    def test_relational_false_value_assertion_is_detected(self):
        turn = next(row for row in self.case["turns"] if row["turn"] == 50)
        row = {
            "condition": "plain_full",
            "reply": "メロンソーダが一番好きって言ってた。",
            "history_turns_supplied": list(range(1, 50)),
            "visible_contract": {"pass": True},
        }
        score = v218._score_condition(row, turn, self.case)
        self.assertTrue(score["false_memory_assertion"])
        self.assertFalse(score["task_pass"])

    def test_summary_does_not_call_full_context_match_superior_reasoning(self):
        comparisons = []
        roles = ["delayed_recall", "explicit_correction", "corrected_recall", "withdrawal_probe", "false_memory_control"]
        for index, role in enumerate(roles, start=1):
            conditions = {}
            for condition in v218.CONDITIONS:
                grounded = condition != "plain_recent" and role in v218.PRIMARY_RECALL_ROLES
                score = {
                    "expected_current_value_hit": condition != "plain_recent" or role not in v218.PRIMARY_RECALL_ROLES,
                    "source_grounded_current_value_hit": grounded,
                    "task_pass": condition != "plain_recent" or role not in v218.PRIMARY_RECALL_ROLES,
                    "epistemic_safe": True,
                    "stale_value_revival": False,
                    "false_memory_assertion": False,
                    "visible_japanese_contract_pass": True,
                }
                conditions[condition] = {
                    "role": role,
                    "score": score,
                    "source_trace_available": condition == "uruha_memory",
                    "compute": {"model_call_count": 1, "prompt_tokens": 10, "completion_tokens": 2},
                    "elapsed_seconds": 1.0,
                }
            comparisons.append({"conditions": conditions})
        summary = v218.summarize(comparisons, self.prereg, True, {}, 24)
        self.assertTrue(summary["bounded_recent_context_advantage_supported"])
        self.assertTrue(summary["full_context_llm_matches_system"])
        self.assertFalse(summary["answer_quality_superiority_over_full_context_llm_supported"])
        self.assertFalse(summary["general_llm_superiority_supported"])
        self.assertIn("persistence/traceability", summary["interpretation"])

    def test_blind_packet_hides_condition_names_and_has_blank_ratings(self):
        comparisons = []
        for turn in (25, 48):
            comparisons.append(
                {
                    "turn": turn,
                    "role": "delayed_recall",
                    "user": "question",
                    "recent_context": [],
                    "conditions": {
                        "uruha_memory": {"reply": "system"},
                        "plain_recent": {"reply": "baseline"},
                    },
                }
            )
        packet, key = v218.build_blind_packet(comparisons)
        serialized = json.dumps(packet, ensure_ascii=False)
        self.assertNotIn("uruha_memory", serialized)
        self.assertNotIn("plain_recent", serialized)
        self.assertEqual(packet["status"], "rating_instrument_not_human_result")
        self.assertEqual(len(key["cases"]), 2)


if __name__ == "__main__":
    unittest.main()
