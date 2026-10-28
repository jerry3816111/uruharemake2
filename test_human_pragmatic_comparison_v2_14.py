import ast
import json
import unittest
from pathlib import Path
from unittest import mock

import human_pragmatic_comparison_v2_14 as comparison
import human_pragmatic_human_eval_v2_14 as human_eval


class HumanPragmaticComparisonV214HarnessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.preregistration = comparison.load_json(comparison.DEVELOPMENT_CONFIG)
        cls.development_cases = cls.preregistration["development_cases"]

    def test_exposed_cases_are_development_not_holdout(self):
        self.assertIn("development", self.preregistration["status"])
        self.assertNotIn("holdout_cases", self.preregistration)
        self.assertEqual(len(self.development_cases), 4)
        self.assertIn("not holdout", self.preregistration["claim_scope"])

    def test_same_model_persona_decoding_and_output_contract_are_shared(self):
        contract = self.preregistration["model_contract"]
        self.assertEqual(contract["model"], "qwen3.5:9b")
        self.assertEqual(contract["temperature"], 0)
        self.assertEqual(contract["num_predict"], 96)
        self.assertTrue(contract["same_persona_expression_prompt_required"])
        self.assertTrue(contract["same_output_token_budget_required"])
        self.assertEqual(set(comparison.CONDITIONS), {"baseline", "system"})

    def test_visible_reply_contract_rejects_chinese_polite_and_non_uruha_surface(self):
        clean = comparison.visible_reply_contract("それ、断り方の方で詰まってたんだな。")
        chinese = comparison.visible_reply_contract("静不下来吗？最近是不是太累了。")
        polite = comparison.visible_reply_contract("そこが気になっているんですね。")
        quoted = comparison.visible_reply_contract("「分かった。」")

        self.assertTrue(all(clean.values()))
        self.assertFalse(chinese["no_foreign_or_nonstandard_language"])
        self.assertFalse(polite["no_polite_register"])
        self.assertFalse(quoted["no_quote_wrapper"])
        self.assertEqual(comparison.normalize_visible_reply("  「分かった。」  "), "分かった。")

    def test_system_packet_has_traceable_state_while_baseline_does_not(self):
        case = self.development_cases[0]
        pair = comparison.build_matched_prompt_pair(
            [case["turns"][0]], [], [], tokenizer=None
        )
        system = pair["system"]
        baseline = pair["baseline"]

        self.assertIn("uruha_v2_14_system_condition_packet", system)
        self.assertIn("persistent_other_model", system)
        self.assertIn("fact_memory_write_allowed_for_inferences", system)
        self.assertIn("uruha_v2_14_baseline_condition_packet", baseline)
        self.assertIn('"structured_hypothesis":null', baseline)
        self.assertNotIn("typed_calibration", baseline)

    def test_real_token_balance_uses_fixed_equal_preflight_calls_and_fails_closed(self):
        case = self.development_cases[0]
        pair = comparison.build_matched_prompt_pair(
            [case["turns"][0]], [], [], tokenizer=None
        )
        raw = {condition: pair[condition] for condition in comparison.CONDITIONS}
        raw_zero_counts = {
            condition: raw[condition].count(" 0")
            for condition in comparison.CONDITIONS
        }

        def fake_ollama(_endpoint, _contract, prompt, num_predict_override=None):
            condition = (
                "system"
                if "uruha_v2_14_system_condition_packet" in prompt
                else "baseline"
            )
            base = 900 if condition == "system" else 700
            token_padding = (
                (prompt.count(" 0") - raw_zero_counts[condition]) * 2
                + max(0, prompt.count("。") - raw[condition].count("。"))
            )
            return {
                "reply": "破棄",
                "transport_error": None,
                "prompt_eval_count": base + token_padding,
                "eval_count": 1,
            }

        with mock.patch.object(comparison, "ollama_chat", side_effect=fake_ollama):
            balanced = comparison.balance_prompt_pair_with_ollama(
                pair,
                "http://127.0.0.1:11434",
                self.preregistration["model_contract"],
                max_rounds=4,
            )

        for condition in comparison.CONDITIONS:
            self.assertLess(
                balanced[condition].rfind(" 0"),
                balanced[condition].rfind(comparison.FINAL_REPLY_RULE),
            )

        self.assertTrue(balanced["gate_passed"])
        self.assertEqual(balanced["final_delta"], 0)
        self.assertEqual(balanced["preflight_call_count"], 8)
        self.assertTrue(
            all(row["preflight_output_discarded"] for row in balanced["rounds"])
        )

    def test_blind_packet_hides_conditions_and_key_is_separate(self):
        rows = []
        for condition in comparison.CONDITIONS:
            rows.append(
                {
                    "case_id": "case-1",
                    "turn_index": 1,
                    "condition": condition,
                    "reply": "日本語の返事。",
                    "dialogue_context": "ユーザー: テスト",
                }
            )
        packet, key = comparison.build_blind_packet(rows, seed=7)
        rendered_packet = json.dumps(packet, ensure_ascii=False)

        self.assertNotIn('"baseline"', rendered_packet)
        self.assertNotIn('"system"', rendered_packet)
        self.assertIn("context_A", packet["items"][0])
        self.assertIn("context_B", packet["items"][0])
        self.assertTrue(packet["condition_labels_hidden"])
        self.assertEqual({key["items"][0]["A"], key["items"][0]["B"]}, set(comparison.CONDITIONS))

    def test_proxy_is_explicitly_not_human_preference_evidence(self):
        proxy = comparison.proxy_score(
            "断りづらいだけかもな。違ったら言って。",
            {
                "turn_1_expected_japanese_anchors_any": ["断"],
                "forbidden_overclaim_anchors": ["絶対"],
            },
            1,
        )
        self.assertTrue(proxy["proxy_pass"])
        self.assertIn("not evidence of human", self.preregistration["proxy_evidence_boundary"])

    def test_holdout_validator_requires_balanced_three_turn_source_disjoint_design(self):
        cases = []
        for language in ("zh", "en", "ja"):
            for index in range(6):
                cases.append(
                    {
                        "case_id": f"{language}-{index}",
                        "language": language,
                        "phenomenon": "test",
                        "turns": [
                            f"{language} turn {index} a",
                            f"{language} turn {index} b",
                            f"{language} turn {index} c",
                        ],
                        "expected_trace_outcome_sequence": ["a", "b", "c"],
                        "evaluation_focus_by_turn": [[], [], []],
                    }
                )
        validation = comparison.validate_holdout_design(
            {"source_disjoint_from_development_cases": True, "cases": cases}
        )

        self.assertTrue(validation["passed"])
        self.assertEqual(validation["language_counts"], {"zh": 6, "en": 6, "ja": 6})
        self.assertFalse(validation["exact_gold_replies_present"])

    def test_harness_has_no_production_memory_or_training_path(self):
        source = Path(comparison.__file__).read_text(encoding="utf-8")
        tree = ast.parse(source)
        calls = {
            node.func.attr
            for node in ast.walk(tree)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
        }
        self.assertNotIn("save_episode", calls)
        self.assertNotIn("fit", calls)
        self.assertNotIn("backward", calls)
        self.assertNotIn("uruha_memory_mac_db", source)


