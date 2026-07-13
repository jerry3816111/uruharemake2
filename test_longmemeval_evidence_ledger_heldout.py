import copy
import datetime
import unittest
from unittest.mock import patch

from run_longmemeval_evidence_ledger_development import generate_condition
from run_longmemeval_evidence_ledger_heldout import (
    SCOPE,
    build_report,
    paired_condition_analysis,
    validate_resume_checkpoint,
)


def _condition(correct, *, structured=False, ledger=False):
    result = {
        "response": "correct" if correct else "wrong",
        "strict_answer_support": correct,
        "query_latency_seconds": 1.0,
        "end_to_end_latency_seconds": 1.0,
        "local_judge": {"label": correct},
    }
    if structured:
        result.update(
            {
                "question_frame": {"answer_type": "text"},
                "notes": [
                    {
                        "structured_parse_ok": True,
                        "schema_parse_ok": True,
                        "quote_grounded": True,
                        "extracted_fact_count": 1,
                        "accepted_grounded_fact_count": 1,
                    }
                ],
            }
        )
    if ledger:
        result.update(
            {
                "ledger": {"events": [], "omitted_grounded_facts": []},
                "ledger_schema_parse_ok": True,
                "ledger_grounded": True,
            }
        )
    return result


def _result(question_id, direct, notes, ledger):
    return {
        "question_id": question_id,
        "all_gold_sessions_retrieved": True,
        "conditions": {
            "direct_chronological": _condition(direct),
            "grounded_notes": _condition(notes, structured=True),
            "versioned_ledger": _condition(
                ledger,
                structured=True,
                ledger=True,
            ),
        },
    }


class LongMemEvalEvidenceLedgerHeldoutTest(unittest.TestCase):
    def test_gold_answer_is_not_in_direct_generation_prompt(self):
        prompts = []

        def chat(prompt, **_kwargs):
            prompts.append(prompt)
            return {"text": "reader response", "latency_seconds": 0.1}

        generate_condition(
            {
                "question": "What is current?",
                "question_date": "2026-01-01",
                "answer": "UNIQUE_GOLD_VALUE",
            },
            [],
            "direct_chronological",
            chat,
        )

        self.assertEqual(len(prompts), 1)
        self.assertNotIn("UNIQUE_GOLD_VALUE", prompts[0])

    def test_paired_analysis_uses_same_questions(self):
        results = [
            _result("q1", False, True, True),
            _result("q2", True, True, False),
            _result("q3", False, False, True),
        ]

        analysis = paired_condition_analysis(
            results,
            "direct_chronological",
            "versioned_ledger",
            "strict_answer_support",
        )

        self.assertEqual(analysis["treatment_wins"], 2)
        self.assertEqual(analysis["treatment_losses"], 1)
        self.assertEqual(analysis["net_treatment_wins"], 1)
        self.assertAlmostEqual(analysis["paired_rate_delta"], 1 / 3)

    @patch(
        "run_longmemeval_evidence_ledger_heldout.current_heldout_implementation_evidence",
        return_value={"runner": "frozen"},
    )
    @patch(
        "run_longmemeval_evidence_ledger_heldout.file_sha256",
        return_value="a" * 64,
    )
    def test_report_never_authorizes_runtime_change(self, _sha, _implementation):
        rows = [{"question_id": f"q{index}"} for index in range(54)]
        results = [
            _result(
                f"q{index}",
                direct=index >= 12,
                notes=True,
                ledger=True,
            )
            for index in range(54)
        ]
        development = {
            "scope": "longmemeval_evidence_ledger_development_only_v3",
            "results_sha256": "b" * 64,
            "implementation_evidence": {"frozen": True},
        }
        config = {
            "model": "qwen",
            "model_evidence": {"digest": "d"},
            "seed": 1,
            "top_k": 5,
            "reference_time": datetime.datetime(2026, 1, 1),
        }

        report = build_report(
            rows,
            results,
            {"sha256": "c" * 64},
            {"schema": "cache", "contains_gold_answers": False},
            development,
            config,
            config["model_evidence"],
        )

        self.assertTrue(report["complete"])
        self.assertTrue(report["decision"]["supports_evidence_ledger_hypothesis"])
        self.assertFalse(report["decision"]["authorize_runtime_change"])

    def test_resume_rejects_changed_frozen_binding(self):
        rows = [{"question_id": "q1"}, {"question_id": "q2"}]
        binding = {
            "data_boundary": {"dataset_sha256": "data"},
            "frozen_evidence": {"model": "qwen", "seed": 1},
        }
        checkpoint = {
            "scope": SCOPE,
            "complete": False,
            "results": [_result("q1", True, True, True)],
            "frozen_evidence": {"model": "qwen", "seed": 2},
            "data_boundary": {"dataset_sha256": "data"},
        }
        from run_longmemeval_retrieval_benchmark import canonical_sha256

        checkpoint["results_sha256"] = canonical_sha256(checkpoint["results"])

        with self.assertRaisesRegex(ValueError, "seed"):
            validate_resume_checkpoint(checkpoint, rows, binding)

    def test_resume_requires_results_to_be_population_prefix(self):
        rows = [{"question_id": "q1"}, {"question_id": "q2"}]
        binding = {
            "data_boundary": {"dataset_sha256": "data"},
            "frozen_evidence": {"model": "qwen"},
        }
        checkpoint = {
            "scope": SCOPE,
            "complete": False,
            "results": [_result("q2", True, True, True)],
            "frozen_evidence": copy.deepcopy(binding["frozen_evidence"]),
            "data_boundary": copy.deepcopy(binding["data_boundary"]),
        }
        from run_longmemeval_retrieval_benchmark import canonical_sha256

        checkpoint["results_sha256"] = canonical_sha256(checkpoint["results"])

        with self.assertRaisesRegex(ValueError, "population prefix"):
            validate_resume_checkpoint(checkpoint, rows, binding)

    def test_cli_does_not_offer_item_selection(self):
        from run_longmemeval_evidence_ledger_heldout import main

        with self.assertRaises(SystemExit):
            main(["--max-items", "1"])


if __name__ == "__main__":
    unittest.main()
