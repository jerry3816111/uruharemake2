import hashlib
import json
import unittest
from copy import deepcopy
from pathlib import Path

import uruha_compositional_multilingual_pragmatic_eval_m36 as evaluator
from uruha_pragmatic_annotation_integrity_m36 import validate_annotation_rows_m36


ROOT = Path(__file__).resolve().parent
DATASET = ROOT / "datasets/m36_compositional_multilingual_pragmatic_reserve_v1.json"
PROTOCOL = ROOT / "research/m36_compositional_multilingual_pragmatic_protocol.json"
EXPECTED_DATASET_SHA256 = "c9e0b2418a7ad616ee9ac62683d92332f7520d73c5e3c39b395fc6d4eeb0011f"
EXPECTED_PROTOCOL_SHA256 = "d83861b8656f4dea068ae5b303ee1ae0fffb178a90f72ccbd98914c370703f5a"


class CompositionalMultilingualPragmaticEvaluationM36Tests(unittest.TestCase):
    def test_reserve_hash_structure_disjointness_and_annotations(self):
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
        self.assertTrue(validation["annotation_integrity"]["passed"])
        self.assertEqual(validation["annotation_integrity"]["error_count"], 0)

    def test_post_seal_annotation_corruption_is_rejected(self):
        dataset = json.loads(DATASET.read_text(encoding="utf-8"))
        corrupted = deepcopy(dataset["cases"])
        contradicted = next(
            row for row in corrupted if row["expected_feedback_outcome"] == "contradicted"
        )
        contradicted["expected_feedback_policy"] = "not_scored"
        contradicted["feedback_policy_scoring"] = "not_scored"
        validation = validate_annotation_rows_m36(corrupted)
        self.assertFalse(validation["passed"])
        self.assertTrue(
            any("contradiction_feedback_policy_must_be_scored" in item for item in validation["errors"])
        )

    def test_summary_separates_policy_and_surface_and_applies_all_gates(self):
        dataset = json.loads(DATASET.read_text(encoding="utf-8"))
        protocol = json.loads(PROTOCOL.read_text(encoding="utf-8"))
        annotation = validate_annotation_rows_m36(dataset["cases"])
        pair_baseline_policy = {}
        rows = []
        for case in dataset["cases"]:
            pair_baseline_policy.setdefault(case["pair_id"], case["expected_current_policy"])
            current = {}
            feedback = {}
            for condition in evaluator.m35.CONDITIONS:
                current_policy = (
                    pair_baseline_policy[case["pair_id"]
                    ] if condition == "baseline" else case["expected_current_policy"]
                )
                current[condition] = {
                    "selected_policy": current_policy,
                    "surface_proxy_match": current_policy == case["expected_current_policy"],
                    "visible_japanese": True,
                    "transport_error": None,
                    "parsed": True,
                    "prompt_eval_count": 1400,
                    "eval_count": 24,
                    "latency_seconds": 1.0,
                    "reply": "テスト用の自然な日本語。",
                }
                feedback[condition] = {
                    "selected_policy": (
                        case["expected_feedback_policy"]
                        if case["feedback_policy_scoring"] == "scored"
                        else "not_applicable"
                    ),
                    "surface_proxy_match": (
                        True if case["feedback_policy_scoring"] == "scored" else None
                    ),
                    "visible_japanese": True,
                    "transport_error": None,
                    "parsed": True,
                    "prompt_eval_count": 1400,
                    "eval_count": 24,
                    "latency_seconds": 1.0,
                    "reply": "テスト用の自然な日本語。",
                }
            rows.append(
                {
                    "case_id": case["case_id"],
                    "pair_id": case["pair_id"],
                    "expected_current_policy": case["expected_current_policy"],
                    "expected_feedback_outcome": case["expected_feedback_outcome"],
                    "expected_feedback_policy": case["expected_feedback_policy"],
                    "feedback_policy_scoring": case["feedback_policy_scoring"],
                    "m34_current_policy": case["expected_current_policy"],
                    "m34_feedback_outcome": case["expected_feedback_outcome"],
                    "m34_revision_replacement": (
                        case["expected_feedback_policy"]
                        if case["feedback_policy_scoring"] == "scored"
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
            rows,
            protocol["frozen_success_gates"],
            annotation,
        )
        self.assertEqual(metrics["system_current_policy_accuracy"], 1.0)
        self.assertEqual(metrics["system_current_surface_proxy_match_rate"], 1.0)
        self.assertEqual(metrics["system_feedback_surface_proxy_match_rate"], 1.0)
        self.assertEqual(metrics["feedback_policy_scored_case_count"], 6)
        self.assertTrue(all(gates.values()), gates)


if __name__ == "__main__":
    unittest.main()
