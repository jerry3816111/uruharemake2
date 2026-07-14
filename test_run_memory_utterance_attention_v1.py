import unittest

import run_memory_utterance_attention_v1 as runner


class RunMemoryUtteranceAttentionV1Test(unittest.TestCase):
    def test_frozen_protocol_loads_and_hashes_match(self):
        protocol, dataset, dataset_path = runner.load_protocol()
        self.assertTrue(dataset_path.exists())
        self.assertEqual(len(dataset["cases"]), 36)
        self.assertEqual(protocol["dataset"]["official_benchmark_items_used"], 0)
        self.assertFalse(protocol["research_boundary"]["runtime_change_authorized"])

    def test_span_metric_normalizes_number_words_and_hyphens(self):
        self.assertTrue(runner._span_present("eleven", "The answer is 11."))
        self.assertTrue(
            runner._span_present("thirty-five minutes", "It now takes 35 minutes.")
        )
        self.assertFalse(runner._span_present("three cups", "It is one cup."))

    def test_relation_metric_requires_explicit_direction_or_polarity(self):
        self.assertTrue(runner._relation_hit("yes", "Yes — a road bike."))
        self.assertTrue(runner._relation_hit("decrease", "It decreased from 3 to 1."))
        self.assertTrue(runner._relation_hit("decrease", "The trip is shorter now."))
        self.assertFalse(runner._relation_hit("decrease", "It changed from 3 to 1."))

    def test_score_localizes_evidence_and_answer_realization(self):
        case = {
            "gold": {
                "attention_quotes": [
                    "I counted the plants.",
                    "There are eleven now.",
                ],
                "answer_spans": ["eleven"],
                "relation": "none",
            }
        }
        note = {
            "selected_context": "User: I counted the plants.\nUser: There are eleven now.",
            "schema_parse_ok": True,
            "quote_grounded": True,
            "evidence": {
                "facts": [
                    {
                        "source_role": "user",
                        "quote": "There are eleven now.",
                        "attribute": "count",
                    }
                ]
            },
        }
        ledger = {"schema_parse_ok": True, "grounded": True}

        passed = runner.score_condition(case, note, ledger, "There are 11.")
        lost = runner.score_condition(case, note, ledger, "I remember counting them.")

        self.assertEqual(passed["gold_evidence_quote_recall"], 1.0)
        self.assertTrue(passed["semantic_case_pass"])
        self.assertEqual(lost["gold_evidence_quote_recall"], 1.0)
        self.assertFalse(lost["required_answer_span_hit"])

    def test_mcnemar_and_bootstrap_are_paired(self):
        control = [False, True, False, True]
        treatment = [True, True, False, False]
        result = runner.mcnemar_exact(control, treatment)
        interval = runner.bootstrap_delta_ci(control, treatment, seed=7, samples=1000)

        self.assertEqual(result["wins"], 1)
        self.assertEqual(result["losses"], 1)
        self.assertEqual(result["p_value"], 1.0)
        self.assertLessEqual(interval[0], 0.0)
        self.assertGreaterEqual(interval[1], 0.0)

    def test_generation_totals_cover_each_condition_cost(self):
        totals = runner.generation_totals(
            {"latency_seconds": 1.2, "prompt_tokens": 10, "completion_tokens": 2},
            {"latency_seconds": 0.8, "prompt_tokens": 5, "completion_tokens": 1},
            None,
        )
        self.assertEqual(totals["latency_seconds"], 2.0)
        self.assertEqual(totals["prompt_tokens"], 15)
        self.assertEqual(totals["completion_tokens"], 3)


if __name__ == "__main__":
    unittest.main()