class HumanPragmaticHumanEvalV214Tests(unittest.TestCase):
    def setUp(self):
        self.packet = {
            "items": [
                {"item_id": "blind-001"},
                {"item_id": "blind-002"},
            ]
        }
        self.key = {
            "items": [
                {"item_id": "blind-001", "A": "system", "B": "baseline"},
                {"item_id": "blind-002", "A": "baseline", "B": "system"},
            ]
        }

    def _ratings(self, rater_count):
        rows = []
        for rater_index in range(rater_count):
            for item in self.key["items"]:
                system_label = "A" if item["A"] == "system" else "B"
                baseline_label = "B" if system_label == "A" else "A"
                scores = {}
                for dimension in human_eval.DIMENSIONS:
                    scores[dimension] = {
                        system_label: 5,
                        baseline_label: 2,
                    }
                rows.append(
                    {
                        "rater_id": f"rater-{rater_index + 1}",
                        "item_id": item["item_id"],
                        "scores": scores,
                        "preference": system_label,
                    }
                )
        return rows

    def test_template_requires_paired_A_B_scores(self):
        template = human_eval.rating_template(self.packet, "rater-1")
        self.assertEqual(
            set(template[0]["scores"][human_eval.DIMENSIONS[0]]),
            {"A", "B"},
        )

    def test_fewer_than_three_raters_is_pilot_only(self):
        result = human_eval.analyze(self.packet, self.key, self._ratings(1))
        self.assertEqual(result["status"], "pilot_only")
        self.assertFalse(result["claim_authorized"])
        self.assertEqual(result["validation"]["missing_rater_count"], 2)

    def test_three_complete_raters_can_pass_only_the_frozen_condition_claim(self):
        result = human_eval.analyze(self.packet, self.key, self._ratings(3))
        self.assertEqual(result["status"], "formal_human_result")
        self.assertTrue(result["claim_authorized"])
        self.assertEqual(result["system_decisive_preference_rate"], 1.0)
        self.assertGreater(
            result["system_preference_cluster_bootstrap"]["ci95"][0],
            0.5,
        )
        self.assertIn("only this frozen", result["claim_scope"])


if __name__ == "__main__":
    unittest.main()
