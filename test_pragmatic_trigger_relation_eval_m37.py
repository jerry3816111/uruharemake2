import hashlib
import json
import unittest
from pathlib import Path

import uruha_pragmatic_trigger_relation_eval_m37 as evaluator


ROOT = Path(__file__).resolve().parent
DATASET = ROOT / "datasets/m37_pragmatic_trigger_relation_reserve_v1_1.json"
PROTOCOL = ROOT / "research/m37_pragmatic_trigger_relation_protocol_v1_1.json"
EXPECTED_DATASET_SHA256 = (
    "0ef035f6f131191776c4d5eaceac58f91ddd30856804b22b731770ac97b150de"
)
EXPECTED_PROTOCOL_SHA256 = (
    "a14c1f567de8503fdb3a6ca7e114ddee6e857ceab2786a5cfa47d7d6d75d584f"
)


class PragmaticTriggerRelationEvaluationM37Tests(unittest.TestCase):
    def test_sealed_reserve_validation_is_source_disjoint_and_preclassified(self):
        dataset_raw = DATASET.read_bytes()
        protocol_raw = PROTOCOL.read_bytes()
        dataset = json.loads(dataset_raw)
        protocol = json.loads(protocol_raw)
        validation = evaluator.validate_reserve(dataset, protocol)

        self.assertEqual(hashlib.sha256(dataset_raw).hexdigest(), EXPECTED_DATASET_SHA256)
        self.assertEqual(hashlib.sha256(protocol_raw).hexdigest(), EXPECTED_PROTOCOL_SHA256)
        self.assertTrue(validation["passed"], validation["errors"])
        self.assertEqual(validation["case_count"], 12)
        self.assertEqual(validation["pair_count"], 6)
        self.assertEqual(validation["language_counts"], {"zh": 4, "en": 4, "ja": 4})
        self.assertTrue(
            all(row["candidate_status"] == "candidate_ready" for row in validation["annotation_audits"])
        )

    def test_system_packet_exposes_only_typed_verified_relation(self):
        packet = evaluator._system_packet(
            {
                "authoritative": True,
                "match": {
                    "status": "matched_verified_trigger_relation",
                    "trigger_predicate": "task_stall",
                    "response_policy": "listen_presence",
                    "match_kind": "typed_predicate_morphology_or_bounded_paraphrase",
                    "relation_id": "m37-safe",
                },
            }
        )

        self.assertTrue(packet["must_execute_policy"])
        self.assertEqual(packet["authoritative_policy"], "listen_presence")
        self.assertFalse(packet["raw_history_available"])
        self.assertFalse(packet["private_mental_state_truth_available"])
        self.assertNotIn("seed_input", packet)

    def test_prompt_applies_the_same_surface_act_contract_before_final_anchor(self):
        baseline = evaluator.build_prompt_m37(
            "same current",
            "ユーザー: same current",
            evaluator.m35._baseline_packet("current"),
        )
        system = evaluator.build_prompt_m37(
            "same current",
            "ユーザー: same current",
            evaluator._system_packet(
                {
                    "authoritative": True,
                    "match": {
                        "status": "matched_verified_trigger_relation",
                        "trigger_predicate": "task_stall",
                        "response_policy": "listen_presence",
                    },
                }
            ),
        )

        self.assertIn(evaluator.M37_SURFACE_VALIDATION_RULE, baseline)
        self.assertIn(evaluator.M37_SURFACE_VALIDATION_RULE, system)
        self.assertTrue(baseline.endswith("JSON:"))
        self.assertTrue(system.endswith("JSON:"))

    def test_summary_applies_mechanism_pair_surface_and_cost_gates(self):
        dataset = json.loads(DATASET.read_text(encoding="utf-8"))
        protocol = json.loads(PROTOCOL.read_text(encoding="utf-8"))
        proxy_replies = {
            "playful_tease": "また脳内会議かよ。",
            "solve_regulation": "まず一個だけメモに書こ。",
            "listen_presence": "直そうとしなくていいから、そのまま話して。",
            "share_arousal": "うちも一緒にいる。",
        }
        pair_baseline_policy = {}
        rows = []
        for case in dataset["cases"]:
            pair_baseline_policy.setdefault(
                case["pair_id"], case["expected_current_policy"]
            )
            current = {}
            for condition in evaluator.m35.CONDITIONS:
                policy = (
                    pair_baseline_policy[case["pair_id"]]
                    if condition == "baseline"
                    else case["expected_current_policy"]
                )
                current[condition] = {
                    "selected_policy": policy,
                    "surface_proxy_match": policy == case["expected_current_policy"],
                    "visible_japanese": True,
                    "transport_error": None,
                    "parsed": True,
                    "prompt_eval_count": 1000,
                    "eval_count": 20,
                    "latency_seconds": 1.0,
                    "reply": proxy_replies[policy],
                }
            rows.append(
                {
                    "case_id": case["case_id"],
                    "pair_id": case["pair_id"],
                    "expected_trigger_predicate": case["expected_trigger_predicate"],
                    "expected_current_policy": case["expected_current_policy"],
                    "relation_candidate": {
                        "status": "candidate_ready",
                        "trigger_predicate": case["expected_trigger_predicate"],
                        "response_policy": case["expected_current_policy"],
                    },
                    "relation_persistence": {
                        "status": "verified_relation_persisted",
                        "trigger_predicate": case["expected_trigger_predicate"],
                        "response_policy": case["expected_current_policy"],
                    },
                    "relation_current_match": {
                        "status": "matched_verified_trigger_relation",
                        "trigger_predicate": case["expected_trigger_predicate"],
                        "response_policy": case["expected_current_policy"],
                    },
                    "mechanism_selected_policy": case["expected_current_policy"],
                    "mechanism_authoritative": True,
                    "current": current,
                    "current_token_balance": {"gate_passed": True},
                    "unverified_mental_fact_write_count": 0,
                    "raw_dialogue_persisted": False,
                }
            )

        metrics, gates = evaluator.summarize(
            rows,
            protocol["frozen_success_gates"],
            reserve_validation_error_count=0,
        )

        self.assertEqual(metrics["baseline_current_policy_accuracy"], 0.5)
        self.assertEqual(metrics["system_current_policy_accuracy"], 1.0)
        self.assertEqual(metrics["system_minus_baseline_current_policy_accuracy"], 0.5)
        self.assertEqual(metrics["system_relation_candidate_accuracy"], 1.0)
        self.assertEqual(metrics["system_relation_persistence_accuracy"], 1.0)
        self.assertEqual(metrics["system_relation_current_match_accuracy"], 1.0)
        self.assertEqual(metrics["system_mechanism_current_policy_accuracy"], 1.0)
        self.assertEqual(metrics["system_pair_divergence_rate"], 1.0)
        self.assertEqual(metrics["baseline_pair_policy_invariance_rate"], 1.0)
        self.assertTrue(all(gates.values()), gates)

    def test_summary_fails_a_broken_relation_even_if_model_output_is_correct(self):
        protocol = json.loads(PROTOCOL.read_text(encoding="utf-8"))
        row = {
            "case_id": "broken",
            "pair_id": "broken-pair",
            "expected_trigger_predicate": "task_stall",
            "expected_current_policy": "solve_regulation",
            "relation_candidate": {
                "status": "candidate_ready",
                "trigger_predicate": "cognitive_overactivity",
                "response_policy": "solve_regulation",
            },
            "relation_persistence": {
                "status": "verified_relation_persisted",
                "trigger_predicate": "task_stall",
                "response_policy": "solve_regulation",
            },
            "relation_current_match": {
                "status": "matched_verified_trigger_relation",
                "trigger_predicate": "task_stall",
                "response_policy": "solve_regulation",
            },
            "mechanism_selected_policy": "solve_regulation",
            "mechanism_authoritative": True,
            "current": {
                condition: {
                    "selected_policy": "solve_regulation",
                    "surface_proxy_match": True,
                    "visible_japanese": True,
                    "transport_error": None,
                    "parsed": True,
                    "prompt_eval_count": 100,
                    "eval_count": 10,
                    "latency_seconds": 1.0,
                }
                for condition in evaluator.m35.CONDITIONS
            },
            "current_token_balance": {"gate_passed": True},
            "unverified_mental_fact_write_count": 0,
            "raw_dialogue_persisted": False,
        }
        metrics, gates = evaluator.summarize(
            [row],
            protocol["frozen_success_gates"],
            reserve_validation_error_count=0,
        )

        self.assertEqual(metrics["system_relation_candidate_accuracy"], 0.0)
        self.assertFalse(gates["system_relation_candidate_accuracy_min"])


if __name__ == "__main__":
    unittest.main()
