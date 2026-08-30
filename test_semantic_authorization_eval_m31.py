import json
import unittest
from pathlib import Path

import uruha_semantic_authorization_eval_m31 as evaluator


ROOT = Path(__file__).resolve().parent


class SemanticAuthorizationEvaluationM31Tests(unittest.TestCase):
    def test_sealed_reserve_hash_count_and_language_balance(self):
        protocol, dataset, _protocol_path, dataset_path = (
            evaluator.load_dataset_protocol(
                evaluator.DEFAULT_RESERVE_PROTOCOL,
                "reserve",
            )
        )
        cases = dataset["cases"]

        self.assertEqual(
            evaluator._sha256(dataset_path),
            protocol["reserve"]["sha256"],
        )
        self.assertEqual(len(cases), 12)
        self.assertEqual(
            {language: sum(row["language"] == language for row in cases)
             for language in ("zh", "en", "ja")},
            {"zh": 4, "en": 4, "ja": 4},
        )
        self.assertEqual(sum(row["authority_expected"] for row in cases), 9)

    def test_summary_distinguishes_false_authority_reject_and_abstention(self):
        rows = [
            self._row("zh", True, "faithful_authority", "affirmed", True, True),
            self._row("en", True, "false_authority", "negated", False, True),
            self._row("ja", True, "false_reject", "affirmed", True, False),
            self._row("zh", False, "true_abstention", "unknown", True, False),
        ]
        gates = json.loads(
            evaluator.DEFAULT_RESERVE_PROTOCOL.read_text(encoding="utf-8")
        )["frozen_success_gates"]

        metrics, gate_results = evaluator.summarize(rows, gates)

        self.assertEqual(metrics["overall_faithful_valid_rate"], 0.3333)
        self.assertEqual(metrics["false_authority_valid_rate"], 0.3333)
        self.assertEqual(metrics["false_reject_valid_rate"], 0.3333)
        self.assertEqual(metrics["unsafe_incomplete_authority_count"], 0)
        self.assertFalse(gate_results["overall_faithful_valid_rate_min"])

    @staticmethod
    def _row(language, expected, outcome, polarity, polarity_passed, authority):
        return {
            "language": language,
            "authority_expected": expected,
            "outcome": outcome,
            "expected_polarity": polarity,
            "polarity_passed": polarity_passed,
            "surface_authority": authority,
            "authorization_checks": {"unsupported_addition_absent": True},
            "total_seconds": 1.0,
            "raw_dialogue_persisted": False,
            "model_response_raw_persisted": False,
        }


if __name__ == "__main__":
    unittest.main()
