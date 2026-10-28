import unittest

import desired_response_comparison_v2_16 as comparison
from uruha_reference_person_equation import load_case_bundle


class _WhitespaceTokenizer:
    def encode(self, text, add_special_tokens=False):
        del add_special_tokens
        return str(text).split()


class DesiredResponseComparisonV216Tests(unittest.TestCase):
    def setUp(self):
        self.bundle = load_case_bundle()
        self.prereg = comparison.load_json(comparison.PREREG_PATH)

    def test_design_freezes_same_input_and_all_six_policy_targets(self):
        result = comparison.validate_design(self.bundle, self.prereg)
        self.assertTrue(result["passed"], result["errors"])
        self.assertEqual(result["case_count"], 6)
        self.assertEqual(len(set(result["policies"])), 6)

    def test_matched_pair_differs_only_by_explicit_equation_packet_and_is_padded(self):
        case = self.bundle["cases"][0]
        tokenizer = _WhitespaceTokenizer()
        # The fake tokenizer is deliberately simple; use a budget above both raw prompts.
        pair = comparison.build_prompt_pair(
            case,
            self.bundle["shared_current_input"],
            tokenizer,
            360,
        )

        self.assertEqual(pair["local_token_counts"], {"baseline": 360, "system": 360})
        self.assertIn("direct_same_model_generation", pair["baseline"])
        self.assertIn("desired_response_equation", pair["system"])
        self.assertIn("selected_policy", pair["system"])
        self.assertIn(self.bundle["shared_current_input"], pair["baseline"])
        self.assertIn(self.bundle["shared_current_input"], pair["system"])

    def test_proxy_is_narrow_and_explicitly_not_human_preference(self):
        case = next(row for row in self.bundle["cases"] if row["gold_policy"] == "playful_tease")
        passed = comparison.policy_proxy("朝から脳内だけ二十四時間営業かよ。止まる気ゼロじゃん。", case)
        failed = comparison.policy_proxy("それは多動症に決まってる。", case)

        self.assertTrue(passed["proxy_pass"])
        self.assertFalse(failed["proxy_pass"])
        self.assertTrue(failed["forbidden_anchor_hit"])
        self.assertIn("not desired-response human preference", passed["evidence_boundary"])

    def test_summary_keeps_proxy_and_human_claim_separate(self):
        rows = []
        for case in self.bundle["cases"]:
            for condition, proxy_pass in (("baseline", False), ("system", True)):
                rows.append(
                    {
                        "case_id": case["case_id"],
                        "condition": condition,
                        "prompt_eval_count": 2050 if condition == "baseline" else 2051,
                        "transport_error": None,
                        "proxy": {"proxy_pass": proxy_pass, "visible_contract_pass": True},
                    }
                )
        summary = comparison.summarize(rows, self.prereg)

        self.assertEqual(summary["pair_count"], 6)
        self.assertEqual(summary["token_gate_pair_count"], 6)
        self.assertEqual(summary["baseline_proxy_pass_count"], 0)
        self.assertEqual(summary["system_proxy_pass_count"], 6)
        self.assertTrue(summary["preregistered_proxy_success"])
        self.assertIn("no target-user", summary["evidence_boundary"])

    def test_summary_enforces_system_forbidden_policy_gate(self):
        rows = []
        for condition in ("baseline", "system"):
            rows.append(
                {
                    "case_id": "case-a",
                    "condition": condition,
                    "prompt_eval_count": 100,
                    "transport_error": None,
                    "proxy": {
                        "proxy_pass": condition == "system",
                        "visible_contract_pass": True,
                        "forbidden_anchor_hit": condition == "system",
                    },
                }
            )
        prereg = self.prereg.copy()
        prereg["fresh_generation_success_criteria"] = {
            **self.prereg["fresh_generation_success_criteria"],
            "system_desired_policy_proxy_minus_baseline_min": 1,
        }
        summary = comparison.summarize(rows, prereg)
        self.assertEqual(summary["system_forbidden_policy_violation_count"], 1)
        self.assertFalse(summary["preregistered_proxy_success"])

    def test_blind_packet_hides_condition_and_contains_blank_human_ratings(self):
        rows = []
        for case in self.bundle["cases"]:
            for condition in ("baseline", "system"):
                rows.append(
                    {
                        "case_id": case["case_id"],
                        "condition": condition,
                        "label": case["label"],
                        "context_history": case["context_history"],
                        "current_input": self.bundle["shared_current_input"],
                        "reply": f"{condition} reply",
                    }
                )
        packet, key = comparison.build_blind_packet(rows)

        self.assertTrue(packet["condition_labels_hidden"])
        self.assertNotIn("condition", packet["cases"][0])
        self.assertIsNone(packet["cases"][0]["ratings"]["felt_understanding_A_1_to_5"])
        self.assertEqual(len(key["cases"]), 6)
        self.assertEqual({key["cases"][0]["A"], key["cases"][0]["B"]}, {"baseline", "system"})

    def test_harness_has_no_production_or_training_path(self):
        source = comparison.Path(comparison.__file__).read_text(encoding="utf-8")
        self.assertIn('"production_memory_write_count": 0', source)
        self.assertNotIn("brain.remember", source)
        self.assertNotIn("optimizer.step", source)


if __name__ == "__main__":
    unittest.main()
