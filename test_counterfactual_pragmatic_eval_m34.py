import hashlib
import json
import unittest
from pathlib import Path

import uruha_counterfactual_pragmatic_eval_m34 as evaluator


ROOT = Path(__file__).resolve().parent
DATASET = ROOT / "datasets/m34_counterfactual_pragmatic_branch_reserve_v1.json"
PROTOCOL = ROOT / "research/m34_counterfactual_pragmatic_branch_reserve_protocol.json"
EXPECTED_DATASET_SHA256 = "e5b8bc9a8e219639d751fa78009ad6db201735b951c81053ac028fc2cbbc6d26"
EXPECTED_PROTOCOL_SHA256 = "39ecbfe63e63a7287c2c08c9184f287d9e030726d1248da72c172e335bf31829"


class CounterfactualPragmaticEvaluationM34Tests(unittest.TestCase):
    def test_reserve_and_protocol_remain_preimplementation_sealed(self):
        dataset_raw = DATASET.read_bytes()
        protocol_raw = PROTOCOL.read_bytes()
        dataset = json.loads(dataset_raw)
        protocol = json.loads(protocol_raw)

        self.assertEqual(hashlib.sha256(dataset_raw).hexdigest(), EXPECTED_DATASET_SHA256)
        self.assertEqual(hashlib.sha256(protocol_raw).hexdigest(), EXPECTED_PROTOCOL_SHA256)
        self.assertEqual(dataset["status"], "sealed_before_m34_implementation")
        self.assertEqual(protocol["status"], "sealed_before_m34_implementation")
        self.assertEqual(len(dataset["cases"]), 8)

    def test_pairs_hold_current_utterance_and_language_constant(self):
        cases = json.loads(DATASET.read_text(encoding="utf-8"))["cases"]
        pairs = {}
        for case in cases:
            pairs.setdefault(case["pair_id"], []).append(case)

        self.assertEqual(len(pairs), 4)
        self.assertEqual({case["language"] for case in cases}, {"zh", "en", "ja"})
        for group in pairs.values():
            self.assertEqual(len(group), 2)
            self.assertEqual(len({row["current_input"] for row in group}), 1)
            self.assertEqual(len({row["language"] for row in group}), 1)
            self.assertEqual(len({row["expected_policy"] for row in group}), 2)

    def test_summary_applies_every_frozen_gate(self):
        dataset = json.loads(DATASET.read_text(encoding="utf-8"))
        protocol = json.loads(PROTOCOL.read_text(encoding="utf-8"))
        rows = []
        for case in dataset["cases"]:
            rows.append(
                {
                    "case_id": case["case_id"],
                    "pair_id": case["pair_id"],
                    "current_input_digest": hashlib.sha256(
                        case["current_input"].encode("utf-8")
                    ).hexdigest()[:16],
                    "literal_observation_digest": hashlib.sha256(
                        case["current_input"].encode("utf-8")
                    ).hexdigest()[:16],
                    "selected_policy": case["expected_policy"],
                    "selected_mode": case["expected_mode"],
                    "bounded_alternative_policy": "ask_clarify",
                    "candidate_count": 2,
                    "context_evidence_traced": True,
                    "observable_prediction_traced": True,
                    "previous_outcome": case["expected_previous_outcome"],
                    "replacement_policy": case["expected_replacement_policy"],
                    "original_evidence_rewritten": False,
                    "current_surface_status": "matched",
                    "current_visible_japanese": True,
                    "feedback_visible_japanese": True,
                    "unverified_mental_fact_write_count": 0,
                    "raw_dialogue_persisted": False,
                    "model_response_raw_persisted": False,
                    "elapsed_seconds": 0.2,
                }
            )

        metrics, gates = evaluator.summarize(
            rows,
            dataset["cases"],
            protocol["frozen_success_gates"],
        )

        self.assertEqual(metrics["counterfactual_pair_divergence_rate"], 1.0)
        self.assertEqual(metrics["previous_outcome_verification_accuracy"], 1.0)
        self.assertEqual(metrics["contradiction_replacement_accuracy"], 1.0)
        self.assertTrue(all(gates.values()))


if __name__ == "__main__":
    unittest.main()
