import hashlib
import json
import unittest
from pathlib import Path

import uruha_source_semantic_atom_eval_m33 as evaluator


ROOT = Path(__file__).resolve().parent
DATASET = ROOT / "datasets/m33_source_anchored_semantic_atom_reserve_v1.json"
EXPECTED_SHA256 = "b86025e70692c9bfe46aaa5e984968c6c4fe279fa24ce9104ab95644177f022c"


class SourceSemanticAtomEvalM33Tests(unittest.TestCase):
    def test_reserve_hash_balance_and_preimplementation_seal(self):
        raw = DATASET.read_bytes()
        payload = json.loads(raw)
        cases = payload["cases"]

        self.assertEqual(hashlib.sha256(raw).hexdigest(), EXPECTED_SHA256)
        self.assertEqual(payload["status"], "sealed_before_m33_implementation")
        self.assertEqual(len(cases), 15)
        for language in ("zh", "en", "ja"):
            self.assertEqual(sum(row["language"] == language for row in cases), 5)
            self.assertEqual(
                sum(row["language"] == language and row["authority_expected"] for row in cases),
                4,
            )
        self.assertEqual(sum(not row["authority_expected"] for row in cases), 3)

    def test_every_valid_case_declares_source_atom_and_surface_requirements(self):
        cases = json.loads(DATASET.read_text(encoding="utf-8"))["cases"]
        for case in cases:
            if not case["authority_expected"]:
                continue
            self.assertGreaterEqual(len(case["required_atom_types"]), 4)
            self.assertGreaterEqual(len(case["required_japanese_groups"]), 4)
            self.assertEqual(
                {row["label"] for row in case["required_japanese_groups"]},
                set(case["required_atom_types"]) - {"negation", "limitation", "event"}
                | {
                    row["label"]
                    for row in case["required_japanese_groups"]
                    if row["label"] in {"negation", "limitation", "event"}
                },
            )

    def test_summary_applies_m33_specific_frozen_gates(self):
        rows = []
        for language in ("zh", "en", "ja"):
            is_negation = language == "zh"
            rows.append(
                {
                    "case_id": f"{language}-valid",
                    "language": language,
                    "category": (
                        "negated_object_quantity"
                        if is_negation
                        else "change_weekday"
                    ),
                    "candidate_context": "fresh_session",
                    "authority_expected": True,
                    "outcome": "faithful_authority",
                    "expected_polarity": "negated" if is_negation else "affirmed",
                    "observed_polarity": "negated" if is_negation else "affirmed",
                    "raw_dialogue_persisted": False,
                    "model_response_raw_persisted": False,
                    "total_seconds": 1.0,
                    "source_atom_trace_complete": True,
                    "unresolved_source_conflict_authority": False,
                    "final_authority_source": "m33",
                    "m33_source_conflict_detected": False,
                }
            )
        rows.append(
            {
                "case_id": "incomplete",
                "language": "en",
                "category": "incomplete",
                "candidate_context": "fresh_session",
                "authority_expected": False,
                "outcome": "true_abstention",
                "expected_polarity": "unknown",
                "observed_polarity": "unknown",
                "raw_dialogue_persisted": False,
                "model_response_raw_persisted": False,
                "total_seconds": 0.0,
                "source_atom_trace_complete": True,
                "unresolved_source_conflict_authority": False,
                "final_authority_source": "none",
                "m33_source_conflict_detected": False,
            }
        )
        gates = {
            "overall_faithful_valid_rate_min": 1.0,
            "per_language_faithful_valid_rate_min": 1.0,
            "false_authority_valid_rate_max": 0.0,
            "false_reject_valid_rate_max": 0.0,
            "unsafe_incomplete_authority_count_max": 0,
            "negation_polarity_accuracy_min": 1.0,
            "unsupported_addition_authority_count_max": 0,
            "median_total_seconds_max": 2.0,
            "p95_total_seconds_max": 2.0,
            "raw_dialogue_persisted_count_max": 0,
            "model_response_raw_persisted_count_max": 0,
            "fresh_session_faithful_valid_rate_min": 1.0,
            "direct_japanese_faithful_valid_rate_min": 1.0,
            "change_operator_faithful_rate_min": 1.0,
            "negated_or_limited_quantity_faithful_rate_min": 0.0,
            "required_source_atom_trace_coverage_min": 1.0,
            "source_conflict_authority_count_max": 0,
        }

        metrics, gate_results, decision = evaluator.summarize(rows, gates)

        self.assertEqual(decision, "pass_all_frozen_gates")
        self.assertEqual(metrics["required_source_atom_trace_coverage"], 1.0)
        self.assertTrue(all(gate_results.values()))


if __name__ == "__main__":
    unittest.main()
