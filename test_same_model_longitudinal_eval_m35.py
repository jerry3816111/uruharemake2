import hashlib
import json
import unittest
from pathlib import Path

import uruha_same_model_longitudinal_eval_m35 as evaluator


ROOT = Path(__file__).resolve().parent
DATASET = ROOT / "datasets/m35_same_model_longitudinal_pragmatic_reserve_v1.json"
PROTOCOL = ROOT / "research/m35_same_model_longitudinal_pragmatic_protocol.json"
EXPECTED_DATASET_SHA256 = "5ab3fcd8a1dbbe0b5a036499e8cd1425b1812620076b61007a1e1359cf0b299f"


class _CharacterTokenizer:
    def encode(self, text, add_special_tokens=False):
        del add_special_tokens
        return list(str(text))


class SameModelLongitudinalEvaluationM35Tests(unittest.TestCase):
    def test_reserve_hash_balance_and_counterfactual_pairs(self):
        raw = DATASET.read_bytes()
        dataset = json.loads(raw)
        protocol = json.loads(PROTOCOL.read_text(encoding="utf-8"))
        validation = evaluator.validate_reserve(dataset, protocol)

        self.assertEqual(hashlib.sha256(raw).hexdigest(), EXPECTED_DATASET_SHA256)
        self.assertTrue(validation["passed"], validation["errors"])
        self.assertEqual(validation["case_count"], 12)
        self.assertEqual(validation["pair_count"], 6)
        self.assertEqual(validation["language_counts"], {"zh": 4, "en": 4, "ja": 4})

    def test_prompt_padding_is_exact_and_keeps_final_instruction_last(self):
        tokenizer = _CharacterTokenizer()
        prompt = evaluator.build_prompt(
            "same input",
            "ユーザー: same input",
            evaluator._baseline_packet("current"),
            "current",
        )
        target = len(prompt) + 17
        padded = evaluator.pad_prompt_to_exact_tokens(prompt, tokenizer, target)

        self.assertEqual(len(padded), target)
        self.assertTrue(padded.endswith("JSON:"))
        self.assertIn("__M35_PADDING__", padded)

    def test_parser_rejects_invalid_policy_and_keeps_visible_reply_separate(self):
        valid = evaluator.parse_model_output(
            '{"selected_policy":"listen_presence","reply":"そのまま話して。"}'
        )
        invalid = evaluator.parse_model_output(
            '{"selected_policy":"mind_reading","reply":"全部分かる。"}'
        )

        self.assertTrue(valid["parsed"])
        self.assertEqual(valid["selected_policy"], "listen_presence")
        self.assertFalse(invalid["parsed"])
        self.assertIn("invalid_policy", invalid["parse_error"])

    def test_summary_applies_same_model_advantage_and_cost_gates(self):
        dataset = json.loads(DATASET.read_text(encoding="utf-8"))
        protocol = json.loads(PROTOCOL.read_text(encoding="utf-8"))
        surface_reply = {
            "playful_tease": "また脳内会議かよ。",
            "solve_regulation": "まず一個だけメモに書こ。",
            "listen_presence": "そのまま話して。",
            "share_arousal": "うちも一緒にいる。",
        }
        pair_baseline_policy = {}
        rows = []
        for case in dataset["cases"]:
            pair_baseline_policy.setdefault(
                case["pair_id"], case["expected_current_policy"]
            )
            current = {}
            feedback = {}
            for condition in evaluator.CONDITIONS:
                current_policy = (
                    pair_baseline_policy[case["pair_id"]]
                    if condition == "baseline"
                    else case["expected_current_policy"]
                )
                current[condition] = {
                    "selected_policy": current_policy,
                    "surface_proxy_match": (
                        current_policy == case["expected_current_policy"]
                    ),
                    "visible_japanese": True,
                    "transport_error": None,
                    "parsed": True,
                    "prompt_eval_count": 1400,
                    "eval_count": 28,
                    "latency_seconds": 1.0,
                    "reply": surface_reply[case["expected_current_policy"]],
                }
                feedback[condition] = {
                    "selected_policy": case["expected_feedback_policy"],
                    "visible_japanese": True,
                    "transport_error": None,
                    "parsed": True,
                    "prompt_eval_count": 1400,
                    "eval_count": 24,
                    "latency_seconds": 1.0,
                    "reply": "ん、分かった。",
                }
            rows.append(
                {
                    "case_id": case["case_id"],
                    "pair_id": case["pair_id"],
                    "expected_current_policy": case["expected_current_policy"],
                    "expected_feedback_outcome": case["expected_feedback_outcome"],
                    "expected_feedback_policy": case["expected_feedback_policy"],
                    "m34_current_policy": case["expected_current_policy"],
                    "m34_feedback_outcome": case["expected_feedback_outcome"],
                    "m34_revision_replacement": (
                        case["expected_feedback_policy"]
                        if case["expected_feedback_outcome"] == "contradicted"
                        else None
                    ),
                    "m34_original_evidence_rewritten": False,
                    "current": current,
                    "feedback": feedback,
                    "current_token_balance": {"gate_passed": True},
                    "feedback_token_balance": {"gate_passed": True},
                    "unverified_mental_fact_write_count": 0,
                    "raw_dialogue_persisted": False,
                }
            )

        metrics, gates = evaluator.summarize(
            rows, protocol["frozen_success_gates"]
        )

        self.assertEqual(metrics["baseline_current_policy_accuracy"], 0.5)
        self.assertEqual(metrics["system_current_policy_accuracy"], 1.0)
        self.assertEqual(metrics["system_pair_divergence_rate"], 1.0)
        self.assertEqual(metrics["baseline_pair_policy_invariance_rate"], 1.0)
        self.assertTrue(all(gates.values()), gates)


if __name__ == "__main__":
    unittest.main()
