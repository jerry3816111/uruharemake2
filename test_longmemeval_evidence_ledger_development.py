import io
import json
import unittest
from unittest.mock import patch

from run_longmemeval_evidence_ledger_development import (
    CONDITIONS,
    build_report,
    exact_mcnemar_two_sided_p,
    generate_condition,
    generate_notes,
    inference_token_diagnostics,
    local_diagnostic_judge,
    ollama_model_evidence,
    official_style_judge_prompt,
    paired_binary_analysis,
    retrieval_conditioned_summary,
    summarize,
)


FRAME = {
    "subject": "user",
    "attribute": "count",
    "time_focus": "current",
    "operation": "count",
    "answer_type": "number",
    "evidence_requirements": ["explicit count"],
}
NOTE = {
    "session_id": "s1",
    "timestamp": "2024-01-01",
    "evidence": {"relevant": False, "facts": []},
    "schema_parse_ok": True,
    "quote_grounded": True,
    "structured_parse_ok": True,
}


def _condition(correct, *, structured=False, ledger=None, latency=1.0):
    result = {
        "response": "4" if correct else "3",
        "strict_answer_support": correct,
        "query_latency_seconds": latency,
        "end_to_end_latency_seconds": latency,
        "local_judge": {"label": correct},
    }
    if structured:
        result.update({"question_frame": FRAME, "notes": [NOTE]})
    if ledger is not None:
        result["ledger"] = ledger
        result["ledger_schema_parse_ok"] = True
        result["ledger_grounded"] = True
    return result


