import copy
import unittest
from unittest.mock import patch

from analyze_longmemeval_evidence_ledger_heldout import (
    condition_value,
    strict_failure_layer,
    validate_report,
)
from run_longmemeval_evidence_ledger_development import CONDITIONS
from run_longmemeval_evidence_ledger_heldout import SCOPE
from run_longmemeval_retrieval_benchmark import canonical_sha256


def _condition(correct):
    return {
        "strict_answer_support": correct,
        "local_judge": {"label": correct},
        "response": "5" if correct else "4",
    }


class LongMemEvalEvidenceLedgerHeldoutAnalysisTest(unittest.TestCase):
    def test_failure_layer_localizes_answer_realization(self):
        ledger = _condition(False)
        ledger.update(
            {
                "notes": [
                    {
                        "evidence": {
                            "facts": [{"quote": "The current count is 5."}]
                        }
                    }
                ],
                "ledger": {
                    "events": [{"source_quote": "The current count is 5."}]
                },
            }
        )
        row = {
            "question": "How many are there now?",
            "answer": "5",
            "all_gold_sessions_retrieved": True,
            "conditions": {"versioned_ledger": ledger},
        }

        failure = strict_failure_layer(row)

        self.assertEqual(
            failure["layer"],
            "answer_realization_missing_gold_support",
        )

    def test_condition_value_keeps_scorers_separate(self):
        condition = {
            "strict_answer_support": False,
            "local_judge": {"label": True},
        }

        self.assertFalse(condition_value(condition, "strict_answer_support"))
        self.assertTrue(condition_value(condition, "local_judge"))

    @patch(
        "analyze_longmemeval_evidence_ledger_heldout.file_sha256",
        return_value="runner-sha",
    )
    def test_integrity_rejects_tampered_results(self, _sha):
        results = [
            {
                "question_id": f"q{index}",
                "conditions": {condition: _condition(True) for condition in CONDITIONS},
            }
            for index in range(54)
        ]
        report = {
            "scope": SCOPE,
            "complete": True,
            "status": "complete",
            "results": results,
            "results_sha256": canonical_sha256(results),
            "completed_question_count": 54,
            "data_boundary": {
                "completed_question_count": 54,
                "completed_question_ids_sha256": canonical_sha256(
                    [row["question_id"] for row in results]
                ),
                "candidate_cache_contains_gold_answers": False,
            },
            "frozen_evidence": {
                "heldout_implementation_evidence": {
                    "heldout_runner_sha256": "runner-sha"
                }
            },
            "decision": {"authorize_runtime_change": False},
        }
        tampered = copy.deepcopy(report)
        tampered["results"][0]["conditions"]["versioned_ledger"][
            "response"
        ] = "changed"

        with self.assertRaisesRegex(ValueError, "payload SHA"):
            validate_report(tampered)


if __name__ == "__main__":
    unittest.main()