class LongMemEvalEvidenceLedgerDevelopmentTest(unittest.TestCase):
    def test_empty_response_is_never_sent_to_or_accepted_by_judge(self):
        calls = []

        def chat(*args, **kwargs):
            calls.append((args, kwargs))

        judged = local_diagnostic_judge("Question", "Answer", "  ", chat)

        self.assertFalse(judged["label"])
        self.assertEqual(judged["scoring_guard"], "empty_response")
        self.assertEqual(calls, [])

    def test_ollama_model_tag_is_bound_to_digest(self):
        payload = {
            "models": [
                {
                    "name": "qwen2.5:7b",
                    "digest": "abc123",
                    "size": 7,
                    "modified_at": "2026-07-01T00:00:00Z",
                }
            ]
        }
        with patch(
            "run_longmemeval_evidence_ledger_development.urllib.request.urlopen",
            return_value=io.BytesIO(json.dumps(payload).encode("utf-8")),
        ):
            evidence = ollama_model_evidence(
                "qwen2.5:7b", "http://localhost:11434/api/chat"
            )

        self.assertEqual(evidence["digest"], "abc123")

    def test_official_style_judge_prompt_is_scoring_only(self):
        prompt = official_style_judge_prompt("How many?", "4", "You have four.")

        self.assertIn("Correct Answer: 4", prompt)
        self.assertIn("Answer yes or no only", prompt)

    def test_shared_notes_do_not_trigger_extraction_again(self):
        row = {"question": "How many?", "question_date": "2024-01-02", "answer": "4"}
        notes = [
            {
                **NOTE,
                "evidence": {
                    "relevant": True,
                    "facts": [
                        {
                            "source_role": "user",
                            "quote": "I have four.",
                            "attribute": "count",
                        }
                    ],
                },
            }
        ]
        calls = []

        def chat(prompt, max_tokens=220, format_schema=None):
            calls.append(prompt)
            return {"text": "4", "latency_seconds": 0.1}

        result = generate_condition(
            row,
            [],
            "grounded_notes",
            chat,
            question_frame=FRAME,
            frame_generation={"latency_seconds": 0.1},
            shared_notes=notes,
        )

        self.assertEqual(len(calls), 1)
        self.assertTrue(result["strict_answer_support"])

    def test_invalid_question_frame_fails_closed_without_model_calls(self):
        calls = []

        def chat(*args, **kwargs):
            calls.append((args, kwargs))

        notes = generate_notes({}, [], None, chat)

        self.assertEqual(notes, [])
        self.assertEqual(calls, [])

    def test_evidence_note_with_fabricated_quote_fails_closed(self):
        def chat(*args, **kwargs):
            return {
                "text": json.dumps(
                    {
                        "relevant": True,
                        "facts": [
                            {
                                "source_role": "user",
                                "quote": "I own five bikes.",
                                "attribute": "count",
                            }
                        ],
                    }
                ),
                "latency_seconds": 0.1,
            }

        notes = generate_notes(
            {"question": "How many?", "question_date": "2024-01-02"},
            [
                {
                    "session_id": "s1",
                    "timestamp": "2024-01-01",
                    "text": "User: I own four bikes.",
                }
            ],
            FRAME,
            chat,
        )

        self.assertTrue(notes[0]["schema_parse_ok"])
        self.assertFalse(notes[0]["quote_grounded"])
        self.assertEqual(notes[0]["evidence"], {"relevant": False, "facts": []})
        self.assertTrue(notes[0]["structured_parse_ok"])
        self.assertEqual(notes[0]["rejected_ungrounded_fact_count"], 1)

    def test_empty_primary_note_can_use_one_focused_retry(self):
        calls = []

        def chat(*args, **kwargs):
            calls.append(args[0])
            if len(calls) == 1:
                payload = {"relevant": False, "facts": []}
            else:
                payload = {
                    "relevant": True,
                    "facts": [
                        {
                            "source_role": "user",
                            "quote": "My weekly tennis sessions with friends are at the local park.",
                            "attribute": "tennis frequency",
                        }
                    ],
                }
            return {"text": json.dumps(payload), "latency_seconds": 0.1}

        notes = generate_notes(
            {
                "question": "How often do I play tennis with friends at the local park?",
                "question_date": "2024-01-02",
            },
            [
                {
                    "session_id": "s1",
                    "timestamp": "2024-01-01",
                    "text": (
                        "User: I need new socks.\n"
                        "User: My weekly tennis sessions with friends are at the local park."
                    ),
                }
            ],
            {**FRAME, "subject": "tennis", "attribute": "tennis frequency"},
            chat,
        )

        self.assertEqual(len(calls), 2)
        self.assertTrue(notes[0]["attention_retry_attempted"])
        self.assertTrue(notes[0]["attention_retry_used"])
        self.assertEqual(notes[0]["accepted_grounded_fact_count"], 1)

    def test_summary_keeps_strict_and_local_judge_separate(self):
        results = [
            {
                "conditions": {
                    "direct_chronological": _condition(False),
                    "grounded_notes": _condition(True, structured=True),
                    "versioned_ledger": _condition(
                        True,
                        structured=True,
                        ledger={"schema": "uruha_memory_evidence_ledger_v3"},
                    ),
                }
            }
        ]

        summary = summarize(results)

        self.assertEqual(summary["direct_chronological"]["strict_answer_support_rate"], 0.0)
        self.assertEqual(summary["versioned_ledger"]["local_diagnostic_judge_rate"], 1.0)
        self.assertEqual(summary["versioned_ledger"]["ledger_parse_rate"], 1.0)

    def test_paired_analysis_reports_direction_and_exact_mcnemar(self):
        results = [
            {
                "conditions": {
                    "direct_chronological": _condition(False),
                    "versioned_ledger": _condition(True),
                }
            },
            {
                "conditions": {
                    "direct_chronological": _condition(True),
                    "versioned_ledger": _condition(True),
                }
            },
        ]

        paired = paired_binary_analysis(results, "strict_answer_support")

        self.assertEqual(paired["ledger_wins"], 1)
        self.assertEqual(paired["ledger_losses"], 0)
        self.assertEqual(paired["net_ledger_wins"], 1)
        self.assertEqual(exact_mcnemar_two_sided_p(1, 0), 1.0)

    def test_retrieval_conditioning_excludes_missing_gold_sessions(self):
        results = [
            {
                "all_gold_sessions_retrieved": True,
                "conditions": {
                    condition: _condition(True) for condition in CONDITIONS
                },
            },
            {
                "all_gold_sessions_retrieved": False,
                "conditions": {
                    condition: _condition(False) for condition in CONDITIONS
                },
            },
        ]

        conditioned = retrieval_conditioned_summary(results)

        self.assertEqual(conditioned["all_gold_sessions_retrieved_count"], 1)
        self.assertEqual(
            conditioned["condition_rates_when_evidence_available"][
                "versioned_ledger"
            ]["strict_answer_support_rate"],
            1.0,
        )

    def test_token_diagnostics_count_shared_extraction_once(self):
        generation = {"prompt_tokens": 100, "completion_tokens": 10}
        judge = {"label": True, "prompt_tokens": 20, "completion_tokens": 1}
        result = {
            "conditions": {
                "direct_chronological": {
                    "answer_generation": generation,
                    "local_judge": judge,
                },
                "grounded_notes": {
                    "frame_generation": generation,
                    "notes": [{"generation": generation}, {"generation": generation}],
                    "answer_generation": generation,
                    "local_judge": judge,
                },
                "versioned_ledger": {
                    "ledger_generation": generation,
                    "answer_generation": generation,
                    "local_judge": judge,
                },
            }
        }

        diagnostics = inference_token_diagnostics([result])

        self.assertEqual(diagnostics["stages"]["evidence_note"]["observed_call_count"], 2)
        self.assertEqual(diagnostics["observed_call_count"], 10)
        self.assertEqual(diagnostics["max_observed_total_tokens"], 110)

    @patch("run_longmemeval_evidence_ledger_development.file_sha256", return_value="a" * 64)
    def test_development_report_never_authorizes_runtime(self, _sha):
        rows = [{"question_id": "q1"}]
        results = [
            {
                "question_id": "q1",
                "conditions": {
                    "direct_chronological": _condition(False),
                    "grounded_notes": _condition(True, structured=True),
                    "versioned_ledger": _condition(
                        True,
                        structured=True,
                        ledger={"schema": "uruha_memory_evidence_ledger_v3"},
                    ),
                },
            }
        ]
        evidence = {"sha256": "b" * 64}

        baseline = {"generated_at": "2026-07-13T12:00:00+09:00"}
        report = build_report(
            rows,
            results,
            evidence,
            {},
            baseline,
            "qwen",
            1,
            5,
            1,
            {"name": "qwen", "digest": "d" * 64},
        )

        self.assertEqual(report["data_boundary"]["test_question_count_evaluated"], 0)
        self.assertTrue(report["decision"]["authorize_test_evaluation"])
        self.assertFalse(report["decision"]["authorize_runtime_change"])
        self.assertEqual(set(report["matched_control"]["conditions"]), set(CONDITIONS))
        self.assertEqual(report["matched_control"]["generation_options"]["num_ctx"], 32768)
        self.assertIn(
            "memory_runtime_module_sha256", report["implementation_evidence"]
        )

    @patch("run_longmemeval_evidence_ledger_development.file_sha256", return_value="a" * 64)
    def test_pilot_cannot_authorize_heldout_test(self, _sha):
        rows = [{"question_id": "q1"}]
        results = [
            {
                "question_id": "q1",
                "conditions": {
                    "direct_chronological": _condition(False),
                    "grounded_notes": _condition(True, structured=True),
                    "versioned_ledger": _condition(
                        True,
                        structured=True,
                        ledger={"schema": "uruha_memory_evidence_ledger_v3"},
                    ),
                },
            }
        ]

        report = build_report(
            rows,
            results,
            {"sha256": "b" * 64},
            {},
            {"generated_at": "2026-07-13T12:00:00+09:00"},
            "qwen",
            1,
            5,
            18,
            {"name": "qwen", "digest": "d" * 64},
        )

        self.assertFalse(report["data_boundary"]["development_population_complete"])
        self.assertFalse(report["decision"]["authorize_test_evaluation"])


if __name__ == "__main__":
    unittest.main()
